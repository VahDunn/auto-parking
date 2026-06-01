from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from auto_parking.bot.service import (
    BotService,
    BotSession,
    day_range,
    format_mileage_summary,
    month_range,
)

HELP_TEXT = """Выберите действие кнопками ниже или используйте команды:
/login <логин> <пароль>
/mileage_vehicle_day <начало_номера> <YYYY-MM-DD>
/mileage_vehicle_month <начало_номера> <YYYY-MM>
/mileage_enterprise_day <начало_названия> <YYYY-MM-DD>
/mileage_enterprise_month <начало_названия> <YYYY-MM>
/notifications
/cancel

Обычный текст бот пока возвращает эхом."""


@dataclass(slots=True)
class BotReply:
    text: str
    reply_markup: dict[str, Any] | None = None


@dataclass(slots=True)
class DialogState:
    action: str
    step: str
    target: str | None = None
    period: str | None = None
    target_id: int | None = None
    target_name: str | None = None
    vehicle_options: list[dict[str, Any]] = field(default_factory=list)
    username: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    enterprise_options: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class TelegramBotHandlers:
    service: BotService
    sessions: dict[int, BotSession] = field(default_factory=dict)
    states: dict[int, DialogState] = field(default_factory=dict)

    async def handle_text(self, chat_id: int, text: str) -> BotReply:
        text = text.strip()
        if not text:
            return BotReply("Не понял сообщение.")

        if text == "/cancel":
            self.states.pop(chat_id, None)
            return BotReply("Ок, отменил текущий сценарий.", self._main_menu())

        if text.startswith("/"):
            return await self._handle_command(chat_id, text)

        state = self.states.get(chat_id)
        if state is not None:
            return await self._handle_state_text(chat_id, text, state)

        return BotReply(text, self._main_menu())

    async def handle_callback(self, chat_id: int, data: str) -> BotReply:
        if data == "menu":
            self.states.pop(chat_id, None)
            return BotReply("Что делаем?", self._main_menu())

        if data == "login":
            self.states[chat_id] = DialogState(action="login", step="username")
            return BotReply("Введите логин менеджера.")

        if data == "notifications":
            return await self._handle_notifications(chat_id)

        if data == "notifications:read_all":
            return await self._handle_mark_all_notifications_read(chat_id)

        if data.startswith("notification:read:"):
            return await self._handle_mark_notification_read(chat_id, data)

        if data.startswith("enterprise:"):
            return await self._handle_enterprise_choice(chat_id, data)

        if data.startswith("vehicle:"):
            return await self._handle_vehicle_choice(chat_id, data)

        if data.startswith("mileage:"):
            try:
                _, target, period = data.split(":", 2)
            except ValueError:
                return BotReply("Не понял кнопку.", self._main_menu())

            if target not in {"vehicle", "enterprise"} or period not in {"day", "month"}:
                return BotReply("Не понял кнопку.", self._main_menu())

            self.states[chat_id] = DialogState(
                action="mileage",
                step="target_name",
                target=target,
                period=period,
            )
            if target == "vehicle":
                return BotReply("Введите начало госномера автомобиля.")
            return BotReply("Введите начало названия предприятия.")

        return BotReply("Не понял кнопку.", self._main_menu())

    async def _handle_command(self, chat_id: int, text: str) -> BotReply:
        command, *args = text.split()

        if command in {"/start", "/help"}:
            return BotReply(HELP_TEXT, self._main_menu())

        if command == "/login":
            return await self._handle_login(chat_id, args)

        if command == "/notifications":
            return await self._handle_notifications(chat_id)

        if command.startswith("/mileage_vehicle_"):
            return await self._handle_vehicle_mileage(chat_id, command, args)

        if command.startswith("/mileage_enterprise_"):
            return await self._handle_enterprise_mileage(chat_id, command, args)

        return BotReply(text, self._main_menu())

    async def _handle_state_text(
        self,
        chat_id: int,
        text: str,
        state: DialogState,
    ) -> BotReply:
        if state.action == "login":
            return await self._handle_login_state(chat_id, text, state)

        if state.action == "mileage":
            return await self._handle_mileage_state(chat_id, text, state)

        self.states.pop(chat_id, None)
        return BotReply("Сценарий сброшен.", self._main_menu())

    async def _handle_login_state(
        self,
        chat_id: int,
        text: str,
        state: DialogState,
    ) -> BotReply:
        if state.step == "username":
            state.username = text
            state.step = "password"
            return BotReply("Теперь введите пароль.")

        if state.step == "password" and state.username is not None:
            self.states.pop(chat_id, None)
            return await self._login(chat_id, username=state.username, password=text)

        self.states.pop(chat_id, None)
        return BotReply("Не получилось продолжить логин. Начните заново.", self._main_menu())

    async def _handle_mileage_state(
        self,
        chat_id: int,
        text: str,
        state: DialogState,
    ) -> BotReply:
        if state.step == "target_id":
            try:
                state.target_id = int(text)
            except ValueError:
                return BotReply("Введите id числом.")

            state.step = "date"
            date_format = "YYYY-MM-DD" if state.period == "day" else "YYYY-MM"
            return BotReply(f"Введите дату в формате {date_format}.")

        if state.step == "target_name":
            if state.target == "vehicle":
                return await self._offer_vehicle_choices(chat_id, text, state)
            if state.target == "enterprise":
                return await self._offer_enterprise_choices(chat_id, text, state)

        if state.step in {"vehicle_choice", "enterprise_choice"}:
            target_title = "автомобиль" if state.step == "vehicle_choice" else "предприятие"
            return BotReply(f"Выберите {target_title} кнопкой из списка.")

        if state.step == "date" and (state.target_id is not None or state.target_name is not None):
            self.states.pop(chat_id, None)
            command = f"/mileage_{state.target}_{state.period}"
            if state.target == "vehicle":
                if state.target_id is None:
                    return BotReply("Сначала выберите автомобиль.", self._main_menu())
                return await self._calculate_vehicle_mileage(
                    chat_id=chat_id,
                    vehicle_id=state.target_id,
                    vehicle_number=state.target_name,
                    command=command,
                    raw_date=text,
                )
            if state.target == "enterprise":
                if state.target_id is None:
                    return BotReply("Сначала выберите предприятие.", self._main_menu())
                return await self._calculate_enterprise_mileage(
                    chat_id=chat_id,
                    enterprise_id=state.target_id,
                    enterprise_name=state.target_name,
                    command=command,
                    raw_date=text,
                )

        self.states.pop(chat_id, None)
        return BotReply("Не получилось продолжить сценарий. Начните заново.", self._main_menu())

    async def _handle_login(self, chat_id: int, args: list[str]) -> BotReply:
        if len(args) != 2:
            return BotReply("Формат: /login <логин> <пароль>")

        return await self._login(chat_id, username=args[0], password=args[1])

    async def _login(self, chat_id: int, *, username: str, password: str) -> BotReply:
        session = await self.service.login(username=username, password=password)
        if session is None:
            return BotReply("Не удалось авторизоваться как менеджер.", self._main_menu())

        self.sessions[chat_id] = session
        return BotReply(f"Готово, вы вошли как {session.username}.", self._main_menu())

    async def _handle_notifications(self, chat_id: int) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        notifications = await self.service.unread_notifications(session=session)
        if not notifications:
            return BotReply("Непрочитанных уведомлений нет.", self._main_menu())

        return BotReply(
            self._format_notifications(notifications),
            self._notifications_menu(notifications),
        )

    async def _handle_mark_notification_read(self, chat_id: int, data: str) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        try:
            notification_id = int(data.rsplit(":", 1)[1])
        except ValueError:
            return BotReply("Не понял уведомление.", self._main_menu())

        notification = await self.service.mark_notification_read(
            session=session,
            notification_id=notification_id,
        )
        if notification is None:
            return BotReply("Уведомление не найдено.", self._main_menu())

        return await self._handle_notifications(chat_id)

    async def _handle_mark_all_notifications_read(self, chat_id: int) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        ok = await self.service.mark_all_notifications_read(session=session)
        if not ok:
            return BotReply("Не получилось отметить уведомления прочитанными.", self._main_menu())

        return BotReply("Все уведомления отмечены прочитанными.", self._main_menu())

    async def _handle_vehicle_mileage(
        self,
        chat_id: int,
        command: str,
        args: list[str],
    ) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        if len(args) != 2:
            return BotReply("Формат: /mileage_vehicle_day <начало_номера> <YYYY-MM-DD>")

        try:
            date_from, date_to = self._parse_period(command, args[1])
        except ValueError:
            return BotReply("Не понял дату. Для суток: YYYY-MM-DD, для месяца: YYYY-MM.")

        state = DialogState(
            action="mileage",
            step="vehicle_choice",
            target="vehicle",
            period="day" if command.endswith("_day") else "month",
            date_from=date_from,
            date_to=date_to,
        )
        return await self._offer_vehicle_choices(chat_id, args[0], state)

    async def _calculate_vehicle_mileage(
        self,
        *,
        chat_id: int,
        vehicle_id: int,
        vehicle_number: str | None,
        command: str,
        raw_date: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        if date_from is None or date_to is None:
            if raw_date is None:
                return BotReply("Не понял дату. Для суток: YYYY-MM-DD, для месяца: YYYY-MM.")
            try:
                date_from, date_to = self._parse_period(command, raw_date)
            except ValueError:
                return BotReply("Не понял дату. Для суток: YYYY-MM-DD, для месяца: YYYY-MM.")

        summary = await self.service.vehicle_mileage(
            session=session,
            vehicle_id=vehicle_id,
            date_from=date_from,
            date_to=date_to,
        )
        if summary is None:
            return BotReply("Автомобиль не найден или недоступен.", self._main_menu())

        if vehicle_number:
            summary.title = f"Автомобиль {vehicle_number}"
        return BotReply(format_mileage_summary(summary), self._main_menu())

    async def _handle_enterprise_mileage(
        self,
        chat_id: int,
        command: str,
        args: list[str],
    ) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        if len(args) != 2:
            return BotReply("Формат: /mileage_enterprise_day <начало_названия> <YYYY-MM-DD>")

        try:
            date_from, date_to = self._parse_period(command, args[1])
        except ValueError:
            return BotReply("Не понял дату. Для суток: YYYY-MM-DD, для месяца: YYYY-MM.")

        state = DialogState(
            action="mileage",
            step="enterprise_choice",
            target="enterprise",
            period="day" if command.endswith("_day") else "month",
            date_from=date_from,
            date_to=date_to,
        )
        return await self._offer_enterprise_choices(chat_id, args[0], state)

    async def _calculate_enterprise_mileage(
        self,
        *,
        chat_id: int,
        enterprise_id: int,
        enterprise_name: str | None,
        command: str,
        raw_date: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        if date_from is None or date_to is None:
            if raw_date is None:
                return BotReply("Не понял дату. Для суток: YYYY-MM-DD, для месяца: YYYY-MM.")
            try:
                date_from, date_to = self._parse_period(command, raw_date)
            except ValueError:
                return BotReply("Не понял дату. Для суток: YYYY-MM-DD, для месяца: YYYY-MM.")

        summary = await self.service.enterprise_mileage(
            session=session,
            enterprise_id=enterprise_id,
            date_from=date_from,
            date_to=date_to,
        )
        if summary is None:
            return BotReply("Предприятие не найдено или недоступно.", self._main_menu())

        if enterprise_name:
            summary.title = f"Предприятие {enterprise_name}"
        return BotReply(format_mileage_summary(summary), self._main_menu())

    async def _offer_enterprise_choices(
        self,
        chat_id: int,
        name_prefix: str,
        state: DialogState,
    ) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        lookup = await self.service.find_enterprise_by_name_prefix(
            session=session,
            name_prefix=name_prefix,
        )
        if not lookup.matches:
            self.states.pop(chat_id, None)
            return BotReply("Подходящих предприятий не найдено.", self._main_menu())

        state.step = "enterprise_choice"
        state.enterprise_options = lookup.matches
        self.states[chat_id] = state
        return BotReply(
            "Выберите предприятие из списка.",
            self._enterprise_choices_menu(lookup.matches),
        )

    async def _offer_vehicle_choices(
        self,
        chat_id: int,
        number_prefix: str,
        state: DialogState,
    ) -> BotReply:
        session = self._get_session(chat_id)
        if session is None:
            return BotReply("Сначала выполните /login <логин> <пароль>.", self._main_menu())

        lookup = await self.service.find_vehicle_by_number_prefix(
            session=session,
            number_prefix=number_prefix,
        )
        if not lookup.matches:
            self.states.pop(chat_id, None)
            return BotReply("Подходящих автомобилей не найдено.", self._main_menu())

        state.step = "vehicle_choice"
        state.vehicle_options = lookup.matches
        self.states[chat_id] = state
        return BotReply(
            "Выберите автомобиль из списка.",
            self._vehicle_choices_menu(lookup.matches),
        )

    async def _handle_vehicle_choice(self, chat_id: int, data: str) -> BotReply:
        state = self.states.get(chat_id)
        if state is None or state.action != "mileage" or state.target != "vehicle":
            return BotReply("Сначала начните сценарий сводки по автомобилю.", self._main_menu())

        try:
            vehicle_id = int(data.split(":", 1)[1])
        except ValueError:
            return BotReply("Не понял автомобиль.", self._main_menu())

        selected = next(
            (
                vehicle
                for vehicle in state.vehicle_options
                if int(vehicle.get("id", -1)) == vehicle_id
            ),
            None,
        )
        if selected is None:
            return BotReply(
                "Выбранный автомобиль уже недоступен. Начните заново.", self._main_menu()
            )

        state.target_id = vehicle_id
        state.target_name = str(selected.get("vehicle_number") or vehicle_id)

        if state.date_from is not None and state.date_to is not None:
            self.states.pop(chat_id, None)
            command = f"/mileage_vehicle_{state.period}"
            return await self._calculate_vehicle_mileage(
                chat_id=chat_id,
                vehicle_id=vehicle_id,
                vehicle_number=state.target_name,
                command=command,
                date_from=state.date_from,
                date_to=state.date_to,
            )

        state.step = "date"
        date_format = "YYYY-MM-DD" if state.period == "day" else "YYYY-MM"
        return BotReply(f"Введите дату в формате {date_format}.")

    async def _handle_enterprise_choice(self, chat_id: int, data: str) -> BotReply:
        state = self.states.get(chat_id)
        if state is None or state.action != "mileage" or state.target != "enterprise":
            return BotReply("Сначала начните сценарий сводки по предприятию.", self._main_menu())

        try:
            enterprise_id = int(data.split(":", 1)[1])
        except ValueError:
            return BotReply("Не понял предприятие.", self._main_menu())

        selected = next(
            (
                enterprise
                for enterprise in state.enterprise_options
                if int(enterprise.get("id", -1)) == enterprise_id
            ),
            None,
        )
        if selected is None:
            return BotReply(
                "Выбранное предприятие уже недоступно. Начните заново.", self._main_menu()
            )

        state.target_id = enterprise_id
        state.target_name = str(selected.get("name") or enterprise_id)

        if state.date_from is not None and state.date_to is not None:
            self.states.pop(chat_id, None)
            command = f"/mileage_enterprise_{state.period}"
            return await self._calculate_enterprise_mileage(
                chat_id=chat_id,
                enterprise_id=enterprise_id,
                enterprise_name=state.target_name,
                command=command,
                date_from=state.date_from,
                date_to=state.date_to,
            )

        state.step = "date"
        date_format = "YYYY-MM-DD" if state.period == "day" else "YYYY-MM"
        return BotReply(f"Введите дату в формате {date_format}.")

    def _get_session(self, chat_id: int) -> BotSession | None:
        return self.sessions.get(chat_id)

    @staticmethod
    def _parse_period(command: str, raw_value: str):
        if command.endswith("_day"):
            return day_range(raw_value)
        if command.endswith("_month"):
            return month_range(raw_value)
        raise ValueError("Unsupported period")

    @staticmethod
    def _main_menu() -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [{"text": "Войти", "callback_data": "login"}],
                [{"text": "Уведомления", "callback_data": "notifications"}],
                [
                    {"text": "Машина за сутки", "callback_data": "mileage:vehicle:day"},
                    {"text": "Машина за месяц", "callback_data": "mileage:vehicle:month"},
                ],
                [
                    {"text": "Предприятие за сутки", "callback_data": "mileage:enterprise:day"},
                    {"text": "Предприятие за месяц", "callback_data": "mileage:enterprise:month"},
                ],
            ]
        }

    @staticmethod
    def _format_notifications(notifications: list[dict[str, Any]]) -> str:
        lines = [f"Непрочитанные уведомления: {len(notifications)}"]
        for notification in notifications[:10]:
            lines.extend(
                [
                    "",
                    f"#{notification['id']} {notification.get('title') or 'Уведомление'}",
                    str(notification.get("body") or ""),
                    f"Поездка: {notification.get('trip_id')}",
                ]
            )
        if len(notifications) > 10:
            lines.append(f"\nПоказаны первые 10 из {len(notifications)}.")
        return "\n".join(lines)

    @staticmethod
    def _notifications_menu(notifications: list[dict[str, Any]]) -> dict[str, Any]:
        buttons = [
            [
                {
                    "text": f"Прочитать #{notification['id']}",
                    "callback_data": f"notification:read:{notification['id']}",
                }
            ]
            for notification in notifications[:10]
        ]
        buttons.append([{"text": "Прочитать все", "callback_data": "notifications:read_all"}])
        buttons.append([{"text": "Назад", "callback_data": "menu"}])
        return {"inline_keyboard": buttons}

    @staticmethod
    def _enterprise_choices_menu(enterprises: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": str(enterprise.get("name") or enterprise.get("id")),
                        "callback_data": f"enterprise:{enterprise['id']}",
                    }
                ]
                for enterprise in enterprises[:10]
            ]
        }

    @staticmethod
    def _vehicle_choices_menu(vehicles: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": (
                            f"{vehicle.get('vehicle_number') or vehicle.get('id')}"
                            f" (ID {vehicle['id']})"
                        ),
                        "callback_data": f"vehicle:{vehicle['id']}",
                    }
                ]
                for vehicle in vehicles[:10]
            ]
        }
