function onGoogleCredential(response) {
    var errorEl = document.querySelector("[data-google-error]");
    if (errorEl) errorEl.textContent = "";

    fetch("/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential: response.credential }),
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.ok) {
                window.location.href = data.redirect;
            } else if (errorEl) {
                errorEl.textContent = data.error || "Não foi possível entrar com Google.";
            }
        })
        .catch(function () {
            if (errorEl) errorEl.textContent = "Não foi possível entrar com Google. Tente novamente.";
        });
}
