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
    const buttons = document.getElementById("enterpriseExportButtons");

    if (!enterprise) {
        container.innerHTML = `<span class="text-muted">Сначала выберите предприятие слева</span>`;
        buttons?.classList.add("d-none");
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

    buttons?.classList.remove("d-none");
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

function localInputToIso(value) {
    if (!value) return "";
    return new Date(value).toISOString();
}

function reportTypeLabel(type) {
    const labels = {
        vehicle_mileage: "Пробег автомобиля",
        vehicle_activity: "Активность автомобиля",
        vehicle_geography: "География поездок"
    };

    return labels[type] || type;
}

function reportPeriodLabel(period) {
    const labels = {
        day: "день",
        month: "месяц",
        year: "год"
    };

    return labels[period] || period;
}

function renderReportsList(reports, selectedEnterpriseId, onOpen, onRebuild, onDelete) {
    const container = document.getElementById("reportList");
    if (!container) return;

    const filtered = selectedEnterpriseId
        ? reports.filter(report => report.enterprise_id === selectedEnterpriseId)
        : reports;

    container.innerHTML = "";

    if (!filtered || filtered.length === 0) {
        container.innerHTML = `
            <div class="list-group-item text-muted">
                Отчётов пока нет
            </div>
        `;
        return;
    }

    filtered.forEach((report) => {
        const item = document.createElement("div");
        item.className = "list-group-item";

        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-start gap-2 flex-wrap">
                <div>
                    <div class="fw-semibold">${report.name}</div>
                    <div class="small text-muted">
                        #${report.id} · ${reportTypeLabel(report.report_type)} · период: ${reportPeriodLabel(report.period)}
                    </div>
                    <div class="small text-muted">
                        Машина: ${report.vehicle_id ?? "—"} · ${formatDateTime(report.date_from)} — ${formatDateTime(report.date_to)}
                    </div>
                </div>
                <div class="d-flex gap-2 flex-wrap">
                    <button class="btn btn-sm btn-outline-primary open-report-btn">Открыть</button>
                    <button class="btn btn-sm btn-outline-secondary rebuild-report-btn">Пересчитать</button>
                    <button class="btn btn-sm btn-danger delete-report-btn">Удалить</button>
                </div>
            </div>
        `;

        item.querySelector(".open-report-btn").addEventListener("click", () => onOpen(report));
        item.querySelector(".rebuild-report-btn").addEventListener("click", () => onRebuild(report));
        item.querySelector(".delete-report-btn").addEventListener("click", () => onDelete(report));

        container.appendChild(item);
    });
}

function renderReportResult(report) {
    const card = document.getElementById("reportResultCard");
    const output = document.getElementById("reportResultOutput");
    const exportJsonBtn = document.getElementById("exportReportJsonBtn");
    const exportCsvBtn = document.getElementById("exportReportCsvBtn");

    if (!card || !output) return;

    selectedReport = report;
    card.classList.remove("d-none");

    const rows = report.result_json || [];

    const resultRows = rows.length
        ? rows.map((row) => {
            const extra = row.extra || {};
            const extraText = Object.entries(extra)
                .map(([key, value]) => `${key}: ${value}`)
                .join(", ");

            return `
                <tr>
                    <td>${row.time ?? "—"}</td>
                    <td>${row.value ?? "—"}</td>
                    <td>${extraText || "—"}</td>
                </tr>
            `;
        }).join("")
        : `
            <tr>
                <td colspan="3" class="text-muted">Нет данных за выбранный период</td>
            </tr>
        `;

    output.innerHTML = `
        <div class="mb-3">
            <h6 class="mb-2">${report.name}</h6>
            <div class="small"><strong>ID:</strong> ${report.id}</div>
            <div class="small"><strong>Тип:</strong> ${reportTypeLabel(report.report_type)}</div>
            <div class="small"><strong>Период:</strong> ${reportPeriodLabel(report.period)}</div>
            <div class="small"><strong>Enterprise ID:</strong> ${report.enterprise_id}</div>
            <div class="small"><strong>Vehicle ID:</strong> ${report.vehicle_id ?? "—"}</div>
            <div class="small"><strong>Дата от:</strong> ${formatDateTime(report.date_from)}</div>
            <div class="small"><strong>Дата до:</strong> ${formatDateTime(report.date_to)}</div>
            <div class="small"><strong>Создан:</strong> ${formatDateTime(report.created_at)}</div>
        </div>

        <div class="table-responsive">
            <table class="table table-sm table-striped align-middle mb-0">
                <thead>
                    <tr>
                        <th>Период / зона</th>
                        <th>Значение</th>
                        <th>Доп. данные</th>
                    </tr>
                </thead>
                <tbody>
                    ${resultRows}
                </tbody>
            </table>
        </div>
    `;

    if (exportJsonBtn) exportJsonBtn.disabled = false;
    if (exportCsvBtn) exportCsvBtn.disabled = false;
}