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