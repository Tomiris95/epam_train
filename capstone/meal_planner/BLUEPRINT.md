# Architecture Blueprint — AI-Powered Multi-Agent Meal Planner

## 1. Problem Statement

Families with specific dietary restrictions (medical diets, allergies, religious requirements, calorie targets) struggle to plan varied, nutritionally balanced meals every day. Manual meal planning is time-consuming and error-prone. This system automates daily meal plan generation using a multi-agent AI architecture that understands family-level dietary constraints, searches a recipe knowledge base semantically, validates calorie targets mathematically, and allows natural-language plan adjustments.

---

## 2. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend                        │
│  Setup Family │ Fridge Manager │ Generate Plan │ Shopping List  │
│               │                │  Weekly Summary│               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST (JWT-authenticated)
┌───────────────────────────▼─────────────────────────────────────┐
│                        FastAPI Backend                           │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐             │
│  │  Auth Router │  │ Family Router│  │ Plan Router│  ...        │
│  └─────────────┘  └──────────────┘  └──────┬─────┘             │
│                                             │                    │
│  ┌──────────────────────────────────────────▼──────────────────┐│
│  │                  Multi-Agent Orchestration Layer             ││
│  │                                                              ││
│  │  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  ││
│  │  │  Preference  │───▶│    Recipe    │───▶│    Planner    │  ││
│  │  │    Agent     │    │  Agent (MCP) │    │    Agent      │  ││
│  │  └──────────────┘    └──────┬───────┘    └───────────────┘  ││
│  │                             │                                 ││
│  │                    ┌────────▼────────┐                       ││
│  │                    │  Conversational │                       ││
│  │                    │  Agent (GPT-4o) │                       ││
│  │                    └─────────────────┘                       ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────────┐ │
│  │  SQLite DB   │  │  FAISS Index   │  │   Audit Log (DB)     │ │
│  │ (SQLAlchemy) │  │ (multilingual  │  │                      │ │
│  └──────────────┘  │  embeddings)   │  └──────────────────────┘ │
│                    └────────────────┘                            │
└──────────────────────────────────────────────────────────────────┘
                            │ HTTP/SSE
┌───────────────────────────▼─────────────────────────────────────┐
│                  Recipe MCP Server (FastMCP)                     │
│                                                                  │
│  Tool 1: search_local_recipes  (FAISS semantic + SQL filter)    │
│  Tool 2: search_online_recipes (Spoonacular API fallback)       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Roles & Responsibilities

### 3.1 Preference Agent
**Type:** Deterministic rule-based agent (no LLM)  
**Input:** List of `FamilyMember` objects with dietary tags  
**Output:** `{allowed_tags, forbidden_tags, member_count, members_summary}`

**Logic:**
- Aggregates tags across all family members
- A tag is **forbidden** for the family if ANY member forbids it (union of restrictions)
- A tag is **allowed** only if at least one member has it as preferred
- Forbidden tags override allowed tags (safety-first)

**Rationale:** Pure deterministic logic — no LLM needed, fast, predictable, auditable.

---

### 3.2 Recipe Agent (MCP Client)
**Type:** Tool-calling agent  
**Input:** Preference result, meal type, preference hint, exclusion lists  
**Output:** List of candidate `Recipe` objects

**Search cascade (in order of priority):**
1. **Ingredient keyword search** — when a preference hint is given (e.g. "eggs"), searches recipe ingredients directly via SQL `ILIKE`. Runs before FAISS to handle cross-language gaps.
2. **FAISS semantic search via MCP** — sends query to Recipe MCP Server; returns top-K semantically similar recipes filtered by meal type and dietary tags.
3. **Spoonacular online fallback** — if local search is empty and stol5 behavior tag is not set, fetches from Spoonacular API and saves to local DB.
4. **Local SQL random fallback** — last resort; returns random recipes of the correct meal type with forbidden-tag filtering.

**Soft exclusion logic:**
- Disliked recipes (user-rated 👎) are excluded first; falls back to full pool if no alternatives exist
- Recently served recipes (last 3 approved plans) are soft-excluded for variety

---

### 3.3 Planner Agent
**Type:** Orchestrator agent (no LLM)  
**Input:** Preference result, family members, fridge items, disliked/recent recipe IDs  
**Output:** `{breakfast, lunch, dinner, member_portions, retries}`

**Plan generation loop (up to 5 attempts):**
1. Calls Recipe Agent for each meal slot
2. Scores candidates by fridge overlap (prefer recipes using available ingredients)
3. If fridge is empty (all scores = 0), selects randomly from full candidate pool for variety
4. Validates daily calorie totals for every family member (±100 kcal tolerance)
5. Tracks best plan across attempts; returns even if constraints aren't fully met

