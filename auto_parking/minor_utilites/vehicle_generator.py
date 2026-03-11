import asyncio
import random
from typing import Annotated

import typer
from faker import Faker
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.api.schemas.vehicle import VehicleCreate, is_valid_plate
from auto_parking.db.engine import AsyncSessionLocal  # замени на свой путь
from auto_parking.db.models import Driver, Enterprise, Vehicle, VehicleModel

app = typer.Typer(help="Утилита генерации тестовых машин и водителей")

PLATE_LETTERS = "АВЕКМНОРСТУХ"

fake = Faker("ru_RU")


def random_plate() -> str:
    while True:
        plate = (
            f"{random.choice(PLATE_LETTERS)}"
            f"{random.randint(0, 999):03d}"
            f"{random.choice(PLATE_LETTERS)}"
            f"{random.choice(PLATE_LETTERS)}"
            f"{random.randint(1, 999)}"
        )
        if is_valid_plate(plate):
            return plate


async def generate_unique_plate(db: AsyncSession) -> str:
    while True:
        plate = random_plate()
        exists = await db.scalar(
            select(func.count()).select_from(Vehicle).where(Vehicle.vehicle_number == plate)
        )
        if not exists:
            return plate


def build_vehicle_payload(*, enterprise_id: int, model_id: int) -> VehicleCreate:
    return VehicleCreate(
        price=random.randint(500_000, 7_000_000),
        mileage=random.randint(0, 350_000),
        vehicle_number="TEMP",
        owners_count=random.randint(0, 6),
        accident_number=random.randint(0, 5),
        manufacture_year=random.randint(2000, 2026),
        model_id=model_id,
        enterprise_id=enterprise_id,
    )


def build_driver(*, enterprise_id: int) -> Driver:
    return Driver(
        name=fake.name(),
        salary_rub=random.randint(60_000, 180_000),
        enterprise_id=enterprise_id,
    )


async def get_enterprise_ids(
    db: AsyncSession,
    requested_ids: list[int] | None,
) -> list[int]:
    stmt = select(Enterprise.id)

    if requested_ids:
        stmt = stmt.where(Enterprise.id.in_(requested_ids))

    result = await db.execute(stmt)
    enterprise_ids = list(result.scalars().all())

    if not enterprise_ids:
        raise ValueError("Не найдено ни одного предприятия")

    return enterprise_ids


async def get_model_ids(db: AsyncSession) -> list[int]:
    result = await db.execute(select(VehicleModel.id))
    model_ids = list(result.scalars().all())

    if not model_ids:
        raise ValueError("В таблице vehicle_model нет записей")

    return model_ids


async def generate_vehicles(
    *,
    total_count: int,
    enterprise_ids: list[int] | None,
    driver_ratio: int,
    seed: int | None,
) -> None:
    if total_count <= 0:
        raise ValueError("Количество машин должно быть больше 0")

    if driver_ratio <= 0:
        raise ValueError("driver_ratio должен быть больше 0")

    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    async with AsyncSessionLocal() as db:
        real_enterprise_ids = await get_enterprise_ids(db, enterprise_ids)
        model_ids = await get_model_ids(db)

        created_vehicles: list[Vehicle] = []
        created_drivers = 0

        for i in range(total_count):
            enterprise_id = real_enterprise_ids[i % len(real_enterprise_ids)]
            model_id = random.choice(model_ids)

            payload = build_vehicle_payload(
                enterprise_id=enterprise_id,
                model_id=model_id,
            )

            data = payload.model_dump()
            data["vehicle_number"] = await generate_unique_plate(db)

            vehicle = Vehicle(**data)

            if (i + 1) % driver_ratio == 0:
                driver = build_driver(enterprise_id=enterprise_id)
                db.add(driver)
                await db.flush()

                vehicle.active_driver = driver
                vehicle.drivers.append(driver)
                created_drivers += 1

            db.add(vehicle)
            created_vehicles.append(vehicle)

        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    typer.echo(f"Создано машин: {len(created_vehicles)}")
    typer.echo(f"Создано активных водителей: {created_drivers}")


@app.command()
def generate(
    count: Annotated[
        int,
        typer.Option("--count", "-c", help="Количество машин для генерации"),
    ],
    enterprise_ids: Annotated[
        list[int] | None,
        typer.Option(
            "--enterprise-id",
            "-e",
            help="ID предприятия. Можно указать несколько раз: -e 1 -e 2 -e 3",
        ),
    ] = None,
    driver_ratio: Annotated[
        int,
        typer.Option(
            "--driver-ratio",
            "-r",
            help="У каждой N-й машины будет активный водитель",
        ),
    ] = 10,
    seed: Annotated[
        int | None,
        typer.Option(
            "--seed",
            help="Seed для воспроизводимой генерации",
        ),
    ] = None,
) -> None:
    if not enterprise_ids:
        raise ValueError("Укажите enterprise id")
    asyncio.run(
        generate_vehicles(
            total_count=count,
            enterprise_ids=enterprise_ids[1:],
            driver_ratio=driver_ratio,
            seed=seed,
        )
    )


if __name__ == "__main__":
    app()
