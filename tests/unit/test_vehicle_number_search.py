from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import postgresql

from auto_parking.app.filter import VehicleFilter
from auto_parking.infrastructure.db.repositories.vehicle import VehicleRepository

pytestmark = pytest.mark.asyncio


async def test_vehicle_number_prefix_uses_normalized_like_query():
    db = AsyncMock()
    result = Mock()
    result.unique.return_value.scalars.return_value.all.return_value = []
    db.execute.return_value = result
    repo = VehicleRepository(db)

    await repo.get(
        VehicleFilter(
            vehicle_number_prefix=" а123 ",
            load_relations=False,
        )
    )

    stmt = db.execute.await_args.args[0]
    compiled = str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert "vehicle.vehicle_number LIKE 'А123%%'" in compiled
    assert "ILIKE" not in compiled