**Calorie engine (deterministic math):**
```
meal_split = {breakfast: 30%, lunch: 40%, dinner: 30%}
target_meal_calories = member.calorie_target × meal_split[meal_type]
adjusted_grams = base_portion_grams × (target_meal_calories / calories_per_base)
```
Computes: calories, protein, fat, carbohydrates per member per meal.

---

### 3.4 Conversational Agent (GPT-4o)
**Type:** LLM function-calling agent  
**Model:** `gpt-4o`  
**Input:** Current plan, user message, chat history, disliked recipe IDs  
**Output:** `{response: str, updated_plan: MealPlanDetailOut | None}`

**Tool:** `replace_meal(meal_type, preference?)`  
**Behavior:**
- Detects replacement intent via keyword matching (`_wants_replacement`)
- When replacement keywords detected: `tool_choice="required"` — GPT **must** call the tool
- Tool calls `PlannerAgent.replace_meal()` with the user's preference as a FAISS/ingredient search hint
- Follow-up call with `tool_choice="none"` generates the human-readable response
- System prompt enforces: never invent recipe names, always report tool result exactly

**Content filtering:** Applied before LLM call — rejects messages >500 chars or containing prompt injection patterns.

---

## 4. Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Streamlit 1.35 | Rapid UI prototyping; session state for chat/plan management |
| Backend API | FastAPI 0.115 | Async-capable, auto OpenAPI docs, Pydantic validation |
| ORM / DB | SQLAlchemy 2.0 + SQLite | Relational data with zero infrastructure overhead for local demo |
| Vector Store | FAISS (faiss-cpu 1.8) | In-process similarity search; no external vector DB needed |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | Supports Russian + English cross-lingual search (EPUB + Spoonacular) |
| LLM | OpenAI GPT-4o | Function calling, multilingual, best reasoning for meal adjustments |
| MCP Framework | FastMCP (mcp 1.0) | Standardized tool protocol; decouples recipe search from orchestration |
| Auth | JWT (python-jose) + bcrypt | Stateless token auth; bcrypt used directly (passlib dropped, incompatible) |
| Rate Limiting | slowapi 0.1.9 | Per-IP rate limits on auth and plan generation endpoints |
| Recipe Data | Spoonacular API | External recipe source with nutrition data (protein/fat/carbs) |
| EPUB Parsing | BeautifulSoup + zipfile | Extracts recipes from "Стол №5" medical diet cookbook |

---

## 5. Data Model

```
User ──< Family ──< FamilyMember ──< MemberDietTag
                  │
                  ├──< FridgeItem
                  │
                  └──< MealPlan ──< MealPlanItem >── Recipe ──< RecipeIngredient
                                 │                          └──< RecipeTag
                                 └──< ShoppingList ──< ShoppingItem

Recipe ──< RecipeRating (user_id, recipe_id, rating: 1|-1)
AuditLog  (user_id, action, timestamp, family_id, plan_id, details JSON)
```

**Key design decisions:**
- `owner_id` on `Family` enables multi-user isolation without tenancy complexity
- `MealPlan.date` stored as ISO string for SQLite compatibility and simple range queries
- `Recipe.source` distinguishes local EPUB recipes (`"local"`) from Spoonacular (`"spoonacular"`)
- `Recipe.protein/fat/carbs_per_100g` populated at seed time; EPUB uses parsed nutrition table; Spoonacular uses API nutrition data

---

## 6. MCP Integration

**Server:** `backend/mcp/recipe_mcp_server.py` — launched as a subprocess by `main.py` on startup; communicates via HTTP/SSE on `localhost:8001`.

### Tool 1: `search_local_recipes`
```
Input:  query (str), meal_type, forbidden_tags_json, allowed_tags_json, top_k
Output: {recipe_ids: List[int], source: "local"}
```
**Pipeline:**
1. FAISS semantic search → top-K candidate IDs
2. Filter by `meal_type`
3. Filter out recipes with any `forbidden_tag`
4. Filter for recipes that have all `filter_tags` (allowed tags minus behavioral tags like `stol5`)
5. If results empty → fallback: query all recipes of `meal_type` directly (handles FAISS meal-type miss)
6. Shuffle before returning (variety across repeated calls)

**Behavioral tags:** `stol5` is excluded from `filter_tags` — it controls whether Spoonacular is called, not recipe attribute matching.

