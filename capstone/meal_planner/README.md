# AI-Powered Multi-Agent Meal Planner

A daily meal planning assistant built with a multi-agent AI architecture, RAG-based recipe search, JWT authentication, and a conversational interface for natural-language plan adjustments.

---

## Architecture at a Glance

```
Streamlit UI  ──►  FastAPI Backend (JWT-secured)
                        │
            ┌───────────▼────────────┐
            │   Multi-Agent Layer    │
            │                        │
            │  PreferenceAgent       │  (deterministic)
            │  RecipeAgent ──► MCP   │  (FAISS + SQL + Spoonacular)
            │  PlannerAgent          │  (deterministic, calorie engine)
            │  ConversationalAgent   │  (GPT-4o, function calling)
            └───────────────────────┘
                        │
              SQLite · FAISS · audit_logs
```

---

## Prerequisites

- Python 3.11+
- Conda (recommended) or `venv`
- OpenAI API key — required for the conversational agent
- Spoonacular API key — optional, for online recipe fallback

---

## Installation

### 1. Create environment

```bash
conda create -n capstone_epam python=3.11
conda activate capstone_epam
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
OPENAI_API_KEY=sk-...                        # required
SPOONACULAR_API_KEY=...                      # optional
SECRET_KEY=your-long-random-secret-here      # used to sign JWT tokens
MCP_PORT=8001
MCP_SERVER_URL=http://127.0.0.1:8001/sse
```

> ⚠️ **Never commit `.env`** — it is excluded via `.gitignore`.

---

## Seed the Database

### Required — EPUB recipes (Стол №5, Russian, 124 recipes)

```bash
python backend/seed_from_epub.py
```

### Optional — Spoonacular recipes (English, with protein/fat/carbs data)

```bash
python spoonacular_seed.py --api-key YOUR_KEY --count 100
```

Free Spoonacular tier: ~150 points/day, ~1 point per recipe.

To re-seed Spoonacular recipes (e.g. to add macro data):

```bash
python clear_spoonacular.py
python spoonacular_seed.py --api-key YOUR_KEY
```

---

## Running the Application

### Terminal 1 — Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

On startup the backend:
- Runs DB migrations automatically
- Launches the Recipe MCP Server on port 8001
- Serves REST API at `http://localhost:8000`
- Interactive API docs: `http://localhost:8000/docs`

### Terminal 2 — Frontend

```bash
streamlit run frontend/app.py
```

Opens at `http://localhost:8501`

---

## First-Time Usage

1. **Register** — create an account and accept the AI disclaimer
2. **Setup Family** — add family members with age, calorie targets, and dietary tags
3. **Manage Fridge** — add ingredients you already have (used for recipe scoring)
4. **Generate Plan** — AI generates breakfast / lunch / dinner
5. **Chat** — ask the assistant to swap meals in natural language
6. **Approve** — lock the plan and generate the shopping list
7. **Weekly Summary** — see nutrition trends across the week

---

## Project Structure

```
meal_planner/
├── backend/
│   ├── agents/
│   │   ├── preference_agent.py       # Agent 1 — dietary constraint aggregation
│   │   ├── recipe_agent.py           # Agent 2 — MCP client, ingredient search, FAISS
│   │   ├── planner_agent.py          # Agent 3 — meal selection, calorie validation
│   │   └── conversational_agent.py   # Agent 4 — GPT-4o with tool calling
│   ├── mcp/
│   │   └── recipe_mcp_server.py      # MCP server — FAISS search + Spoonacular fallback
│   ├── rag/
│   │   └── vector_store.py           # FAISS index (multilingual embeddings + category hints)
│   ├── engine/
│   │   ├── calorie_engine.py         # Deterministic portion + macro calculation
│   │   └── shopping_engine.py        # Ingredient deduplication + shopping list
│   ├── routers/
│   │   ├── auth.py                   # Register / login / me
│   │   ├── families.py               # Family + member management
│   │   ├── fridge.py                 # Fridge inventory
│   │   ├── meal_plans.py             # Plan generation, chat, approval
│   │   ├── shopping.py               # Shopping list
│   │   ├── recipes.py                # Recipe ratings
│   │   ├── audit.py                  # Audit log + stats
│   │   └── export.py                 # Data export (GDPR portability)
│   ├── content_filter.py             # Prompt injection detection
│   ├── audit.py                      # Audit log writer
│   ├── limiter.py                    # Rate limiter (slowapi)
│   ├── models.py                     # SQLAlchemy ORM models
│   ├── schemas.py                    # Pydantic schemas
│   ├── security.py                   # JWT + bcrypt
│   └── main.py                       # FastAPI app + middleware
├── frontend/
│   └── app.py                        # Streamlit UI (5 pages)
├── logs/
│   └── app.log                       # Rotating log — auto-created, git-ignored
├── rag_eval.py                       # RAG precision/recall evaluation
├── tag_epub_recipes.py               # Enrich EPUB recipes with dietary content tags
├── clear_spoonacular.py              # Remove Spoonacular recipes before re-seeding
├── spoonacular_seed.py               # Seed from Spoonacular API
├── BLUEPRINT.md                   # Full system architecture blueprint
├── .env.example                      # Env variable template (safe to commit)
├── .gitignore
└── requirements.txt
```

