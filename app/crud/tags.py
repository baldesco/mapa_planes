import uuid
import asyncio
from typing import List, Optional
from supabase import Client as SupabaseClient
from postgrest import APIResponse, APIError

from app.core.config import logger
from app.models.tags import TagCreate, TagInDB  # Assuming TagCreate is just name

TAGS_TABLE = "tags"
PLACE_TAGS_TABLE = "place_tags"


async def get_tag_by_name_for_user(
    db: SupabaseClient, *, name: str, user_id: uuid.UUID
) -> TagInDB | None:
    """Retrieves a specific tag by name (case-insensitive) for a user."""
    clean_name = name.strip().lower()
    if not clean_name:
        return None
    logger.debug(f"CRUD: Getting tag by name '{clean_name}' for user {user_id}")
    try:
        query = (
            db.table(TAGS_TABLE)
            .select("*")
            .eq("user_id", str(user_id))
            .eq("name", clean_name)  # Name is stored lowercase due to trigger
            .maybe_single()
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        # ** FIX: Check for response attribute before accessing .data **
        if hasattr(response, "data") and response.data:
            return TagInDB(**response.data)
        else:
            # Log if error occurred, otherwise just not found
            if hasattr(response, "error") and response.error:
                logger.error(
                    f"CRUD: Error fetching tag '{clean_name}' for user {user_id}: {response.error.message}"
                )
            # ** FIX: Handle potential None response object **
            elif response is None:
                logger.warning(
                    f"CRUD: Supabase response was None when fetching tag '{clean_name}' for user {user_id}."
                )
            return None
    except APIError as e:
        logger.error(
            f"CRUD: APIError getting tag '{clean_name}' for user {user_id}: {e.message}",
            exc_info=False,
        )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error getting tag '{clean_name}' for user {user_id}: {e}",
            exc_info=True,
        )
        return None


async def create_tag(
    db: SupabaseClient, *, name: str, user_id: uuid.UUID
) -> TagInDB | None:
    """Creates a new tag for a user. Name is automatically lowercased."""
    clean_name = name.strip().lower()
    if not clean_name:
        logger.warning(
            f"CRUD: Attempted to create tag with empty name for user {user_id}."
        )
        return None

    logger.info(f"CRUD: Creating tag '{clean_name}' for user {user_id}")
    try:
        tag_data = {"name": clean_name, "user_id": str(user_id)}
        # ** FIX: Execute insert first, then select if needed (or rely on return preference) **
        # Option 1: Use 'return=representation' preference (simpler)
        query = db.table(TAGS_TABLE).insert(
            tag_data, returning="representation"
        )  # Use returning preference
        response: APIResponse = await asyncio.to_thread(query.execute)

        # Option 2: Insert then Select (more explicit if representation fails)
        # query_insert = db.table(TAGS_TABLE).insert(tag_data)
        # response_insert = await asyncio.to_thread(query_insert.execute)
        # if not response_insert.data: # Check if insert succeeded (might need error check too)
        #     # Handle insert failure...
        #     pass
        # # If insert succeeded, select the newly created tag (less efficient)
        # query_select = db.table(TAGS_TABLE).select("*").eq("user_id", str(user_id)).eq("name", clean_name).single()
        # response = await asyncio.to_thread(query_select.execute)

        if response.data:
            created_tag = TagInDB(**response.data[0])
            logger.info(
                f"CRUD: Successfully created tag ID {created_tag.id} ('{created_tag.name}') for user {user_id}"
            )
            return created_tag
        else:
            error_detail = (
                "Insert failed, possibly RLS violation, duplicate tag, or DB error."
            )
            if hasattr(response, "error") and response.error:
                # Check for unique constraint violation (PostgreSQL code 23505)
                if getattr(response.error, "code", "") == "23505":
                    logger.warning(
                        f"CRUD: Tag '{clean_name}' already exists for user {user_id}. Fetching existing."
                    )
                    # Attempt to fetch the existing tag if creation failed due to duplicate
                    return await get_tag_by_name_for_user(
                        db=db, name=clean_name, user_id=user_id
                    )
                else:
                    error_detail = getattr(
                        response.error, "message", str(response.error)
                    )
            logger.error(
                f"CRUD: Failed to create tag '{clean_name}' for user {user_id}: {error_detail}"
            )
            return None
    except APIError as e:
        # Handle potential API errors during insert or select
        logger.error(
            f"CRUD: APIError creating tag '{clean_name}' for user {user_id}: {e.message}",
            exc_info=False,
        )
        # Check if it was a duplicate error that wasn't caught above
        if (
            "duplicate key value violates unique constraint" in e.message.lower()
            and "tags_user_id_name_key" in e.message.lower()
        ):
            logger.warning(
                f"CRUD: Tag '{clean_name}' already exists for user {user_id} (caught in APIError). Fetching existing."
            )
            return await get_tag_by_name_for_user(
                db=db, name=clean_name, user_id=user_id
            )
        return None
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error creating tag '{clean_name}' for user {user_id}: {e}",
            exc_info=True,
        )
        return None


