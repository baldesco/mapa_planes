import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import (
    sessionmaker,
    declarative_base,
)
from supabase import create_client, Client as SupabaseClient

# Ensure config is loaded correctly
try:
    from .core.config import settings, logger
except ImportError:
    # Adjust path for standalone script execution
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from app.core.config import settings, logger


# --- SQLAlchemy Base for local models ---
Base = declarative_base()


# --- Constants ---
IS_LOCAL_SQLITE = (
    settings.APP_ENV == "development" and settings.DATABASE_URL.startswith("sqlite")
)

# --- Global Variables ---
local_engine = None
SessionLocal = None
supabase: SupabaseClient | None = None

# --- Supabase Client Setup (Attempt first) ---
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    logger.info("Attempting to initialize Supabase client...")
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        # Optional: Add a quick check here to see if connection works
        # e.g., supabase.table('places').select('id', head=True).execute()
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
        supabase = None
else:
    logger.info(
        "Supabase URL or Key not provided, skipping Supabase client initialization."
    )


# --- Local SQLite Setup (Attempt if relevant and Supabase failed/absent) ---
if IS_LOCAL_SQLITE:
    db_url = settings.DATABASE_URL
    db_path = db_url.replace("sqlite:///", "")  # Simple path extraction
    db_dir = os.path.dirname(db_path)

    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"Created directory for SQLite database: {db_dir}")
        except OSError as e:
            logger.error(f"Failed to create directory {db_dir}: {e}")

    try:
        local_engine = create_engine(
            db_url, connect_args={"check_same_thread": False}, echo=False
        )
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=local_engine
        )
        logger.info(f"Local SQLite engine configured for: {db_url}")
    except Exception as e:
        logger.error(f"Failed to create SQLite engine: {e}", exc_info=True)
        local_engine = None
else:
    logger.debug("Skipping local SQLite setup (not development env or not SQLite URL).")


# --- Dependency Functions for FastAPI ---
def get_local_db():
    """FastAPI dependency to get a local SQLite session."""
    if not SessionLocal:
        logger.error(
            "Dependency Error: Request for local DB session, but SessionLocal is not initialized."
        )
        raise RuntimeError("Local database session (SessionLocal) not initialized.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_supabase_client() -> SupabaseClient:
    """FastAPI dependency to get the initialized Supabase client."""
    if not supabase:
        logger.error(
            "Dependency Error: Request for Supabase client, but it's not initialized."
        )
        raise RuntimeError(
            "Supabase client not initialized. Check config and connectivity."
        )
    return supabase


# --- Determine the primary 'get_db' dependency ---
# PRIORITIZE Supabase if it's configured, as CRUD is written for it.
if supabase:
    logger.info(
        "Using Supabase client (get_supabase_client) as the primary 'get_db' dependency."
    )
    get_db = get_supabase_client
elif (
    IS_LOCAL_SQLITE and SessionLocal
):  # Fallback to SQLite ONLY if Supabase is absent AND local is configured
    logger.warning(
        "Supabase client NOT available. Falling back to local SQLite 'get_local_db'."
    )
    logger.warning(
        "NOTE: Current CRUD functions expect Supabase. Endpoints using CRUD will likely fail!"
    )
    # Assign local DB, but be aware of the limitation
    get_db = get_local_db
    # Alternatively, raise a configuration error immediately if CRUD must work:
    # def get_db(): raise RuntimeError("Application requires Supabase configuration for database operations, but it's missing.")
else:  # No working database configuration found
    logger.critical(
        "FATAL: No database client available (Supabase not configured/failed, local SQLite not configured/failed)."
    )

    def get_db():
        raise RuntimeError("No functional database connection available.")


# --- Function to Create Local Tables (for standalone script) ---
def create_local_tables():
    """Creates SQLite tables if they don't exist, using SQLAlchemy models."""
    if not local_engine:
        logger.error("Local SQLite engine is not initialized. Cannot create tables.")
        return False

    logger.info(f"Checking/creating tables for database: {local_engine.url}")
    try:
        # Import models here, works when run as module or script if path correct
        # Using absolute import based on expected structure when run via `-m`
        from app import schemas  # Contains PlaceDB inheriting from Base

        inspector = inspect(local_engine)
        existing_tables = inspector.get_table_names()
        logger.debug(f"Existing tables: {existing_tables}")

        Base.metadata.create_all(bind=local_engine)  # checkfirst=True is default

        inspector = inspect(local_engine)  # Re-inspect
        new_tables = inspector.get_table_names()
        logger.info(f"Tables after creation attempt: {new_tables}")
        expected_tables = Base.metadata.tables.keys()
        missing_tables = [t for t in expected_tables if t not in new_tables]
        if not missing_tables:
            logger.info("All expected tables confirmed.")
            return True
        else:
            logger.error(f"Failed to create the following tables: {missing_tables}")
            return False

    except ImportError as e:
        logger.error(
            f"Could not import 'app.schemas'. Ensure it exists and check Python path. Error: {e}",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(f"Error during local table creation: {e}", exc_info=True)
        return False


# --- Main execution block for standalone script ---
if __name__ == "__main__":
    print("-" * 30)
    print("Running Database Setup Script")
    print(f"Environment: {settings.APP_ENV}")
    print(f"Local DB URL: {settings.DATABASE_URL}")
    print(
        f"Supabase Configured: {'Yes' if settings.SUPABASE_URL and settings.SUPABASE_KEY else 'No'}"
    )
    print(f"Supabase Client Initialized: {'Yes' if supabase else 'No'}")
    print(f"Local SQLite Engine Initialized: {'Yes' if local_engine else 'No'}")
    print("-" * 30)

    if IS_LOCAL_SQLITE:
        print("Attempting local SQLite table setup...")
        if create_local_tables():
            print("Local SQLite table setup completed successfully.")
        else:
            print("Local SQLite table setup failed. Check logs above.")
    else:
        print(
            "Skipping local SQLite table setup (not development env or not SQLite URL)."
        )

    print("-" * 30)
