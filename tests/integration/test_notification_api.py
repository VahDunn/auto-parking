from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auto_parking.core.domain.enums import NotificationType, UserRole
from auto_parking.core.security.passwords import hash_password
from auto_parking.db.models import Enterprise, Notification, Trip, User, Vehicle
from auto_parking.db.models.vehicle_model import VehicleModel as VehicleModelOrm
from auto_parking.repo.vehicle_track import VehicleTrackRepository

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def seed_notification_flow(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> tuple[User, list[Notification], Notification]:
    async with sessionmaker() as session:
        enterprise = Enterprise(
            name="Notification enterprise",
            settlement="Moscow",
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
        other_manager = User(
            username="other-manager",
            password_hash=hash_password("secret"),
            role=UserRole.manager,
        )
        manager.enterprises.append(enterprise)
        other_manager.enterprises.append(enterprise)
        session.add_all([enterprise, model, manager, other_manager])
        await session.commit()
        await session.refresh(enterprise)
        await session.refresh(model)
        await session.refresh(manager)
        await session.refresh(other_manager)

        vehicle = Vehicle(
            price=1_500_000,
            mileage=12_000,
            vehicle_number="А444АА77",
            owners_count=1,
            accident_number=0,
            manufacture_year=2022,
            model_id=model.id,
            enterprise_id=enterprise.id,
            color="white",
        )
        session.add(vehicle)
        await session.commit()
        await session.refresh(vehicle)

        started_at = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
        points = await VehicleTrackRepository(session).create_many(
            [
                {
                    "vehicle_id": vehicle.id,
                    "recorded_at_utc": started_at,
                    "latitude": 55.751244,
                    "longitude": 37.618423,
                },
                {
                    "vehicle_id": vehicle.id,
                    "recorded_at_utc": started_at + timedelta(minutes=5),
                    "latitude": 55.752,
                    "longitude": 37.62,
                },
                {
                    "vehicle_id": vehicle.id,
                    "recorded_at_utc": started_at + timedelta(minutes=10),
                    "latitude": 55.753,
                    "longitude": 37.621,
                },
                {
                    "vehicle_id": vehicle.id,
                    "recorded_at_utc": started_at + timedelta(minutes=15),
                    "latitude": 55.754,
                    "longitude": 37.622,
                },
            ]
        )

        trips = [
            Trip(
                vehicle_id=vehicle.id,
                started_at_utc=points[0].recorded_at_utc,
                ended_at_utc=points[1].recorded_at_utc,
                start_point_id=points[0].id,
                end_point_id=points[1].id,
            ),
            Trip(
                vehicle_id=vehicle.id,
                started_at_utc=points[2].recorded_at_utc,
                ended_at_utc=points[3].recorded_at_utc,
                start_point_id=points[2].id,
                end_point_id=points[3].id,
            ),
        ]
        session.add_all(trips)
        await session.commit()
        for trip in trips:
            await session.refresh(trip)

        own_notifications = [
            Notification(
                recipient_user_id=manager.id,
                enterprise_id=enterprise.id,
                trip_id=trips[0].id,
                type=NotificationType.trip_created,
                title="Новая поездка",
                body="Оформлена новая поездка автомобиля А444АА77",
                payload={"trip_id": trips[0].id, "vehicle_number": "А444АА77"},
            ),
            Notification(
                recipient_user_id=manager.id,
                enterprise_id=enterprise.id,
                trip_id=trips[1].id,
                type=NotificationType.trip_created,
                title="Новая поездка",
                body="Оформлена новая поездка автомобиля А444АА77",
                payload={"trip_id": trips[1].id, "vehicle_number": "А444АА77"},
            ),
        ]
        other_notification = Notification(
            recipient_user_id=other_manager.id,
            enterprise_id=enterprise.id,
            trip_id=trips[0].id,
            type=NotificationType.trip_created,
            title="Новая поездка",
            body="Оформлена новая поездка автомобиля А444АА77",
            payload={"trip_id": trips[0].id, "vehicle_number": "А444АА77"},
        )
        session.add_all([*own_notifications, other_notification])
        await session.commit()
        for notification in [*own_notifications, other_notification]:
            await session.refresh(notification)

        return manager, own_notifications, other_notification


async def test_notification_api_lists_marks_one_and_marks_all_for_logged_in_manager(
    authenticated_integration_client,
    integration_sessionmaker,
):
    manager, own_notifications, other_notification = await seed_notification_flow(
        integration_sessionmaker,
    )

    login_response = await authenticated_integration_client.post(
        "/api/auth/login",
        json={"username": manager.username, "password": "secret"},
    )
    assert login_response.status_code == 200

    count_response = await authenticated_integration_client.get("/api/notifications/unread-count")
    assert count_response.status_code == 200
    assert count_response.json() == {"unread_count": 2}

    list_response = await authenticated_integration_client.get(
        "/api/notifications",
        params={"unread_only": "true"},
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert {item["id"] for item in listed} == {
        notification.id for notification in own_notifications
    }
    assert other_notification.id not in {item["id"] for item in listed}

    foreign_read_response = await authenticated_integration_client.patch(
        f"/api/notifications/{other_notification.id}/read",
    )
    assert foreign_read_response.status_code == 404

    read_response = await authenticated_integration_client.patch(
        f"/api/notifications/{own_notifications[0].id}/read",
    )
    assert read_response.status_code == 200
    assert read_response.json()["read_at"] is not None

    count_after_one_response = await authenticated_integration_client.get(
        "/api/notifications/unread-count",
    )
    assert count_after_one_response.status_code == 200
    assert count_after_one_response.json() == {"unread_count": 1}

    read_all_response = await authenticated_integration_client.patch(
        "/api/notifications/read-all",
    )
    assert read_all_response.status_code == 200
    assert read_all_response.json() == {"updated_count": 1}

    final_count_response = await authenticated_integration_client.get(
        "/api/notifications/unread-count",
    )
    assert final_count_response.status_code == 200
    assert final_count_response.json() == {"unread_count": 0}

    async with integration_sessionmaker() as session:
        result = await session.execute(
            select(Notification).where(Notification.recipient_user_id == manager.id)
        )
        persisted_notifications = result.scalars().all()

    assert all(notification.read_at is not None for notification in persisted_notifications)
