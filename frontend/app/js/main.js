const loginForm = document.getElementById("loginForm");
const loginCard = document.getElementById("loginCard");
const enterpriseCard = document.getElementById("enterpriseCard");
const vehicleCard = document.getElementById("vehicleCard");
const messageBox = document.getElementById("messageBox");
const enterpriseMessage = document.getElementById("enterpriseMessage");
const vehicleMessage = document.getElementById("vehicleMessage");
const reloadBtn = document.getElementById("reloadBtn");
const showCreateFormBtn = document.getElementById("showCreateFormBtn");
const cancelVehicleFormBtn = document.getElementById("cancelVehicleFormBtn");
const vehicleForm = document.getElementById("vehicleForm");
const vehicleEnterpriseTitle = document.getElementById("vehicleEnterpriseTitle");
const loadTripsBtn = document.getElementById("loadTripsBtn");
const showAllTripsMapBtn = document.getElementById("showAllTripsMapBtn");
const exportFullJsonBtn = document.getElementById("exportFullJsonBtn");
const exportFullCsvBtn = document.getElementById("exportFullCsvBtn");
const exportVehiclesJsonBtn = document.getElementById("exportVehiclesJsonBtn");
const exportVehiclesCsvBtn = document.getElementById("exportVehiclesCsvBtn");
const exportVehicleTripsJsonBtn = document.getElementById("exportVehicleTripsJsonBtn");
const exportVehicleTripsCsvBtn = document.getElementById("exportVehicleTripsCsvBtn");
const importDropZone = document.getElementById("importDropZone");
const importFileInput = document.getElementById("importFileInput");
const importBtn = document.getElementById("importBtn");
const importFileName = document.getElementById("importFileName");
const reportMessage = document.getElementById("reportMessage");
const reportForm = document.getElementById("reportForm");
const reloadReportsBtn = document.getElementById("reloadReportsBtn");
const exportReportJsonBtn = document.getElementById("exportReportJsonBtn");
const exportReportCsvBtn = document.getElementById("exportReportCsvBtn");
const reportsCard = document.getElementById("reportsCard");

let selectedReport = null;
let reportsState = [];
let selectedImportFile = null;
let enterprisesState = [];
let selectedEnterprise = null;
let selectedEnterpriseVehicles = [];
let vehicleModels = [];
let vehicleModelsMap = new Map();

let selectedVehicle = null;
let selectedVehicleTrips = [];
let selectedVehicleGroupedTracks = [];

let vehiclePage = 1;
const vehiclePageSize = 10;

let leafletMap = null;
let leafletLayers = [];

function getTrackColor(index) {
    const colors = [
        "#0d6efd",
        "#dc3545",
        "#198754",
        "#fd7e14",
        "#6f42c1",
        "#20c997",
        "#6610f2",
        "#d63384"
    ];
    return colors[index % colors.length];
}

function initMapIfNeeded() {
    if (!leafletMap) {
        leafletMap = L.map("map").setView([55.75, 37.61], 11);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors"
        }).addTo(leafletMap);
    }

    setTimeout(() => {
        leafletMap.invalidateSize();
    }, 100);
}

function detectImportFormat(file) {
    const name = file.name.toLowerCase();

    if (name.endsWith(".json")) {
        return "json";
    }

    if (name.endsWith(".csv")) {
        return "csv";
    }

    return null;
}

function clearMapLayers() {
    if (!leafletMap) {
        return;
    }

    leafletLayers.forEach(layer => leafletMap.removeLayer(layer));
    leafletLayers = [];
}

function setImportFile(file) {
    selectedImportFile = file;

    if (importFileName) {
        importFileName.textContent = file
            ? `Выбран файл: ${file.name}`
            : "Файл не выбран";
    }
}

