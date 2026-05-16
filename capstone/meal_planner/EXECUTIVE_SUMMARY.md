# Executive Summary — AI-Powered Multi-Agent Meal Planner

## Problem Statement

Daily meal planning for families with specific dietary needs is time-consuming and cognitively demanding. A family where one member follows a medical diet (Стол №5 for liver conditions), another requires halal-certified food, and children have calorie targets must simultaneously satisfy multiple constraints — every single day. Manual planning leads to repetitive menus, missed nutritional targets, and wasted ingredients already available at home.

This project automates that process entirely: given a family profile, it generates a nutritionally validated daily meal plan, explains what to buy, and allows natural-language adjustments through a conversational interface.

---

## What Was Built

A **production-grade multi-agent AI system** with a Streamlit web interface and a FastAPI backend. Four specialized agents collaborate to produce each daily plan:

1. **Preference Agent** — aggregates dietary constraints across all family members deterministically (no LLM; any member's restriction applies to the whole family)
2. **Recipe Agent** — searches a bilingual recipe knowledge base using FAISS semantic vector search, with Spoonacular API as an online fallback
3. **Planner Agent** — selects the optimal breakfast/lunch/dinner combination, scores recipes by fridge overlap, and validates calorie targets (±100 kcal tolerance) for every family member
4. **Conversational Agent** — allows natural-language plan adjustments via GPT-4o with function calling ("replace dinner with something with salmon")

The system stores 124 Russian recipes from a certified medical diet cookbook (*Стол №5*) and supplements them with 69 English recipes from the Spoonacular API. All recipe search runs locally via FAISS with no cloud vector database.

---

## Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| **Multi-agent architecture** | Each agent has a single, testable responsibility. Preference and Planner agents are fully deterministic — eliminating hallucination risk in the core planning logic |
| **MCP (Model Context Protocol)** | Recipe search is decoupled from the orchestration layer via a standardized tool protocol. The MCP server can be replaced or extended without touching agent code |
| **FAISS in-process** | Zero infrastructure cost; sufficient for hundreds of recipes. Embeddings use a multilingual model (`paraphrase-multilingual-MiniLM-L12-v2`) to handle the Russian/English bilingual corpus |
| **`tool_choice="required"` for GPT-4o** | When replacement intent is detected, GPT-4o is forced to call the `replace_meal` tool before responding. This eliminates the hallucination pattern where the model describes a replacement it never executed |
| **Ingredient keyword search before FAISS** | Cross-language semantic search fails for specific ingredient queries ("eggs" → "яйца"). A SQL `ILIKE` search on ingredient names runs first, catching these cases reliably |

---

## Results

**Functional correctness:**
- Generates valid meal plans satisfying all dietary constraints across tested families
- Handles 7 graceful degradation scenarios (MCP failure, FAISS miss, Spoonacular outage, empty pools after exclusions)
- Conversational meal replacement works in both Russian and English

**RAG quality (evaluated on 14 test cases):**
- Average F1: **0.563** across breakfast, lunch, and dinner queries
- Perfect scores (F1 = 1.0) for direct ingredient matches ("chicken dinner", "lentil soup")
- Identified gap: English queries for Russian EPUB recipes score lower due to cross-language semantic distance

**Test coverage:**
- **72 automated tests** — 100% passing, 0 warnings
- Unit tests: calorie engine math, shopping deduplication, prompt injection filter
- Integration tests: full auth flow, family ownership isolation, plan lifecycle, content filtering

**Non-functional requirements:**
- JWT authentication + per-endpoint rate limiting (slowapi)
- Persistent audit log with OpenAI cost tracking per conversation turn
- Structured data retention, user feedback ratings, and GDPR data export endpoint
- All requests logged to rotating file (`logs/app.log`, 5 MB × 5 backups)

---

## Business Value

For a family spending 20-30 minutes per day on meal planning, this system reduces that to under 10 seconds for plan generation, with natural-language adjustment taking an additional 30-60 seconds per swap. For families managing medical diets (Стол №5 is prescribed for liver, gallbladder, and pancreatic conditions), the system ensures dietary compliance automatically, removing the cognitive burden of checking constraints manually.

The recipe knowledge base compounds in value over time: every Spoonacular recipe fetched by one user's request is stored locally and immediately available for all users without additional API cost.

---

## Lessons Learned

**Cross-language RAG is harder than expected.** Switching from an English-only embedding model to `paraphrase-multilingual-MiniLM-L12-v2` helped, but semantic search still struggles with specific ingredient names across languages. The ingredient keyword fallback (`ILIKE '%курица%'`) was the practical fix, not a better embedding model.

**LLM tool calling requires hard enforcement.** Setting `tool_choice="auto"` allowed GPT-4o to describe meal replacements without actually executing them — a confident hallucination. Switching to `tool_choice="required"` when replacement intent is detected eliminated this entirely. System prompt rules alone were not sufficient.

**Behavioral tags vs attribute tags must be separated.** The `stol5` tag served two purposes: controlling which recipe source to use (skip Spoonacular) and labelling recipe origin (from the Стол №5 cookbook). Conflating these caused the planner to filter out all EPUB recipes for non-stol5 users. Explicit separation of behavioral and attribute roles resolved the issue.

---

## Potential Next Steps

1. **Production database** — Replace SQLite with PostgreSQL to support concurrent writes and horizontal scaling
2. **Shared vector store** — Replace in-process FAISS with Qdrant or Weaviate for multi-instance deployment
3. **Query translation** — Translating user preference keywords to Russian before FAISS search would significantly improve recall for stol5 recipe queries from non-Russian speakers
4. **Weekly plan generation** — Extend the planner to generate a full week at once, with cross-day variety constraints and a consolidated weekly shopping list
5. **Recipe tagging enrichment** — Automatically tag EPUB recipes with ingredient-category attributes (fish, chicken, vegetarian) so the FAISS filter works without relying on the SQL keyword fallback
