from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.models.places import Place, PlaceCategory, PlaceStatus


@pytest.mark.asyncio
async def test_check_duplicate_api(client: AsyncClient, mock_user):
    sample_place = Place(
        id=42,
        user_id=mock_user.id,
        name="Cafe San Alberto",
        category=PlaceCategory.RESTAURANT,
        latitude=4.6534,
        longitude=-74.0567,
        status=PlaceStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        tags=[],
        visits=[],
    )

    with patch(
        "app.routers.api_places.crud_places.check_for_potential_duplicates",
        return_value=[sample_place],
    ):
        response = await client.post(
            "/api/v1/places/check-duplicate",
            json={
                "name": "Cafe San Alberto",
                "latitude": 4.6534,
                "longitude": -74.0567,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 42
        assert data[0]["name"] == "Cafe San Alberto"
