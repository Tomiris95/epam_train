# Self-Review — Architecture Decisions and Trade-offs

This document reflects on the key technical decisions made during development,
the trade-offs accepted, and what would be done differently in a production system.

---

## 1. Multi-Agent Architecture

### Decision
Four specialised agents (Preference → Recipe → Planner → Conversational) rather than a single orchestrator LLM.

### Rationale
Separation of concerns: the Preference and Planner agents are fully deterministic Python functions. They have no LLM involvement, so they cannot hallucinate, and their logic can be unit-tested with simple assertions. Only the Conversational agent uses GPT-4o, which limits the blast radius of any LLM failure to the adjustment interface alone.

### Trade-off accepted
A single orchestrator LLM (e.g. Claude with tool use) would have been faster to prototype — one model, one prompt, one call. The multi-agent approach requires more code and careful handoff design between agents. The trade-off is justified: deterministic core logic is more reliable and auditable for a health-related application than letting an LLM decide calorie splits and calculations.

### What I would change in production
Add distributed tracing (e.g. LangSmith or OpenTelemetry) to visualise the full agent chain per request, including which fallback paths were taken.

---

## 2. MCP for Recipe Search

### Decision
Expose recipe search as an MCP (Model Context Protocol) server rather than a direct function call inside the Recipe Agent.

### Rationale
MCP standardises the tool-calling interface. The Recipe MCP Server can run as an independent process, be replaced with a different implementation (e.g. a cloud vector database), or be connected to by any MCP-compatible client — without changing the orchestration layer. It also allowed the FAISS index to live in a long-running process rather than being rebuilt on every request.

### Trade-off accepted
MCP adds a network hop (HTTP/SSE to localhost:8001) and requires subprocess lifecycle management. If the MCP server crashes, the system falls back to direct SQL — but this fallback has no semantic search, only random sampling. For a local demo the added complexity is acceptable; for production, MCP would be replaced with a managed vector store service.

### What I would change in production
Replace the subprocess MCP server with a managed vector store (Qdrant or Weaviate) exposed via a proper API. Keep MCP as the client-facing protocol but point it at a scalable backend.

---

## 3. FAISS Semantic Search with Multilingual Embeddings

### Decision
Use FAISS in-process with `paraphrase-multilingual-MiniLM-L12-v2` embeddings instead of a cloud vector database or English-only model.

### Rationale
The recipe corpus is bilingual: 124 Russian recipes from the Стол №5 cookbook plus English Spoonacular recipes. An English-only model (`all-MiniLM-L6-v2`, the original choice) failed to match "ужин" (dinner) and "курица" (chicken) to English queries. The multilingual model handles cross-lingual similarity significantly better. FAISS in-process eliminates infrastructure cost for a local demo.

### Trade-off accepted
Even the multilingual model has gaps: "fish" does not reliably map to "лосось" (salmon) or "треска" (cod) in the embedding space. This was partially resolved by enriching the indexed text with English category hints (`fish salmon seafood`) derived from Russian ingredient names at index build time. A full fix would require query translation to Russian before embedding.

### What I would change in production
Implement query translation (or a language-detection step + parallel search) so Russian queries hit Russian recipes directly without relying on cross-lingual embedding alignment. Consider fine-tuning the embedding model on domain-specific food pairs.

---

## 4. `tool_choice="required"` for Meal Replacement

### Decision
When the user's message contains replacement keywords, the GPT-4o call uses `tool_choice="required"` instead of `tool_choice="auto"`.

### Rationale
Early testing revealed a critical hallucination pattern: with `tool_choice="auto"`, GPT-4o would sometimes describe a meal replacement ("I've replaced dinner with Salmon Delight") without calling the `replace_meal` tool at all. The plan in the database was never updated. Users saw a confident false statement. Switching to `tool_choice="required"` forces the model to call the tool before generating any text response — the tool result is then the only source of truth the model can report.

### Trade-off accepted
`tool_choice="required"` forces a tool call even when the user's message only partially matches replacement intent (e.g. "different" as a word rather than explicit replacement request). The keyword detection (`_wants_replacement()`) was tuned to minimise false positives. Occasional over-triggering is preferable to the alternative: a confident hallucination that misleads the user.

### What I would change in production
Use a two-step approach: a fast classifier call (cheap model, no tools) to determine intent, then route to the appropriate handler. This avoids the binary keyword-matching heuristic and handles ambiguous phrasing more gracefully.

---

## 5. Ingredient Keyword Search Before FAISS

