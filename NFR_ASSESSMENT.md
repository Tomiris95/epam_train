# Non-Functional Requirements Assessment

Legend: ✅ Implemented | ⚠️ Partial | ❌ Not implemented | N/A Not applicable

---

## 📊 Observability & Monitoring

### LLM Tracing: Track all agent interactions, token usage, and response quality
**Status: ⚠️ Partial**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Token usage per LLM call | ✅ | `conversational_agent.py` — logs `prompt_tokens`, `completion_tokens`, `total_tokens` for both GPT-4o calls per turn |
| Estimated cost per call | ✅ | `conversational_agent.py` — logs `est. cost=$X.XXXXX`; prices configurable via env vars |
| Cumulative token & cost totals | ✅ | `GET /audit/stats` — sums all `chat_message` audit entries → `openai.total_tokens_used`, `openai.estimated_total_cost_usd` |
| Agent interaction timing | ✅ | `routers/meal_plans.py` — logs PreferenceAgent, PlannerAgent, ConversationalAgent duration in seconds |
| Response quality scoring | ❌ | No automated quality metric (RAGAS, G-Eval). Requires a labelled ground-truth dataset. |

**Remaining gap:** Automated LLM response quality evaluation not implemented — acceptable for demo scope.

---

### Performance Metrics: Monitor response times, success rates, and system throughput
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Response times | ✅ | `time.perf_counter()` around every agent call, logged to `app.log` |
| Request timing (all endpoints) | ✅ | `RequestLoggingMiddleware` in `main.py` — logs every HTTP request with method, path, status, and duration in ms |
| Retry count | ✅ | `planner_agent.run()` returns `retries` count, stored in `plan_generated` audit entry |
| Chat replacement success rate | ✅ | `GET /audit/stats` — `chat_replacement_success_rate_pct` computed from audit log |
| System throughput | ✅ | Every request logged to `logs/app.log`; greppable for per-minute request counts |

---

### Error Tracking: Comprehensive logging of failures and system errors
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Structured logging | ✅ | `logging.basicConfig` in `main.py`; all modules use named loggers |
| MCP/agent failures | ✅ | `recipe_agent.py` logs MCP failures and every fallback path taken |
| Calorie constraint violations | ✅ | Planner logs each attempt with deviation value |
| RAG hit rate | ✅ | `recipe_mcp_server.py` logs `candidates → passed → hit_rate%` per search |
| Persistent error storage | ✅ | `logs/app.log` — rotating file handler (5 MB × 5 backups); survives restarts |

---

### User Feedback: Implement rating systems for response quality assessment
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Recipe ratings | ✅ | 👍/👎 per recipe; stored in `recipe_ratings` table; disliked recipes excluded from future plans |
| AI response ratings | ✅ | 👍/👎 buttons below every assistant chat message; stored as `chat_response_rated` in audit log |

---

### Resource Usage: Track memory, CPU, and API quota consumption
**Status: ⚠️ Partial**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| LLM token counts + cost | ✅ | Per-call and cumulative totals via audit log + `/audit/stats` |
| Spoonacular quota proxy | ✅ | `GET /health` reports `recipes_spoonacular` count — proxy for API calls made |
| Server uptime | ✅ | `GET /health` reports `uptime_seconds` since last start |
| Memory / CPU profiling | ❌ | No runtime profiling; not critical for local demo |

---

## 🔒 Security & Safety

### Input Validation: Sanitize all user inputs and API responses
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Schema validation | ✅ | Pydantic on all request bodies; FastAPI rejects malformed JSON |
| Username validator | ✅ | `schemas.py` — min 3 chars |
| Password validator | ✅ | `schemas.py` — 8–72 chars; bcrypt 72-byte limit enforced |
| Rating validator | ✅ | `schemas.py` — must be 1, -1, or null |
| SQL injection prevention | ✅ | ORM parameterized queries throughout; no raw string interpolation |

---

### Content Filtering: Implement guardrails against harmful or inappropriate content
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Prompt injection patterns | ✅ | `content_filter.py` — 14 regex patterns (jailbreak, "ignore instructions", etc.) |
| Message length limit | ✅ | 500-character cap on chat messages |
| Applied before LLM | ✅ | `routers/meal_plans.py` — filter runs before `ConversationalAgent.run()` |

---

### Privacy Protection: PII detection and data anonymization
**Status: N/A**

Local demo application. User data is family member names, ages, and calorie targets — low PII sensitivity. Full PII detection pipeline not applicable for this scope.

---

