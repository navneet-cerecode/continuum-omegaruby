# Architecture — CONTINUUM / OmegaRuby

```mermaid
flowchart LR
    U[Operations lead] --> UI[React + TypeScript\nContext / Investigation / Queue]
    UI --> API[FastAPI\nTyped inputs + origin checks]
    MD[Synthetic Markdown + curated metadata] --> IMPORT[Deterministic import\nStable IDs + immutable versions]
    IMPORT --> DB[(FalkorDB\nPersistent volume + AOF)]
    API --> SERVICE[Application state transitions\nChange / Plan / Human approval]
    SERVICE --> DB
    API --> AGENT[One bounded agent loop]
    AGENT <--> MODEL[Configured model\nFree local Ollama or API provider]
    AGENT --> TOOLS[Read-only allowlisted tools\nNo arbitrary Cypher or task approval]
    TOOLS --> DB
    DB --> EVIDENCE[Paths + excerpts + conflicts + actions]
    EVIDENCE --> UI
```

The frontend makes explicit `/api` requests. The backend uses the official FalkorDB Python client, parameterized queries and bounds. The model selects from seven investigation tools; its output is validated against returned source IDs and complete paths. Natural-language entailment is still a review responsibility.

Local Ollama needs no API key and uses native `/api/chat` and a six-turn/ten-tool budget. The verified installed Llama 3 model uses a validated JSON protocol to select typed tools. After it retrieves source evidence, an answer schema constrains citations to returned source IDs and full graph paths. Native-tool Ollama models may instead use tool schemas with thinking output disabled. Hosted adapters support Responses or compatible Chat Completions. No hidden reasoning is retained in the trace. Each run must retrieve real sources before the application accepts a substantive answer. Invalid or unavailable inference is surfaced, not replaced by a canned agent response.

The only task mutation is the application's explicit approval endpoint. A model tool cannot invoke it. Browser-origin checks apply to writes, and all local ports bind to loopback. This local demonstration has no public user authentication or tenant isolation.

## Why a graph

The workflow is variable-depth dependency discovery with provenance at each step. FalkorDB finds the paths and the entities; the application formats returned results and deduplicates endpoints. It does not load JSON topology to reason in memory. SQL can also implement recursive dependencies; the graph model makes the relationships and explainable paths first-class for this demo.

## Scaling constraints

The fixture is small. Current evidence hydration uses multiple queries per impacted entity, and queries lack mature indexes/pagination. Eight-hop and 200-path bounds constrain work but can truncate a dense graph. Larger graphs need indexed IDs, batched evidence queries, path pagination, controlled writes, source authority governance, quality review, authentication, and operational monitoring. No vector database or graph algorithm unrelated to dependency semantics is used. A small local latency result is not enterprise-scale evidence.