async function handleImportEnterprise() {
    if (!selectedImportFile) {
        showMessage(enterpriseMessage, "warning", "Сначала выберите файл для импорта");
        return;
    }

    const format = detectImportFormat(selectedImportFile);

    if (!format) {
        showMessage(enterpriseMessage, "warning", "Поддерживаются только .json и .csv файлы");
        return;
    }

    try {
        clearMessage(enterpriseMessage);

        const result = await importEnterpriseRequest(selectedImportFile, format);

        showMessage(
            enterpriseMessage,
            "success",
            `Импорт завершён. Enterprise ID: ${result.enterprise_id}, машин: ${result.imported_vehicles}, поездок: ${result.imported_trips}, точек: ${result.imported_points}`
        );

        setImportFile(null);

        if (importFileInput) {
            importFileInput.value = "";
        }

        await loadEnterprises();
    } catch (error) {
        showMessage(enterpriseMessage, "danger", error.message);
    }
}

function drawGroupedGeojsonTracks(groupedTracks) {
    initMapIfNeeded();
    clearMapLayers();

    const bounds = [];
    let drawnCount = 0;

    groupedTracks.forEach((trip, index) => {
        const features = trip.track?.features || [];

        const latlngs = features
            .map((feature) => {
                const coords = feature?.geometry?.coordinates;
                if (!coords || coords.length < 2) return null;

                const [lon, lat] = coords;
                if (typeof lat !== "number" || typeof lon !== "number") return null;

                return [lat, lon];
            })
            .filter(Boolean);

        if (latlngs.length < 2) {
            return;
        }

        drawnCount += 1;
        latlngs.forEach((point) => bounds.push(point));

        const polyline = L.polyline(latlngs, {
            color: getTrackColor(index),
            weight: 5,
            opacity: 0.9
        }).addTo(leafletMap);

        polyline.bindPopup(
            `Поездка #${trip.trip_id}<br>${formatDateTime(trip.started_at_enterprise)} — ${formatDateTime(trip.ended_at_enterprise)}`
        );

        leafletLayers.push(polyline);
    });

    setTimeout(() => {
        leafletMap.invalidateSize();

        if (bounds.length > 0) {
            leafletMap.fitBounds(bounds, {
                padding: [30, 30],
                maxZoom: 15
            });
        } else if (drawnCount === 0) {
            leafletMap.setView([29.95, -90.07], 12);
        }
    }, 100);
}

function renderTrackJson(titleText, payload) {
    const container = document.getElementById("trackContainer");
    const output = document.getElementById("trackOutput");
    const title = document.getElementById("trackTitle");

    title.textContent = titleText;
    container.classList.remove("d-none");
    output.textContent = JSON.stringify(payload, null, 2);
}

function setDefaultTripDateRange() {
    const now = new Date();

    const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    document.getElementById("tripDateFrom").value = toDateTimeLocalValue(dayAgo.toISOString());
    document.getElementById("tripDateTo").value = toDateTimeLocalValue(now.toISOString());

    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const exportFrom = document.getElementById("exportDateFrom");
    const exportTo = document.getElementById("exportDateTo");

    if (exportFrom) {
        exportFrom.value = toDateTimeLocalValue(monthAgo.toISOString());
    }

    if (exportTo) {
        exportTo.value = toDateTimeLocalValue(now.toISOString());
    }
}

function getExportDateRange() {
    const dateFromValue = document.getElementById("exportDateFrom").value;
    const dateToValue = document.getElementById("exportDateTo").value;

    const dateFrom = localInputToIso(dateFromValue);
    const dateTo = localInputToIso(dateToValue);

    if (!dateFrom || !dateTo) {
        throw new Error("Укажите диапазон дат для экспорта");
    }

    if (new Date(dateTo) < new Date(dateFrom)) {
        throw new Error("Дата 'до' должна быть больше даты 'от'");
    }

    return {dateFrom, dateTo};
}

