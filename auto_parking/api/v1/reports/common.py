from fastapi import Depends

from auto_parking.api.schemas.report import ReportInfo, ReportOut
from auto_parking.core.domain.models import ReportInfoModel, ReportModel
from auto_parking.deps.access import require_manager_or_higher
from auto_parking.deps.visibility import ensure_enterprise_visible, get_visible_enterprise_ids

dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


def report_info_out(report_info: ReportInfoModel) -> ReportInfo:
    return ReportInfo(**report_info.to_dict())


def report_out(report: ReportModel) -> ReportOut:
    return ReportOut(**report.to_dict())


def ensure_report_visible(
    report: ReportModel,
    visible_enterprise_ids: set[int] | None,
) -> None:
    ensure_enterprise_visible(report.enterprise_id, visible_enterprise_ids)
