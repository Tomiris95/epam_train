"""
RAG Vector Store — FAISS-based recipe retrieval.
Builds embeddings from recipe text (name + tags + ingredients).
Falls back to keyword search if FAISS/sentence-transformers not available.

Index is persisted to disk and reloaded on startup.
Rebuilds automatically when the recipe count in DB differs from the saved index.
"""
import json
import logging
import os
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# Persist index files next to this module
_INDEX_DIR = os.path.dirname(os.path.abspath(__file__))
_FAISS_PATH = os.path.join(_INDEX_DIR, "recipes.faiss")
_META_PATH  = os.path.join(_INDEX_DIR, "recipes_meta.json")

_model = None
_index = None
_recipe_ids: List[int] = []
_recipe_texts: List[str] = []


def _get_model():
    global _model
    if not ST_AVAILABLE:
        return None
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _category_hints(ingredients) -> str:
    """
    Map Russian ingredient keywords to English food-category terms so that
    queries like 'fish dinner' or 'eggs breakfast' find Russian EPUB recipes.
    """
    text = " ".join(i.name.lower() for i in ingredients)
    hints = []
    if any(k in text for k in ["лосось","треска","рыба","семга","форель","судак","сом","окунь","тунец","горбуша"]):
        hints += ["fish", "seafood"]
    if any(k in text for k in ["курица","куриц","птиц","индейка"]):
        hints += ["chicken", "poultry"]
    if any(k in text for k in ["говядина","телятина","свинина","баранина","мясо","фарш"]):
        hints += ["beef", "meat", "pork"]
    if any(k in text for k in ["яйц", "яйцо", "белок яич"]):
        hints += ["egg", "eggs"]
    if any(k in text for k in ["творог"]):
        hints += ["cottage cheese", "curd", "dairy"]
    if any(k in text for k in ["каша","овсян","гречн","рис","манн","пшен"]):
        hints += ["porridge", "oatmeal", "cereal", "grains"]
    if any(k in text for k in ["салат","капуст","морковь","свекл","огурц","помидор","овощ"]):
        hints += ["salad", "vegetable", "greens"]
    if any(k in text for k in ["гриб"]):
        hints += ["mushroom"]
    if any(k in text for k in ["банан","яблок","груш","ягод","фрукт","апельсин"]):
        hints += ["fruit", "banana", "berry"]
    return " ".join(hints)


def recipe_to_text(recipe) -> str:
    """Convert a recipe object to a searchable text string."""
    tags = " ".join(t.tag for t in recipe.tags)
    ingredients = " ".join(i.name for i in recipe.ingredients)
    hints = _category_hints(recipe.ingredients)
    return f"{recipe.name} {recipe.meal_type} {tags} {ingredients} {hints}"


def build_index(recipes: list) -> None:
    """Build FAISS index from a list of Recipe ORM objects and persist to disk."""
    global _index, _recipe_ids, _recipe_texts

    texts = [recipe_to_text(r) for r in recipes]
    _recipe_ids = [r.id for r in recipes]
    _recipe_texts = texts

    if not FAISS_AVAILABLE or not ST_AVAILABLE:
        logger.warning("Using keyword search fallback (FAISS/ST not available).")
        _save_meta()
        return

    model = _get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    # IndexFlatIP computes inner product; after L2 normalisation this equals
    # cosine similarity, giving better semantic ranking than Euclidean distance.
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    _index = index

    _save_index()
    logger.info("Built and saved FAISS index with %d recipes.", len(recipes))


def load_or_build_index(recipes: list) -> None:
    """
    Load persisted index from disk if recipe count matches DB.
    Rebuilds and saves if counts differ or no saved index exists.
    """
    global _index, _recipe_ids, _recipe_texts

    if _try_load(expected_count=len(recipes)):
        logger.info("Loaded FAISS index from disk (%d recipes).", len(_recipe_ids))
        return

    logger.info("Index missing or stale — rebuilding...")
    build_index(recipes)


def search(query: str, top_k: int = 10) -> List[int]:
    """
    Search for recipes matching query.
    Returns list of recipe IDs (top_k results).
    """
    global _index, _recipe_ids, _recipe_texts

    if not _recipe_ids:
        return []

    # Keyword fallback (always available)
    if not FAISS_AVAILABLE or not ST_AVAILABLE or _index is None:
        q = query.lower()
        scored = []
        for idx, text in enumerate(_recipe_texts):
            score = sum(1 for word in q.split() if word in text.lower())
            scored.append((score, idx))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [_recipe_ids[i] for _, i in scored[:top_k]]

    # FAISS semantic search
    model = _get_model()
    query_emb = model.encode([query], show_progress_bar=False)
    query_emb = np.array(query_emb, dtype="float32")
    faiss.normalize_L2(query_emb)

    distances, indices = _index.search(query_emb, min(top_k, len(_recipe_ids)))
    results = []
    for i in indices[0]:
        if 0 <= i < len(_recipe_ids):
            results.append(_recipe_ids[i])
    return results


def is_ready() -> bool:
    return len(_recipe_ids) > 0


# ─── Persistence helpers ──────────────────────────────────────────────────────

def _save_index() -> None:
    """Save FAISS index + metadata to disk."""
    if FAISS_AVAILABLE and _index is not None:
        faiss.write_index(_index, _FAISS_PATH)
    _save_meta()


def _save_meta() -> None:
    """Save recipe IDs and texts to a JSON sidecar file."""
    with open(_META_PATH, "w", encoding="utf-8") as f:
        json.dump({"ids": _recipe_ids, "texts": _recipe_texts}, f)


def _try_load(expected_count: int) -> bool:
    """
    Try loading index + metadata from disk.
    Returns True only if both files exist and recipe count matches.
    """
    global _index, _recipe_ids, _recipe_texts

    if not os.path.exists(_META_PATH):
        return False

    with open(_META_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if len(meta.get("ids", [])) != expected_count:
        return False

    # Also rebuild if recipe texts changed (e.g. tags were added to existing recipes)
    if meta.get("ids") and meta.get("texts"):
        from backend.database import SessionLocal
        from backend.models import Recipe as _Recipe
        _db = SessionLocal()
        try:
            sample = _db.query(_Recipe).filter(_Recipe.id == meta["ids"][0]).first()
            if sample and recipe_to_text(sample) != meta["texts"][0]:
                return False
        finally:
            _db.close()

    _recipe_ids = meta["ids"]
    _recipe_texts = meta["texts"]

    if FAISS_AVAILABLE and os.path.exists(_FAISS_PATH):
        _index = faiss.read_index(_FAISS_PATH)

    return True
