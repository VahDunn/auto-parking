import asyncio
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import httpx
import typer
from geoalchemy2.elements import WKTElement
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.db.engine import AsyncSessionLocal
from auto_parking.db.models import Enterprise, Vehicle, VehicleGpsPoint

app = typer.Typer(help="Утилита генерации GPS-треков для существующих машин")

OSRM_BASE_URL = "https://router.project-osrm.org"

CITY_CENTERS: dict[str, tuple[float, float]] = {
    "москва": (55.7558, 37.6176),
    "moscow": (55.7558, 37.6176),
    "санкт-петербург": (59.9343, 30.3351),
    "saint petersburg": (59.9343, 30.3351),
    "петербург": (59.9343, 30.3351),
    "казань": (55.7961, 49.1064),
    "kazan": (55.7961, 49.1064),
    "екатеринбург": (56.8389, 60.6057),
    "yekaterinburg": (56.8389, 60.6057),
    "новосибирск": (55.0302, 82.9204),
    "novosibirsk": (55.0302, 82.9204),
    "нижний новгород": (56.3269, 44.0065),
    "nizhny novgorod": (56.3269, 44.0065),
    "new orleans": (29.9511, -90.0715),
    "new orleans, la": (29.9511, -90.0715),
}


@dataclass
class VehicleRouteState:
    vehicle_id: int
    route_points: list[tuple[float, float]]
    point_index: int
    route_number: int
    seed: int | None
    skipped: bool = False


def _normalize_city_name(name: str | None) -> str | None:
    if not name:
        return None
    return " ".join(name.strip().lower().split())


def _city_center_from_name(name: str | None) -> tuple[float, float] | None:
    normalized = _normalize_city_name(name)
    if not normalized:
        return None
    return CITY_CENTERS.get(normalized)


async def _get_vehicle_ids_by_enterprise(
    db: AsyncSession,
    enterprise_id: int,
) -> list[int]:
    result = await db.execute(
        select(Vehicle.id).where(Vehicle.enterprise_id == enterprise_id).order_by(Vehicle.id)
    )
    vehicle_ids = list(result.scalars().all())

    if not vehicle_ids:
        raise ValueError(f"У enterprise_id={enterprise_id} нет машин")

    return vehicle_ids


async def clear_enterprise_track_points(enterprise_id: int) -> None:
    async with AsyncSessionLocal() as db:
        vehicle_ids = await _get_vehicle_ids_by_enterprise(db, enterprise_id)
        await db.execute(delete(VehicleGpsPoint).where(VehicleGpsPoint.vehicle_id.in_(vehicle_ids)))
        await db.commit()
        typer.echo(
            f"Удалены точки машин предприятия {enterprise_id}. Количество машин: {len(vehicle_ids)}"
        )


async def _get_vehicle_with_enterprise(db: AsyncSession, vehicle_id: int) -> Vehicle:
    result = await db.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    vehicle = result.scalar_one_or_none()

    if not vehicle:
        raise ValueError(f"Машина с id={vehicle_id} не найдена")

    await vehicle.awaitable_attrs.enterprise
    return vehicle


def _resolve_center(
    enterprise: Enterprise | None,
    center_lat: float | None,
    center_lon: float | None,
) -> tuple[float, float] | None:
    if center_lat is not None and center_lon is not None:
        return center_lat, center_lon

    if enterprise:
        settlement = (enterprise.settlement or "").strip().lower()
        if settlement and settlement != "неизвестно":
            guessed = _city_center_from_name(settlement)
            if guessed:
                return guessed

    return None


def _random_point_in_radius(
    center_lat: float,
    center_lon: float,
    radius_km: float,
) -> tuple[float, float]:
    radius_m = radius_km * 1000.0
    distance_m = radius_m * math.sqrt(random.random())
    angle = random.random() * 2.0 * math.pi

    delta_lat = (distance_m * math.cos(angle)) / 111_320.0
    lon_scale = 111_320.0 * math.cos(math.radians(center_lat))
    if abs(lon_scale) < 1e-9:
        lon_scale = 1e-9
    delta_lon = (distance_m * math.sin(angle)) / lon_scale

    return center_lat + delta_lat, center_lon + delta_lon


