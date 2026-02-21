from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import AsyncClient

from app.auth.dependencies import get_current_active_user, get_db
from app.core.config import logger
from app.crud import tags as crud_tags
from app.models import tags as models_tags
from app.models.auth import UserInToken

router = APIRouter(prefix="/api/v1/tags", tags=["API - Tags"])


@router.get("/", response_model=list[models_tags.Tag])
async def list_tags_api(
    db: Annotated[AsyncClient, Depends(get_db)],
    current_user: Annotated[UserInToken, Depends(get_current_active_user)],
    query: Annotated[
        str | None,
        Query(description="Search query to filter tags by name (case-insensitive)."),
    ] = None,
):
    """
    API endpoint to list tags for the authenticated user.
    Can be used for tag suggestions in input fields.
    """
    logger.info(
        f"API List tags request for user {current_user.email}, Query: '{query}'"
    )
    try:
        tags_db = await crud_tags.get_tags_for_user(
            db=db, user_id=current_user.id, query=query
        )
        # Convert TagInDB to Tag (though they might be identical here)
        return [models_tags.Tag(**tag.model_dump()) for tag in tags_db]
    except Exception as e:
        logger.error(
            f"API Error listing tags for user {current_user.email}: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tags.",
        ) from None


# Potential future endpoints (not strictly required by current plan but good practice):
# POST /: Create a new tag (though creation happens implicitly in update_place)
# DELETE /{tag_id}: Delete an unused tag (requires checking place_tags)
