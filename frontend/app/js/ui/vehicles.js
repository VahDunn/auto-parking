function renderVehicleModelOptions(models, selectedId = null) {
    const select = document.getElementById("modelId");
    select.innerHTML = `<option value="">Выберите модель</option>`;

    models.forEach((model) => {
        const option = document.createElement("option");
        option.value = model.id;
        option.textContent = `${model.id} — ${model.name}`;
        if (selectedId && Number(selectedId) === model.id) {
            option.selected = true;
        }
        select.appendChild(option);
    });
}

function renderVehiclesTable(vehicles, modelsMap, onEdit, onDelete, onSelectVehicle) {
    const tbody = document.getElementById("vehicleTableBody");
    tbody.innerHTML = "";

    if (!vehicles || vehicles.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-muted">У этого предприятия нет машин</td>
            </tr>
        `;
        return;
    }

    vehicles.forEach((vehicle) => {
        const tr = document.createElement("tr");
        const modelName = modelsMap.get(vehicle.model_id)?.name || `Модель ${vehicle.model_id}`;

        tr.innerHTML = `
            <td>${vehicle.id}</td>
            <td>${vehicle.vehicle_number}</td>
            <td>${modelName}</td>
            <td>
                <div class="d-flex gap-2 flex-wrap">
                    <button class="btn btn-sm btn-outline-primary select-btn">Выбрать</button>
                    <button class="btn btn-sm btn-primary edit-btn">Редактировать</button>
                    <button class="btn btn-sm btn-danger delete-btn">Удалить</button>
                </div>
            </td>
        `;

        tr.querySelector(".select-btn").addEventListener("click", () => onSelectVehicle(vehicle));
        tr.querySelector(".edit-btn").addEventListener("click", () => onEdit(vehicle));
        tr.querySelector(".delete-btn").addEventListener("click", () => onDelete(vehicle));
        tbody.appendChild(tr);
    });
}

function renderSelectedVehicleInfo(vehicle, modelName = "—") {
    const container = document.getElementById("selectedVehicleInfo");

    if (!vehicle) {
        container.innerHTML = `<span class="text-muted">Сначала выберите машину в таблице</span>`;
        return;
    }

    container.innerHTML = `
        <div><strong>ID:</strong> ${vehicle.id}</div>
        <div><strong>Госномер:</strong> ${vehicle.vehicle_number ?? "—"}</div>
        <div><strong>Модель:</strong> ${modelName}</div>
        <div><strong>Год выпуска:</strong> ${vehicle.manufacture_year ?? "—"}</div>
        <div><strong>Пробег:</strong> ${vehicle.mileage ?? "—"}</div>
        <div><strong>Цена:</strong> ${vehicle.price ?? "—"}</div>
        <div><strong>Цвет:</strong> ${vehicle.color ?? "—"}</div>
        <div><strong>Дата покупки:</strong> ${formatDateTime(vehicle.purchased_at_enterprise)}</div>
        <div><strong>Enterprise ID:</strong> ${vehicle.enterprise_id ?? "—"}</div>
    `;
}

function renderTripList(trips, onShowTripMap) {
    const container = document.getElementById("tripList");
    container.innerHTML = "";

    if (!trips || trips.length === 0) {
        container.innerHTML = `
            <div class="list-group-item text-muted">
                Поездок за выбранный диапазон нет
            </div>
        `;
        return;
    }

    trips.forEach((trip) => {
        const item = document.createElement("div");
        item.className = "list-group-item";

        const startAddr = trip.start_point?.address || "—";
        const endAddr = trip.end_point?.address || "—";

        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
                <div>
                    <div class="fw-semibold">Поездка #${trip.id}</div>
                    <div class="small text-muted">
                        ${formatDateTime(trip.started_at_enterprise)} — ${formatDateTime(trip.ended_at_enterprise)}
                    </div>
                    <div class="small mt-2"><strong>Начало:</strong> ${startAddr}</div>
                    <div class="small"><strong>Конец:</strong> ${endAddr}</div>
                </div>
                <div>
                    <button class="btn btn-sm btn-outline-primary show-trip-map-btn">
                        Показать на карте
                    </button>
                </div>
            </div>
        `;

        item.querySelector(".show-trip-map-btn").addEventListener("click", () => onShowTripMap(trip));
        container.appendChild(item);
    });
}

function resetVehicleForm() {
    document.getElementById("vehicleForm").reset();
    document.getElementById("vehicleId").value = "";
    document.getElementById("vehicleFormTitle").textContent = "Добавление машины";
}

function fillVehicleForm(vehicle) {
    document.getElementById("vehicleId").value = vehicle.id ?? "";
    document.getElementById("price").value = vehicle.price ?? "";
    document.getElementById("mileage").value = vehicle.mileage ?? "";
    document.getElementById("vehicleNumber").value = vehicle.vehicle_number ?? "";
    document.getElementById("ownersCount").value = vehicle.owners_count ?? "";
    document.getElementById("accidentNumber").value = vehicle.accident_number ?? "";
    document.getElementById("manufactureYear").value = vehicle.manufacture_year ?? "";
    document.getElementById("modelId").value = vehicle.model_id ?? "";
    document.getElementById("color").value = vehicle.color ?? "";
    document.getElementById("purchasedAt").value = toDateTimeLocalValue(
        vehicle.purchased_at_enterprise || vehicle.purchased_at_utc
    );
    document.getElementById("vehicleFormTitle").textContent = "Редактирование машины";
}

function showVehicleForm() {
    document.getElementById("vehicleFormCard").classList.remove("d-none");
}

function hideVehicleForm() {
    document.getElementById("vehicleFormCard").classList.add("d-none");
}
function renderVehiclePagination(vehicles, currentPage, pageSize, onPageChange) {
    const container = document.getElementById("vehiclePagination");
    if (!container) return;

    const hasPrev = currentPage > 1;
    const hasNext = vehicles.length === pageSize;

    container.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mt-3">
            <button class="btn btn-outline-secondary btn-sm" id="vehiclePrevBtn" ${hasPrev ? "" : "disabled"}>
                Назад
            </button>
            <span class="text-muted small">Страница ${currentPage}</span>
            <button class="btn btn-outline-secondary btn-sm" id="vehicleNextBtn" ${hasNext ? "" : "disabled"}>
                Вперёд
            </button>
        </div>
    `;

    document.getElementById("vehiclePrevBtn")?.addEventListener("click", async () => {
        await onPageChange("prev");
    });

    document.getElementById("vehicleNextBtn")?.addEventListener("click", async () => {
        await onPageChange("next");
    });
}
