from datetime import datetime

from fastapi import Depends, HTTPException, status
from fastapi.responses import Response

from auto_parking.app.deps.access import require_manager_or_higher
from auto_parking.app.deps.visibility import get_visible_enterprise_ids
from auto_parking.app.schemas.enterprise import EnterpriseOut
from auto_parking.core.domain.enums.import_export_format import ExportFormat
from auto_parking.core.domain.models import EnterpriseModel

dep_actor_guard = Depends(require_manager_or_higher)
dep_visible_ids = Depends(get_visible_enterprise_ids)


def enterprise_out(enterprise: EnterpriseModel) -> EnterpriseOut:
    return EnterpriseOut(**enterprise.to_dict())


def ensure_aware_datetime(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be timezone-aware",
        )


def ensure_valid_date_range(date_from: datetime, date_to: datetime) -> None:
    if date_to < date_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to must be >= date_from",
        )


def export_response(
    *,
    content: str,
    format: ExportFormat,
    filename_base: str,
) -> Response:
    if format == ExportFormat.csv:
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename_base}.csv"'},
        )

    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename_base}.json"'},
    )
