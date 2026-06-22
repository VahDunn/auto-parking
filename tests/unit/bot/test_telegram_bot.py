from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from auto_parking.bot.handlers import TelegramBotHandlers
from auto_parking.bot.service import BotService, EnterpriseLookup, MileageSummary, VehicleLookup
from auto_parking.core.security.jwt import create_access_token

pytestmark = pytest.mark.asyncio


class FakeCacheClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, int]] = []

    async def get_text(self, key: str) -> str | None:
        return self.values.get(key)

    async def set_text(self, key: str, value: str, *, ttl_seconds: int) -> None:
        self.values[key] = value
        self.set_calls.append((key, ttl_seconds))

    async def delete_prefix(self, prefix: str) -> None:
        return None


async def test_telegram_bot_echoes_plain_text():
    app = TelegramBotHandlers(service=AsyncMock())

    reply = await app.handle_text(chat_id=1, text="hello")

    assert reply.text == "hello"
    assert reply.reply_markup is not None


async def test_telegram_bot_login_stores_session():
    service = AsyncMock()
    service.login.return_value = SimpleNamespace(
        username="manager",
        access_token="token",
    )
    app = TelegramBotHandlers(service=service)

    result = await app.handle_text(chat_id=42, text="/login manager secret")

    assert result.text == "Готово, вы вошли как manager."
    assert result.reply_markup is not None
    assert app.sessions[42].username == "manager"
    service.login.assert_awaited_once_with(username="manager", password="secret")


async def test_telegram_bot_requires_login_for_mileage():
    app = TelegramBotHandlers(service=AsyncMock())

    result = await app.handle_text(
        chat_id=42,
        text="/mileage_vehicle_day 7 2026-05-26",
    )

    assert result.text == "Сначала выполните /login <логин> <пароль>."
    assert result.reply_markup is not None


