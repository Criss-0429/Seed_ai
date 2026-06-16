# Graph Report - .  (2026-06-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 155 nodes · 99 edges · 80 communities (13 shown, 67 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 10 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f078dddd`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Mutation Validation|Mutation Validation]]
- [[_COMMUNITY_Evaluation Reporting|Evaluation Reporting]]
- [[_COMMUNITY_Lineage Tracking|Lineage Tracking]]
- [[_COMMUNITY_Evolution Engine|Evolution Engine]]
- [[_COMMUNITY_Descendant Building|Descendant Building]]
- [[_COMMUNITY_Memory Management|Memory Management]]
- [[_COMMUNITY_Promotion Authority|Promotion Authority]]
- [[_COMMUNITY_Onboarding Logic|Onboarding Logic]]
- [[_COMMUNITY_Personality Runtime|Personality Runtime]]
- [[_COMMUNITY_Telemetry and Testing|Telemetry and Testing]]
- [[_COMMUNITY_File System Security|File System Security]]
- [[_COMMUNITY_Capability Registry|Capability Registry]]
- [[_COMMUNITY_Command Routing|Command Routing]]
- [[_COMMUNITY_Configuration Management|Configuration Management]]
- [[_COMMUNITY_Activity Watching|Activity Watching]]
- [[_COMMUNITY_LLM and Voice Interface|LLM and Voice Interface]]
- [[_COMMUNITY_Privacy Redaction|Privacy Redaction]]
- [[_COMMUNITY_Core Orchestration|Core Orchestration]]
- [[_COMMUNITY_Onboarding Tests|Onboarding Tests]]
- [[_COMMUNITY_Background Job Scheduling|Background Job Scheduling]]
- [[_COMMUNITY_Permission Brokering|Permission Brokering]]
- [[_COMMUNITY_Audit Reporting|Audit Reporting]]
- [[_COMMUNITY_System Architecture|System Architecture]]
- [[_COMMUNITY_Design Principles|Design Principles]]
- [[_COMMUNITY_System Components|System Components]]
- [[_COMMUNITY_Runtime Adaptation|Runtime Adaptation]]
- [[_COMMUNITY_Experiment Protocol|Experiment Protocol]]
- [[_COMMUNITY_Product Vision|Product Vision]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]

## God Nodes (most connected - your core abstractions)
1. `build_runtime_benchmark()` - 15 edges
2. `write_runtime_benchmark()` - 6 edges
3. `SEED Memory` - 5 edges
4. `RuntimeOption` - 4 edges
5. `Implementation Plan SEED` - 4 edges
6. `Memory Consolidation Plan` - 4 edges
7. `SEED Salience Gate` - 4 edges
8. `D0 Runtime Option Benchmark` - 4 edges
9. `SEED Evolutionary Architecture` - 3 edges
10. `SEED Mutation Contract` - 3 edges

## Surprising Connections (you probably didn't know these)
- `SEED Memory` --implements--> `Memory Consolidation (M1-M4)`  [EXTRACTED]
  seed/core/memory.py → docs/12_ImplementationPlan.md
- `SEED Knowledge Store` --implements--> `K2 - Living Profile + Counterpoint`  [INFERRED]
  seed/core/knowledge.py → docs/12_ImplementationPlan.md
- `SEED Salience Gate` --implements--> `K3 - Salience / Awareness`  [EXTRACTED]
  seed/core/salience.py → docs/12_ImplementationPlan.md
- `D0 Runtime Option Benchmark` --conceptually_related_to--> `SEED Core`  [EXTRACTED]
  seed/core/runtime_bench.py → docs/12_ImplementationPlan.md
- `D0 Runtime Option Benchmark` --references--> `Hermes`  [EXTRACTED]
  seed/core/runtime_bench.py → docs/12_ImplementationPlan.md

## Import Cycles
- None detected.

## Communities (80 total, 67 thin omitted)

### Community 0 - "Mutation Validation"
Cohesion: 0.23
Nodes (12): build_runtime_benchmark(), Return deterministic D0 evidence without touching external runtimes., Atomically persist the privacy-safe D0 report., write_runtime_benchmark(), Path, D0 runtime option benchmark: deterministic, synthetic, privacy-safe., test_benchmark_is_deterministic_and_hash_is_stable(), test_broad_runtime_authority_is_blocked() (+4 more)

### Community 1 - "Evaluation Reporting"
Cohesion: 0.18
Nodes (11): Mutation Contract, K2 - Living Profile + Counterpoint, K3 - Salience / Awareness, Memory Consolidation (M1-M4), SEED Knowledge Store, SEED Memory, Model Roles, Design Governor and Voice Plan, SEED Promotion (+3 more)

### Community 2 - "Lineage Tracking"
Cohesion: 0.17
Nodes (11): Activity Watcher, Agentic Background Daemon Plan, Cognitive User Knowledge Plan, Implementation Plan SEED, Memory Consolidation Plan, Personalità Compatibile, AgentMemory Wiki, Cognitive User Model Execution Harness (+3 more)

### Community 3 - "Evolution Engine"
Cohesion: 0.24
Nodes (10): _blockers(), _canonical_hash(), Criterion, _fixture_results(), OptionResult, D0 deterministic benchmark for agentic runtime options.  Evaluates architecture, RuntimeOption, SyntheticFixture (+2 more)

### Community 4 - "Descendant Building"
Cohesion: 0.40
Nodes (6): SeedApp, KnowledgeStore, M1 Relevant Recall, Recall Discipline Router, K3 Salience/Awareness, Sleep-time Consolidator

### Community 5 - "Memory Management"
Cohesion: 0.40
Nodes (5): Hermes, OpenClaw, OpenHarness, D0 Runtime Option Benchmark, SEED Core

### Community 6 - "Promotion Authority"
Cohesion: 0.40
Nodes (5): JARVIS Agent Ecosystem, M3 Memory, JARVIS Operational Workflow, SEED Evolutionary Architecture, SEED Stable Boot Supervisor

### Community 7 - "Onboarding Logic"
Cohesion: 0.50
Nodes (4): Hermes Agent, OpenClaw, OpenHarness, SEED Implementation Plan

### Community 8 - "Personality Runtime"
Cohesion: 0.50
Nodes (4): JARVIS Design Principles, SEED Mutation Contract, SEED Evolution Engine, SEED Isolation & Security

### Community 9 - "Telemetry and Testing"
Cohesion: 0.50
Nodes (4): JARVIS User Knowledge Ontology, SEED Activity Watcher, SEED Compatible Personality, SEED Privacy Gate

### Community 11 - "Capability Registry"
Cohesion: 0.67
Nodes (3): Corpus Bridges, Model Roles, Design Governor and Voice Plan, J.A.R.V.I.S. Mission

## Knowledge Gaps
- **89 isolated node(s):** `SEED Product Vision`, `SEED Evolution Engine`, `SEED Privacy Gate`, `SEED Isolation & Security`, `SEED Activity Watcher` (+84 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **67 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Implementation Plan SEED` connect `Lineage Tracking` to `Evolution Engine`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `build_runtime_benchmark()` connect `Mutation Validation` to `Evolution Engine`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **What connects `SEED Product Vision`, `SEED Evolution Engine`, `SEED Privacy Gate` to the rest of the system?**
  _100 weakly-connected nodes found - possible documentation gaps or missing edges._