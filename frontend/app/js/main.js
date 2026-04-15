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

let enterprisesState = [];
let selectedEnterprise = null;
let selectedEnterpriseVehicles = [];
let vehicleModels = [];
let vehicleModelsMap = new Map();

let vehiclePage = 1;
const vehiclePageSize = 10;

async function loadVehicleModels() {
    vehicleModels = await getVehicleModelsRequest();
    vehicleModelsMap = new Map(vehicleModels.map(model => [model.id, model]));
    renderVehicleModelOptions(vehicleModels);
}

async function handleShowTrack(vehicle) {
    try {
        clearMessage(vehicleMessage);

        const now = new Date();
        const dateTo = now.toISOString();

        const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        const dateFrom = dayAgo.toISOString();

        const format = document.getElementById("trackFormat").value;

        const track = await getVehicleTrackRequest(
            vehicle.id,
            dateFrom,
            dateTo,
            format
        );

        const container = document.getElementById("trackContainer");
        const output = document.getElementById("trackOutput");
        const title = document.getElementById("trackTitle");

        title.textContent = `Трек машины ${vehicle.vehicle_number} за последние 24 часа (${format})`;
        container.classList.remove("d-none");
        output.textContent = JSON.stringify(track, null, 2);
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function loadEnterprises() {
    clearMessage(enterpriseMessage);
    renderEnterpriseInfo(null);
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
    vehicleEnterpriseTitle.textContent = `${enterprise.name} (ID: ${enterprise.id})`;
    document.getElementById("vehicleTableBody").innerHTML = `
        <tr><td colspan="8">Загрузка...</td></tr>
    `;

    try {
        const offset = (vehiclePage - 1) * vehiclePageSize;

        const vehicles = await getVehiclesByEnterpriseRequest(
            enterprise.id,
            vehiclePageSize,
            offset
        );

        selectedEnterpriseVehicles = vehicles;

        renderVehiclesTable(
            vehicles,
            vehicleModelsMap,
            startEditVehicle,
            handleDeleteVehicle,
            handleShowTrack
        );

        renderVehiclePagination(vehicles, vehiclePage, vehiclePageSize, async (direction) => {
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
        showMessage(vehicleMessage, "danger", error.message);
    }
}

async function handleEnterpriseSelect(enterprise) {
    selectedEnterprise = enterprise;
    vehiclePage = 1;

    renderEnterpriseInfo(enterprise);
    renderEnterprises(
        enterprisesState,
        selectedEnterprise.id,
        handleEnterpriseSelect
    );

    vehicleCard.classList.remove("d-none");
    hideVehicleForm();
    resetVehicleForm();

    await loadVehiclesForEnterprise(enterprise);
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

    const updatedEnterprises = await getEnterprisesRequest();
    enterprisesState = updatedEnterprises;

    const updatedEnterprise = updatedEnterprises.find(
        e => e.id === selectedEnterprise.id
    );

    if (!updatedEnterprise) {
        selectedEnterprise = null;
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
            const updatedEnterprise = enterprisesState.find(
                e => e.id === selectedEnterprise.id
            );

            if (updatedEnterprise) {
                selectedEnterprise = updatedEnterprise;
                renderEnterpriseInfo(updatedEnterprise);
                await loadVehiclesForEnterprise(updatedEnterprise);
            } else {
                selectedEnterprise = null;
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
            const updatePayload = {
                ...basePayload
            };

            if (colorValue) {
                updatePayload.color = colorValue;
            }

            await updateVehicleRequest(Number(vehicleId), updatePayload);
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