### Tool 2: `search_online_recipes`
```
Input:  meal_type, allowed_tags_json, min_health_score
Output: {recipe_ids: List[int], source: "online", saved: int}
```
- Calls Spoonacular `complexSearch` with nutrition data
- Saves new recipes to local DB (deduplication by name)
- Skipped when `stol5` is in allowed tags

---

## 7. Data Flow: Plan Generation

```
User clicks "Generate Plan"
        │
        ▼
FastAPI POST /meal-plans/generate
        │
        ├─► PreferenceAgent.run(members)
        │         └─► {forbidden_tags, allowed_tags}
        │
        ├─► Fetch fridge items, disliked recipe IDs, recent plan recipe IDs
        │
        ├─► PlannerAgent.run(preference_result, fridge, disliked+recent IDs)
        │    │
        │    └─► for meal_type in [breakfast, lunch, dinner]:
        │         │
        │         ├─► RecipeAgent.run(meal_type, preference_result)
        │         │    ├─► Ingredient search (if hint given)
        │         │    ├─► MCP: FAISS search → filter → shuffle
        │         │    ├─► Spoonacular fallback (if empty + not stol5)
        │         │    └─► SQL random fallback (last resort)
        │         │
        │         ├─► Score by fridge overlap
        │         ├─► Random pick (full pool if empty fridge)
        │         └─► Validate calories ±100 kcal (retry up to 5×)
        │
        ├─► Save MealPlan + MealPlanItems to DB
        ├─► Write AuditLog entry
        └─► Return MealPlanDetailOut with per-member portions + macros
```

---

## 8. Data Flow: Conversational Plan Adjustment

```
User sends chat message
        │
        ▼
Content filter (length ≤500, no injection patterns)
        │
        ▼
Detect replacement intent (_wants_replacement keywords)
        │
        ├─► YES: tool_choice="required"
        │         GPT-4o must call replace_meal(meal_type, preference?)
        │              │
        │              ▼
        │         RecipeAgent.get_alternatives(query_hint=preference)
        │              │ ingredient search → FAISS → SQL fallback
        │              ▼
        │         PlannerAgent selects best by calorie deviation
        │              │
        │              ▼
        │         DB updated, follow-up GPT call with tool result
        │
        └─► NO: tool_choice="auto"
                  GPT answers informational question from system prompt context
```

---

## 9. Non-Functional Requirements Implementation

### 📊 Observability & Monitoring

#### LLM Tracing
Every GPT-4o API call logs `prompt_tokens`, `completion_tokens`, `total_tokens`, and estimated USD cost to both the terminal and `logs/app.log`. Token and cost data are stored in the `chat_message` audit log entry so cumulative spend is queryable via `GET /audit/stats → openai.estimated_total_cost_usd`. GPT-4o pricing is configurable via `GPT4O_INPUT_COST_PER_1K` / `GPT4O_OUTPUT_COST_PER_1K` environment variables.

#### Performance Metrics
A `RequestLoggingMiddleware` in `main.py` logs every HTTP request with method, path, status code, and duration in milliseconds to `logs/app.log`. Individual agent timings are logged for PreferenceAgent, PlannerAgent, and ConversationalAgent using `time.perf_counter()`. Chat replacement success rate (how often a chat request actually changed the plan) is computed from the audit log and exposed via `GET /audit/stats → chat_replacement_success_rate_pct`.

#### Error Tracking
Python `logging` with structured format is used throughout all modules. A `RotatingFileHandler` writes to `logs/app.log` (5 MB per file, 5 backups — ~30 MB max) and survives server restarts. MCP server failures, calorie constraint violations, FAISS fallback paths, and every step of the recipe agent search cascade are individually logged.

#### User Feedback
Two feedback mechanisms are implemented. Recipe ratings (👍/👎) are stored in the `recipe_ratings` table — disliked recipes are soft-excluded from future plan generation, falling back to the full pool only when no alternatives remain. Chat response ratings (👍/👎) appear below every assistant message and are stored as `chat_response_rated` audit events, enabling response quality monitoring over time.

#### Resource Usage
LLM token counts and estimated USD cost are tracked per call and cumulatively in the audit log. `GET /health` reports `recipes_spoonacular` (a proxy metric for Spoonacular API quota consumed) and `uptime_seconds` since the last server start.

---

### 🔒 Security & Safety

#### Input Validation
Pydantic validates all request bodies — FastAPI rejects malformed JSON automatically before any handler runs. Custom field validators enforce: username ≥ 3 characters, password 8–72 bytes (bcrypt hard limit), and ratings restricted to 1, −1, or null. All database queries use SQLAlchemy ORM parameterisation — no raw string interpolation anywhere in the codebase.

