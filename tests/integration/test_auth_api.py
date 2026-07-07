import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.core.domain.enums.user_role import UserRole
from auto_parking.core.security.passwords import hash_password
from auto_parking.db.models import Enterprise, User, Vehicle
from auto_parking.db.models.vehicle_model import VehicleModel as VehicleModelOrm

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def seed_user(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    username: str,
    password: str,
    role: UserRole = UserRole.manager,
) -> User:
    async with sessionmaker() as session:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def test_login_returns_jwt_and_cookie_for_existing_user(
    integration_client,
    integration_sessionmaker,
):
    await seed_user(
        integration_sessionmaker,
        username="manager",
        password="secret",
    )

    response = await integration_client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "secret"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert response.cookies.get("access_token") == body["access_token"]


async def test_login_rejects_wrong_password(
    integration_client,
    integration_sessionmaker,
):
    await seed_user(
        integration_sessionmaker,
        username="manager",
        password="secret",
    )

    response = await integration_client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Wrong login or password"


async def test_manager_cookie_auth_applies_real_visibility_from_database(
    authenticated_integration_client,
    integration_sessionmaker,
):
    async with integration_sessionmaker() as session:
        visible_enterprise = Enterprise(
            name="Visible enterprise",
            settlement="Moscow",
            timezone="Europe/Moscow",
        )
        hidden_enterprise = Enterprise(
            name="Hidden enterprise",
            settlement="Kazan",
            timezone="Europe/Moscow",
        )
        model = VehicleModelOrm(
            name="Solaris",
            type="sedan",
            horse_powers=123,
            seats_number=5,
            fuel_capacity_liters=50,
        )
        manager = User(
            username="manager",
            password_hash=hash_password("secret"),
            role=UserRole.manager,
        )
        manager.enterprises.append(visible_enterprise)
        session.add_all([visible_enterprise, hidden_enterprise, model, manager])
        await session.commit()
        await session.refresh(visible_enterprise)
        await session.refresh(hidden_enterprise)
        await session.refresh(model)

        visible_vehicle = Vehicle(
            price=1_500_000,
            mileage=12_000,
            vehicle_number="А111АА77",
            owners_count=1,
            accident_number=0,
            manufacture_year=2022,
            model_id=model.id,
            enterprise_id=visible_enterprise.id,
            color="white",
        )
        hidden_vehicle = Vehicle(
            price=1_600_000,
            mileage=8_000,
            vehicle_number="А222АА77",
            owners_count=1,
            accident_number=0,
            manufacture_year=2023,
            model_id=model.id,
            enterprise_id=hidden_enterprise.id,
            color="black",
        )
        session.add_all([visible_vehicle, hidden_vehicle])
        await session.commit()
        await session.refresh(visible_vehicle)
        await session.refresh(hidden_vehicle)

    login_response = await authenticated_integration_client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "secret"},
    )
    assert login_response.status_code == 200

    list_response = await authenticated_integration_client.get("/api/vehicles")
    assert list_response.status_code == 200
    assert [vehicle["id"] for vehicle in list_response.json()] == [visible_vehicle.id]

    hidden_response = await authenticated_integration_client.get(
        f"/api/vehicles/{hidden_vehicle.id}",
    )
    assert hidden_response.status_code == 403