### Decision
Before calling the FAISS/MCP search, the Recipe Agent runs a direct SQL `ILIKE` search on ingredient names and recipe names.

### Rationale
FAISS semantic search fails for specific ingredient queries like "eggs" or "chicken" when the recipe corpus is in Russian. "eggs" and "яйца" are semantically related but not close enough in the embedding space to reliably surface Russian egg-based recipes. A direct SQL keyword match (`recipe_ingredients.name ILIKE '%egg%'`) finds them immediately. This runs first; FAISS runs only if the keyword search returns nothing.

### Trade-off accepted
The keyword search introduces a dependency on exact substring matching. If a recipe uses "яйцо" (singular) but the user searches "eggs", the substring match fails. However, this is a smaller problem than FAISS completely missing the recipe — partial keyword recall is better than zero semantic recall.

### What I would change in production
Maintain a keyword synonym table (egg ↔ яйцо/яйца, chicken ↔ курица/куриц, fish ↔ рыба/лосось/треска) and expand queries before both the SQL search and FAISS embedding. This would make ingredient-level search language-agnostic.

---

## 6. SQLite as the Database

### Decision
Use SQLite (`meal_planner.db`) as the single database for all data.

### Rationale
Zero infrastructure setup. For a local demo with one or two concurrent users, SQLite is entirely sufficient. The ORM (SQLAlchemy) abstracts the database layer, so switching to PostgreSQL requires only a connection string change and a production migration.

### Trade-off accepted
SQLite is a single-writer database. Under concurrent writes (e.g. two users generating plans simultaneously), requests are serialised at the file-system level — acceptable for a demo, unacceptable for production. The FAISS index is also in-process, preventing horizontal scaling entirely.

### What I would change in production
PostgreSQL + connection pooling (PgBouncer) for the database. Qdrant or Weaviate for the vector store. Stateless FastAPI instances behind a load balancer. The current architecture was deliberately scoped for a local demo with the production path documented.

---

## 7. Soft Exclusion for Disliked and Recently Served Recipes

### Decision
Disliked recipes (👎) and recently served recipes are excluded from plan generation with a fallback: if excluding them leaves no candidates, the planner retries with the full pool.

### Rationale
Hard exclusion creates dead ends when the recipe pool is small. If a user has disliked 5 dinner recipes and the DB only has 6, hard exclusion would make plan generation fail entirely. Soft exclusion respects the preference when possible and degrades gracefully when not.

### Trade-off accepted
The user may occasionally see a disliked recipe if it is the only available option. This is communicated via the server log (`No candidates for dinner after excluding disliked — falling back to full pool`). In a production system with a larger recipe corpus, this fallback would trigger rarely enough to ignore.

### What I would change in production
Add a UI notification when a disliked or recently served recipe appears in the plan due to a limited pool. Users should know when their preference could not be honoured and why.

---

## 8. JWT Authentication with bcrypt (No passlib)

### Decision
Implement authentication using `python-jose` for JWT signing and the `bcrypt` library directly — without the `passlib` wrapper.

### Rationale
`passlib` was originally used but proved incompatible with `bcrypt` 4.x: passlib's internal `detect_wrap_bug()` function calls `bcrypt.checkpw()` with a 73-byte test secret, which bcrypt 4.x rejects with a hard error (`ValueError: password cannot be longer than 72 bytes`). Removing passlib and calling bcrypt directly eliminated the incompatibility. The 72-byte truncation is now enforced explicitly before hashing.

### Trade-off accepted
Using bcrypt directly means fewer convenience features (no automatic algorithm migration, no password strength metrics). These are acceptable omissions for a demo application where password policy is enforced at the Pydantic schema level (8–72 character requirement).

### What I would change in production
Use a mature auth library (e.g. `fastapi-users`) that handles token refresh, email verification, and password reset flows out of the box. Keep bcrypt as the hashing backend but wrap it in a tested library layer.

---

## Summary of Key Trade-offs

| Area | Chosen for demo | Production path |
|------|----------------|-----------------|
| Database | SQLite (zero setup) | PostgreSQL + PgBouncer |
| Vector search | FAISS in-process | Qdrant / Weaviate |
| LLM orchestration | GPT-4o direct API | Add LangSmith tracing |
| Query language | English + Russian via embeddings | Query translation layer |
| Auth | Custom JWT + bcrypt | `fastapi-users` |
| Scalability | Single instance | Stateless replicas + shared store |
| RAG evaluation | SQL-derived ground truth | Human-labelled benchmark dataset |
| EPUB dietary tagging | Rule-based ingredient keyword matching | LLM-based ingredient analysis |
