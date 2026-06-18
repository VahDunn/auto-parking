async function loadNotifications() {
    clearMessage(notificationMessage);

    try {
        notificationsState = await getNotificationsRequest(true);
        renderNotifications(notificationsState);
        await refreshUnreadNotificationsCount();
    } catch (error) {
        showMessage(notificationMessage, "danger", error.message);
    }
}

async function refreshUnreadNotificationsCount() {
    const data = await getUnreadNotificationsCountRequest();
    renderNotificationUnreadCount(data.unread_count);
}

function startNotificationsRealtime() {
    if (!accessToken || notificationSocket) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    notificationSocket = new WebSocket(`${protocol}://${window.location.host}/api/notifications/ws`);

    notificationSocket.addEventListener("open", () => {
        setNotificationStatus("Realtime подключен", "success");
    });

    notificationSocket.addEventListener("message", async (event) => {
        const payload = JSON.parse(event.data);
        if (payload.event === "connected") {
            return;
        }

        if (payload.event === "notification.created") {
            upsertNotification(payload.notification);
            renderNotifications(notificationsState);
            await refreshUnreadNotificationsCount();
        }
    });

    notificationSocket.addEventListener("close", () => {
        notificationSocket = null;
        setNotificationStatus("Realtime отключен", "secondary");
    });

    notificationSocket.addEventListener("error", () => {
        setNotificationStatus("Ошибка realtime-подключения", "danger");
    });
}

function upsertNotification(notification) {
    const existingIndex = notificationsState.findIndex((item) => item.id === notification.id);
    if (existingIndex >= 0) {
        notificationsState[existingIndex] = notification;
    } else {
        notificationsState.unshift(notification);
    }
}

async function handleNotificationClick(notificationId) {
    clearMessage(notificationMessage);

    try {
        const updated = await markNotificationReadRequest(notificationId);
        upsertNotification(updated);
        notificationsState = notificationsState.filter((notification) => !notification.read_at);
        renderNotifications(notificationsState);
        await refreshUnreadNotificationsCount();
    } catch (error) {
        showMessage(notificationMessage, "danger", error.message);
    }
}
