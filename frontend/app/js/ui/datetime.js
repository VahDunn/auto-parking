function formatDateTime(value) {
    if (!value) return "—";
    return new Date(value).toLocaleString("ru-RU");
}

function toDateTimeLocalValue(value) {
    if (!value) return "";

    const d = new Date(value);
    const pad = (n) => String(n).padStart(2, "0");

    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function localInputToIso(value) {
    if (!value) return "";
    return new Date(value).toISOString();
}
