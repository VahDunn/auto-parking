async function loadVehicleModels() {
    vehicleModels = await getVehicleModelsRequest();
    vehicleModelsMap = new Map(vehicleModels.map(model => [model.id, model]));
    renderVehicleModelOptions(vehicleModels);
}

function setDefaultTripDateRange() {
    const now = new Date();
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const tripDateFrom = document.getElementById("tripDateFrom");
    const tripDateTo = document.getElementById("tripDateTo");

    if (tripDateFrom) {
        tripDateFrom.value = toDateTimeLocalValue(monthAgo.toISOString());
    }

    if (tripDateTo) {
        tripDateTo.value = toDateTimeLocalValue(now.toISOString());
    }
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
    document.getElementById("vehicleTableBody").innerHTML = `
        <tr><td colspan="4">Загрузка...</td></tr>
    `;

    await loadVehiclesForEnterprise(enterprise);
    await loadReports();

    initMapIfNeeded();
    clearMapLayers();
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
