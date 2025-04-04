from fastapi import APIRouter, Query, Depends, HTTPException, status

from app.services.geocoding import perform_geocode
from app.models.general import GeocodeResult
from app.core.config import logger, settings  # Import settings to check geocoder key

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
)
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


# Note: Moved geocode endpoint here as it's more of a system utility/service API
@router.get(
    "/api/v1/geocode",  # Keep the API path for consistency if used externally
    response_model=GeocodeResult,
    summary="Geocode Address (API)",
    dependencies=[Depends(lambda: None)]
    if not settings.OPENCAGE_API_KEY
    else [],  # Optional: Disable if no key
)
async def geocode_address_endpoint(address: str = Query(..., min_length=3)):
    """Geocodes a given address string using OpenCage."""
    if not settings.OPENCAGE_API_KEY:
        logger.error("Geocode endpoint called but OPENCAGE_API_KEY is not set.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Geocoding service is not configured.",
        )

    logger.info(f"API Geocoding request for: '{address}'")
    # Use the geocoding service function
    result = await perform_geocode(address)
    # perform_geocode raises HTTPException on failure, so no need to check None here
    return result
