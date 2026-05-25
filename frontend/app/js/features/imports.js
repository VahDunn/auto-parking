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
async function handleImportGpx() {
    if (!selectedVehicle) {
        showMessage(vehicleMessage, "warning", "Сначала выберите машину");
        return;
    }

    const file = gpxFileInput?.files?.[0];

    if (!file) {
        showMessage(vehicleMessage, "warning", "Сначала выберите GPX-файл");
        return;
    }

    try {
        clearMessage(vehicleMessage);

        const trip = await importVehicleTripGpxRequest(selectedVehicle.id, file);

        showMessage(
            vehicleMessage,
            "success",
            `GPX импортирован. Создана поездка #${trip.id}`
        );

        gpxFileInput.value = "";

        await loadTripsForSelectedVehicle();
        await showAllTripsOnMap();
    } catch (error) {
        showMessage(vehicleMessage, "danger", error.message);
    }
}
