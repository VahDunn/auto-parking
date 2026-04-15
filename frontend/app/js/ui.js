function showMessage(container, type, text) {
    container.innerHTML = `
        <div class="alert alert-${type}" role="alert">
            ${text}
        </div>
    `;
}

function clearMessage(container) {
    container.innerHTML = "";
}

function renderEnterpriseInfo(enterprise) {
    const container = document.getElementById("selectedEnterpriseInfo");

    if (!enterprise) {
        container.innerHTML = `<span class="text-muted">Сначала выберите предприятие слева</span>`;
        return;
    }

    container.innerHTML = `
        <div><strong>ID:</strong> ${enterprise.id}</div>
        <div><strong>Название:</strong> ${enterprise.name}</div>
        <div><strong>Населённый пункт:</strong> ${enterprise.settlement}</div>
        <div><strong>Таймзона:</strong> ${enterprise.timezone || "UTC"}</div>
        <div><strong>Менеджеры:</strong> ${enterprise.managers?.join(", ") || "—"}</div>
        <div><strong>Машины:</strong> ${enterprise.vehicles?.length || 0}</div>
    `;
}

function renderEnterprises(items, selectedEnterpriseId, onSelect) {
    const enterpriseList = document.getElementById("enterpriseList");
    enterpriseList.innerHTML = "";

    if (!items || items.length === 0) {
        enterpriseList.innerHTML = `
            <li class="list-group-item text-muted">
                Нет доступных предприятий
            </li>
        `;
        return;
    }

    items.forEach((enterprise) => {
        const li = document.createElement("li");
        li.className = "list-group-item list-group-item-action";

        if (enterprise.id === selectedEnterpriseId) {
            li.classList.add("selected-enterprise");
        }

        li.innerHTML = `
            <div class="fw-semibold">${enterprise.name ?? "Без названия"}</div>
            <div class="text-muted small">ID: ${enterprise.id}</div>
            <div class="text-muted small">Город: ${enterprise.settlement ?? "—"}</div>
        `;

        li.addEventListener("click", () => onSelect(enterprise));
        enterpriseList.appendChild(li);
    });
}

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

function renderVehiclesTable(vehicles, modelsMap, onEdit, onDelete, onTrack) {
    const tbody = document.getElementById("vehicleTableBody");
    tbody.innerHTML = "";

    if (!vehicles || vehicles.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-muted">У этого предприятия нет машин</td>
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
            <td>${vehicle.manufacture_year}</td>
            <td>${vehicle.mileage}</td>
            <td>${vehicle.price}</td>
            <td>${formatDateTime(vehicle.purchased_at_enterprise)}</td>
           <td>
                <div class="d-flex gap-2">
                    <button class="btn btn-sm btn-primary edit-btn">Редактировать</button>
                    <button class="btn btn-sm btn-danger delete-btn">Удалить</button>
                    <button class="btn btn-sm btn-outline-secondary track-btn">Трек</button>
                </div>
           </td>
        `;

        tr.querySelector(".edit-btn").addEventListener("click", () => onEdit(vehicle));
        tr.querySelector(".delete-btn").addEventListener("click", () => onDelete(vehicle));
        tr.querySelector(".track-btn").addEventListener("click", () => onTrack(vehicle));

        tbody.appendChild(tr);
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

function formatDateTime(value) {
    if (!value) return "—";
    return new Date(value).toLocaleString("ru-RU");
}

function toDateTimeLocalValue(value) {
    if (!value) return "";

    const d = new Date(value);
    const pad = (n) => String(n).padStart(2, "0");

    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
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