from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auto_parking.deps.commons import depends_db
from auto_parking.repo.enterprise import EnterpriseRepository


def get_enterprise_repo(
    db: AsyncSession = depends_db,
) -> EnterpriseRepository:
    return EnterpriseRepository(db)


depends_enterprise_repo = Depends(get_enterprise_repo)
