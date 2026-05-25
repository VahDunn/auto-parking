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