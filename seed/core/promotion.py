"""Core-only shadow, contextual canary, promotion, and rollback authority.

S5 owns activation decisions. Generator, descendant builder, and evaluator can
provide evidence but cannot promote a candidate directly.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .descendant import DescendantBuilder, DescendantIntegrityError
from .evaluator import EvaluatorHarness
from .lineage import LineageError, LineageStore, MutationCandidate


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_OWNER_GATED_SCOPES = {
    "architecture", "core", "evaluator", "governance", "identity", "lineage",
    "permissions", "personality", "privacy", "recovery", "supervisor",
}
_PROMOTABLE_PROPOSAL_TYPES = {"trait_change", "policy_change", "prune_capability"}


class PromotionError(ValueError):
    """Raised when exposure, promotion, or rollback cannot proceed safely."""


class PromotionIntegrityError(PromotionError):
    """Raised when activation evidence or artifacts have been altered."""


@dataclass(frozen=True)
class PromotionPolicy:
    min_shadow_passes: int = 2
    min_canary_passes: int = 2
    default_canary_ttl_seconds: int = 3600

    def validate(self) -> None:
        if self.min_shadow_passes < 1 or self.min_canary_passes < 1:
            raise PromotionError("promotion pass thresholds must be positive")
        if self.default_canary_ttl_seconds < 1:
            raise PromotionError("canary ttl must be positive")


@dataclass(frozen=True)
class CanaryLease:
    schema_version: str
    mutation_id: str
    descendant_ref: str
    context_ids: list[str]
    created_at: float
    expires_at: float

    def validate(self) -> None:
        if self.schema_version != "seed.canary-lease.v1":
            raise PromotionError(f"unsupported canary lease schema: {self.schema_version}")
        _safe_component(self.mutation_id, "mutation_id")
        if not self.context_ids or not all(_nonempty(value) for value in self.context_ids):
            raise PromotionError("canary lease requires context ids")
        if len(set(self.context_ids)) != len(self.context_ids):
            raise PromotionError("canary context ids must be unique")
        if self.expires_at <= self.created_at:
            raise PromotionError("canary lease expiry must follow creation")

    def active_for(self, context_id: str, now: float | None = None) -> bool:
        self.validate()
        return context_id in self.context_ids and (now or time.time()) < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanaryLease":
        if not isinstance(data, dict):
            raise PromotionIntegrityError("canary lease must be an object")
        try:
            lease = cls(**data)
        except TypeError as exc:
            raise PromotionIntegrityError(f"invalid canary lease: {exc}") from exc
        lease.validate()
        return lease


class PromotionAuthority:
    AUTHORITY_ID = "seed-promotion-authority-v1"

    def __init__(
        self,
        lineage: LineageStore,
        descendants: DescendantBuilder,
        evaluator: EvaluatorHarness,
        state_dir: Path,
        capabilities_dir: Path,
        versions_dir: Path,
        active_root: Path,
        canary_leases_root: Path,
        policy: PromotionPolicy | None = None,
        on_runtime_changed: Callable[[], None] | None = None,
    ):
        self.lineage = lineage
        self.descendants = descendants
        self.evaluator = evaluator
        self.state_dir = Path(state_dir)
        self.capabilities_dir = Path(capabilities_dir)
        self.versions_dir = Path(versions_dir)
        self.active_root = Path(active_root)
        self.canary_leases_root = Path(canary_leases_root)
        self.policy = policy or PromotionPolicy()
        self.on_runtime_changed = on_runtime_changed
        self.policy.validate()
        self.active_root.mkdir(parents=True, exist_ok=True)
        self.canary_leases_root.mkdir(parents=True, exist_ok=True)

    def start_shadow(self, candidate: MutationCandidate) -> MutationCandidate:
        recorded = self._candidate(candidate.mutation_id)
        if recorded.status != "validating":
            raise PromotionError(f"shadow requires validating status, got: {recorded.status}")
        if self.lineage.latest_evaluation_outcome(
            recorded.mutation_id, EvaluatorHarness.EVALUATOR_ID
        ) != "pass":
            raise PromotionError("shadow requires latest independent evaluator pass")
        self._verify_descendant(recorded)
        recorded = self.lineage.transition(
            recorded, "shadow", reason="S5 shadow exposure opened"
        )
        self.lineage.record_exposure_start(
            recorded.mutation_id,
            "shadow",
            policy={"controls_real_effects": False},
        )
        return recorded

    def observe(
        self,
        mutation_id: str,
        phase: str,
        outcome: str,
        source: str,
        metrics: dict[str, Any] | None = None,
        blocking: bool = False,
        context_id: str = "",
    ) -> dict[str, Any]:
        candidate = self._candidate(mutation_id)
        if candidate.status != phase:
            raise PromotionError(
                f"{phase} observation requires {phase} status, got: {candidate.status}"
            )
        if phase == "canary":
            if not _nonempty(context_id):
                raise PromotionError("canary observation requires context_id")
            lease = self.lease(mutation_id)
            if lease is None or not lease.active_for(context_id):
                raise PromotionError("canary observation context has no active lease")
        return self.lineage.record_exposure_observation(
            mutation_id,
            phase,
            outcome,
            source,
            metrics=metrics,
            blocking=blocking,
            context_id=context_id,
        )

    def start_canary(
        self,
        candidate: MutationCandidate,
        context_ids: list[str],
        *,
        owner_approved: bool = False,
        ttl_seconds: int | None = None,
    ) -> CanaryLease:
        recorded = self._candidate(candidate.mutation_id)
        if recorded.status != "shadow":
            raise PromotionError(f"canary requires shadow status, got: {recorded.status}")
        blockers = self._exposure_blockers(recorded, "shadow", self.policy.min_shadow_passes)
        blockers.extend(self._owner_gate_blockers(recorded, owner_approved))
        if blockers:
            raise PromotionError(f"canary blocked: {', '.join(sorted(set(blockers)))}")
        self._verify_descendant(recorded)
        ttl = ttl_seconds or self.policy.default_canary_ttl_seconds
        if ttl < 1:
            raise PromotionError("canary ttl must be positive")
        now = time.time()
        lease = CanaryLease(
            schema_version="seed.canary-lease.v1",
            mutation_id=recorded.mutation_id,
            descendant_ref=self._descendant_ref(recorded),
            context_ids=sorted(set(context_ids)),
            created_at=now,
            expires_at=now + ttl,
        )
        lease.validate()
        path = self._lease_path(recorded.mutation_id)
        if path.exists():
            raise PromotionError(f"canary lease already exists: {recorded.mutation_id}")
        _atomic_create_json(path, lease.to_dict())
        try:
            recorded = self.lineage.transition(
                recorded, "canary", reason="S5 contextual canary opened"
            )
            self.lineage.record_exposure_start(
                recorded.mutation_id,
                "canary",
                policy={
                    "context_ids": lease.context_ids,
                    "expires_at": lease.expires_at,
                    "global_activation": False,
                    "owner_approved": bool(owner_approved),
                },
            )
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return lease

    def lease(self, mutation_id: str) -> CanaryLease | None:
        _safe_component(mutation_id, "mutation_id")
        path = self._lease_path(mutation_id)
        if not path.is_file():
            return None
        try:
            return CanaryLease.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            raise PromotionIntegrityError("unreadable canary lease") from exc

    def state_dir_for_context(self, context_id: str = "") -> Path:
        if not _nonempty(context_id):
            return self.state_dir
        matches: list[Path] = []
        for path in sorted(self.canary_leases_root.glob("*.json")):
            lease = self.lease(path.stem)
            if lease is None or not lease.active_for(context_id):
                continue
            candidate = self.lineage.candidate(lease.mutation_id)
            if candidate is None or candidate.status != "canary":
                continue
            descendant = self.descendants.descendants_root / lease.mutation_id
            self.descendants.verify(descendant)
            matches.append(descendant / "runtime" / "state")
        if len(matches) > 1:
            raise PromotionError(f"multiple active canary leases for context: {context_id}")
        return matches[0] if matches else self.state_dir

    def promotion_blockers(
        self,
        candidate: MutationCandidate,
        *,
        owner_approved: bool = False,
    ) -> list[str]:
        recorded = self._candidate(candidate.mutation_id)
        blockers: list[str] = []
        if recorded.status != "canary":
            blockers.append("canary_status_required")
        if self.lineage.latest_evaluation_outcome(
            recorded.mutation_id, EvaluatorHarness.EVALUATOR_ID
        ) != "pass":
            blockers.append("independent_evaluator_pass_missing")
        blockers.extend(self._exposure_blockers(
            recorded, "shadow", self.policy.min_shadow_passes
        ))
        blockers.extend(self._exposure_blockers(
            recorded, "canary", self.policy.min_canary_passes
        ))
        blockers.extend(self._owner_gate_blockers(recorded, owner_approved))
        proposal = self.lineage.proposal(recorded.mutation_id) or {}
        if proposal.get("type") not in _PROMOTABLE_PROPOSAL_TYPES:
            blockers.append("proposal_type_not_state_promotable")
        if recorded.rollback_plan != recorded.parent_version:
            blockers.append("rollback_plan_parent_mismatch")
        parent = self.versions_dir / recorded.parent_version
        if not (parent / "state").is_dir():
            blockers.append("rollback_parent_missing")
        try:
            self._verify_descendant(recorded)
        except PromotionError:
            blockers.append("descendant_integrity_failed")
        if (parent / "state").is_dir() and not self._active_matches_parent(parent):
            blockers.append("active_parent_stale")
        return sorted(set(blockers))

    def promote(
        self,
        candidate: MutationCandidate,
        *,
        owner_approved: bool = False,
        reason: str = "S5 promotion gates passed",
    ) -> MutationCandidate:
        recorded = self._candidate(candidate.mutation_id)
        blockers = self.promotion_blockers(recorded, owner_approved=owner_approved)
        if blockers:
            raise PromotionError(f"promotion blocked: {', '.join(blockers)}")
        descendant = self.descendants.descendants_root / recorded.mutation_id / "runtime"
        version_target = self.versions_dir / recorded.mutation_id
        if version_target.exists():
            if _tree_hashes(version_target) != _tree_hashes(descendant):
                raise PromotionIntegrityError("existing promoted version differs")
        else:
            shutil.copytree(descendant, version_target)
        backup = self._backup_active(recorded.mutation_id)
        try:
            self._activate_runtime(descendant)
            self._write_active_pointer(recorded.mutation_id, recorded.parent_version)
            self._notify_runtime_changed()
            evidence = {
                "evaluator": EvaluatorHarness.EVALUATOR_ID,
                "shadow_passes": self._pass_count(recorded.mutation_id, "shadow"),
                "canary_passes": self._pass_count(recorded.mutation_id, "canary"),
                "owner_approved": bool(owner_approved),
                "rollback_version": recorded.parent_version,
            }
            self.lineage.authorize_promotion(
                recorded.mutation_id,
                self.AUTHORITY_ID,
                owner_approved,
                evidence,
            )
            self.lineage.record_promotion_decision(
                recorded.mutation_id,
                "promote",
                reason,
                version_id=recorded.mutation_id,
            )
            promoted = self.lineage.transition(
                recorded, "promoted", reason=reason
            )
            self._lease_path(recorded.mutation_id).unlink(missing_ok=True)
            shutil.rmtree(backup, ignore_errors=True)
            return promoted
        except Exception as exc:
            self._restore_backup(backup)
            self._write_active_pointer(recorded.parent_version, recorded.parent_version)
            self._notify_runtime_changed(strict=False)
            try:
                self.lineage.record_rollback(
                    recorded.mutation_id,
                    recorded.parent_version,
                    f"automatic activation rollback: {exc}",
                    automatic=True,
                )
                current = self.lineage.candidate(recorded.mutation_id)
                if current is not None and current.status in {"canary", "promoted"}:
                    self.lineage.transition(
                        current, "rolled_back", reason="automatic activation rollback"
                    )
            except LineageError:
                pass
            raise PromotionError(f"activation failed and parent restored: {exc}") from exc

    def rollback(self, candidate: MutationCandidate, reason: str) -> MutationCandidate:
        recorded = self._candidate(candidate.mutation_id)
        if recorded.status != "promoted":
            raise PromotionError(f"rollback requires promoted status, got: {recorded.status}")
        parent = self.versions_dir / recorded.parent_version
        if not (parent / "state").is_dir():
            raise PromotionError("rollback parent missing")
        backup = self._backup_active(f"rollback-{recorded.mutation_id}")
        try:
            self._activate_runtime(parent)
            self._write_active_pointer(recorded.parent_version, recorded.parent_version)
            self._notify_runtime_changed()
            self.lineage.record_rollback(
                recorded.mutation_id,
                recorded.parent_version,
                reason,
                automatic=False,
            )
            self.lineage.record_promotion_decision(
                recorded.mutation_id,
                "rollback",
                reason,
                version_id=recorded.parent_version,
            )
            rolled_back = self.lineage.transition(recorded, "rolled_back", reason=reason)
            shutil.rmtree(backup, ignore_errors=True)
            return rolled_back
        except Exception as exc:
            self._restore_backup(backup)
            self._notify_runtime_changed(strict=False)
            raise PromotionError(f"rollback failed; prior active state restored: {exc}") from exc

    def _candidate(self, mutation_id: str) -> MutationCandidate:
        candidate = self.lineage.candidate(mutation_id)
        if candidate is None:
            raise PromotionError(f"unknown candidate: {mutation_id}")
        return candidate

    def _verify_descendant(self, candidate: MutationCandidate) -> None:
        try:
            manifest = self.descendants.verify(
                self.descendants.descendants_root / candidate.mutation_id
            )
        except DescendantIntegrityError as exc:
            raise PromotionIntegrityError(str(exc)) from exc
        if manifest.parent_version != candidate.parent_version:
            raise PromotionIntegrityError("candidate and descendant parent differ")

    def _exposure_blockers(
        self,
        candidate: MutationCandidate,
        phase: str,
        min_passes: int,
    ) -> list[str]:
        observations = self.lineage.exposure_observations(candidate.mutation_id, phase)
        blockers: list[str] = []
        if sum(item.get("outcome") == "pass" for item in observations) < min_passes:
            blockers.append(f"{phase}_passes_missing")
        if any(item.get("blocking") or item.get("outcome") == "fail" for item in observations):
            blockers.append(f"{phase}_blocking_observation")
        return blockers

    def _owner_gate_blockers(
        self,
        candidate: MutationCandidate,
        owner_approved: bool,
    ) -> list[str]:
        scopes = {scope.lower() for scope in candidate.target_scope}
        if candidate.permissions_delta and not owner_approved:
            return ["permission_delta_owner_approval_missing"]
        if scopes & _OWNER_GATED_SCOPES and not owner_approved:
            return ["high_impact_owner_approval_missing"]
        return []

    def _pass_count(self, mutation_id: str, phase: str) -> int:
        return sum(
            item.get("outcome") == "pass"
            for item in self.lineage.exposure_observations(mutation_id, phase)
        )

    def _active_matches_parent(self, parent: Path) -> bool:
        if _tree_hashes(self.state_dir) != _tree_hashes(parent / "state"):
            return False
        return _tree_hashes(self.capabilities_dir) == _tree_hashes(parent / "capabilities")

    def _backup_active(self, label: str) -> Path:
        _safe_component(label, "backup label")
        root = Path(tempfile.mkdtemp(prefix=f".backup-{label}-", dir=self.active_root))
        if self.state_dir.exists():
            shutil.copytree(self.state_dir, root / "state")
        if self.capabilities_dir.exists():
            shutil.copytree(self.capabilities_dir, root / "capabilities")
        pointer = self.active_root / "current_version.json"
        if pointer.is_file():
            shutil.copy2(pointer, root / "current_version.json")
        return root

    def _activate_runtime(self, runtime: Path) -> None:
        source_state = runtime / "state"
        if not source_state.is_dir():
            raise PromotionError("descendant runtime state missing")
        _replace_tree(source_state, self.state_dir)
        source_capabilities = runtime / "capabilities"
        _replace_tree(source_capabilities, self.capabilities_dir)

    def _restore_backup(self, backup: Path) -> None:
        _replace_tree(backup / "state", self.state_dir)
        _replace_tree(backup / "capabilities", self.capabilities_dir)
        pointer = self.active_root / "current_version.json"
        backup_pointer = backup / "current_version.json"
        if backup_pointer.is_file():
            shutil.copy2(backup_pointer, pointer)
        else:
            pointer.unlink(missing_ok=True)
        shutil.rmtree(backup, ignore_errors=True)

    def _write_active_pointer(self, version_id: str, rollback_version: str) -> None:
        _safe_component(version_id, "active version_id")
        _safe_component(rollback_version, "rollback version_id")
        _atomic_replace_json(
            self.active_root / "current_version.json",
            {
                "schema_version": "seed.active-version.v1",
                "version_id": version_id,
                "rollback_version": rollback_version,
            },
        )

    def _notify_runtime_changed(self, *, strict: bool = True) -> None:
        if self.on_runtime_changed is None:
            return
        try:
            self.on_runtime_changed()
        except Exception:
            if strict:
                raise

    def _descendant_ref(self, candidate: MutationCandidate) -> str:
        return (self.descendants.descendants_root / candidate.mutation_id).as_posix()

    def _lease_path(self, mutation_id: str) -> Path:
        return self.canary_leases_root / f"{mutation_id}.json"


def _replace_tree(source: Path, target: Path) -> None:
    staging = target.parent / f".{target.name}.staging"
    shutil.rmtree(staging, ignore_errors=True)
    if source.is_dir():
        shutil.copytree(source, staging)
    else:
        staging.mkdir(parents=True)
    shutil.rmtree(target, ignore_errors=True)
    staging.replace(target)


def _tree_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(item for item in root.rglob("*") if item.is_file())
    }


def _safe_component(value: str, field_name: str) -> None:
    if not _SAFE_COMPONENT.fullmatch(value):
        raise PromotionError(f"unsafe {field_name}: {value!r}")


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _atomic_create_json(path: Path, data: dict[str, Any]) -> None:
    if path.exists():
        raise PromotionError(f"append-only file already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        temp = Path(handle.name)
    try:
        if path.exists():
            raise PromotionError(f"append-only file already exists: {path.name}")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _atomic_replace_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        temp = Path(handle.name)
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
