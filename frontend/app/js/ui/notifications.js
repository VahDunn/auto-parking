function renderNotifications(notifications) {
    const list = document.getElementById("notificationList");
    list.innerHTML = "";

    if (!notifications.length) {
        list.innerHTML = '<div class="list-group-item text-muted">Уведомлений пока нет</div>';
        return;
    }

    notifications.forEach((notification) => {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "list-group-item list-group-item-action";
        item.dataset.notificationId = notification.id;

        const createdAt = notification.created_at
            ? new Date(notification.created_at).toLocaleString("ru-RU")
            : "";

        item.innerHTML = `
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${notification.title}</div>
                    <div>${notification.body}</div>
                    <div class="text-muted small mt-1">
                        Поездка #${notification.trip_id}
                        ${createdAt ? ` · ${createdAt}` : ""}
                    </div>
                </div>
                <span class="badge text-bg-${notification.read_at ? "secondary" : "success"}">
                    ${notification.read_at ? "прочитано" : "новое"}
                </span>
            </div>
        `;

        list.appendChild(item);
    });
}

function renderNotificationUnreadCount(count) {
    document.getElementById("notificationUnreadBadge").textContent = String(count);
}

function setNotificationStatus(text, variant = "muted") {
    const status = document.getElementById("notificationStatus");
    status.className = `text-${variant} small`;
    status.textContent = text;
}
