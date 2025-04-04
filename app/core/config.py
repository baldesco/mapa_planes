import logging
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import List

# Load .env file explicitly for flexibility
load_dotenv()


class Settings(BaseSettings):
    """Application configuration settings."""

    APP_ENV: str = "development"
    SUPABASE_URL: str | None = None
    SUPABASE_KEY: str | None = None  # anon public key
    SUPABASE_SERVICE_ROLE_KEY: str | None = (
        None  # Use with caution for admin tasks like deleting storage objects
    )
    SUPABASE_BUCKET_NAME: str = "place-images"
    OPENCAGE_API_KEY: str | None = None

    # --- JWT Settings ---
    # Generate a strong secret key: openssl rand -hex 32
    SECRET_KEY: str = "default_super_secret_key_replace_me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # --- CORS ---
    # List of allowed origins for CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]  # Adjust for production

    # Pydantic V2 configuration
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
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
    if not settings.SUPABASE_SERVICE_ROLE_KEY and settings.APP_ENV != "development":
        logger.warning(
            "SUPABASE_SERVICE_ROLE_KEY is not set. Certain operations (like cross-user storage deletion) might require it."
        )
    elif not settings.SUPABASE_SERVICE_ROLE_KEY and settings.APP_ENV == "development":
        logger.info("SUPABASE_SERVICE_ROLE_KEY is not set (optional for dev).")

else:
    logger.critical(
        "Supabase URL or Key NOT configured. Application cannot function without Supabase."
    )
    # Consider raising an exception here if Supabase is absolutely required at startup
    # raise ValueError("Supabase URL and Key must be configured in .env")

if not settings.OPENCAGE_API_KEY:
    logger.warning("OPENCAGE_API_KEY is missing in .env. Geocoding will not function.")
else:
    logger.info("OpenCage API Key found.")

if (
    settings.SECRET_KEY == "default_super_secret_key_replace_me"
    and settings.APP_ENV != "development"
):
    logger.critical(
        "FATAL: Default SECRET_KEY is being used in a non-development environment. Please generate and set a secure SECRET_KEY in .env."
    )
    # raise ValueError("A secure SECRET_KEY must be set for non-development environments.")
elif settings.SECRET_KEY == "default_super_secret_key_replace_me":
    logger.warning(
        "Using default SECRET_KEY for development. Generate a real key for production."
    )


logger.info(f"Access token expiration: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
logger.info(f"CORS origins: {settings.BACKEND_CORS_ORIGINS}")

IS_LOCAL_SQLITE = False
logger.info("Configuration loaded. Database backend set to Supabase.")
