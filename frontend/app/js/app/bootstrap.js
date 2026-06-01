loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMessage(messageBox);

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    try {
        const loginData = await loginRequest(username, password);
        accessToken = loginData.access_token;

        showMessage(messageBox, "success", "Успешный вход");

        loginCard.classList.add("d-none");
        enterpriseCard.classList.remove("d-none");
        notificationCard.classList.remove("d-none");

        await loadVehicleModels();
        await loadEnterprises();
        setDefaultReportDateRange();
        await loadReports();
        await loadNotifications();
        startNotificationsRealtime();
    } catch (error) {
        showMessage(messageBox, "danger", error.message);
    }
});

reloadNotificationsBtn.addEventListener("click", async () => {
    await loadNotifications();
});

markAllNotificationsReadBtn.addEventListener("click", async () => {
    clearMessage(notificationMessage);

    try {
        await markAllNotificationsReadRequest();
        await loadNotifications();
    } catch (error) {
        showMessage(notificationMessage, "danger", error.message);
    }
});

notificationList.addEventListener("click", async (event) => {
    const item = event.target.closest("[data-notification-id]");
    if (!item) {
        return;
    }

    await handleNotificationClick(Number(item.dataset.notificationId));
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

    await exportReportRequest(selectedReport, "json");
});

exportReportCsvBtn?.addEventListener("click", async () => {
    if (!selectedReport) {
        showMessage(reportMessage, "warning", "Сначала выберите отчёт");
        return;
    }

    await exportReportRequest(selectedReport, "csv");
});

exportReportPdfBtn?.addEventListener("click", async () => {
    if (!selectedReport) {
        showMessage(reportMessage, "warning", "Сначала выберите отчёт");
        return;
    }

    await exportReportRequest(selectedReport, "pdf");
});

importGpxBtn?.addEventListener("click", async () => {
    await handleImportGpx();
});
