import asyncio

from sqlalchemy import text

from auto_parking.infrastructure.db.engine import AsyncSessionLocal

SUPERMAN_PASSWORD_HASH = "$2b$12$UiPAu7oiyKPU.7a5dwyVWuksXQbHI76zH8nFOR3KQMg93RWtE5vV2"


async def seed_e2e_data() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO enterprise (name, settlement, timezone)
                SELECT 'E2E Test Enterprise', 'Москва', 'Europe/Moscow'
                WHERE NOT EXISTS (
                    SELECT 1 FROM enterprise WHERE name = 'E2E Test Enterprise'
                )
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO vehicle_model (
                    name,
                    type,
                    horse_powers,
                    seats_number,
                    fuel_capacity_liters
                )
                SELECT 'E2E Test Model', 'sedan', 150, 5, 55
                WHERE NOT EXISTS (
                    SELECT 1 FROM vehicle_model WHERE name = 'E2E Test Model'
                )
                """
            )
        )
        await session.execute(
            text(
                """
                INSERT INTO "user" (username, password_hash, role)
                VALUES ('superman', :password_hash, 'manager')
                ON CONFLICT (username)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = 'manager'
                """
            ).bindparams(password_hash=SUPERMAN_PASSWORD_HASH)
        )
        await session.execute(
            text(
                """
                INSERT INTO user_enterprise (user_id, enterprise_id)
                SELECT u.id, e.id
                FROM "user" u
                CROSS JOIN enterprise e
                WHERE u.username = 'superman'
                  AND e.name = 'E2E Test Enterprise'
                ON CONFLICT (user_id, enterprise_id) DO NOTHING
                """
            )
        )
        await session.commit()


def main() -> None:
    asyncio.run(seed_e2e_data())


if __name__ == "__main__":
    main()