async def get_tags_for_user(
    db: SupabaseClient, *, user_id: uuid.UUID, query: Optional[str] = None
) -> List[TagInDB]:
    """Retrieves all tags for a user, optionally filtered by a search query (case-insensitive)."""
    logger.debug(f"CRUD: Fetching tags for user {user_id}, query: '{query}'")
    try:
        select_query = db.table(TAGS_TABLE).select("*").eq("user_id", str(user_id))

        if query:
            # Use ilike for case-insensitive partial matching
            select_query = select_query.ilike("name", f"%{query.strip().lower()}%")

        final_query = select_query.order("name", desc=False)  # Order alphabetically
        response: APIResponse = await asyncio.to_thread(final_query.execute)

        tags_validated = []
        if response.data:
            for tag_data in response.data:
                try:
                    tags_validated.append(TagInDB(**tag_data))
                except Exception as validation_error:
                    logger.error(
                        f"CRUD: Pydantic validation failed for tag record for user {user_id}. Data: {tag_data}. Error: {validation_error}",
                        exc_info=False,
                    )
            logger.debug(
                f"CRUD: Found {len(tags_validated)} tags for user {user_id} matching query '{query}'."
            )
        elif hasattr(response, "error") and response.error:
            logger.error(
                f"CRUD: Error fetching tags for user {user_id}: {response.error.message}"
            )
        else:
            logger.debug(
                f"CRUD: No tags found for user {user_id} matching query '{query}'."
            )

        return tags_validated

    except APIError as e:
        logger.error(
            f"CRUD: APIError fetching tags for user {user_id}: {e.message}",
            exc_info=False,
        )
        return []
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error fetching tags for user {user_id}: {e}",
            exc_info=True,
        )
        return []


async def link_tags_to_place(
    db: SupabaseClient, *, place_id: int, tag_ids: List[int]
) -> bool:
    """Creates associations between a place and multiple tags."""
    if not tag_ids:
        return True  # Nothing to link

    logger.info(f"CRUD: Linking tags {tag_ids} to place {place_id}")
    try:
        records_to_insert = [
            {"place_id": place_id, "tag_id": tag_id} for tag_id in tag_ids
        ]
        # ** FIX: Add returning='minimal' to potentially avoid large data return on success **
        query = db.table(PLACE_TAGS_TABLE).insert(
            records_to_insert, returning="minimal"
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        # Check for errors first
        if hasattr(response, "error") and response.error:
            error_detail = getattr(response.error, "message", str(response.error))
            # Ignore duplicate key errors during linking (might happen in concurrent requests)
            if getattr(response.error, "code", "") == "23505":
                logger.warning(
                    f"CRUD: Attempted to link duplicate tags to place {place_id}. Ignoring duplicate errors."
                )
                # Check if *any* data was returned (meaning at least some links succeeded if duplicates were ignored)
                if response.data:
                    logger.info(
                        f"CRUD: Successfully linked some non-duplicate tags to place {place_id}."
                    )
                    return True
                else:  # No data and duplicate error likely means all were duplicates
                    return True  # Still consider it success if only duplicates failed
            else:
                logger.error(
                    f"CRUD: Failed to link tags {tag_ids} to place {place_id}: {error_detail}"
                )
                return False
        elif response.data:
            logger.info(
                f"CRUD: Successfully linked {len(response.data)} tags to place {place_id}."
            )
            return True
        else:
            # No error, no data -> This case might indicate RLS prevented insert without raising error
            logger.warning(
                f"CRUD: Linking tags {tag_ids} to place {place_id} affected 0 rows and returned no error. Check RLS."
            )
            return False  # Treat as failure if 0 rows affected without specific duplicate error
    except APIError as e:
        logger.error(
            f"CRUD: APIError linking tags to place {place_id}: {e.message}",
            exc_info=False,
        )
        return False
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error linking tags to place {place_id}: {e}",
            exc_info=True,
        )
        return False


