function renderEnterpriseInfo(enterprise) {
    const container = document.getElementById("selectedEnterpriseInfo");
    const buttons = document.getElementById("enterpriseExportButtons");

    if (!enterprise) {
        container.innerHTML = `<span class="text-muted">Сначала выберите предприятие слева</span>`;
        buttons?.classList.add("d-none");
        return;
    }

    container.innerHTML = `
        <div><strong>ID:</strong> ${enterprise.id}</div>
        <div><strong>Название:</strong> ${enterprise.name}</div>
        <div><strong>Населённый пункт:</strong> ${enterprise.settlement}</div>
        <div><strong>Таймзона:</strong> ${enterprise.timezone || "UTC"}</div>
        <div><strong>Менеджеры:</strong> ${enterprise.managers?.join(", ") || "—"}</div>
        <div><strong>Машины:</strong> ${enterprise.vehicles?.length || 0}</div>
    `;

    buttons?.classList.remove("d-none");
}

function renderEnterprises(items, selectedEnterpriseId, onSelect) {
    const enterpriseList = document.getElementById("enterpriseList");
    enterpriseList.innerHTML = "";

    if (!items || items.length === 0) {
        enterpriseList.innerHTML = `
            <li class="list-group-item text-muted">
                Нет доступных предприятий
            </li>
        `;
        return;
    }

    items.forEach((enterprise) => {
        const li = document.createElement("li");
        li.className = "list-group-item list-group-item-action";

        if (enterprise.id === selectedEnterpriseId) {
            li.classList.add("selected-enterprise");
        }

        li.innerHTML = `
            <div class="fw-semibold">${enterprise.name ?? "Без названия"}</div>
            <div class="text-muted small">ID: ${enterprise.id}</div>
            <div class="text-muted small">Город: ${enterprise.settlement ?? "—"}</div>
        `;

        li.addEventListener("click", () => onSelect(enterprise));
        enterpriseList.appendChild(li);
    });
}
