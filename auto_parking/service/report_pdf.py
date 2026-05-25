import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from auto_parking.core.domain.enums.report_type import ReportType


class ReportPdfBuilder:
    FONT_REGULAR = "DejaVuSans"
    FONT_BOLD = "DejaVuSans-Bold"

    REPORT_TYPE_LABELS = {
        ReportType.vehicle_mileage.value: "Пробег автомобиля",
        ReportType.vehicle_activity.value: "Активность автомобиля",
        ReportType.vehicle_geography.value: "География поездок",
    }

    PERIOD_LABELS = {
        "day": "День",
        "month": "Месяц",
        "year": "Год",
    }

    def __init__(self) -> None:
        self._register_fonts()

        self._result_table_builders: dict[
            str,
            Callable[[list[dict[str, Any]]], Table],
        ] = {
            ReportType.vehicle_mileage.value: self._build_mileage_table,
            ReportType.vehicle_activity.value: self._build_activity_table,
            ReportType.vehicle_geography.value: self._build_geography_table,
        }

    def build(self, report) -> bytes:
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=24,
            leftMargin=24,
            topMargin=24,
            bottomMargin=24,
        )

        styles = getSampleStyleSheet()
        styles["Title"].fontName = self.FONT_BOLD
        styles["BodyText"].fontName = self.FONT_REGULAR
        styles["Heading2"].fontName = self.FONT_BOLD

        elements = [
            Paragraph(f"Отчёт: {report.name}", styles["Title"]),
            Spacer(1, 16),
            self._build_meta_table(report),
            Spacer(1, 20),
            Paragraph("Результаты", styles["Heading2"]),
            Spacer(1, 10),
            self._build_result_table(report),
        ]

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        return pdf

    def _build_meta_table(self, report) -> Table:
        report_type = self._enum_value(report.report_type)
        period = self._enum_value(report.period)

        rows = [
            ["ID", str(report.id)],
            ["Название", str(report.name)],
            ["Тип отчёта", self.REPORT_TYPE_LABELS.get(report_type, report_type)],
            ["Период", self.PERIOD_LABELS.get(period, period)],
            ["Enterprise ID", str(report.enterprise_id)],
            ["Vehicle ID", str(report.vehicle_id or "—")],
            ["Дата от", report.date_from.isoformat()],
            ["Дата до", report.date_to.isoformat()],
            ["Создан", report.created_at.isoformat()],
        ]

        table = Table(rows, colWidths=[180, 620])
        table.setStyle(self._meta_style())

        return table

    def _build_result_table(self, report) -> Table:
        report_type = self._enum_value(report.report_type)
        builder = self._result_table_builders.get(report_type, self._build_generic_table)

        return builder(report.result_json or [])

    def _build_mileage_table(self, result_json: list[dict[str, Any]]) -> Table:
        rows = [["Период", "Пробег, км"]]

        for item in result_json:
            rows.append(
                [
                    str(item.get("time", "—")),
                    self._format_number(item.get("value", 0)),
                ]
            )

        return self._styled_result_table(
            rows=rows,
            col_widths=[300, 220],
        )

    def _build_activity_table(self, result_json: list[dict[str, Any]]) -> Table:
        rows = [
            [
                "Период",
                "В движении, ч",
                "Простой, ч",
                "Всего, ч",
                "Активность, %",
            ]
        ]

        for item in result_json:
            extra = item.get("extra", {}) or {}

            moving_hours = self._to_float(extra.get("moving_hours", item.get("value", 0)))
            idle_hours = self._to_float(extra.get("idle_hours", 0))
            total_hours = moving_hours + idle_hours

            activity_percent = moving_hours / total_hours * 100 if total_hours > 0 else 0

            rows.append(
                [
                    str(item.get("time", "—")),
                    f"{moving_hours:.2f}",
                    f"{idle_hours:.2f}",
                    f"{total_hours:.2f}",
                    f"{activity_percent:.2f}",
                ]
            )

        return self._styled_result_table(
            rows=rows,
            col_widths=[150, 150, 150, 150, 150],
        )

    def _build_geography_table(self, result_json: list[dict[str, Any]]) -> Table:
        rows = [
            [
                "Период",
                "Широта",
                "Долгота",
                "Количество поездок",
            ]
        ]

        for item in result_json:
            extra = item.get("extra", {}) or {}
            zone = str(extra.get("zone", ""))

            lat = "—"
            lon = "—"

            if "_" in zone:
                lat, lon = zone.split("_", 1)

            rows.append(
                [
                    str(item.get("time", "—")),
                    lat,
                    lon,
                    str(item.get("value", "—")),
                ]
            )

        return self._styled_result_table(
            rows=rows,
            col_widths=[200, 180, 180, 200],
        )

    def _build_generic_table(self, result_json: list[dict[str, Any]]) -> Table:
        rows = [["Период", "Значение", "Дополнительно"]]

        for item in result_json:
            rows.append(
                [
                    str(item.get("time", "—")),
                    str(item.get("value", "—")),
                    json.dumps(item.get("extra", {}), ensure_ascii=False),
                ]
            )

        return self._styled_result_table(
            rows=rows,
            col_widths=[180, 160, 440],
        )

    def _meta_style(self) -> TableStyle:
        return TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("FONTNAME", (0, 0), (0, -1), self.FONT_BOLD),
                ("FONTNAME", (1, 0), (-1, -1), self.FONT_REGULAR),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )

    def _styled_result_table(
        self,
        *,
        rows: list[list[str]],
        col_widths: list[int],
    ) -> Table:
        if len(rows) == 1:
            rows.append(["Нет данных"] + ["—"] * (len(rows[0]) - 1))

        table = Table(
            rows,
            colWidths=col_widths,
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("FONTNAME", (0, 0), (-1, 0), self.FONT_BOLD),
                    ("FONTNAME", (0, 1), (-1, -1), self.FONT_REGULAR),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )

        return table

    @classmethod
    def _register_fonts(cls) -> None:
        root_dir = Path(__file__).resolve().parents[2]
        fonts_dir = root_dir / "assets" / "fonts"

        regular_font = fonts_dir / "DejaVuSans.ttf"
        bold_font = fonts_dir / "DejaVuSans-Bold.ttf"

        registered = set(pdfmetrics.getRegisteredFontNames())

        if cls.FONT_REGULAR not in registered:
            pdfmetrics.registerFont(TTFont(cls.FONT_REGULAR, str(regular_font)))

        if cls.FONT_BOLD not in registered:
            pdfmetrics.registerFont(TTFont(cls.FONT_BOLD, str(bold_font)))

    @staticmethod
    def _enum_value(value) -> str:
        return getattr(value, "value", str(value))

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _format_number(value: Any) -> str:
        number = ReportPdfBuilder._to_float(value)

        if number.is_integer():
            return str(int(number))

        return f"{number:.3f}"