def _haversine_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    r = 6_371_000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _polyline_length_m(coords: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(coords)):
        lon1, lat1 = coords[i - 1]
        lon2, lat2 = coords[i]
        total += _haversine_m(lat1, lon1, lat2, lon2)
    return total


def _interpolate_segment(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    fraction: float,
) -> tuple[float, float]:
    return (
        lon1 + (lon2 - lon1) * fraction,
        lat1 + (lat2 - lat1) * fraction,
    )


def _resample_route(
    coords: list[tuple[float, float]],
    step_m: float,
    jitter_m: float,
) -> list[tuple[float, float]]:
    if len(coords) < 2:
        return coords[:]

    result: list[tuple[float, float]] = [coords[0]]
    target_distance = max(5.0, step_m + random.uniform(-jitter_m, jitter_m))
    accumulated = 0.0

    prev_lon, prev_lat = coords[0]

    for i in range(1, len(coords)):
        curr_lon, curr_lat = coords[i]
        segment_length = _haversine_m(prev_lat, prev_lon, curr_lat, curr_lon)

        while accumulated + segment_length >= target_distance and segment_length > 0:
            remain = target_distance - accumulated
            fraction = remain / segment_length

            point_lon, point_lat = _interpolate_segment(
                prev_lon,
                prev_lat,
                curr_lon,
                curr_lat,
                fraction,
            )
            result.append((point_lon, point_lat))

            prev_lon, prev_lat = point_lon, point_lat
            segment_length = _haversine_m(prev_lat, prev_lon, curr_lat, curr_lon)
            accumulated = 0.0
            target_distance = max(5.0, step_m + random.uniform(-jitter_m, jitter_m))

        accumulated += segment_length
        prev_lon, prev_lat = curr_lon, curr_lat

    if result[-1] != coords[-1]:
        result.append(coords[-1])

    return result


