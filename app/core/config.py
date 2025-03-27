# app/core/config.py
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
    GEOCODING_USER_AGENT: str = (
        "mapa_planes_generic_agent/1.0"  # Default, override in .env
    )

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


# Instantiate settings
settings = Settings()

# --- Basic Logging Setup ---
log_level = logging.DEBUG if settings.APP_ENV == "development" else logging.INFO
# Basic console logging
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],  # Ensure logs go to console/stdout
)
# You might want to configure file logging for production later
logger = logging.getLogger(__name__)

logger.info(f"Application environment: {settings.APP_ENV}")
if settings.APP_ENV == "development" and settings.DATABASE_URL.startswith("sqlite"):
    logger.info(f"Using local SQLite database: {settings.DATABASE_URL}")
elif settings.SUPABASE_URL:
    logger.info("Using Supabase database.")
else:
    logger.warning(
        "Database configuration unclear. Check APP_ENV, DATABASE_URL, SUPABASE_URL."
    )

if (
    not settings.GEOCODING_USER_AGENT
    or "your_email@example.com" in settings.GEOCODING_USER_AGENT
    or "generic_agent" in settings.GEOCODING_USER_AGENT
):
    logger.warning(
        "IMPORTANT: Update GEOCODING_USER_AGENT in your .env file with a unique app identifier and your contact email for Nominatim."
    )
