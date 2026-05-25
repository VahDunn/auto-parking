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