#### Content Filtering
`backend/content_filter.py` runs before every GPT-4o call. It applies 14 compiled regex patterns covering prompt injection, jailbreak attempts, and role-override instructions (e.g. "ignore previous instructions", "you are now a", "DAN mode"). Messages longer than 500 characters are also rejected. Blocked requests return HTTP 400 with a descriptive message and never reach the LLM.

#### Privacy Protection
Not applicable to this project. User data consists of family member names, ages, and calorie targets — low PII sensitivity in a local, single-user demo. A PII detection and anonymisation pipeline would be appropriate for a production multi-tenant deployment.

#### Access Control
JWT tokens (7-day expiry) are signed with a configurable `SECRET_KEY`. All endpoints use `Depends(get_current_user)`. Every data resource checks `Family.owner_id == current_user.id` to enforce ownership isolation. Passwords are hashed with bcrypt, truncated to 72 bytes before hashing (bcrypt hard limit). Login brute-force is prevented by rate limiting.

#### Rate Limiting
Implemented via `slowapi` (per-IP): login 5/min, register 3/min, plan generation 10/min, meal replace 10/min, chat 20/min. Exceeded limits return HTTP 429.

---

### ✓ RAG Quality Assurance

#### Retrieval Accuracy
FAISS hit rate is logged per search call: `candidates → passed → hit_rate%`. A precision/recall evaluation script (`rag_eval.py`) provides 14 test cases covering breakfast, lunch, and dinner in both English and Russian, using SQL-derived ground truth. Current average F1: **0.563**. Results are saved to `rag_eval_results.json` for reproducibility.

#### Answer Relevance
Not implemented. Automated relevance scoring requires a labelled reference dataset pairing queries with known correct answers. Creating this dataset for a bilingual recipe domain requires significant domain-annotation effort. The risk is structurally mitigated: two of the four agents (PreferenceAgent and PlannerAgent) are fully deterministic with no LLM involvement, and the ConversationalAgent is constrained by `tool_choice="required"` and strict system prompt rules to only report what the tool actually returned.

#### Source Attribution
Every meal card in the UI displays a coloured source badge: 📚 Local (EPUB) or 🌐 Spoonacular. The `Recipe.source` column is populated at seed time (`"local"` or `"spoonacular"`) and included in all `RecipeOut` API responses.

#### Hallucination Detection
Three complementary guards prevent the ConversationalAgent from fabricating recipe names: (1) `tool_choice="required"` forces GPT-4o to call `replace_meal` before responding when replacement intent is detected — it cannot describe a replacement it did not execute; (2) the system prompt includes explicit rules: "NEVER invent recipe names" and "if the tool returns Failed, say you couldn't find one"; (3) the frontend shows a yellow warning if `updated_plan` is None despite replacement keywords in the user's message.

#### Bias Assessment
Not applicable. The meal planning domain does not involve sensitive demographic decisions. All recommendations are based on user-provided calorie targets and established medical diet guidelines, not inferred demographic attributes.

---

### 💰 Cost & Resource Management

#### Local-First Architecture
All core components run locally with no cloud dependencies: FAISS vector search runs in-process, SQLite is a local file, and the Recipe MCP Server is a subprocess on localhost. Only the ConversationalAgent uses GPT-4o (external API), which is necessary for natural-language understanding — no viable free alternative exists at the required reasoning quality.

#### Free Tier Optimisation
The `stol5` behavioural tag bypasses Spoonacular online search entirely, eliminating API quota usage for users of the local recipe book. The Spoonacular seed script enforces a configurable delay between API calls (default 0.5s). Spoonacular usage is approximated by the `recipes_spoonacular` count in `GET /health`. OpenAI cost is logged per call and aggregated in `GET /audit/stats`.

#### Efficient Processing
The FAISS index is built once on first request and kept in memory — `vector_store.is_ready()` prevents redundant rebuilds. All four agents are singletons instantiated at module load, not per request. Recipe deduplication in the shopping engine uses canonical key comparison (sorted word order) to merge entries like "Грудка Куриная" and "Куриная Грудка".

#### Scalability
Multi-user isolation is fully implemented via JWT authentication and `owner_id` resource scoping. Horizontal scaling is out of scope for a local demo — SQLite is single-writer and FAISS is in-process. A production path would use PostgreSQL and a shared vector store (Qdrant or Weaviate).

#### Data Management
`POST /meal-plans/cleanup?days=N` deletes unapproved plans older than N days. A DB migration on every startup removes orphaned `meal_plan_items` referencing deleted recipes and any plans left empty as a result. Application logs rotate at 5 MB and keep 5 backups.

