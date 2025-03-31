import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file explicitly for flexibility
load_dotenv()


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_ENV: str = "development"
    DATABASE_URL: str = "sqlite:///./local_mapa_planes.db"
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None  # Use with caution
    SUPABASE_BUCKET_NAME: str = "place-images"
    OPENCAGE_API_KEY: str | None = None

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Instantiate settings
settings = Settings()

# --- Basic Logging Setup ---
log_level = logging.DEBUG if settings.APP_ENV == "development" else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)  # Get logger for the current module context

# --- Initial Config Logging ---
logger.info(f"Application environment: {settings.APP_ENV}")
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    logger.info("Supabase configured: URL and Key found.")
elif settings.APP_ENV != "development":
    logger.warning(
        "Supabase NOT configured (URL or Key missing) in non-development environment."
    )

if (
    IS_LOCAL_SQLITE := settings.APP_ENV == "development"
    and settings.DATABASE_URL.startswith("sqlite")
):
    logger.info(f"Local SQLite configured: {settings.DATABASE_URL}")
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        logger.info(
            "Supabase is also configured; it will be prioritized for DB operations."
        )
    else:
        logger.warning(
            "Local SQLite is configured, but Supabase is not. CRUD operations expecting Supabase may fail."
        )
else:
    logger.debug("Local SQLite is not configured for the current environment.")


if not settings.OPENCAGE_API_KEY:
    logger.warning("OPENCAGE_API_KEY is missing in .env. Geocoding will not function.")
