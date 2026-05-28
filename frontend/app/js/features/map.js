function getTrackColor(index) {
    const colors = [
        "#0d6efd",
        "#dc3545",
        "#198754",
        "#fd7e14",
        "#6f42c1",
        "#20c997",
        "#6610f2",
        "#d63384"
    ];
    return colors[index % colors.length];
}

function isLeafletAvailable() {
    return typeof L !== "undefined";
}

function initMapIfNeeded() {
    if (!isLeafletAvailable()) {
        return false;
    }

    if (!leafletMap) {
        leafletMap = L.map("map").setView([55.75, 37.61], 11);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "&copy; OpenStreetMap contributors"
        }).addTo(leafletMap);
    }

    setTimeout(() => {
        leafletMap.invalidateSize();
    }, 100);

    return true;
}
function clearMapLayers() {
    if (!leafletMap) {
        return;
    }

    leafletLayers.forEach(layer => leafletMap.removeLayer(layer));
    leafletLayers = [];
}
function drawGroupedGeojsonTracks(groupedTracks) {
    if (!initMapIfNeeded()) {
        renderTrackJson("Карта недоступна", groupedTracks);
        return;
    }

    clearMapLayers();

    const bounds = [];
    let drawnCount = 0;

    groupedTracks.forEach((trip, index) => {
        const features = trip.track?.features || [];

        const latlngs = features
            .map((feature) => {
                const coords = feature?.geometry?.coordinates;
                if (!coords || coords.length < 2) return null;

                const [lon, lat] = coords;
                if (typeof lat !== "number" || typeof lon !== "number") return null;

                return [lat, lon];
            })
            .filter(Boolean);

        if (latlngs.length < 2) {
            return;
        }

        drawnCount += 1;
        latlngs.forEach((point) => bounds.push(point));

        const polyline = L.polyline(latlngs, {
            color: getTrackColor(index),
            weight: 5,
            opacity: 0.9
        }).addTo(leafletMap);

        polyline.bindPopup(
            `Поездка #${trip.trip_id}<br>${formatDateTime(trip.started_at_enterprise)} — ${formatDateTime(trip.ended_at_enterprise)}`
        );

        leafletLayers.push(polyline);
    });

    setTimeout(() => {
        leafletMap.invalidateSize();

        if (bounds.length > 0) {
            leafletMap.fitBounds(bounds, {
                padding: [30, 30],
                maxZoom: 15
            });
        } else if (drawnCount === 0) {
            leafletMap.setView([29.95, -90.07], 12);
        }
    }, 100);
}

function renderTrackJson(titleText, payload) {
    const container = document.getElementById("trackContainer");
    const output = document.getElementById("trackOutput");
    const title = document.getElementById("trackTitle");

    title.textContent = titleText;
    container.classList.remove("d-none");
    output.textContent = JSON.stringify(payload, null, 2);
}
