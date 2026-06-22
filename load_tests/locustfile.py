import os
import random

from locust import HttpUser, constant, task
from locust.exception import StopUser


def _env_int_list(name: str, default: str) -> list[int]:
    raw = os.getenv(name, default)
    return [int(item.strip()) for item in raw.split(",") if item.strip()]


USERNAME = os.getenv("LOCUST_USERNAME", "superman")
PASSWORD = os.getenv("LOCUST_PASSWORD", "superman")
TOKEN = os.getenv("LOCUST_TOKEN")
VEHICLE_IDS = _env_int_list("LOCUST_VEHICLE_IDS", "1,2,3,4,5")
ENTERPRISE_IDS = _env_int_list("LOCUST_ENTERPRISE_IDS", "2")
WRITE_ENTERPRISE_ID = int(os.getenv("LOCUST_WRITE_ENTERPRISE_ID", "2"))
WRITE_MODEL_ID = int(os.getenv("LOCUST_WRITE_MODEL_ID", "1"))
TRACK_DATE_FROM = os.getenv("LOCUST_TRACK_DATE_FROM", "2024-01-01T00:00:00+00:00")
TRACK_DATE_TO = os.getenv("LOCUST_TRACK_DATE_TO", "2026-01-01T00:00:00+00:00")
PLATE_LETTERS = "АВЕКМНОРСТУХ"


class HealthUser(HttpUser):
    wait_time = constant(0)

    @task
    def health(self):
        self.client.get("/api/health", name="GET /api/health")


class AuthenticatedUserMixin:
    wait_time = constant(0)

    def on_start(self):
        self._created_vehicle_ids: set[int] = set()
        if TOKEN:
            self.headers = {"Authorization": f"Bearer {TOKEN}"}
            return

        with self.client.post(
            "/api/auth/login",
            json={"username": USERNAME, "password": PASSWORD},
            name="POST /api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed: {response.status_code}")
                raise StopUser()

            token = response.json().get("access_token")
            if not token:
                response.failure("login response has no access_token")
                raise StopUser()

        self.headers = {"Authorization": f"Bearer {token}"}

    def on_stop(self):
        for vehicle_id in tuple(getattr(self, "_created_vehicle_ids", ())):
            self.client.delete(
                f"/api/vehicles/{vehicle_id}",
                headers=self.headers,
                name="DELETE /api/vehicles/{id} cleanup",
            )
            self._created_vehicle_ids.discard(vehicle_id)

    def _temporary_vehicle_payload(self) -> dict:
        vehicle_number = (
            f"{random.choice(PLATE_LETTERS)}"
            f"{random.randint(0, 999):03d}"
            f"{random.choice(PLATE_LETTERS)}"
            f"{random.choice(PLATE_LETTERS)}"
            f"{random.randint(100, 999)}"
        )
        return {
            "price": random.randint(800_000, 2_500_000),
            "mileage": random.randint(10_000, 180_000),
            "vehicle_number": vehicle_number,
            "owners_count": random.randint(1, 3),
            "accident_number": random.randint(0, 2),
            "manufacture_year": random.randint(2016, 2025),
            "model_id": WRITE_MODEL_ID,
            "enterprise_id": WRITE_ENTERPRISE_ID,
            "color": random.choice(("black", "white", "silver", "blue")),
            "purchased_at": "2026-01-01T12:00:00+03:00",
        }

    def _vehicle_write_cycle(self) -> None:
        vehicle_id = None

        with self.client.post(
            "/api/vehicles",
            json=self._temporary_vehicle_payload(),
            headers=self.headers,
            name="POST /api/vehicles",
            catch_response=True,
        ) as response:
            if response.status_code != 201:
                response.failure(f"create vehicle failed: {response.status_code}")
                return
            vehicle_id = response.json().get("id")
            if not vehicle_id:
                response.failure("create vehicle response has no id")
                return
            self._created_vehicle_ids.add(vehicle_id)

        with self.client.patch(
            f"/api/vehicles/{vehicle_id}",
            json={"mileage": random.randint(10_000, 200_000)},
            headers=self.headers,
            name="PATCH /api/vehicles/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"patch vehicle failed: {response.status_code}")

        with self.client.delete(
            f"/api/vehicles/{vehicle_id}",
            headers=self.headers,
            name="DELETE /api/vehicles/{id}",
            catch_response=True,
        ) as response:
            if response.status_code != 204:
                response.failure(f"delete vehicle failed: {response.status_code}")
                return
            self._created_vehicle_ids.discard(vehicle_id)


class HotApiUser(AuthenticatedUserMixin, HttpUser):
    @task(20)
    def vehicles_list(self):
        self.client.get(
            "/api/vehicles?limit=50&offset=0",
            headers=self.headers,
            name="GET /api/vehicles",
        )

    @task(12)
    def vehicle_detail(self):
        vehicle_id = random.choice(VEHICLE_IDS)
        self.client.get(
            f"/api/vehicles/{vehicle_id}",
            headers=self.headers,
            name="GET /api/vehicles/{id}",
        )

    @task(8)
    def drivers_list(self):
        self.client.get(
            "/api/drivers",
            headers=self.headers,
            name="GET /api/drivers",
        )

    @task(8)
    def enterprises_list(self):
        self.client.get(
            "/api/enterprises",
            headers=self.headers,
            name="GET /api/enterprises",
        )

    @task(6)
    def unread_count(self):
        self.client.get(
            "/api/notifications/unread-count",
            headers=self.headers,
            name="GET /api/notifications/unread-count",
        )

    @task(4)
    def notifications_list(self):
        self.client.get(
            "/api/notifications?unread_only=true&limit=50&offset=0",
            headers=self.headers,
            name="GET /api/notifications",
        )

    @task(3)
    def vehicle_models(self):
        self.client.get(
            "/api/vehicle-models",
            headers=self.headers,
            name="GET /api/vehicle-models",
        )

    @task(2)
    def vehicles_by_enterprise(self):
        enterprise_id = random.choice(ENTERPRISE_IDS)
        self.client.get(
            f"/api/vehicles?enterprise_ids={enterprise_id}&limit=50&offset=0",
            headers=self.headers,
            name="GET /api/vehicles?enterprise_ids={id}",
        )


class ReadOnlyUser(HotApiUser):
    pass


class WriteUser(AuthenticatedUserMixin, HttpUser):
    @task
    def vehicle_write_cycle(self):
        self._vehicle_write_cycle()


class ReadWriteUser(HotApiUser):
    @task(2)
    def vehicle_write_cycle(self):
        self._vehicle_write_cycle()


class TrackApiUser(HotApiUser):
    @task(8)
    def vehicle_track(self):
        vehicle_id = random.choice(VEHICLE_IDS)
        self.client.get(
            f"/api/vehicles/{vehicle_id}/track",
            params={"date_from": TRACK_DATE_FROM, "date_to": TRACK_DATE_TO},
            headers=self.headers,
            name="GET /api/vehicles/{id}/track",
        )

    @task(4)
    def vehicle_trips(self):
        vehicle_id = random.choice(VEHICLE_IDS)
        self.client.get(
            f"/api/vehicles/{vehicle_id}/trips",
            params={
                "date_from": TRACK_DATE_FROM,
                "date_to": TRACK_DATE_TO,
                "include_addresses": "false",
            },
            headers=self.headers,
            name="GET /api/vehicles/{id}/trips",
        )
