from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.models.tags import TagInDB


@pytest.mark.asyncio
async def test_list_tags_endpoint(client: AsyncClient, mock_user):
    now = datetime.now(UTC)
    sample_tags = [
        TagInDB(id=1, name="cafe", user_id=mock_user.id, created_at=now),
        TagInDB(id=2, name="rooftop", user_id=mock_user.id, created_at=now),
    ]

    with patch(
        "app.routers.api_tags.crud_tags.get_tags_for_user",
        return_value=sample_tags,
    ):
        response = await client.get("/api/v1/tags/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "cafe"
        assert data[1]["name"] == "rooftop"