async def _build_route_osrm(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> tuple[list[tuple[float, float]], float]:
    url = f"{OSRM_BASE_URL}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "false",
    }

    timeout = httpx.Timeout(20.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    routes = data.get("routes") or []
    if not routes:
        raise ValueError("OSRM не вернул маршрут")

    route = routes[0]
    geometry = route.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    distance_m = float(route.get("distance") or 0.0)

    if len(coordinates) < 2:
        raise ValueError("OSRM вернул слишком короткий маршрут")

    parsed_coords: list[tuple[float, float]] = [
        (float(lon), float(lat)) for lon, lat in coordinates
    ]
    return parsed_coords, distance_m


def _build_route_fallback(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> tuple[list[tuple[float, float]], float]:
    wiggle = 0.01

    mid1_lon = start_lon + (end_lon - start_lon) * 0.33 + random.uniform(-wiggle, wiggle)
    mid1_lat = start_lat + (end_lat - start_lat) * 0.33 + random.uniform(-wiggle, wiggle)
    mid2_lon = start_lon + (end_lon - start_lon) * 0.66 + random.uniform(-wiggle, wiggle)
    mid2_lat = start_lat + (end_lat - start_lat) * 0.66 + random.uniform(-wiggle, wiggle)

    coords = [
        (start_lon, start_lat),
        (mid1_lon, mid1_lat),
        (mid2_lon, mid2_lat),
        (end_lon, end_lat),
    ]
    return coords, _polyline_length_m(coords)


async def _build_route_segment(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    use_osrm: bool,
) -> tuple[list[tuple[float, float]], float, bool]:
    if use_osrm:
        try:
            coords, distance_m = await _build_route_osrm(
                start_lat=start_lat,
                start_lon=start_lon,
                end_lat=end_lat,
                end_lon=end_lon,
            )
            return coords, distance_m, True
        except Exception:
            pass

    coords, distance_m = _build_route_fallback(
        start_lat=start_lat,
        start_lon=start_lon,
        end_lat=end_lat,
        end_lon=end_lon,
    )
    return coords, distance_m, False


async def _build_full_route(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    track_length_km: float,
    use_osrm: bool,
) -> tuple[list[tuple[float, float]], bool]:
    total_target_m = track_length_km * 1000.0
    total_distance_m = 0.0
    used_osrm_any = False

    current_lat, current_lon = _random_point_in_radius(center_lat, center_lon, radius_km)
    full_coords: list[tuple[float, float]] = [(current_lon, current_lat)]

    attempts = 0
    while total_distance_m < total_target_m and attempts < 20:
        attempts += 1
        next_lat, next_lon = _random_point_in_radius(center_lat, center_lon, radius_km)

        segment_coords, segment_distance_m, used_osrm = await _build_route_segment(
            start_lat=current_lat,
            start_lon=current_lon,
            end_lat=next_lat,
            end_lon=next_lon,
            use_osrm=use_osrm,
        )

        if segment_distance_m < 50.0:
            continue

        used_osrm_any = used_osrm_any or used_osrm

        if len(segment_coords) > 1:
            full_coords.extend(segment_coords[1:])

        total_distance_m += segment_distance_m
        current_lat, current_lon = next_lat, next_lon

    if len(full_coords) < 2:
        raise ValueError("Не удалось построить маршрут")

    return full_coords, used_osrm_any


def _point_wkt(lon: float, lat: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def _make_track_point(
    vehicle_id: int,
    recorded_at_utc: datetime,
    lon: float,
    lat: float,
) -> VehicleGpsPoint:
    return VehicleGpsPoint(
        vehicle_id=vehicle_id,
        recorded_at_utc=recorded_at_utc,
        position=_point_wkt(lon, lat),
    )


async def _insert_track_points_batch(
    db: AsyncSession,
    points: list[VehicleGpsPoint],
) -> None:
    if not points:
        return

    db.add_all(points)
    await db.commit()


async def _insert_single_track_point(
    db: AsyncSession,
    vehicle_id: int,
    recorded_at_utc: datetime,
    lon: float,
    lat: float,
) -> None:
    point = _make_track_point(
        vehicle_id=vehicle_id,
        recorded_at_utc=recorded_at_utc,
        lon=lon,
        lat=lat,
    )
    db.add(point)
    await db.commit()


async def _prepare_vehicle_route_state(
    *,
    vehicle_id: int,
    center_lat: float | None,
    center_lon: float | None,
    radius_km: float,
    track_length_km: float,
    step_m: float,
    step_jitter_m: float,
    seed: int | None,
    use_osrm: bool,
) -> VehicleRouteState:
    if seed is not None:
        random.seed(seed)

    async with AsyncSessionLocal() as db:
        vehicle = await _get_vehicle_with_enterprise(db, vehicle_id)
        enterprise = vehicle.enterprise

    center = _resolve_center(
        enterprise=enterprise,
        center_lat=center_lat,
        center_lon=center_lon,
    )

    if center is None:
        typer.echo(
            f"[SKIP] vehicle_id={vehicle_id} — неизвестный settlement='{enterprise.settlement}'"
        )
        return VehicleRouteState(
            vehicle_id=vehicle_id,
            route_points=[],
            point_index=0,
            route_number=0,
            seed=seed,
            skipped=True,
        )

    route_center_lat, route_center_lon = center

    raw_route, used_osrm_any = await _build_full_route(
        center_lat=route_center_lat,
        center_lon=route_center_lon,
        radius_km=radius_km,
        track_length_km=track_length_km,
        use_osrm=use_osrm,
    )

    resampled_route = _resample_route(
        coords=raw_route,
        step_m=step_m,
        jitter_m=step_jitter_m,
    )

    typer.echo(
        f"Маршрут #1 для машины {vehicle_id} подготовлен. "
        f"Точек: {len(resampled_route)}. "
        f"Источник: {'OSRM' if used_osrm_any else 'fallback'}."
    )

    return VehicleRouteState(
        vehicle_id=vehicle_id,
        route_points=resampled_route,
        point_index=0,
        route_number=1,
        seed=seed,
        skipped=False,
    )


async def _rebuild_vehicle_route_state(
    state: VehicleRouteState,
    *,
    center_lat: float | None,
    center_lon: float | None,
    radius_km: float,
    track_length_km: float,
    step_m: float,
    step_jitter_m: float,
    use_osrm: bool,
) -> VehicleRouteState:
    next_seed = None if state.seed is None else state.seed + state.route_number

    new_state = await _prepare_vehicle_route_state(
        vehicle_id=state.vehicle_id,
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        track_length_km=track_length_km,
        step_m=step_m,
        step_jitter_m=step_jitter_m,
        seed=next_seed,
        use_osrm=use_osrm,
    )

    if not new_state.skipped:
        new_state.route_number = state.route_number + 1

    return new_state


async def generate_live_track(
    *,
    vehicle_id: int,
    center_lat: float | None,
    center_lon: float | None,
    radius_km: float,
    track_length_km: float,
    interval_sec: int,
    step_m: float,
    step_jitter_m: float,
    seed: int | None,
    use_osrm: bool,
    clear_before: bool,
    loop: bool,
) -> None:
    if radius_km <= 0:
        raise ValueError("radius_km должен быть больше 0")
    if track_length_km <= 0:
        raise ValueError("track_length_km должен быть больше 0")
    if interval_sec <= 0:
        raise ValueError("interval_sec должен быть больше 0")
    if step_m <= 0:
        raise ValueError("step_m должен быть больше 0")
    if step_jitter_m < 0:
        raise ValueError("step_jitter_m не может быть отрицательным")

    if seed is not None:
        random.seed(seed)

    async with AsyncSessionLocal() as db:
        vehicle = await _get_vehicle_with_enterprise(db, vehicle_id)
        enterprise = vehicle.enterprise

        center = _resolve_center(
            enterprise=enterprise,
            center_lat=center_lat,
            center_lon=center_lon,
        )

        if center is None:
            typer.echo(
                f"[SKIP] vehicle_id={vehicle_id} — неизвестный settlement='{enterprise.settlement}'"
            )
            return

        route_center_lat, route_center_lon = center

        if clear_before:
            await db.execute(
                delete(VehicleGpsPoint).where(VehicleGpsPoint.vehicle_id == vehicle_id)
            )
            await db.commit()

        route_number = 0

        while True:
            route_number += 1

            raw_route, used_osrm_any = await _build_full_route(
                center_lat=route_center_lat,
                center_lon=route_center_lon,
                radius_km=radius_km,
                track_length_km=track_length_km,
                use_osrm=use_osrm,
            )

            resampled_route = _resample_route(
                coords=raw_route,
                step_m=step_m,
                jitter_m=step_jitter_m,
            )

            typer.echo(
                f"Маршрут #{route_number} для машины {vehicle_id} подготовлен. "
                f"Точек: {len(resampled_route)}. "
                f"Источник: {'OSRM' if used_osrm_any else 'fallback'}."
            )

            for idx, (lon, lat) in enumerate(resampled_route, start=1):
                now_utc = datetime.now(UTC)

                await _insert_single_track_point(
                    db=db,
                    vehicle_id=vehicle_id,
                    recorded_at_utc=now_utc,
                    lon=lon,
                    lat=lat,
                )

                typer.echo(
                    f"[route {route_number}][{idx}/{len(resampled_route)}] "
                    f"vehicle_id={vehicle_id} "
                    f"time={now_utc.isoformat()} "
                    f"lon={lon:.6f} lat={lat:.6f}"
                )

                if idx < len(resampled_route):
                    await asyncio.sleep(interval_sec)

            if not loop:
                break

    typer.echo("Генерация live-трека завершена")


async def generate_enterprise_live_tracks(
    *,
    enterprise_id: int,
    center_lat: float | None,
    center_lon: float | None,
    radius_km: float,
    track_length_km: float,
    interval_sec: int,
    step_m: float,
    step_jitter_m: float,
    seed: int | None,
    use_osrm: bool,
    clear_before: bool,
) -> None:
    if radius_km <= 0:
        raise ValueError("radius_km должен быть больше 0")
    if track_length_km <= 0:
        raise ValueError("track_length_km должен быть больше 0")
    if interval_sec <= 0:
        raise ValueError("interval_sec должен быть больше 0")
    if step_m <= 0:
        raise ValueError("step_m должен быть больше 0")
    if step_jitter_m < 0:
        raise ValueError("step_jitter_m не может быть отрицательным")

    async with AsyncSessionLocal() as db:
        vehicle_ids = await _get_vehicle_ids_by_enterprise(db, enterprise_id)

        if clear_before:
            await db.execute(
                delete(VehicleGpsPoint).where(VehicleGpsPoint.vehicle_id.in_(vehicle_ids))
            )
            await db.commit()

    typer.echo(
        f"Запуск live-генерации для enterprise_id={enterprise_id}. "
        f"Машин найдено: {len(vehicle_ids)}"
    )

    states: list[VehicleRouteState] = []

    for index, vehicle_id in enumerate(vehicle_ids):
        vehicle_seed = None if seed is None else seed + index

        state = await _prepare_vehicle_route_state(
            vehicle_id=vehicle_id,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            track_length_km=track_length_km,
            step_m=step_m,
            step_jitter_m=step_jitter_m,
            seed=vehicle_seed,
            use_osrm=use_osrm,
        )
        states.append(state)

    active_states = [state for state in states if not state.skipped]

    if not active_states:
        typer.echo("Нет машин с валидным маршрутом для генерации")
        return

    typer.echo(f"Активных машин для генерации: {len(active_states)}")

    try:
        while True:
            now_utc = datetime.now(UTC)
            batch: list[VehicleGpsPoint] = []

            for i, state in enumerate(active_states):
                if state.point_index >= len(state.route_points):
                    new_state = await _rebuild_vehicle_route_state(
                        state,
                        center_lat=center_lat,
                        center_lon=center_lon,
                        radius_km=radius_km,
                        track_length_km=track_length_km,
                        step_m=step_m,
                        step_jitter_m=step_jitter_m,
                        use_osrm=use_osrm,
                    )

                    if new_state.skipped or not new_state.route_points:
                        typer.echo(
                            f"[SKIP] vehicle_id={state.vehicle_id} — новый маршрут не построен"
                        )
                        continue

                    active_states[i] = new_state
                    state = new_state

                    typer.echo(
                        f"Маршрут #{state.route_number} для машины {state.vehicle_id} подготовлен. "
                        f"Точек: {len(state.route_points)}"
                    )

                lon, lat = state.route_points[state.point_index]
                state.point_index += 1

                batch.append(
                    _make_track_point(
                        vehicle_id=state.vehicle_id,
                        recorded_at_utc=now_utc,
                        lon=lon,
                        lat=lat,
                    )
                )

            async with AsyncSessionLocal() as db:
                await _insert_track_points_batch(db, batch)

            typer.echo(f"[tick] {now_utc.isoformat()} записано точек: {len(batch)}")

            await asyncio.sleep(interval_sec)

    except KeyboardInterrupt:
        typer.echo("Остановка генерации enterprise...")


async def clear_track_points(
    *,
    vehicle_id: int | None,
    clear_all: bool,
) -> None:
    if not clear_all and vehicle_id is None:
        raise ValueError("Укажите --vehicle-id или --all")

    async with AsyncSessionLocal() as db:
        if clear_all:
            await db.execute(delete(VehicleGpsPoint))
            await db.commit()
            typer.echo("Удалены все точки")
            return

        await db.execute(delete(VehicleGpsPoint).where(VehicleGpsPoint.vehicle_id == vehicle_id))
        await db.commit()
        typer.echo(f"Удалены точки машины {vehicle_id}")


@app.command("track-generate-live")
def track_generate_live(
    vehicle_id: Annotated[
        int,
        typer.Option("--vehicle-id", help="ID машины"),
    ],
    radius_km: Annotated[
        float,
        typer.Option("--radius-km", help="Радиус зоны генерации в километрах"),
    ] = 5.0,
    track_length_km: Annotated[
        float,
        typer.Option("--track-length-km", help="Желаемая длина маршрута в километрах"),
    ] = 8.0,
    interval_sec: Annotated[
        int,
        typer.Option("--interval-sec", help="Интервал записи точек в секундах"),
    ] = 10,
    step_m: Annotated[
        float,
        typer.Option("--step-m", help="Средний шаг между соседними точками в метрах"),
    ] = 80.0,
    step_jitter_m: Annotated[
        float,
        typer.Option("--step-jitter-m", help="Случайный разброс шага в метрах"),
    ] = 20.0,
    center_lat: Annotated[
        float | None,
        typer.Option("--center-lat", help="Широта центра маршрута"),
    ] = None,
    center_lon: Annotated[
        float | None,
        typer.Option("--center-lon", help="Долгота центра маршрута"),
    ] = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Seed для воспроизводимой генерации"),
    ] = None,
    no_osrm: Annotated[
        bool,
        typer.Option("--no-osrm", help="Не использовать OSRM, только fallback"),
    ] = False,
    clear_before: Annotated[
        bool,
        typer.Option("--clear-before", help="Очистить старые точки этой машины перед генерацией"),
    ] = False,
    loop: Annotated[
        bool,
        typer.Option("--loop", help="После окончания маршрута сразу начинать новый"),
    ] = False,
) -> None:
    asyncio.run(
        generate_live_track(
            vehicle_id=vehicle_id,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            track_length_km=track_length_km,
            interval_sec=interval_sec,
            step_m=step_m,
            step_jitter_m=step_jitter_m,
            seed=seed,
            use_osrm=not no_osrm,
            clear_before=clear_before,
            loop=loop,
        )
    )


@app.command("track-generate-enterprise-live")
def track_generate_enterprise_live(
    enterprise_id: Annotated[
        int,
        typer.Option("--enterprise-id", help="ID предприятия"),
    ],
    radius_km: Annotated[
        float,
        typer.Option("--radius-km", help="Радиус зоны генерации в километрах"),
    ] = 5.0,
    track_length_km: Annotated[
        float,
        typer.Option("--track-length-km", help="Желаемая длина маршрута в километрах"),
    ] = 8.0,
    interval_sec: Annotated[
        int,
        typer.Option("--interval-sec", help="Интервал записи точек в секундах"),
    ] = 10,
    step_m: Annotated[
        float,
        typer.Option("--step-m", help="Средний шаг между соседними точками в метрах"),
    ] = 80.0,
    step_jitter_m: Annotated[
        float,
        typer.Option("--step-jitter-m", help="Случайный разброс шага в метрах"),
    ] = 20.0,
    center_lat: Annotated[
        float | None,
        typer.Option("--center-lat", help="Широта центра маршрута"),
    ] = None,
    center_lon: Annotated[
        float | None,
        typer.Option("--center-lon", help="Долгота центра маршрута"),
    ] = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="Seed для воспроизводимой генерации"),
    ] = None,
    no_osrm: Annotated[
        bool,
        typer.Option("--no-osrm", help="Не использовать OSRM, только fallback"),
    ] = False,
    clear_before: Annotated[
        bool,
        typer.Option("--clear-before", help="Очистить старые точки всех машин предприятия"),
    ] = False,
) -> None:
    asyncio.run(
        generate_enterprise_live_tracks(
            enterprise_id=enterprise_id,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            track_length_km=track_length_km,
            interval_sec=interval_sec,
            step_m=step_m,
            step_jitter_m=step_jitter_m,
            seed=seed,
            use_osrm=not no_osrm,
            clear_before=clear_before,
        )
    )


@app.command("track-clear")
def track_clear(
    vehicle_id: Annotated[
        int | None,
        typer.Option("--vehicle-id", help="ID машины, у которой удалить точки"),
    ] = None,
    clear_all: Annotated[
        bool,
        typer.Option("--all", help="Удалить все точки всех машин"),
    ] = False,
) -> None:
    asyncio.run(
        clear_track_points(
            vehicle_id=vehicle_id,
            clear_all=clear_all,
        )
    )


if __name__ == "__main__":
    app()
