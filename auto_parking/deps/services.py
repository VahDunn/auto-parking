from fastapi import Depends

from auto_parking.deps.repos import depends_enterprise_repo
from auto_parking.repo.enterprise import EnterpriseRepository
from auto_parking.service.enterprise import EnterpriseService


def get_enterprise_service(
    repo: EnterpriseRepository = depends_enterprise_repo,
) -> EnterpriseService:
    return EnterpriseService(repo)


depends_enterprise_service = Depends(get_enterprise_service)
