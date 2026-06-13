from sqlalchemy.ext.asyncio import AsyncSession


async def commit_transaction(db: AsyncSession | None) -> None:
    if db is not None:
        await db.commit()


async def rollback_transaction(db: AsyncSession | None) -> None:
    if db is not None:
        await db.rollback()
