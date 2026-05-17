from enum import StrEnum


class ExportFormat(StrEnum):
    json = "json"
    csv = "csv"
    pdf = "pdf"


class ImportFormat(StrEnum):
    json = "json"
    csv = "csv"