async function handleExportEnterpriseFull(format) {
    if (!selectedEnterprise) {
        showMessage(enterpriseMessage, "warning", "Сначала выберите предприятие");
        return;
    }

    try {
        clearMessage(enterpriseMessage);
        const {dateFrom, dateTo} = getExportDateRange();

        await exportEnterpriseFullRequest(
            selectedEnterprise.id,
            dateFrom,
            dateTo,
            format
        );
    } catch (error) {
        showMessage(enterpriseMessage, "danger", error.message);
    }
}

async function handleExportEnterpriseVehicles(format) {
    if (!selectedEnterprise) {
        showMessage(enterpriseMessage, "warning", "Сначала выберите предприятие");
        return;
    }

    try {
        clearMessage(enterpriseMessage);

        await exportEnterpriseVehiclesRequest(
            selectedEnterprise.id,
            format
        );
    } catch (error) {
        showMessage(enterpriseMessage, "danger", error.message);
    }
}

async function handleExportVehicleTrips(format) {
    if (!selectedVehicle) {
        showMessage(vehicleMessage, "warning", "Сначала выберите машину");
        return;
    }

    try {
        clearMessage(vehicleMessage);

        const dateFrom = localInputToIso(document.getElementById("tripDateFrom").value);
        const dateTo = localInputToIso(document.getElementById("tripDateTo").value);

        if (!dateFrom || !dateTo) {
            showMessage(vehicleMessage, "warning", "Укажите диапазон дат");
            return;
        }

        if (new Date(dateTo) < new Date(dateFrom)) {
            showMessage(vehicleMessage, "warning", "Дата 'до' должна быть больше даты 'от'");
            return;
        }

        await exportVehicleTripsRequest(
            selectedVehicle.id,
            dateFrom,
            dateTo,
            format
        );
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function loadVehicleModels() {
    vehicleModels = await getVehicleModelsRequest();
    vehicleModelsMap = new Map(vehicleModels.map(model => [model.id, model]));
    renderVehicleModelOptions(vehicleModels);
}

async function loadEnterprises() {
    clearMessage(enterpriseMessage);
    renderEnterpriseInfo(null);
    reportsCard?.classList.add("d-none");
    document.getElementById("enterpriseList").innerHTML = `
        <li class="list-group-item">Загрузка...</li>
    `;

    try {
        enterprisesState = await getEnterprisesRequest();
        renderEnterprises(
            enterprisesState,
            selectedEnterprise?.id ?? null,
            handleEnterpriseSelect
        );
    } catch (error) {
        document.getElementById("enterpriseList").innerHTML = "";
        showMessage(enterpriseMessage, "danger", error.message);
    }
}

async function loadVehiclesForEnterprise(enterprise) {
    clearMessage(vehicleMessage);

    const enterpriseId = enterprise.id;
    vehicleEnterpriseTitle.textContent = `${enterprise.name} (ID: ${enterprise.id})`;

    selectedEnterpriseVehicles = [];

    document.getElementById("vehicleTableBody").innerHTML = `
        <tr><td colspan="4">Загрузка...</td></tr>
    `;

    try {
        const offset = (vehiclePage - 1) * vehiclePageSize;

        const vehicles = await getVehiclesByEnterpriseRequest(
            enterpriseId,
            vehiclePageSize,
            offset
        );

        if (!selectedEnterprise || selectedEnterprise.id !== enterpriseId) {
            return;
        }

        selectedEnterpriseVehicles = vehicles;

        renderVehiclesTable(
            vehicles,
            vehicleModelsMap,
            startEditVehicle,
            handleDeleteVehicle,
            handleSelectVehicle
        );

        renderVehiclePagination(vehicles, vehiclePage, vehiclePageSize, async (direction) => {
            if (!selectedEnterprise || selectedEnterprise.id !== enterpriseId) {
                return;
            }

            if (direction === "prev" && vehiclePage > 1) {
                vehiclePage -= 1;
                await loadVehiclesForEnterprise(selectedEnterprise);
            }

            if (direction === "next" && vehicles.length === vehiclePageSize) {
                vehiclePage += 1;
                await loadVehiclesForEnterprise(selectedEnterprise);
            }
        });
    } catch (error) {
        if (!selectedEnterprise || selectedEnterprise.id !== enterpriseId) {
            return;
        }

        document.getElementById("vehicleTableBody").innerHTML = `
            <tr><td colspan="4" class="text-muted">Не удалось загрузить машины</td></tr>
        `;
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function handleEnterpriseSelect(enterprise) {
    selectedEnterprise = enterprise;
    selectedVehicle = null;
    selectedVehicleTrips = [];
    selectedVehicleGroupedTracks = [];
    selectedEnterpriseVehicles = [];
    vehiclePage = 1;

    renderEnterpriseInfo(enterprise);
    renderEnterprises(
        enterprisesState,
        selectedEnterprise.id,
        handleEnterpriseSelect
    );

    vehicleCard.classList.remove("d-none");
    reportsCard?.classList.remove("d-none");
    hideVehicleForm();
    resetVehicleForm();
    renderSelectedVehicleInfo(null);
    renderTripList([], () => {
    });
    setDefaultTripDateRange();
    setDefaultReportDateRange();
    document.getElementById("reportVehicleId").value = "";
    await loadReports();

    document.getElementById("vehicleTableBody").innerHTML = `
        <tr><td colspan="4">Загрузка...</td></tr>
    `;

    initMapIfNeeded();
    clearMapLayers();

    await loadVehiclesForEnterprise(enterprise);
}

async function handleSelectVehicle(vehicle) {
    selectedVehicle = vehicle;
    const modelName = vehicleModelsMap.get(vehicle.model_id)?.name || `Модель ${vehicle.model_id}`;

    renderSelectedVehicleInfo(vehicle, modelName);
    document.getElementById("reportVehicleId").value = vehicle.id;
    document.getElementById("reportName").value = `Отчёт по машине ${vehicle.vehicle_number}`;
    setDefaultTripDateRange();
    await loadTripsForSelectedVehicle();
}

async function loadTripsForSelectedVehicle() {
    if (!selectedVehicle) {
        showMessage(vehicleMessage, "warning", "Сначала выберите машину");
        return;
    }

    try {
        clearMessage(vehicleMessage);

        const dateFromValue = document.getElementById("tripDateFrom").value;
        const dateToValue = document.getElementById("tripDateTo").value;

        const dateFrom = localInputToIso(dateFromValue);
        const dateTo = localInputToIso(dateToValue);

        if (!dateFrom || !dateTo) {
            showMessage(vehicleMessage, "warning", "Укажите диапазон дат");
            return;
        }

        const trips = await getVehicleTripsRequest(selectedVehicle.id, dateFrom, dateTo);
        selectedVehicleTrips = trips;

        renderTripList(trips, async (trip) => {
            await showSingleTripOnMap(trip);
        });
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function showSingleTripOnMap(trip) {
    if (!selectedVehicle) return;

    try {
        clearMessage(vehicleMessage);

        const grouped = await getVehicleTrackByTripsRequest(
            selectedVehicle.id,
            trip.started_at_utc,
            trip.ended_at_utc,
            "geojson"
        );

        renderTrackJson(
            `Трек поездки #${trip.id} (geojson)`,
            grouped
        );

        drawGroupedGeojsonTracks(grouped);
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function showAllTripsOnMap() {
    if (!selectedVehicle) {
        showMessage(vehicleMessage, "warning", "Сначала выберите машину");
        return;
    }

    try {
        clearMessage(vehicleMessage);

        const dateFromValue = document.getElementById("tripDateFrom").value;
        const dateToValue = document.getElementById("tripDateTo").value;

        const dateFrom = localInputToIso(dateFromValue);
        const dateTo = localInputToIso(dateToValue);

        if (!dateFrom || !dateTo) {
            showMessage(vehicleMessage, "warning", "Укажите диапазон дат");
            return;
        }

        const grouped = await getVehicleTrackByTripsRequest(
            selectedVehicle.id,
            dateFrom,
            dateTo,
            "geojson"
        );

        selectedVehicleGroupedTracks = grouped;

        renderTrackJson(
            `Все треки машины ${selectedVehicle.vehicle_number} за диапазон (geojson)`,
            grouped
        );

        drawGroupedGeojsonTracks(grouped);
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}

function startCreateVehicle() {
    if (!selectedEnterprise) {
        showMessage(vehicleMessage, "warning", "Сначала выберите предприятие");
        return;
    }

    clearMessage(vehicleMessage);
    resetVehicleForm();
    document.getElementById("purchasedAt").value = toDateTimeLocalValue(new Date().toISOString());
    renderVehicleModelOptions(vehicleModels);
    showVehicleForm();
}

function startEditVehicle(vehicle) {
    clearMessage(vehicleMessage);
    resetVehicleForm();
    renderVehicleModelOptions(vehicleModels, vehicle.model_id);
    fillVehicleForm(vehicle);
    showVehicleForm();
}

async function handleDeleteVehicle(vehicle) {
    const confirmed = window.confirm(
        `Удалить машину ${vehicle.vehicle_number} (ID: ${vehicle.id})?`
    );

    if (!confirmed) {
        return;
    }

    try {
        await deleteVehicleRequest(vehicle.id);
        showMessage(vehicleMessage, "success", "Машина удалена");

        if (selectedEnterpriseVehicles.length === 1 && vehiclePage > 1) {
            vehiclePage -= 1;
        }

        await refreshSelectedEnterpriseData();
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function refreshSelectedEnterpriseData() {
    if (!selectedEnterprise) {
        return;
    }

    const enterpriseId = selectedEnterprise.id;

    const updatedEnterprises = await getEnterprisesRequest();
    enterprisesState = updatedEnterprises;

    const updatedEnterprise = updatedEnterprises.find(
        e => e.id === enterpriseId
    );

    if (!updatedEnterprise) {
        selectedEnterprise = null;
        selectedVehicle = null;
        selectedEnterpriseVehicles = [];
        vehicleCard.classList.add("d-none");
        renderEnterpriseInfo(null);
        renderEnterprises(enterprisesState, null, handleEnterpriseSelect);
        return;
    }

    selectedEnterprise = updatedEnterprise;

    renderEnterpriseInfo(updatedEnterprise);
    renderEnterprises(
        enterprisesState,
        selectedEnterprise.id,
        handleEnterpriseSelect
    );

    await loadVehiclesForEnterprise(updatedEnterprise);

    if (selectedVehicle) {
        const refreshedVehicle = selectedEnterpriseVehicles.find(v => v.id === selectedVehicle.id);

        if (refreshedVehicle) {
            selectedVehicle = refreshedVehicle;
            const modelName = vehicleModelsMap.get(refreshedVehicle.model_id)?.name || `Модель ${refreshedVehicle.model_id}`;
            renderSelectedVehicleInfo(refreshedVehicle, modelName);
        } else {
            selectedVehicle = null;
            renderSelectedVehicleInfo(null);
            renderTripList([], () => {
            });
            clearMapLayers();
        }
    }
}

function setDefaultReportDateRange() {
    const now = new Date();
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const reportDateFrom = document.getElementById("reportDateFrom");
    const reportDateTo = document.getElementById("reportDateTo");

    if (reportDateFrom) {
        reportDateFrom.value = toDateTimeLocalValue(monthAgo.toISOString());
    }

    if (reportDateTo) {
        reportDateTo.value = toDateTimeLocalValue(now.toISOString());
    }
}

async function loadReports() {
    try {
        reportsState = await getReportsRequest();
        renderReportsList(
            reportsState,
            selectedEnterprise?.id ?? null,
            handleOpenReport,
            handleRebuildReport,
            handleDeleteReport
        );
    } catch (error) {
        showMessage(reportMessage, "danger", error.message);
    }
}

async function handleCreateReport(event) {
    event.preventDefault();

    if (!selectedEnterprise) {
        showMessage(reportMessage, "warning", "Сначала выберите предприятие");
        return;
    }

    const dateFrom = localInputToIso(document.getElementById("reportDateFrom").value);
    const dateTo = localInputToIso(document.getElementById("reportDateTo").value);
    const vehicleId = Number(document.getElementById("reportVehicleId").value);

    if (!dateFrom || !dateTo) {
        showMessage(reportMessage, "warning", "Укажите диапазон дат");
        return;
    }

    if (new Date(dateTo) < new Date(dateFrom)) {
        showMessage(reportMessage, "warning", "Дата 'до' должна быть больше даты 'от'");
        return;
    }

    try {
        clearMessage(reportMessage);

        const report = await createReportRequest({
            name: document.getElementById("reportName").value.trim(),
            report_type: document.getElementById("reportType").value,
            period: document.getElementById("reportPeriod").value,
            date_from: dateFrom,
            date_to: dateTo,
            enterprise_id: selectedEnterprise.id,
            vehicle_id: vehicleId
        });

        showMessage(reportMessage, "success", `Отчёт создан: #${report.id}`);
        renderReportResult(report);
        await loadReports();
    } catch (error) {
        showMessage(reportMessage, "danger", error.message);
    }
}

async function handleOpenReport(report) {
    try {
        clearMessage(reportMessage);

        selectedReport = report;

        const fullReport = await getReportRequest(report.id);
        renderReportResult(fullReport);
    } catch (error) {
        showMessage(reportMessage, "danger", error.message);
    }
}

async function handleRebuildReport(report) {
    try {
        clearMessage(reportMessage);
        const rebuilt = await rebuildReportRequest(report.id);
        showMessage(reportMessage, "success", `Отчёт #${rebuilt.id} пересчитан`);
        renderReportResult(rebuilt);
        await loadReports();
    } catch (error) {
        showMessage(reportMessage, "danger", error.message);
    }
}

async function handleDeleteReport(report) {
    const confirmed = window.confirm(`Удалить отчёт #${report.id} "${report.name}"?`);
    if (!confirmed) return;

    try {
        clearMessage(reportMessage);
        await deleteReportRequest(report.id);
        showMessage(reportMessage, "success", "Отчёт удалён");
        document.getElementById("reportResultCard")?.classList.add("d-none");
        await loadReports();
    } catch (error) {
        showMessage(reportMessage, "danger", error.message);
    }
}

loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMessage(messageBox);

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
        await loginRequest(username, password);

        showMessage(messageBox, "success", "Успешный вход");

        loginCard.classList.add("d-none");
        enterpriseCard.classList.remove("d-none");

        await loadVehicleModels();
        await loadEnterprises();
        setDefaultReportDateRange();
        await loadReports();
    } catch (error) {
        showMessage(messageBox, "danger", error.message);
    }
});

reloadBtn.addEventListener("click", async () => {
    clearMessage(enterpriseMessage);

    try {
        enterprisesState = await getEnterprisesRequest();

        renderEnterprises(
            enterprisesState,
            selectedEnterprise?.id ?? null,
            handleEnterpriseSelect
        );

        if (selectedEnterprise) {
            const selectedEnterpriseId = selectedEnterprise.id;
            const updatedEnterprise = enterprisesState.find(
                e => e.id === selectedEnterpriseId
            );

            if (updatedEnterprise) {
                selectedEnterprise = updatedEnterprise;
                renderEnterpriseInfo(updatedEnterprise);
                await loadVehiclesForEnterprise(updatedEnterprise);
            } else {
                selectedEnterprise = null;
                selectedVehicle = null;
                selectedEnterpriseVehicles = [];
                vehicleCard.classList.add("d-none");
                renderEnterpriseInfo(null);
            }
        }
    } catch (error) {
        showMessage(enterpriseMessage, "danger", error.message);
    }
});

showCreateFormBtn.addEventListener("click", startCreateVehicle);

cancelVehicleFormBtn.addEventListener("click", () => {
    hideVehicleForm();
    resetVehicleForm();
});

loadTripsBtn.addEventListener("click", async () => {
    await loadTripsForSelectedVehicle();
});

showAllTripsMapBtn.addEventListener("click", async () => {
    await showAllTripsOnMap();
});

exportFullJsonBtn?.addEventListener("click", async () => {
    await handleExportEnterpriseFull("json");
});

exportFullCsvBtn?.addEventListener("click", async () => {
    await handleExportEnterpriseFull("csv");
});

exportVehiclesJsonBtn?.addEventListener("click", async () => {
    await handleExportEnterpriseVehicles("json");
});

exportVehiclesCsvBtn?.addEventListener("click", async () => {
    await handleExportEnterpriseVehicles("csv");
});

exportVehicleTripsJsonBtn?.addEventListener("click", async () => {
    await handleExportVehicleTrips("json");
});

exportVehicleTripsCsvBtn?.addEventListener("click", async () => {
    await handleExportVehicleTrips("csv");
});

vehicleForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMessage(vehicleMessage);

    if (!selectedEnterprise) {
        showMessage(vehicleMessage, "warning", "Сначала выберите предприятие");
        return;
    }

    const vehicleId = document.getElementById("vehicleId").value.trim();
    const colorValue = document.getElementById("color").value.trim();
    const purchasedAtValue = document.getElementById("purchasedAt").value;

    const basePayload = {
        price: Number(document.getElementById("price").value),
        mileage: Number(document.getElementById("mileage").value),
        vehicle_number: document.getElementById("vehicleNumber").value.trim(),
        owners_count: Number(document.getElementById("ownersCount").value),
        accident_number: Number(document.getElementById("accidentNumber").value),
        manufacture_year: Number(document.getElementById("manufactureYear").value),
        model_id: Number(document.getElementById("modelId").value),
        enterprise_id: Number(selectedEnterprise.id),
        color: colorValue
    };

    if (purchasedAtValue) {
        basePayload.purchased_at = new Date(purchasedAtValue).toISOString();
    }

    try {
        if (vehicleId) {
            await updateVehicleRequest(Number(vehicleId), {...basePayload});
            showMessage(vehicleMessage, "success", "Машина обновлена");
        } else {
            await createVehicleRequest(basePayload);
            showMessage(vehicleMessage, "success", "Машина создана");
        }

        hideVehicleForm();
        resetVehicleForm();
        await refreshSelectedEnterpriseData();
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
});

importDropZone?.addEventListener("click", () => {
    importFileInput?.click();
});

importFileInput?.addEventListener("change", () => {
    const file = importFileInput.files?.[0];
    if (file) {
        setImportFile(file);
    }
});

importDropZone?.addEventListener("dragover", (event) => {
    event.preventDefault();
    importDropZone.classList.add("border-primary");
});

importDropZone?.addEventListener("dragleave", () => {
    importDropZone.classList.remove("border-primary");
});

importDropZone?.addEventListener("drop", (event) => {
    event.preventDefault();
    importDropZone.classList.remove("border-primary");

    const file = event.dataTransfer.files?.[0];
    if (file) {
        setImportFile(file);
    }
});

importBtn?.addEventListener("click", async () => {
    await handleImportEnterprise();
});

reportForm?.addEventListener("submit", handleCreateReport);

reloadReportsBtn?.addEventListener("click", async () => {
    clearMessage(reportMessage);
    await loadReports();
});


exportReportJsonBtn?.addEventListener("click", async () => {
    if (!selectedReport) {
        showMessage(reportMessage, "warning", "Сначала выберите отчёт");
        return;
    }

    await exportReportRequest(selectedReport.id, "json");
});

exportReportCsvBtn?.addEventListener("click", async () => {
    if (!selectedReport) {
        showMessage(reportMessage, "warning", "Сначала выберите отчёт");
        return;
    }

    await exportReportRequest(selectedReport.id, "csv");
});