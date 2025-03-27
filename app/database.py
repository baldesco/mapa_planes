import os
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from supabase import Client as SupabaseClient, create_client

# Ensure config is loaded correctly, handle running as script
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

# --- Local SQLite Setup ---
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
            db_url,
            connect_args={"check_same_thread": False},  # Crucial for FastAPI + SQLite
            echo=False,  # Set True to see generated SQL
        )
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=local_engine
        )
        logger.info(f"Local SQLite engine configured for: {db_url}")
    except Exception as e:
        logger.error(f"Failed to create SQLite engine: {e}", exc_info=True)
        local_engine = None
else:
    logger.debug("Skipping local SQLite setup.")

# --- Supabase Client Setup ---
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    logger.info("Initializing Supabase client...")
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        # Verify connection (optional, e.g., try a simple read)
        # test_resp = supabase.table('places').select('id', head=True).execute() # Example check
        logger.info("Supabase client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
        supabase = None
elif settings.APP_ENV != "development":  # Warn if not dev and Supabase isn't configured
    logger.warning("Supabase URL or Key not found. Supabase client NOT initialized.")


# --- Dependency Functions for FastAPI ---
def get_local_db():
    """FastAPI dependency to get a local SQLite session."""
    if not SessionLocal:
        raise RuntimeError("Local database session (SessionLocal) not initialized.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_supabase_client() -> SupabaseClient:
    """FastAPI dependency to get the initialized Supabase client."""
    if not supabase:
        # If running in an env where Supabase should be available, this is an error
        if settings.APP_ENV != "development" or (
            settings.SUPABASE_URL and settings.SUPABASE_KEY
        ):
            logger.error(
                "Supabase client requested but not initialized. Check config and connectivity."
            )
            raise RuntimeError(
                "Supabase client not initialized. Check environment variables."
            )
        else:
            # If in dev without Supabase configured, maybe raise a specific error or return None?
            # For now, raise error as CRUD expects a client.
            raise RuntimeError(
                "Supabase client not configured for the current environment."
            )
    return supabase


# Choose the primary DB dependency based on environment
if supabase:  # If Supabase IS configured, ALWAYS use it as the primary get_db
    logger.info(
        "Supabase client configured, using get_supabase_client as primary 'get_db'."
    )
    get_db = get_supabase_client
elif IS_LOCAL_SQLITE:  # If Supabase is NOT configured, AND we are in local dev
    logger.warning(
        "Using get_local_db for dependency 'get_db'. NOTE: CRUD functions currently require Supabase."
    )
    # This will still likely fail if endpoints use CRUD, but allows running non-DB endpoints.
    # For full local SQLite, CRUD needs modification.
    get_db = get_local_db  # Use local DB *only* as a fallback if Supabase is absent
    # Consider raising a more informative error immediately if CRUD needs Supabase:
    # def get_db(): raise NotImplementedError("Local SQLite CRUD operations not implemented. Configure Supabase or update CRUD functions.")
else:  # Neither Supabase configured nor local dev SQLite
    logger.error("FATAL: No database configured.")

    def get_db():
        raise RuntimeError("No database configured.")


# --- Function to Create Local Tables (for standalone script) ---
def create_local_tables():
    """Creates SQLite tables if they don't exist, using SQLAlchemy models."""
    if not local_engine:
        logger.error("Local SQLite engine is not initialized. Cannot create tables.")
        return False

    logger.info(f"Checking/creating tables for database: {local_engine.url}")
    try:
        # Import models here to ensure Base is defined
        from . import schemas  # Contains PlaceDB inheriting from Base

        inspector = inspect(local_engine)
        existing_tables = inspector.get_table_names()
        logger.debug(f"Existing tables: {existing_tables}")

        # Base.metadata.create_all handles the check internally (checkfirst=True)
        Base.metadata.create_all(bind=local_engine)

        # Verify creation (optional)
        inspector = inspect(local_engine)  # Re-inspect
        new_tables = inspector.get_table_names()
        logger.info(f"Tables after creation attempt: {new_tables}")
        # Check if expected tables are present
        expected_tables = Base.metadata.tables.keys()
        missing_tables = [t for t in expected_tables if t not in new_tables]
        if not missing_tables:
            logger.info("All expected tables confirmed.")
            return True
        else:
            logger.error(f"Failed to create the following tables: {missing_tables}")
            return False

    except ImportError:
        logger.error(
            "Could not import 'app.schemas'. Ensure it exists and defines SQLAlchemy models.",
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
    print(f"Supabase Configured: {'Yes' if settings.SUPABASE_URL else 'No'}")
    print("-" * 30)

    if IS_LOCAL_SQLITE:
        print("Attempting local SQLite table setup...")
        if create_local_tables():
            print("Local SQLite table setup completed successfully.")
        else:
            print("Local SQLite table setup failed. Check logs.")
    else:
        print(
            "Skipping local SQLite table setup (not development env or not SQLite URL)."
        )

    print("-" * 30)
