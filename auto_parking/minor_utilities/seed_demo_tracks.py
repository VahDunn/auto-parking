import asyncio
import math
import random
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

import typer
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.engine import AsyncSessionLocal
from auto_parking.db.models import Trip, Vehicle, VehicleGpsPoint

app = typer.Typer(help="Генератор demo-данных: поездки и GPS-точки")

DEFAULT_TRIPS_PER_VEHICLE = 30
DEFAULT_POINTS_PER_TRIP = 100

DEFAULT_CENTER_LAT = 29.9511
DEFAULT_CENTER_LON = -90.0715


def point_wkt(lon: float, lat: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def random_point_near(
    center_lat: float,
    center_lon: float,
    radius_km: float,
) -> tuple[float, float]:
    distance_km = radius_km * math.sqrt(random.random())
    angle = random.random() * 2.0 * math.pi

    delta_lat = distance_km / 111.0 * math.cos(angle)

    lon_scale = 111.0 * math.cos(math.radians(center_lat))
    if abs(lon_scale) < 1e-9:
        lon_scale = 1e-9

    delta_lon = distance_km / lon_scale * math.sin(angle)

    return center_lat + delta_lat, center_lon + delta_lon


def build_route_points(
    *,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    points_count: int,
) -> list[tuple[float, float]]:
    start_lat, start_lon = random_point_near(center_lat, center_lon, radius_km)
    mid1_lat, mid1_lon = random_point_near(center_lat, center_lon, radius_km)
    mid2_lat, mid2_lon = random_point_near(center_lat, center_lon, radius_km)
    end_lat, end_lon = random_point_near(center_lat, center_lon, radius_km)

    control_points = [
        (start_lat, start_lon),
        (mid1_lat, mid1_lon),
        (mid2_lat, mid2_lon),
        (end_lat, end_lon),
    ]

    result: list[tuple[float, float]] = []

    for i in range(points_count):
        t = i / max(points_count - 1, 1)

        segment_count = len(control_points) - 1
        raw_segment = min(int(t * segment_count), segment_count - 1)

        segment_start_t = raw_segment / segment_count
        segment_end_t = (raw_segment + 1) / segment_count
        local_t = (t - segment_start_t) / (segment_end_t - segment_start_t)

        lat1, lon1 = control_points[raw_segment]
        lat2, lon2 = control_points[raw_segment + 1]

        lat = lat1 + (lat2 - lat1) * local_t
        lon = lon1 + (lon2 - lon1) * local_t

        lat += random.uniform(-0.00025, 0.00025)
        lon += random.uniform(-0.00025, 0.00025)

        result.append((lat, lon))

    return result


async def get_vehicle_ids(
    db: AsyncSession,
    *,
    enterprise_id: int,
) -> list[int]:
    result = await db.execute(
        select(Vehicle.id).where(Vehicle.enterprise_id == enterprise_id).order_by(Vehicle.id)
    )
    vehicle_ids = list(result.scalars().all())

    if not vehicle_ids:
        raise ValueError(f"У enterprise_id={enterprise_id} нет машин")

    return vehicle_ids


async def clear_old_data(db: AsyncSession, vehicle_ids: list[int]) -> None:
    await db.execute(delete(Trip).where(Trip.vehicle_id.in_(vehicle_ids)))
    await db.execute(delete(VehicleGpsPoint).where(VehicleGpsPoint.vehicle_id.in_(vehicle_ids)))
    await db.commit()


def random_trip_start(
    *,
    date_from: date,
    date_to: date,
) -> datetime:
    total_days = (date_to - date_from).days
    trip_day = date_from + timedelta(days=random.randint(0, total_days - 1))

    return datetime.combine(
        trip_day,
        time(
            hour=random.randint(6, 22),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        ),
        tzinfo=UTC,
    )


async def seed_demo_tracks(
    *,
    enterprise_id: int,
    trips_per_vehicle: int,
    points_per_trip: int,
    date_from: date,
    date_to: date,
    center_lat: float,
    center_lon: float,
    radius_km: float,
    clear_before: bool,
    seed: int | None,
) -> None:
    if seed is not None:
        random.seed(seed)

    if trips_per_vehicle <= 0:
        raise ValueError("trips_per_vehicle должен быть больше 0")

    if points_per_trip < 2:
        raise ValueError("points_per_trip должен быть минимум 2")

    if date_to <= date_from:
        raise ValueError("date_to должен быть больше date_from")

    if radius_km <= 0:
        raise ValueError("radius_km должен быть больше 0")

    async with AsyncSessionLocal() as db:
        vehicle_ids = await get_vehicle_ids(db, enterprise_id=enterprise_id)

        if clear_before:
            await clear_old_data(db, vehicle_ids)

        created_trips_total = 0
        created_points_total = 0

        for vehicle_id in vehicle_ids:
            points_to_insert: list[VehicleGpsPoint] = []
            trip_specs: list[tuple[datetime, datetime, int, int]] = []

            for _ in range(trips_per_vehicle):
                started_at = random_trip_start(
                    date_from=date_from,
                    date_to=date_to,
                )

                duration_minutes = random.randint(20, 120)
                ended_at = started_at + timedelta(minutes=duration_minutes)

                route = build_route_points(
                    center_lat=center_lat,
                    center_lon=center_lon,
                    radius_km=radius_km,
                    points_count=points_per_trip,
                )

                first_point_index = len(points_to_insert)
                last_point_index = first_point_index + len(route) - 1

                for point_index, (lat, lon) in enumerate(route):
                    recorded_at = started_at + (
                        (ended_at - started_at) * point_index / max(points_per_trip - 1, 1)
                    )

                    points_to_insert.append(
                        VehicleGpsPoint(
                            vehicle_id=vehicle_id,
                            recorded_at_utc=recorded_at,
                            position=point_wkt(lon, lat),
                        )
                    )

                trip_specs.append(
                    (
                        started_at,
                        ended_at,
                        first_point_index,
                        last_point_index,
                    )
                )

            try:
                db.add_all(points_to_insert)
                await db.flush()

                trips_to_insert: list[Trip] = []

                for started_at, ended_at, first_idx, last_idx in trip_specs:
                    trips_to_insert.append(
                        Trip(
                            vehicle_id=vehicle_id,
                            started_at_utc=started_at,
                            ended_at_utc=ended_at,
                            start_point_id=points_to_insert[first_idx].id,
                            end_point_id=points_to_insert[last_idx].id,
                        )
                    )

                db.add_all(trips_to_insert)
                await db.commit()

            except Exception:
                await db.rollback()
                raise

            created_trips_total += len(trips_to_insert)
            created_points_total += len(points_to_insert)

            typer.echo(
                f"vehicle_id={vehicle_id}: "
                f"поездок={len(trips_to_insert)}, "
                f"точек={len(points_to_insert)}"
            )

    typer.echo("Генерация завершена")
    typer.echo(f"Предприятие: {enterprise_id}")
    typer.echo(f"Машин: {len(vehicle_ids)}")
    typer.echo(f"Поездок на машину: {trips_per_vehicle}")
    typer.echo(f"Поездок всего: {created_trips_total}")
    typer.echo(f"GPS-точек всего: {created_points_total}")


@app.command()
def generate(
    enterprise_id: Annotated[
        int,
        typer.Option("--enterprise-id", help="ID предприятия"),
    ],
    trips_per_vehicle: Annotated[
        int,
        typer.Option(
            "--trips-per-vehicle",
            help="Количество поездок на каждую машину предприятия",
        ),
    ] = DEFAULT_TRIPS_PER_VEHICLE,
    points_per_trip: Annotated[
        int,
        typer.Option("--points-per-trip", help="Количество GPS-точек в одной поездке"),
    ] = DEFAULT_POINTS_PER_TRIP,
    date_from: Annotated[
        str,
        typer.Option("--date-from", help="Начало исторического периода: YYYY-MM-DD"),
    ] = "2024-01-01",
    date_to: Annotated[
        str,
        typer.Option("--date-to", help="Конец исторического периода: YYYY-MM-DD"),
    ] = "2026-01-01",
    center_lat: Annotated[
        float,
        typer.Option("--center-lat", help="Широта центра генерации"),
    ] = DEFAULT_CENTER_LAT,
    center_lon: Annotated[
        float,
        typer.Option("--center-lon", help="Долгота центра генерации"),
    ] = DEFAULT_CENTER_LON,
    radius_km: Annotated[
        float,
        typer.Option("--radius-km", help="Радиус генерации маршрутов"),
    ] = 20.0,
    clear_before: Annotated[
        bool,
        typer.Option("--clear-before", help="Удалить старые поездки и точки этих машин"),
    ] = False,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Seed для воспроизводимой генерации"),
    ] = None,
) -> None:
    try:
        parsed_date_from = date.fromisoformat(date_from)
        parsed_date_to = date.fromisoformat(date_to)
    except ValueError as exc:
        raise typer.BadParameter("date_from/date_to должны быть в формате YYYY-MM-DD") from exc

    asyncio.run(
        seed_demo_tracks(
            enterprise_id=enterprise_id,
            trips_per_vehicle=trips_per_vehicle,
            points_per_trip=points_per_trip,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            clear_before=clear_before,
            seed=seed,
        )
    )


if __name__ == "__main__":
    app()
