import uuid

from postgrest.exceptions import APIError
from supabase import AsyncClient

from app.core.config import logger
from app.models.tags import TagInDB

TAGS_TABLE = "tags"
PLACE_TAGS_TABLE = "place_tags"


async def get_tag_by_name_for_user(
    db: AsyncClient, *, name: str, user_id: uuid.UUID
) -> TagInDB | None:
    """Retrieves a specific tag by name (case-insensitive) for a user asynchronously."""
    clean_name = name.strip().lower()
    if not clean_name:
        return None
    logger.debug(f"CRUD: Getting tag by name '{clean_name}' for user {user_id}")
    try:
        query = (
            db.table(TAGS_TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("name", clean_name)
            .maybe_single()
        )
        response = await query.execute()

        if response.data:
            return TagInDB(**response.data)
        return None
    except APIError as e:
        logger.error(
            f"CRUD: APIError getting tag '{clean_name}' for user {user_id}: {e.message}"
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error getting tag '{clean_name}' for user {user_id}: {e}",
            exc_info=True,
        )
        return None


async def create_tag(
    db: AsyncClient, *, name: str, user_id: uuid.UUID
) -> TagInDB | None:
    """Creates a new tag for a user asynchronously. Name is automatically lowercased."""
    clean_name = name.strip().lower()
    if not clean_name:
        logger.warning(
            f"CRUD: Attempted to create tag with empty name for user {user_id}."
        )
        return None

    logger.info(f"CRUD: Creating tag '{clean_name}' for user {user_id}")
    try:
        tag_data = {"name": clean_name, "user_id": str(user_id)}
        query = db.table(TAGS_TABLE).insert(tag_data)
        response = await query.execute()

        if response.data:
            created_tag = TagInDB(**response.data[0])
            logger.info(
                f"CRUD: Successfully created tag ID {created_tag.id} ('{created_tag.name}')"
            )
            return created_tag
        return None
    except APIError as e:
        # Check for unique constraint violation (PostgreSQL code 23505)
        if e.code == "23505" or "duplicate key" in e.message.lower():
            logger.warning(
                f"CRUD: Tag '{clean_name}' already exists for user {user_id}. Fetching existing."
            )
            return await get_tag_by_name_for_user(
                db=db, name=clean_name, user_id=user_id
            )

        logger.error(f"CRUD: APIError creating tag '{clean_name}': {e.message}")
        return None
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error creating tag '{clean_name}': {e}",
            exc_info=True,
        )
        return None


async def get_tags_for_user(
    db: AsyncClient, *, user_id: uuid.UUID, query: str | None = None
) -> list[TagInDB]:
    """Retrieves all tags for a user asynchronously, optionally filtered by a search query."""
    logger.debug(f"CRUD: Fetching tags for user {user_id}, query: '{query}'")
    try:
        select_query = db.table(TAGS_TABLE).select("*").eq("user_id", str(user_id))

        if query:
            select_query = select_query.ilike("name", f"%{query.strip().lower()}%")

        final_query = select_query.order("name", desc=False)
        response = await final_query.execute()

        tags_validated = []
        if response.data:
            for tag_data in response.data:
                try:
                    tags_validated.append(TagInDB(**tag_data))
                except Exception as validation_error:
                    logger.error(
                        f"CRUD: Validation failed for tag record: {validation_error}"
                    )

        return tags_validated

    except APIError as e:
        logger.error(f"CRUD: APIError fetching tags for user {user_id}: {e.message}")
        return []
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error fetching tags for user {user_id}: {e}",
            exc_info=True,
        )
        return []


async def link_tags_to_place(
    db: AsyncClient, *, place_id: int, tag_ids: list[int]
) -> bool:
    """Creates associations between a place and multiple tags asynchronously."""
    if not tag_ids:
        return True

    logger.info(f"CRUD: Linking tags {tag_ids} to place {place_id}")
    try:
        records_to_insert = [
            {"place_id": place_id, "tag_id": tag_id} for tag_id in tag_ids
        ]
        query = db.table(PLACE_TAGS_TABLE).insert(records_to_insert)
        response = await query.execute()

        if response.data:
            return True
        return False
    except APIError as e:
        if e.code == "23505":
            logger.warning(
                f"CRUD: Some tags already linked to place {place_id}. Ignoring duplicate error."
            )
            return True
        logger.error(f"CRUD: APIError linking tags to place {place_id}: {e.message}")
        return False
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error linking tags to place {place_id}: {e}",
            exc_info=True,
        )
        return False


async def unlink_tags_from_place(
    db: AsyncClient, *, place_id: int, tag_ids: list[int]
) -> bool:
    """Removes associations between a place and multiple tags asynchronously."""
    if not tag_ids:
        return True

    logger.info(f"CRUD: Unlinking tags {tag_ids} from place {place_id}")
    try:
        query = (
            db.table(PLACE_TAGS_TABLE)
            .delete()
            .eq("place_id", place_id)
            .in_("tag_id", tag_ids)
        )
        await query.execute()
        return True
    except APIError as e:
        logger.error(
            f"CRUD: APIError unlinking tags from place {place_id}: {e.message}"
        )
        return False
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error unlinking tags from place {place_id}: {e}",
            exc_info=True,
        )
        return False


async def get_tags_for_place(db: AsyncClient, *, place_id: int) -> list[TagInDB]:
    """Retrieves all tags associated with a specific place asynchronously."""
    logger.debug(f"CRUD: Fetching tags for place ID {place_id}")
    try:
        query = db.table(PLACE_TAGS_TABLE).select("tags(*)").eq("place_id", place_id)
        response = await query.execute()

        tags_validated = []
        if response.data:
            for item in response.data:
                tag_data = item.get("tags")
                if tag_data:
                    try:
                        tags_validated.append(TagInDB(**tag_data))
                    except Exception as validation_error:
                        logger.error(
                            f"CRUD: Validation failed for tag record for place {place_id}: {validation_error}"
                        )

            tags_validated.sort(key=lambda tag: tag.name)

        return tags_validated

    except APIError as e:
        logger.error(f"CRUD: APIError fetching tags for place {place_id}: {e.message}")
        return []
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error fetching tags for place {place_id}: {e}",
            exc_info=True,
        )
        return []
