import uuid
from datetime import UTC, datetime

from app.models.places import Place, PlaceCategory, PlaceStatus
from app.services.mapping import prepare_map_data


def test_prepare_map_data_empty():
    result = prepare_map_data([])
    assert result["places"] == []
    assert result["config"]["center"] == [4.7110, -74.0721]
    assert result["config"]["zoom"] == 12


def test_prepare_map_data_with_places():
    sample_place = Place(
        id=1,
        user_id=uuid.uuid4(),
        name="Monserrate",
        category=PlaceCategory.PARK,
        latitude=4.6056,
        longitude=-74.0555,
        status=PlaceStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        tags=[],
        visits=[],
    )

    result = prepare_map_data([sample_place])
    assert len(result["places"]) == 1
    assert result["places"][0]["name"] == "Monserrate"
    assert result["config"]["center"] == [4.6056, -74.0555]
