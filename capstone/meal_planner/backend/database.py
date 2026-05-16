"""
Database setup and lightweight migration runner.
SQLite is used for zero-infrastructure local deployment.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./meal_planner.db"

# check_same_thread=False: FastAPI handles each request in a thread pool;
# SQLite's default single-thread guard would reject cross-thread DB access.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """
    Add missing columns / tables to an existing DB without dropping data.
    Raw SQL via PRAGMA is used because SQLAlchemy ORM has no ALTER TABLE support.
    """
    from sqlalchemy import text
    with engine.connect() as conn:
        # recipes: add cooking_instructions
        recipe_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(recipes)"))]
        if "cooking_instructions" not in recipe_cols:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN cooking_instructions TEXT"))

        # families: add owner_id
        family_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(families)"))]
        if "owner_id" not in family_cols:
            conn.execute(text("ALTER TABLE families ADD COLUMN owner_id INTEGER REFERENCES users(id)"))

        # recipes: add source + macro columns
        recipe_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(recipes)"))]
        if "source" not in recipe_cols:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN source TEXT DEFAULT 'local'"))
        if "protein_per_100g" not in recipe_cols:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN protein_per_100g REAL DEFAULT 0.0"))
        if "fat_per_100g" not in recipe_cols:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN fat_per_100g REAL DEFAULT 0.0"))
        if "carbs_per_100g" not in recipe_cols:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN carbs_per_100g REAL DEFAULT 0.0"))

        # recipe_ratings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS recipe_ratings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL REFERENCES users(id),
                recipe_id INTEGER NOT NULL REFERENCES recipes(id),
                rating    INTEGER NOT NULL,
                UNIQUE(user_id, recipe_id)
            )
        """))

        # audit_logs table (CREATE IF NOT EXISTS is idempotent)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                user_id   INTEGER REFERENCES users(id),
                action    TEXT    NOT NULL,
                family_id INTEGER,
                plan_id   INTEGER,
                details   TEXT
            )
        """))

        # Remove meal_plan_items whose recipe was deleted (orphaned FKs)
        conn.execute(text("""
            DELETE FROM meal_plan_items
            WHERE recipe_id NOT IN (SELECT id FROM recipes)
        """))
        # Remove meal_plans that now have no items left
        conn.execute(text("""
            DELETE FROM meal_plans
            WHERE id NOT IN (SELECT DISTINCT meal_plan_id FROM meal_plan_items)
        """))

        conn.commit()
