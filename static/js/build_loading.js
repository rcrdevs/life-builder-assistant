(function () {
    "use strict";
    var form = document.getElementById("lb-build-form");
    if (!form || form.dataset.firstBuild !== "true") return;

    var overlay = document.getElementById("lb-build-loading");
    var ring = document.getElementById("lb-build-progress-ring");
    var textEl = document.getElementById("lb-build-loading-text");
    var pctEl = document.getElementById("lb-build-loading-pct");
    var assistantEl = document.getElementById("lb-assistant");
    if (!overlay || !ring) return;

    var messages = [
        "Lendo suas prioridades...",
        "Balanceando as áreas por peso...",
        "Montando seu ciclo de 14 dias...",
        "Gerando sua nota de estratégia...",
        "Quase lá..."
    ];

    var pct = 0;
    var msgIndex = 0;
    var rafId = null;
    var msgTimer = null;
    var finished = false;

    function setPct(v) {
        pct = v;
        ring.style.strokeDashoffset = String(100 - v);
        if (pctEl) pctEl.textContent = Math.round(v) + "%";
    }

    function tick() {
        if (finished) return;
        var target = 92; // nunca fecha sozinho -- só chega a 100% quando a resposta chegar
        pct += (target - pct) * 0.02 + 0.04;
        if (pct > target) pct = target;
        setPct(pct);
        rafId = requestAnimationFrame(tick);
    }

    function cycleMessages() {
        if (finished || !textEl) return;
        textEl.textContent = messages[msgIndex % messages.length];
        msgIndex += 1;
        msgTimer = setTimeout(cycleMessages, 2200);
    }

    function showOverlay() {
        if (assistantEl) assistantEl.classList.add("lb-assistant--hidden");
        overlay.classList.add("is-active");
        overlay.setAttribute("aria-hidden", "false");
        setPct(0);
        cycleMessages();
        rafId = requestAnimationFrame(tick);
    }

    function hideOverlay() {
        overlay.classList.remove("is-active");
        overlay.setAttribute("aria-hidden", "true");
        if (assistantEl) assistantEl.classList.remove("lb-assistant--hidden");
    }

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        showOverlay();

        var formData = new FormData(form);
        fetch(form.action, { method: "POST", body: formData })
            .then(function (res) {
                finished = true;
                if (rafId) cancelAnimationFrame(rafId);
                if (msgTimer) clearTimeout(msgTimer);
                setPct(100);
                if (textEl) textEl.textContent = "Build pronta!";
                setTimeout(function () {
                    window.location.href = res.url || form.action;
                }, 650);
            })
            .catch(function () {
                finished = true;
                if (rafId) cancelAnimationFrame(rafId);
                if (msgTimer) clearTimeout(msgTimer);
                hideOverlay();
                // fallback: envio tradicional caso o fetch falhe (ex: rede instável)
                HTMLFormElement.prototype.submit.call(form);
            });
    });
})();
