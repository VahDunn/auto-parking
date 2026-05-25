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
