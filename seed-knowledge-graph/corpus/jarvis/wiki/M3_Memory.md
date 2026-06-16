# M3 Memory: Hybrid Retrieval Layer

**Last Updated:** April 24, 2026  
**Role:** Persistent Agent Memory

M3 Memory is a specialized memory layer for AI agents that combines **Keyword Search (BM25)**, **Semantic Search (Vector)**, and **Graph Search** into a single retrieval pipeline.

## 🛠️ Key Features
- **Triple-Model**: Uses three different retrieval strategies to ensure no context is missed.
- **MCP Native**: Designed to work as a Model Context Protocol server.
- **Local-First**: Runs entirely on your hardware.

---

## 🏗️ Role in JARVIS
M3 serves as a "long-term working memory" for agents. While [[Obsidian]] is the static knowledge base, M3 tracks evolving conversations, project statuses, and agent "learnings" over time.

---

## Related Components
- [[Jarvis_Memory_Architecture]]
- [[ChromaDB]]
- [[OpenClaw]]

**Canonical Reference:** `raw/Jarvis_Documentation/Documentazione Memoria/README.md`
