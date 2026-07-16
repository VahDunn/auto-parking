from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.infrastructure.db.models import Report


class ReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, enterprise_ids: set[int] | None = None) -> Sequence[Report]:
        stmt = select(Report).order_by(Report.created_at.desc(), Report.id.desc())

        if enterprise_ids is not None:
            stmt = stmt.where(Report.enterprise_id.in_(enterprise_ids))

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_id(self, report_id: int) -> Report | None:
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Report:
        report = Report(**data)

        self.db.add(report)
        await self.db.flush()

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(report)
        return report

    async def update(self, report_id: int, result_json: list[dict]) -> Report | None:
        report = await self.get_by_id(report_id)
        if report is None:
            return None

        report.result_json = result_json

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(report)
        return report

    async def delete(self, report_id: int) -> bool:
        report = await self.get_by_id(report_id)
        if report is None:
            return False

        await self.db.delete(report)

        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        return True
