async function getReportTypesRequest() {
    return await apiRequest("/reports/types", {method: "GET"});
}

async function getReportsRequest() {
    return await apiRequest("/reports", {method: "GET"});
}

async function getReportRequest(id) {
    return await apiRequest(`/reports/${id}`, {method: "GET"});
}

async function createReportRequest(payload) {
    return await apiRequest("/reports", {
        method: "POST",
        body: JSON.stringify(payload)
    });
}

async function rebuildReportRequest(id) {
    return await apiRequest(`/reports/${id}/rebuild`, {
        method: "POST"
    });
}

async function deleteReportRequest(id) {
    return await apiRequest(`/reports/${id}`, {
        method: "DELETE"
    });
}

async function exportReportRequest(report, format = "json") {
    const filename = buildReportFilename(report, format);

    await downloadFile(
        `${API_BASE}/reports/${report.id}/export?format=${format}`,
        filename
    );
}

function buildReportFilename(report, format) {
    const safe = (value) => {
        return String(value ?? "")
            .replace(/[^a-zA-Z0-9а-яА-Я_-]+/g, "_")
            .replace(/_+/g, "_")
            .replace(/^_|_$/g, "");
    };

    const parts = [
        "report",
        report.report_type,
        `vehicle_${report.vehicle_id}`,
        report.period,
        report.date_from?.slice(0, 10),
        report.date_to?.slice(0, 10),
    ];

    return `${parts.map(safe).join("_")}.${format}`;
}