### Access Control: Authentication and authorization mechanisms
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| JWT authentication | ✅ | `security.py`, `routers/auth.py` — 7-day tokens |
| Endpoint protection | ✅ | All routes use `Depends(get_current_user)` |
| Resource ownership | ✅ | `Family.owner_id == current_user.id` checked on every operation |
| Brute-force protection | ✅ | Login rate-limited: 5 attempts/minute per IP |

---

### Rate Limiting: Prevent abuse and manage resource consumption
**Status: ✅ Implemented**

| Endpoint | Limit | Library |
|----------|-------|---------|
| `POST /auth/register` | 3/min | slowapi |
| `POST /auth/login` | 5/min | slowapi |
| `POST /meal-plans/generate` | 10/min | slowapi |
| `POST /meal-plans/{id}/replace` | 10/min | slowapi |
| `POST /meal-plans/{id}/chat` | 20/min | slowapi |

---

## ✓ RAG Quality Assurance

### Retrieval Accuracy: Measure precision and recall
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Hit rate logging | ✅ | MCP server logs `candidates → passed → hit_rate%` per search |
| Formal precision/recall | ✅ | `rag_eval.py` — 14 test queries (breakfast/lunch/dinner, EN+RU); avg F1=0.563, results saved to `rag_eval_results.json` |

---

### Answer Relevance: Evaluate semantic similarity and factual correctness
**Status: ❌ Not implemented**

No automatic relevance scoring. Mitigated in practice by: Preference + Planner agents being fully deterministic (no LLM hallucination risk), and ConversationalAgent being constrained to only report tool results.

---

### Source Attribution: Proper citation and traceability
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Recipe source badge in UI | ✅ | 📚 Local (EPUB) vs 🌐 Spoonacular on every meal card |
| `source` field in DB | ✅ | `Recipe.source` column — `"local"` or `"spoonacular"` |
| MCP source in response | ✅ | MCP server returns `{"source": "local"}` in every search result |

---

### Hallucination Detection: Identify and flag potentially false information
**Status: ⚠️ Partial**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Forced tool calling | ✅ | `tool_choice="required"` when replacement intent detected |
| System prompt guard | ✅ | Rules: "NEVER invent recipe names", "If tool returns Failed, say I couldn't find" |
| Frontend warning | ✅ | Yellow warning if `updated_plan` is None despite replacement keywords |
| Automated detection | ❌ | No LLM-as-judge or semantic consistency checker |

---

### Bias Assessment: Monitor for unfair or discriminatory outputs
**Status: N/A**

Meal planning does not involve sensitive demographic decisions. Dietary recommendations are based on user-provided data and established medical diet guidelines.

---

## 💰 Cost & Resource Management

### Local-First Architecture: Minimize cloud dependencies
**Status: ✅ Implemented**

| Component | Approach |
|-----------|---------|
| Vector search | FAISS in-process (no Pinecone/Weaviate cost) |
| Database | SQLite local file |
| Recipe knowledge base | EPUB parsing (fully offline) |
| MCP server | Local subprocess on port 8001 |
| LLM | GPT-4o cloud (necessary; no viable free alternative at this quality level) |

---

### Free Tier Optimization: Stay within API limits
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Spoonacular skip for stol5 users | ✅ | `stol5` behavioral tag bypasses online search entirely |
| Spoonacular seed rate limiting | ✅ | 0.5s delay between API calls in seed script |
| Spoonacular usage proxy metric | ✅ | `GET /health` → `recipes_spoonacular` count as quota proxy |
| OpenAI cost per call | ✅ | Logged to `app.log` with estimated USD amount |
| OpenAI cumulative cost | ✅ | `GET /audit/stats` → `openai.estimated_total_cost_usd` |

---

### Efficient Processing: Caching and resource optimization
**Status: ⚠️ Partial**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| FAISS index caching | ✅ | Built once on first request, reused in memory |
| Agent singletons | ✅ | All agents instantiated once at module level, not per request |
| HTTP response caching | ❌ | No Redis/in-memory response cache |
| Duplicate prevention | ✅ | Recipe deduplication by canonical name; shopping list ingredient merging |

---

### Scalability: Support concurrent users
**Status: ⚠️ Partial — by design for local demo**

| Sub-requirement | Status | Notes |
|----------------|--------|-------|
| Multi-user isolation | ✅ | JWT + `owner_id` on all resources |
| Concurrent requests | ⚠️ | FastAPI async but FAISS search is synchronous (`asyncio.run()`) |
| SQLite write concurrency | ⚠️ | Single-writer; suitable for demo, bottleneck at scale |
| Horizontal scaling | ❌ | In-process FAISS + SQLite prevent multi-instance deployment |

