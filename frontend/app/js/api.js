const API_BASE = "http://localhost:8001/api";

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
        credentials: "include",
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        }
    });

    if (response.status === 204) {
        return null;
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || "Ошибка запроса");
    }

    return data;
}

async function loginRequest(username, password) {
    return await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({username, password})
    });
}

async function getEnterprisesRequest() {
    return await apiRequest("/enterprises", {
        method: "GET"
    });
}

async function getVehicleRequest(id) {
    return await apiRequest(`/vehicles/${id}`, {
        method: "GET"
    });
}

async function getVehiclesByEnterpriseRequest(enterpriseId, limit = 10, offset = 0) {
    return await apiRequest(
        `/vehicles?enterprise_ids=${enterpriseId}&sort_by=-id&limit=${limit}&offset=${offset}`,
        {method: "GET"}
    );
}

async function getVehicleModelsRequest() {
    return await apiRequest("/vehicle-models", {
        method: "GET"
    });
}

async function createVehicleRequest(payload) {
    return await apiRequest("/vehicles", {
        method: "POST",
        body: JSON.stringify(payload)
    });
}

async function updateVehicleRequest(id, payload) {
    return await apiRequest(`/vehicles/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload)
    });
}

async function deleteVehicleRequest(id) {
    return await apiRequest(`/vehicles/${id}`, {
        method: "DELETE"
    });
}

async function getVehicleTrackRequest(id, dateFrom, dateTo, format = "geojson") {
    const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        format
    });

    return await apiRequest(`/vehicles/${id}/track?${params.toString()}`, {
        method: "GET"
    });
}

async function getVehicleTripsRequest(id, dateFrom, dateTo) {
    const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo
    });

    return await apiRequest(`/vehicles/${id}/trips?${params.toString()}`, {
        method: "GET"
    });
}

async function getVehicleTrackByTripsRequest(id, dateFrom, dateTo, format = "geojson") {
    const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        format
    });

    return await apiRequest(`/vehicles/${id}/track-by-trips?${params.toString()}`, {
        method: "GET"
    });
}

async function exportEnterpriseRequest(enterpriseId, dateFrom, dateTo, format = "json") {
    const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        format
    });

    const response = await fetch(
        `${API_BASE}/enterprises/${enterpriseId}/export?${params.toString()}`,
        {
            method: "GET",
            credentials: "include"
        }
    );

    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Ошибка экспорта");
    }

    const blob = await response.blob();

    const extension = format === "csv" ? "csv" : "json";
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `enterprise_${enterpriseId}_export.${extension}`;
    document.body.appendChild(a);
    a.click();

    a.remove();
    window.URL.revokeObjectURL(url);
}

async function downloadFile(url, filename) {
    const response = await fetch(url, {
        method: "GET",
        credentials: "include"
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Ошибка экспорта");
    }

    const blob = await response.blob();
    const objectUrl = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();

    a.remove();
    window.URL.revokeObjectURL(objectUrl);
}

async function exportEnterpriseFullRequest(enterpriseId, dateFrom, dateTo, format = "json") {
    const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        format
    });

    await downloadFile(
        `${API_BASE}/enterprises/${enterpriseId}/export?${params.toString()}`,
        `enterprise_${enterpriseId}_full_export.${format}`
    );
}

async function exportEnterpriseVehiclesRequest(enterpriseId, format = "json") {
    const params = new URLSearchParams({format});

    await downloadFile(
        `${API_BASE}/enterprises/${enterpriseId}/export-vehicles?${params.toString()}`,
        `enterprise_${enterpriseId}_vehicles_export.${format}`
    );
}

async function exportVehicleTripsRequest(vehicleId, dateFrom, dateTo, format = "json") {
    const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        format
    });

    await downloadFile(
        `${API_BASE}/vehicles/${vehicleId}/export-trips?${params.toString()}`,
        `vehicle_${vehicleId}_trips_export.${format}`
    );
}

async function importEnterpriseRequest(file, format = "json") {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(
        `${API_BASE}/enterprises/import?format=${encodeURIComponent(format)}`,
        {
            method: "POST",
            credentials: "include",
            body: formData
        }
    );

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || "Ошибка импорта");
    }

    return data;
}

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