async def test_telegram_bot_calls_vehicle_mileage_for_day():
    service = AsyncMock()
    service.find_vehicle_by_number_prefix.return_value = VehicleLookup(
        vehicle=None,
        matches=[{"id": 7, "vehicle_number": "А123ВС77"}],
    )
    service.vehicle_mileage.return_value = MileageSummary(
        title="Автомобиль #7",
        date_from=datetime(2026, 5, 26, tzinfo=UTC),
        date_to=datetime(2026, 5, 27, tzinfo=UTC),
        trips_count=2,
        distance_km=13.5,
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    result = await app.handle_text(
        chat_id=42,
        text="/mileage_vehicle_day А123 2026-05-26",
    )

    assert result.text == "Выберите автомобиль из списка."
    assert result.reply_markup == {
        "inline_keyboard": [[{"text": "А123ВС77 (ID 7)", "callback_data": "vehicle:7"}]]
    }

    result = await app.handle_callback(chat_id=42, data="vehicle:7")

    assert "Автомобиль А123ВС77" in result.text
    assert "Пробег: 14 км" in result.text
    assert result.reply_markup is not None
    service.find_vehicle_by_number_prefix.assert_awaited_once_with(
        session=app.sessions[42],
        number_prefix="А123",
    )
    service.vehicle_mileage.assert_awaited_once()
    _, kwargs = service.vehicle_mileage.await_args
    assert kwargs["vehicle_id"] == 7
    assert kwargs["date_from"] == datetime(2026, 5, 26, tzinfo=UTC)
    assert kwargs["date_to"] == datetime(2026, 5, 27, tzinfo=UTC)


async def test_bot_service_login_uses_api_client():
    api_client = AsyncMock()
    token = create_access_token(actor_type="manager", actor_id=7)
    api_client.login.return_value = token
    service = BotService(api_client)

    session = await service.login("manager", "password")

    assert session is not None
    assert session.username == "manager"
    assert session.access_token == token
    assert session.user_id == 7
    assert session.role == "manager"
    api_client.login.assert_awaited_once_with(username="manager", password="password")


async def test_telegram_bot_collects_vehicle_mileage_params_with_buttons():
    service = AsyncMock()
    service.find_vehicle_by_number_prefix.return_value = VehicleLookup(
        vehicle=None,
        matches=[{"id": 7, "vehicle_number": "А123ВС77"}],
    )
    service.vehicle_mileage.return_value = MileageSummary(
        title="Автомобиль #7",
        date_from=datetime(2026, 5, 26, tzinfo=UTC),
        date_to=datetime(2026, 5, 27, tzinfo=UTC),
        trips_count=2,
        distance_km=13.5,
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    reply = await app.handle_callback(chat_id=42, data="mileage:vehicle:day")
    assert reply.text == "Введите начало госномера автомобиля."

    reply = await app.handle_text(chat_id=42, text="А123")
    assert reply.text == "Выберите автомобиль из списка."
    assert reply.reply_markup == {
        "inline_keyboard": [[{"text": "А123ВС77 (ID 7)", "callback_data": "vehicle:7"}]]
    }

    reply = await app.handle_callback(chat_id=42, data="vehicle:7")
    assert reply.text == "Введите дату в формате YYYY-MM-DD."

    reply = await app.handle_text(chat_id=42, text="2026-05-26")

    assert "Автомобиль А123ВС77" in reply.text
    assert "Пробег: 14 км" in reply.text
    assert 42 not in app.states
    service.find_vehicle_by_number_prefix.assert_awaited_once_with(
        session=app.sessions[42],
        number_prefix="А123",
    )
    service.vehicle_mileage.assert_awaited_once()


async def test_telegram_bot_collects_enterprise_name_prefix_with_buttons():
    service = AsyncMock()
    service.find_enterprise_by_name_prefix.return_value = EnterpriseLookup(
        enterprise=None,
        matches=[{"id": 2, "name": "Handsome Family"}],
    )
    service.enterprise_mileage.return_value = MileageSummary(
        title="Предприятие #2",
        date_from=datetime(2025, 5, 1, tzinfo=UTC),
        date_to=datetime(2025, 6, 1, tzinfo=UTC),
        trips_count=12,
        distance_km=42.75,
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    reply = await app.handle_callback(chat_id=42, data="mileage:enterprise:month")
    assert reply.text == "Введите начало названия предприятия."

    reply = await app.handle_text(chat_id=42, text="hand")
    assert reply.text == "Выберите предприятие из списка."
    assert reply.reply_markup == {
        "inline_keyboard": [[{"text": "Handsome Family", "callback_data": "enterprise:2"}]]
    }

    reply = await app.handle_callback(chat_id=42, data="enterprise:2")
    assert reply.text == "Введите дату в формате YYYY-MM."

    reply = await app.handle_text(chat_id=42, text="2025-05")

    assert "Предприятие Handsome Family" in reply.text
    assert "Пробег: 43 км" in reply.text
    assert 42 not in app.states
    service.find_enterprise_by_name_prefix.assert_awaited_once_with(
        session=app.sessions[42],
        name_prefix="hand",
    )
    service.enterprise_mileage.assert_awaited_once()
    _, kwargs = service.enterprise_mileage.await_args
    assert kwargs["enterprise_id"] == 2


async def test_telegram_bot_reports_ambiguous_enterprise_prefix():
    service = AsyncMock()
    service.find_enterprise_by_name_prefix.return_value = EnterpriseLookup(
        enterprise=None,
        matches=[
            {"id": 2, "name": "Handsome Family"},
            {"id": 3, "name": "Handsome Logistics"},
        ],
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    result = await app.handle_text(
        chat_id=42,
        text="/mileage_enterprise_day hand 2025-05-01",
    )

    assert result.text == "Выберите предприятие из списка."
    assert result.reply_markup == {
        "inline_keyboard": [
            [{"text": "Handsome Family", "callback_data": "enterprise:2"}],
            [{"text": "Handsome Logistics", "callback_data": "enterprise:3"}],
        ]
    }
    service.enterprise_mileage.assert_not_awaited()


async def test_telegram_bot_reports_no_enterprises_for_prefix():
    service = AsyncMock()
    service.find_enterprise_by_name_prefix.return_value = EnterpriseLookup(
        enterprise=None,
        matches=[],
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    result = await app.handle_callback(chat_id=42, data="mileage:enterprise:day")
    assert result.text == "Введите начало названия предприятия."

    result = await app.handle_text(chat_id=42, text="zzz")

    assert result.text == "Подходящих предприятий не найдено."
    assert 42 not in app.states


async def test_telegram_bot_reports_no_vehicles_for_number_prefix():
    service = AsyncMock()
    service.find_vehicle_by_number_prefix.return_value = VehicleLookup(
        vehicle=None,
        matches=[],
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    result = await app.handle_callback(chat_id=42, data="mileage:vehicle:day")
    assert result.text == "Введите начало госномера автомобиля."

    result = await app.handle_text(chat_id=42, text="zzz")

    assert result.text == "Подходящих автомобилей не найдено."
    assert 42 not in app.states


async def test_telegram_bot_calculates_command_after_vehicle_choice():
    service = AsyncMock()
    service.find_vehicle_by_number_prefix.return_value = VehicleLookup(
        vehicle=None,
        matches=[{"id": 7, "vehicle_number": "А123ВС77"}],
    )
    service.vehicle_mileage.return_value = MileageSummary(
        title="Автомобиль #7",
        date_from=datetime(2026, 5, 26, tzinfo=UTC),
        date_to=datetime(2026, 5, 27, tzinfo=UTC),
        trips_count=2,
        distance_km=13.5,
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    reply = await app.handle_text(
        chat_id=42,
        text="/mileage_vehicle_day А123 2026-05-26",
    )
    assert reply.text == "Выберите автомобиль из списка."

    reply = await app.handle_callback(chat_id=42, data="vehicle:7")

    assert "Автомобиль А123ВС77" in reply.text
    assert "Пробег: 14 км" in reply.text
    assert 42 not in app.states
    service.vehicle_mileage.assert_awaited_once()


async def test_telegram_bot_calculates_command_after_enterprise_choice():
    service = AsyncMock()
    service.find_enterprise_by_name_prefix.return_value = EnterpriseLookup(
        enterprise=None,
        matches=[{"id": 2, "name": "Handsome Family"}],
    )
    service.enterprise_mileage.return_value = MileageSummary(
        title="Предприятие #2",
        date_from=datetime(2025, 5, 1, tzinfo=UTC),
        date_to=datetime(2025, 5, 2, tzinfo=UTC),
        trips_count=3,
        distance_km=8.25,
    )
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(
        username="manager",
        access_token="token",
    )

    reply = await app.handle_text(
        chat_id=42,
        text="/mileage_enterprise_day hand 2025-05-01",
    )
    assert reply.text == "Выберите предприятие из списка."

    reply = await app.handle_callback(chat_id=42, data="enterprise:2")

    assert "Предприятие Handsome Family" in reply.text
    assert "Пробег: 8 км" in reply.text
    assert 42 not in app.states
    service.enterprise_mileage.assert_awaited_once()


async def test_bot_service_finds_enterprise_by_name_prefix():
    api_client = AsyncMock()
    api_client.get_enterprises.return_value = [
        {"id": 1, "name": "неизвестно"},
        {"id": 2, "name": "Handsome Family"},
    ]
    service = BotService(api_client)
    session = SimpleNamespace(username="manager", access_token="token")

    result = await service.find_enterprise_by_name_prefix(
        session=session,
        name_prefix="han",
    )

    assert result.enterprise == {"id": 2, "name": "Handsome Family"}
    assert result.matches == [{"id": 2, "name": "Handsome Family"}]
    api_client.get_enterprises.assert_awaited_once_with("token")


async def test_bot_service_finds_vehicle_by_number_prefix():
    api_client = AsyncMock()
    api_client.get_vehicles_by_number_prefix.return_value = [
        {"id": 7, "vehicle_number": "А123ВС77"},
    ]
    service = BotService(api_client)
    session = SimpleNamespace(username="manager", access_token="token")

    result = await service.find_vehicle_by_number_prefix(
        session=session,
        number_prefix="А123",
    )

    assert result.vehicle == {"id": 7, "vehicle_number": "А123ВС77"}
    assert result.matches == [{"id": 7, "vehicle_number": "А123ВС77"}]
    api_client.get_vehicles_by_number_prefix.assert_awaited_once_with("token", "А123")


async def test_telegram_bot_shows_unread_notifications():
    service = AsyncMock()
    service.unread_notifications.return_value = [
        {
            "id": 2,
            "trip_id": 9202,
            "title": "Новая поездка",
            "body": "Оформлена новая поездка автомобиля Е754ВУ759",
        }
    ]
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(username="superman", access_token="token")

    reply = await app.handle_text(chat_id=42, text="/notifications")

    assert "Непрочитанные уведомления: 1" in reply.text
    assert "Оформлена новая поездка автомобиля Е754ВУ759" in reply.text
    assert reply.reply_markup == {
        "inline_keyboard": [
            [{"text": "Прочитать #2", "callback_data": "notification:read:2"}],
            [{"text": "Прочитать все", "callback_data": "notifications:read_all"}],
            [{"text": "Назад", "callback_data": "menu"}],
        ]
    }
    service.unread_notifications.assert_awaited_once_with(session=app.sessions[42])


async def test_telegram_bot_marks_notification_read():
    service = AsyncMock()
    service.mark_notification_read.return_value = {"id": 2}
    service.unread_notifications.return_value = []
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(username="superman", access_token="token")

    reply = await app.handle_callback(chat_id=42, data="notification:read:2")

    assert reply.text == "Непрочитанных уведомлений нет."
    service.mark_notification_read.assert_awaited_once_with(
        session=app.sessions[42],
        notification_id=2,
    )
    service.unread_notifications.assert_awaited_once_with(session=app.sessions[42])


async def test_telegram_bot_marks_all_notifications_read():
    service = AsyncMock()
    service.mark_all_notifications_read.return_value = True
    app = TelegramBotHandlers(service=service)
    app.sessions[42] = SimpleNamespace(username="superman", access_token="token")

    reply = await app.handle_callback(chat_id=42, data="notifications:read_all")

    assert reply.text == "Все уведомления отмечены прочитанными."
    service.mark_all_notifications_read.assert_awaited_once_with(
        session=app.sessions[42],
    )


async def test_bot_service_uses_api_for_notifications():
    api_client = AsyncMock()
    api_client.get_unread_notifications.return_value = [{"id": 2}]
    api_client.mark_notification_read.return_value = {"id": 2}
    api_client.mark_all_notifications_read.return_value = True
    service = BotService(api_client)
    session = SimpleNamespace(username="superman", access_token="token")

    assert await service.unread_notifications(session=session) == [{"id": 2}]
    assert await service.mark_notification_read(session=session, notification_id=2) == {"id": 2}
    assert await service.mark_all_notifications_read(session=session)

    api_client.get_unread_notifications.assert_awaited_once_with("token")
    api_client.mark_notification_read.assert_awaited_once_with("token", 2)
    api_client.mark_all_notifications_read.assert_awaited_once_with("token")


async def test_bot_service_caches_enterprise_mileage_summary():
    api_client = AsyncMock()
    api_client.get_enterprise.return_value = {"id": 2}
    api_client.get_enterprise_vehicles.return_value = [{"id": 7}]
    api_client.get_vehicle_trips.return_value = [
        {
            "start_point": {"latitude": 55.75, "longitude": 37.61},
            "end_point": {"latitude": 55.76, "longitude": 37.62},
        }
    ]
    cache = FakeCacheClient()
    service = BotService(api_client, cache=cache, cache_ttl_seconds=123)
    session = SimpleNamespace(username="manager", access_token="token")
    date_from = datetime(2026, 5, 1, tzinfo=UTC)
    date_to = datetime(2026, 6, 1, tzinfo=UTC)

    first = await service.enterprise_mileage(
        session=session,
        enterprise_id=2,
        date_from=date_from,
        date_to=date_to,
    )
    second = await service.enterprise_mileage(
        session=session,
        enterprise_id=2,
        date_from=date_from,
        date_to=date_to,
    )

    assert second == first
    assert cache.set_calls == [
        (
            "bot:mileage:manager:enterprise:2:"
            "2026-05-01T00:00:00+00:00:2026-06-01T00:00:00+00:00",
            123,
        )
    ]
    assert api_client.get_enterprise.await_count == 2
    api_client.get_enterprise_vehicles.assert_awaited_once()
    api_client.get_vehicle_trips.assert_awaited_once()


async def test_bot_service_does_not_return_cached_enterprise_summary_without_access():
    api_client = AsyncMock()
    api_client.get_enterprise.return_value = None
    cache = FakeCacheClient()
    cache.values[
        "bot:mileage:manager:enterprise:2:"
        "2026-05-01T00:00:00+00:00:2026-06-01T00:00:00+00:00"
    ] = (
        '{"title": "Предприятие #2", '
        '"date_from": "2026-05-01T00:00:00+00:00", '
        '"date_to": "2026-06-01T00:00:00+00:00", '
        '"trips_count": 1, "distance_km": 10.0}'
    )
    service = BotService(api_client, cache=cache)
    session = SimpleNamespace(username="manager", access_token="token")

    result = await service.enterprise_mileage(
        session=session,
        enterprise_id=2,
        date_from=datetime(2026, 5, 1, tzinfo=UTC),
        date_to=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert result is None
    api_client.get_enterprise_vehicles.assert_not_awaited()


async def test_bot_service_caches_vehicle_mileage_summary():
    api_client = AsyncMock()
    api_client.get_vehicle.return_value = {"id": 7}
    api_client.get_vehicle_trips.return_value = []
    cache = FakeCacheClient()
    service = BotService(api_client, cache=cache)
    session = SimpleNamespace(username="manager", access_token="token")
    date_from = datetime(2026, 5, 1, tzinfo=UTC)
    date_to = datetime(2026, 6, 1, tzinfo=UTC)

    await service.vehicle_mileage(
        session=session,
        vehicle_id=7,
        date_from=date_from,
        date_to=date_to,
    )
    await service.vehicle_mileage(
        session=session,
        vehicle_id=7,
        date_from=date_from,
        date_to=date_to,
    )

    assert api_client.get_vehicle.await_count == 2
    api_client.get_vehicle_trips.assert_awaited_once()
