import asyncio
from typing import Optional
from timezonefinder import TimezoneFinder  # type: ignore

from app.core.config import logger

# Initialize TimezoneFinder. It loads data on first use, so can be slow initially.
# It's thread-safe after initialization.
_tf: Optional[TimezoneFinder] = None


async def _init_timezone_finder() -> TimezoneFinder:
    """Initializes the TimezoneFinder instance if not already done."""
    global _tf
    if _tf is None:
        logger.info("Initializing TimezoneFinder...")
        # Running synchronous TimezoneFinder() in a thread to avoid blocking asyncio loop
        _tf = await asyncio.to_thread(TimezoneFinder)
        logger.info("TimezoneFinder initialized.")
    return _tf


async def get_timezone_from_coordinates(
    latitude: float, longitude: float
) -> Optional[str]:
    """
    Gets the IANA timezone string from latitude and longitude.
    Returns None if the timezone cannot be determined or for invalid coordinates.
    """
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        logger.warning(
            f"Invalid coordinates for timezone lookup: lat={latitude}, lon={longitude}"
        )
        return None

    try:
        tf_instance = await _init_timezone_finder()
        # timezone_at is synchronous, run in thread
        timezone_str = await asyncio.to_thread(
            tf_instance.timezone_at, lat=latitude, lng=longitude
        )
        if timezone_str:
            logger.debug(
                f"Timezone found for ({latitude}, {longitude}): {timezone_str}"
            )
            return timezone_str
        else:
            logger.warning(
                f"No timezone found for coordinates: ({latitude}, {longitude})"
            )
            return None
    except Exception as e:
        logger.error(
            f"Error finding timezone for ({latitude}, {longitude}): {e}", exc_info=True
        )
        return None