async def unlink_tags_from_place(
    db: SupabaseClient, *, place_id: int, tag_ids: List[int]
) -> bool:
    """Removes associations between a place and multiple tags."""
    if not tag_ids:
        return True  # Nothing to unlink

    logger.info(f"CRUD: Unlinking tags {tag_ids} from place {place_id}")
    try:
        # ** FIX: Add returning='minimal' **
        query = (
            db.table(PLACE_TAGS_TABLE)
            .delete(returning="minimal")
            .eq("place_id", place_id)
            .in_("tag_id", tag_ids)
        )
        response: APIResponse = await asyncio.to_thread(query.execute)

        if hasattr(response, "error") and response.error:
            error_detail = getattr(response.error, "message", str(response.error))
            logger.error(
                f"CRUD: Failed to unlink tags {tag_ids} from place {place_id}: {error_detail}"
            )
            return False
        elif response.data:
            logger.info(
                f"CRUD: Successfully unlinked {len(response.data)} tags from place {place_id}."
            )
            return True
        else:
            logger.warning(
                f"CRUD: Unlink tags command for place {place_id} affected 0 rows. Tags might have been already unlinked."
            )
            return True  # Consider this success

    except APIError as e:
        logger.error(
            f"CRUD: APIError unlinking tags from place {place_id}: {e.message}",
            exc_info=False,
        )
        return False
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error unlinking tags from place {place_id}: {e}",
            exc_info=True,
        )
        return False


async def get_tags_for_place(db: SupabaseClient, *, place_id: int) -> List[TagInDB]:
    """Retrieves all tags associated with a specific place."""
    logger.debug(f"CRUD: Fetching tags for place ID {place_id}")
    try:
        query = db.table(PLACE_TAGS_TABLE).select("tags(*)").eq("place_id", place_id)
        response: APIResponse = await asyncio.to_thread(query.execute)

        tags_validated = []
        if response.data:
            for item in response.data:
                tag_data = item.get("tags")
                if tag_data:
                    try:
                        tags_validated.append(TagInDB(**tag_data))
                    except Exception as validation_error:
                        logger.error(
                            f"CRUD: Pydantic validation failed for tag record for place {place_id}. Data: {tag_data}. Error: {validation_error}",
                            exc_info=False,
                        )
            # Sort tags alphabetically before returning
            tags_validated.sort(key=lambda tag: tag.name)
            logger.debug(
                f"CRUD: Found {len(tags_validated)} tags for place {place_id}."
            )
        elif hasattr(response, "error") and response.error:
            logger.error(
                f"CRUD: Error fetching tags for place {place_id}: {response.error.message}"
            )
        else:
            logger.debug(f"CRUD: No tags found for place {place_id}.")

        return tags_validated

    except APIError as e:
        logger.error(
            f"CRUD: APIError fetching tags for place {place_id}: {e.message}",
            exc_info=False,
        )
        return []
    except Exception as e:
        logger.error(
            f"CRUD: Unexpected error fetching tags for place {place_id}: {e}",
            exc_info=True,
        )
        return []
