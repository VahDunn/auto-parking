async function loginRequest(username, password) {
    return await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify({username, password})
    });
}
