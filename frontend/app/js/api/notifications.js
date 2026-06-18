async function getNotificationsRequest(unreadOnly = true) {
    const params = new URLSearchParams({
        unread_only: String(unreadOnly)
    });
    return await apiRequest(`/notifications?${params.toString()}`);
}

async function getUnreadNotificationsCountRequest() {
    return await apiRequest("/notifications/unread-count");
}

async function markNotificationReadRequest(notificationId) {
    return await apiRequest(`/notifications/${notificationId}/read`, {
        method: "PATCH"
    });
}

async function markAllNotificationsReadRequest() {
    return await apiRequest("/notifications/read-all", {
        method: "PATCH"
    });
}