---

### ⚖️ Compliance & Ethics

#### Industry Standards
The primary recipe dataset is "Стол №5" — a certified medical diet for liver and gallbladder conditions. Calorie splits (30% breakfast / 40% lunch / 30% dinner) and portion adjustment math follow established dietetic norms. No food safety or delivery regulations apply as the system provides advice only.

#### Transparency
Four transparency mechanisms are in place: (1) a persistent sidebar disclaimer stating the app provides AI-assisted suggestions only and is not a substitute for professional medical advice; (2) a coloured source badge (📚 Local / 🌐 Spoonacular) on every recipe card; (3) the sidebar lists all four agent names and their roles; (4) the Weekly Summary page shows a caption noting that macro values depend on each member's actual portion size, not just the base recipe value.

#### Consent Management
The registration form includes a mandatory checkbox acknowledging the AI disclaimer — users cannot create an account without accepting. `GET /export` returns all user data (families, plans, ratings, audit log) as a downloadable JSON file, covering data portability.

#### Audit Trail
The `audit_logs` database table records every significant event with UTC timestamp, user ID, action name, and a structured JSON `details` field. Covered events: `login`, `register`, `plan_generated` (recipe names, retry count), `meal_replaced`, `plan_approved`, `plan_deleted`, `chat_message` (token counts, estimated cost, whether the plan was updated), `cleanup`, `chat_response_rated`. The log is exposed via authenticated endpoints: `GET /audit/logs` and `GET /audit/stats`.

#### Graceful Degradation
Seven fallback layers ensure the system remains functional under partial failures:
1. MCP server unreachable → direct SQL query in `recipe_agent.py`
2. FAISS returns no recipes of the correct meal type → query all local recipes of that type directly
3. Spoonacular API unavailable → return empty result, continue with local recipes only
4. No alternatives after excluding disliked recipes → retry with full recipe pool
5. No alternatives after excluding recently-served recipes → retry with full recipe pool
6. GPT-4o tool call fails → returns honest "I couldn't find a replacement" message; never invents a recipe name
7. Plan references a deleted recipe → orphan cleanup on startup; `Optional[RecipeOut]` in schema prevents HTTP 500

---

## 10. Security Considerations

- Credentials stored in `.env` (excluded from version control via `.gitignore`)
- `SECRET_KEY` for JWT signing loaded from environment; defaults warn about production use
- Passwords truncated to 72 bytes before bcrypt (bcrypt hard limit)
- SQL queries use SQLAlchemy ORM parameterization (no raw string interpolation → no SQL injection)
- CORS configured for local development; should be restricted in production
- Rate limiting prevents brute-force login attacks (5 attempts/minute per IP)

---

## 11. Recipe Knowledge Base

| Source | Count | Language | Macros | Tags |
|--------|-------|----------|--------|------|
| EPUB — "Стол №5" medical diet cookbook | 124 recipes | Russian | Parsed from book nutrition tables (Белки/Жиры/Углеводы) | `stol5`, `lunch`, `dinner`, `breakfast` |
| Spoonacular API | 152 recipes | English | From API nutrition data | Extracted: `vegan`, `vegetarian`, `gluten_free`, `dairy_free`, `halal`, `high_protein`, etc. |

**Embedding model:** `paraphrase-multilingual-MiniLM-L12-v2` — chosen over English-only `all-MiniLM-L6-v2` because the recipe corpus is bilingual (Russian EPUB + English Spoonacular).

---

## 12. Key Architectural Decisions & Rationale

| Decision | Alternative Considered | Rationale |
|----------|----------------------|-----------|
| MCP for recipe search | Direct function calls | Decouples search logic; MCP server can run independently and be replaced |
| FAISS in-process | Pinecone / Weaviate | Zero infrastructure cost; sufficient for hundreds of recipes |
| SQLite | PostgreSQL | No server setup; adequate for single-user local demo |
| GPT-4o for conversation | Anthropic Claude | Function/tool calling API; multilingual support; JSON mode |
| `tool_choice="required"` on replacement | `tool_choice="auto"` | Prevents GPT hallucinating replacements without actually calling the tool |
| Ingredient keyword search before FAISS | FAISS only | Cross-language gap: "eggs" doesn't reliably map to "Яйца" via embeddings |
| Soft exclusion for disliked/recent recipes | Hard exclusion | Prevents dead ends when recipe pool is small |
| bcrypt directly (no passlib) | passlib | passlib incompatible with bcrypt 4.x (`__about__` attribute removed) |
