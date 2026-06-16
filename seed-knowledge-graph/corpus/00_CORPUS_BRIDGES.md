# SEED Specific Knowledge Graph - Corpus Bridges

## Purpose

This corpus creates a SEED-specific knowledge graph while preserving explicit
links to canonical JARVIS documentation and subordinate LLM Wiki context.

## Authority

- SEED product and implementation decisions come from `seed/docs`.
- JARVIS official documents under `jarvis/official` provide canonical design,
  workflow, stack, privacy, capability-governance and model-routing context.
- LLM Wiki pages under `jarvis/wiki` provide subordinate implementation and
  research context. They do not override SEED or official JARVIS decisions.

## Explicit Bridges

- SEED Active Runtime references JARVIS Workflow for conversation-first
  execution, lane selection, specialist execution and visible progress.
- SEED Model Roles and Design Governor references JARVIS Stack model lanes and
  JARVIS Agent Ecosystem separation between orchestrator, specialist and
  evaluator responsibilities.
- SEED Design Governor implements the separation-of-authorities requirements in
  SEED Mutation Contract and Capability Governance in JARVIS Design Principles.
- SEED Tool Builder applies Agent Harness Best Practices, Runtime Harness
  Adaptation and OpenHarness patterns inside the isolated Evolution Lab.
- SEED Personality Runtime references JARVIS User Knowledge Ontology and
  Cognitive User Model Execution Harness while preserving a distinct identity.
- SEED Memory and Evidence State references JARVIS Memory Architecture, M3
  Memory and AgentMemory as subordinate implementation context.
- SEED K3 Salience Gate connects M3 retrieval, living profile and personality
  context while enforcing JARVIS Cognitive User Model default-silence policy.
- SEED Online Research Lane references JARVIS Workflow search planning and
  JARVIS Stack Tavily/Exa provider policy.
- SEED Optional Voice Lane references JARVIS Stack local/cloud voice lanes but
  keeps voice optional, consent-gated and privacy-filtered.
- SEED Promotion Authority and Stable Boot Supervisor implement governance,
  rollback and recovery requirements shared with Personal OS Thesis Direction.
- SEED D0 Runtime Option Benchmark connects Agentic Runtime Options, Hermes,
  OpenClaw and OpenHarness patterns to the SEED Mutation Contract: OpenHarness
  supplies isolation/dry-run patterns, Hermes registry/skills/delegation
  patterns, OpenClaw daemon/session patterns, while SEED Core retains authority.

## Graph Scope

Included:

- current SEED documentation;
- current SEED core Python modules;
- focused tests for personality, onboarding, evaluator and promotion;
- selected official JARVIS documents;
- selected LLM Wiki pages relevant to model roles, memory, harness and
  governance.

Excluded:

- runtime config and API keys;
- local databases, traces and logs;
- build artifacts and executables;
- unrelated JARVIS application code;
- UI prototypes.