---

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| POST | `/families/` | Create family with members |
| PUT | `/families/{id}/members/{id}` | Edit member preferences |
| POST | `/fridge/{id}/bulk` | Add fridge items |
| POST | `/meal-plans/generate` | Run all 4 agents → generate plan |
| POST | `/meal-plans/{id}/chat` | Natural-language plan adjustment |
| POST | `/meal-plans/{id}/approve` | Approve plan |
| POST | `/meal-plans/cleanup?days=7` | Delete old unapproved plans |
| POST | `/shopping/{id}/generate` | Generate shopping list |
| POST | `/recipes/{id}/rate` | Rate a recipe 👍/👎 |
| GET | `/audit/logs` | View audit log |
| GET | `/audit/stats` | Usage statistics + OpenAI cost |
| GET | `/export` | Export all user data as JSON |
| GET | `/health` | System health + DB stats + uptime |

---

## Dietary Tags

| Tag | Behaviour |
|-----|-----------|
| `stol5` | Uses only local EPUB recipes; skips Spoonacular online fallback |
| `vegetarian` | Filters out meat recipes |
| `vegan` | Filters out all animal products |
| `gluten_free` | Gluten-free only |
| `dairy_free` | No dairy |
| `halal` | Halal-certified |
| `high_protein` | High-protein dishes |
| `low_spice` | Mild dishes |
| `soft_food` | Easy-to-chew |
| `high_fiber` | High-fibre dishes |

> **`stol5` is mutually exclusive with all other tags** — the UI enforces this automatically.

---

## Useful Scripts

```bash
# Evaluate RAG retrieval quality (precision / recall / F1)
python rag_eval.py
python rag_eval.py --top-k 15 --meal-type dinner

# Enrich EPUB recipes with dietary content tags (run once after seeding)
python tag_epub_recipes.py

# Seed Spoonacular with a specific diet filter (e.g. vegetarian)
python spoonacular_seed.py --api-key YOUR_KEY --count 15 --diet vegetarian

# Delete stale Spoonacular recipes before re-seeding
python clear_spoonacular.py
```

---

## Security

- All endpoints require JWT authentication (7-day token)
- Rate limits enforced via slowapi: login 5/min, registration 3/min, plan generation 10/min, chat 20/min
- Chat messages filtered for 14 prompt-injection patterns before reaching GPT-4o
- Passwords hashed with bcrypt (72-byte limit enforced)
- All logs written to `logs/app.log` (git-ignored)

---

## Known Limitations

| Limitation | Details |
|-----------|---------|
| SQLite single-writer | Not suitable for >10 concurrent users. Production path: PostgreSQL |
| FAISS in-process | Cannot scale horizontally. Production path: Qdrant / Weaviate |
| Cross-language RAG | English queries for Russian recipes rely on multilingual embeddings. Russian queries give better results for stol5 EPUB recipes |
| Macro data for EPUB | Macros parsed from book nutrition tables. If values show 0g, re-run `seed_from_epub.py` |

---

## AI Disclaimer

> ⚠️ This application provides AI-assisted meal suggestions only. It is **not a substitute for professional dietary or medical advice.** Always consult a qualified nutritionist or physician for specific medical dietary requirements.
