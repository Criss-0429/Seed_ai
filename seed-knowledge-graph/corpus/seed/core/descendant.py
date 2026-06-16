"""Isolated, deterministic descendant materialization.

S3 builds candidate artifacts from parent snapshots. It never executes a
descendant and never writes to the active runtime state.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .capabilities import validate_manifest
from .lineage import MutationCandidate
from .sandbox import static_audit


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class DescendantBuildError(ValueError):
    """Raised when a descendant cannot be materialized safely."""


class DescendantIntegrityError(DescendantBuildError):
    """Raised when a descendant artifact no longer matches its manifest."""


@dataclass(frozen=True)
class DescendantManifest:
    schema_version: str
    descendant_id: str
    mutation_id: str
    parent_version: str
    target_scope: list[str]
    proposal_type: str
    created_from_candidate_at: str
    files: dict[str, str]
    content_hash: str
    executable: bool = False
    active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DescendantBuilder:
    def __init__(self, descendants_root: Path, versions_dir: Path):
        self.descendants_root = Path(descendants_root)
        self.versions_dir = Path(versions_dir)
        self.descendants_root.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        candidate: MutationCandidate,
        proposal: dict[str, Any],
    ) -> tuple[Path, DescendantManifest]:
        candidate.validate()
        if candidate.status != "proposed":
            raise DescendantBuildError("only proposed candidates can be built")
        if not isinstance(proposal, dict):
            raise DescendantBuildError("proposal must be an object")
        _safe_component(candidate.parent_version, "parent_version")
        parent = self.versions_dir / candidate.parent_version
        if not parent.is_dir():
            raise DescendantBuildError(
                f"parent snapshot missing: {candidate.parent_version}")
        _safe_component(candidate.mutation_id, "mutation_id")
        final = self.descendants_root / candidate.mutation_id

        temp = Path(tempfile.mkdtemp(prefix=".build-", dir=self.descendants_root))
        try:
            runtime = temp / "runtime"
            shutil.copytree(parent, runtime)
            _write_json(temp / "candidate.json", candidate.to_dict())
            _write_json(temp / "proposal.json", proposal)
            self._apply_proposal(runtime, proposal, candidate)
            files = _file_hashes(temp)
            manifest = DescendantManifest(
                schema_version="seed.descendant.v1",
                descendant_id=candidate.mutation_id,
                mutation_id=candidate.mutation_id,
                parent_version=candidate.parent_version,
                target_scope=list(candidate.target_scope),
                proposal_type=str(proposal.get("type") or "unknown"),
                created_from_candidate_at=candidate.created_at,
                files=files,
                content_hash=_content_hash(files),
            )
            _write_json(temp / "descendant_manifest.json", manifest.to_dict())

            if final.exists():
                existing = self.verify(final)
                if existing.content_hash != manifest.content_hash:
                    raise DescendantBuildError(
                        f"existing descendant differs: {candidate.mutation_id}")
                return final, existing
            temp.replace(final)
            return final, manifest
        finally:
            if temp.exists():
                shutil.rmtree(temp, ignore_errors=True)

    def verify(self, descendant_dir: Path) -> DescendantManifest:
        root = Path(descendant_dir)
        manifest_path = root / "descendant_manifest.json"
        if not manifest_path.is_file():
            raise DescendantIntegrityError("descendant manifest missing")
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = DescendantManifest(**raw)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise DescendantIntegrityError("invalid descendant manifest") from exc
        actual_files = _file_hashes(root)
        if actual_files != manifest.files:
            raise DescendantIntegrityError("descendant file hashes differ")
        if _content_hash(actual_files) != manifest.content_hash:
            raise DescendantIntegrityError("descendant content hash differs")
        if manifest.executable or manifest.active:
            raise DescendantIntegrityError("S3 descendant cannot be executable or active")
        if root.name != manifest.descendant_id or manifest.descendant_id != manifest.mutation_id:
            raise DescendantIntegrityError("descendant identity differs")
        candidate = _load_json(root / "candidate.json")
        proposal = _load_json(root / "proposal.json")
        if (
            candidate.get("mutation_id") != manifest.mutation_id
            or candidate.get("parent_version") != manifest.parent_version
            or candidate.get("target_scope") != manifest.target_scope
            or candidate.get("created_at") != manifest.created_from_candidate_at
            or proposal.get("type") != manifest.proposal_type
        ):
            raise DescendantIntegrityError("descendant manifest contract differs")
        return manifest

    def _apply_proposal(
        self,
        runtime: Path,
        proposal: dict[str, Any],
        candidate: MutationCandidate,
    ) -> None:
        mtype = proposal.get("type")
        target = str(proposal.get("target") or "")
        diff = proposal.get("diff")
        if not isinstance(diff, dict):
            raise DescendantBuildError("proposal diff must be an object")

        if mtype == "trait_change":
            state = _load_json(runtime / "state" / "user_model.json")
            if not _apply_nested_value(state, target, diff.get("value", diff)):
                raise DescendantBuildError(f"trait target missing: {target}")
            _write_json(runtime / "state" / "user_model.json", state)
            return

        if mtype in ("ui_change", "persona_change"):
            state = _load_json(runtime / "state" / "ui_manifest.json")
            section = "persona" if mtype == "persona_change" else "theme"
            if section not in state or not isinstance(state[section], dict):
                raise DescendantBuildError(f"UI section missing: {section}")
            for key, value in diff.items():
                if key in state[section]:
                    state[section][key] = value
                elif mtype == "ui_change" and key == "widgets":
                    state["widgets"] = value
                else:
                    raise DescendantBuildError(f"UI target missing: {section}.{key}")
            _write_json(runtime / "state" / "ui_manifest.json", state)
            return

        if mtype == "policy_change":
            state = _load_json(runtime / "state" / "policy.json")
            state.setdefault("rules", []).append({
                **diff,
                "reason": candidate.reason,
                "added": candidate.created_at,
            })
            _write_json(runtime / "state" / "policy.json", state)
            return

        if mtype == "new_capability":
            manifest = dict(diff.get("manifest") or {})
            manifest.setdefault("origin", "generated")
            manifest.setdefault("reason", candidate.reason)
            errors = validate_manifest(manifest)
            if errors:
                raise DescendantBuildError(f"invalid capability manifest: {errors}")
            code = diff.get("code")
            if not isinstance(code, str) or not code.strip():
                raise DescendantBuildError("capability code missing")
            audit = static_audit(code, needs_network=bool(manifest.get("needs_network")))
            if not audit.passed:
                raise DescendantBuildError(
                    f"capability static audit failed: {audit.violations}")
            capability_id = str(manifest["capability_id"])
            _safe_component(capability_id, "capability_id")
            cap_dir = runtime / "capabilities" / capability_id
            cap_dir.mkdir(parents=True, exist_ok=False)
            _write_json(cap_dir / "manifest.json", manifest)
            (cap_dir / "tool.py").write_text(code, encoding="utf-8")
            _write_json(cap_dir / "AUDIT.json", {
                "passed": True,
                "violations": [],
                "executed": False,
                "source": "S3 static audit only",
            })
            return

        if mtype == "prune_capability":
            _safe_component(target, "capability target")
            cap_dir = runtime / "capabilities" / target
            if cap_dir.exists():
                shutil.rmtree(cap_dir)
            overlays = runtime / "overlays"
            pruned_path = overlays / "pruned_capabilities.json"
            pruned = _load_json(pruned_path, default={"capability_ids": []})
            if target not in pruned["capability_ids"]:
                pruned["capability_ids"].append(target)
                pruned["capability_ids"].sort()
            _write_json(pruned_path, pruned)
            return

        raise DescendantBuildError(f"unsupported proposal type: {mtype}")


def _safe_component(value: str, field_name: str) -> None:
    if not _SAFE_COMPONENT.fullmatch(value):
        raise DescendantBuildError(f"unsafe {field_name}: {value!r}")


def _load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        if default is not None:
            return dict(default)
        raise DescendantBuildError(f"required parent file missing: {path.name}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DescendantBuildError(f"invalid parent JSON: {path.name}") from exc
    if not isinstance(data, dict):
        raise DescendantBuildError(f"parent JSON must be object: {path.name}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )


def _apply_nested_value(data: dict[str, Any], target: str, value: Any) -> bool:
    parts = target.split(".")
    if not parts or any(not part for part in parts):
        return False
    node: Any = data
    for part in parts[:-1]:
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    if not isinstance(node, dict) or parts[-1] not in node:
        return False
    node[parts[-1]] = value
    return True


def _file_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative == "descendant_manifest.json":
            continue
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _content_hash(files: dict[str, str]) -> str:
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
