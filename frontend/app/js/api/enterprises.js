async function getEnterprisesRequest() {
    return await apiRequest("/enterprises", {
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
