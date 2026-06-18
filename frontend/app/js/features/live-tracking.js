function setLiveTrackingStatus(text, className) {
    const status = document.getElementById("liveTrackingStatus");
    if (!status) return;
    status.textContent = text;
    status.className = `small ${className}`;
}

function startLiveTracking() {
    if (!accessToken) {
        setLiveTrackingStatus("Live: нужна авторизация", "text-danger");
        return;
    }

    if (liveTrackingSocket && liveTrackingSocket.readyState <= WebSocket.OPEN) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    liveTrackingSocket = new WebSocket(`${protocol}://${window.location.host}/api/vehicles/live/ws`);
    setLiveTrackingStatus("Live: подключение", "text-secondary");

    liveTrackingSocket.onopen = () => {
        setLiveTrackingStatus("Live: подключено", "text-success");
        clearInterval(liveTrackingPingTimer);
        liveTrackingPingTimer = setInterval(() => {
            if (liveTrackingSocket?.readyState === WebSocket.OPEN) {
                liveTrackingSocket.send("ping");
            }
        }, 20000);
    };

    liveTrackingSocket.onmessage = (message) => {
        try {
            const payload = JSON.parse(message.data);
            if (payload.event === "vehicle.gps" && payload.point) {
                updateLiveVehicleMarker(payload.point);
            }
        } catch (_) {
            return;
        }
    };

    liveTrackingSocket.onerror = () => {
        setLiveTrackingStatus("Live: ошибка подключения", "text-danger");
    };

    liveTrackingSocket.onclose = (event) => {
        liveTrackingSocket = null;
        clearInterval(liveTrackingPingTimer);
        liveTrackingPingTimer = null;

        if (event.code === 1008) {
            setLiveTrackingStatus("Live: нужна повторная авторизация", "text-danger");
            return;
        }

        setLiveTrackingStatus("Live: отключено", "text-danger");
        clearTimeout(liveTrackingReconnectTimer);
        liveTrackingReconnectTimer = setTimeout(startLiveTracking, 2000);
    };
}
