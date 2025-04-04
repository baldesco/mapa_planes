import asyncio
from fastapi import HTTPException, status
from opencage.geocoder import OpenCageGeocode, RateLimitExceededError

from app.core.config import settings, logger
from app.models.general import GeocodeResult

# --- Geocoder Setup ---
geocoder: OpenCageGeocode | None = None
if not settings.OPENCAGE_API_KEY:
    logger.warning(
        "OPENCAGE_API_KEY is not set. Geocoding service will be unavailable."
    )
else:
    try:
        geocoder = OpenCageGeocode(settings.OPENCAGE_API_KEY)
        logger.info("OpenCage Geocoder initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize OpenCage Geocoder: {e}", exc_info=True)


async def perform_geocode(address: str) -> GeocodeResult | None:
    """Performs geocoding using OpenCage Geocoder. Raises HTTPException on failure."""
    if not geocoder:
        logger.error("Geocoding skipped: OpenCage Geocoder not initialized.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service is not configured or API key missing.",
        )
    try:
        logger.debug(f"Geocoding address with OpenCage: '{address}'")
        # Run synchronous geocode call in a separate thread
        results = await asyncio.to_thread(
            geocoder.geocode,
            address,
            key=settings.OPENCAGE_API_KEY,
            language="es",
            countrycode="co",
            limit=1,
            no_annotations=1,
            timeout=15,
        )

        if results and len(results):
            best_result = results[0]
            components = best_result.get("components", {})
            geometry = best_result.get("geometry", {})
            formatted_address = best_result.get("formatted")

            if geometry and "lat" in geometry and "lng" in geometry:
                city = components.get(
                    "city",
                    components.get(
                        "town",
                        components.get("village", components.get("state_district")),
                    ),
                )
                country = components.get("country")
                road = components.get("road")
                house_number = components.get("house_number")
                neighbourhood = components.get("neighbourhood")
                street_address_parts = filter(None, [house_number, road, neighbourhood])
                street_address = ", ".join(street_address_parts)

                result = GeocodeResult(
                    latitude=geometry["lat"],
                    longitude=geometry["lng"],
                    address=street_address or None,
                    city=city,
                    country=country,
                    display_name=formatted_address,
                )
                logger.debug(f"OpenCage geocoding successful: {formatted_address}")
                return result
            else:
                logger.warning(
                    f"OpenCage result missing geometry for '{address}'. Data: {best_result}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Geocoding result lacks coordinate data.",
                )
        else:
            logger.warning(f"OpenCage geocoding failed: No results for '{address}'")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found by geocoder.",
            )
    except RateLimitExceededError:
        logger.error("OpenCage API rate limit exceeded.")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Geocoding limit reached. Please try again later.",
        )
    except HTTPException as http_exc:
        raise http_exc  # Re-raise known HTTP exceptions
    except asyncio.TimeoutError:
        logger.error(f"OpenCage geocoding timed out for address: '{address}'")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Geocoding request timed out.",
        )
    except Exception as e:
        logger.error(
            f"OpenCage geocoding unexpected error for '{address}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during geocoding.",
        )
