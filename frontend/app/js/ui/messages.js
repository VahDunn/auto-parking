function showMessage(container, type, text) {
    container.innerHTML = `
        <div class="alert alert-${type}" role="alert">
            ${text}
        </div>
    `;
}

function clearMessage(container) {
    container.innerHTML = "";
}