Production path: PostgreSQL + Qdrant/Weaviate + async embedding search.

---

### Data Management: Retention policies and storage optimization
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Retention endpoint | ✅ | `POST /meal-plans/cleanup?days=7` |
| Orphan cleanup | ✅ | DB migration on startup removes `meal_plan_items` with deleted recipes |
| Shopping list deduplication | ✅ | Canonical key (sorted words) merges duplicate ingredients |
| Non-food filtering | ✅ | Shopping engine removes Белки/Жиры/Углеводы/kcal from ingredient lists |
| Log rotation | ✅ | `app.log` rotates at 5 MB, keeps 5 backups (~30 MB max) |

---

## ⚖️ Compliance & Ethics

### Industry Standards: Domain-specific compliance
**Status: ✅ / N/A**

| Sub-requirement | Status | Notes |
|----------------|--------|-------|
| Medically grounded recipes | ✅ | Primary dataset is "Стол №5" — certified medical diet cookbook |
| Nutritional calculation standards | ✅ | Calorie splits (30/40/30) and adjustment math follow dietetic norms |
| Food safety regulations | N/A | No food preparation or delivery service involved |

---

### Transparency: Clear information about system capabilities and limitations
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| AI disclaimer | ✅ | Sidebar: "AI-assisted suggestions only. Not a substitute for professional dietary or medical advice." |
| Source attribution | ✅ | 📚 Local / 🌐 Spoonacular badge per recipe |
| Agent pipeline visible | ✅ | Sidebar lists all 4 agents and their roles |
| Macro data caveat | ✅ | Weekly Summary: "Actual values depend on each member's portion size" |

---

### Consent Management: Handle user data with appropriate permissions
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| User owns their data | ✅ | All data scoped by `owner_id`; user can delete family and plans |
| Explicit consent at registration | ✅ | Mandatory checkbox on register form — acknowledges AI limitations |
| Data export (portability) | ✅ | `GET /export` — returns all user data (families, plans, ratings, audit log) as JSON |

---

### Audit Trail: Logs for accountability and debugging
**Status: ✅ Implemented**

| Sub-requirement | Status | Where |
|----------------|--------|-------|
| Persistent audit log | ✅ | `audit_logs` DB table — survives restarts |
| Events covered | ✅ | `login`, `register`, `plan_generated`, `meal_replaced`, `plan_approved`, `plan_deleted`, `chat_message`, `cleanup`, `chat_response_rated` |
| Structured details | ✅ | JSON `details` field (recipe names, retry counts, token usage, cost, plan_updated) |
| Read endpoint | ✅ | `GET /audit/logs?limit=50&action=<filter>` |
| Stats endpoint | ✅ | `GET /audit/stats` — counts by action, success rate, cumulative OpenAI cost |

---

### Graceful Degradation: Handle service failures with fallbacks
**Status: ✅ Implemented**

| Failure scenario | Fallback | Where |
|-----------------|---------|-------|
| MCP server unreachable | Direct SQL query | `recipe_agent.py` |
| FAISS returns no meal-type matches | Query all local recipes of that type directly | `recipe_mcp_server.py` |
| Spoonacular API down | Return empty, continue with local | `recipe_mcp_server.py` |
| No alternatives after excluding disliked | Retry with full pool | `planner_agent.py` |
| No alternatives after excluding recent plans | Retry with full pool | `planner_agent.py` |
| GPT-4o tool failure | Honest "I couldn't find" response | `conversational_agent.py` |
| Deleted recipe referenced by plan | Orphan cleanup on startup; `Optional[RecipeOut]` in schema | `database.py`, `schemas.py` |

---

## Summary Table

| Category | ✅ | ⚠️ | ❌ | N/A |
|----------|----|----|-----|-----|
| Observability & Monitoring | 12 | 1 | 1 | 0 |
| Security & Safety | 13 | 0 | 0 | 3 |
| RAG Quality Assurance | 6 | 2 | 1 | 2 |
| Cost & Resource Management | 9 | 3 | 1 | 0 |
| Compliance & Ethics | 12 | 0 | 0 | 3 |
| **Total** | **52** | **6** | **3** | **8** |

---

## Remaining Gaps

| Gap | Reason not implemented |
|-----|----------------------|
| LLM response quality scoring (RAGAS) | Requires labelled ground-truth evaluation dataset — out of scope for demo |
| HTTP response caching | Redis dependency; overkill for single-user local demo |
| Memory / CPU profiling | Not critical for local demo; production monitoring belongs in infrastructure layer |
| Horizontal scalability | Requires PostgreSQL + shared vector store — architectural decision to keep demo simple |
