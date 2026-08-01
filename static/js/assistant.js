(function () {
    "use strict";

    var el = document.getElementById("lb-assistant");
    if (!el) return;

    var textEl = document.getElementById("lb-assistant-text");
    var iconEl = el.querySelector(".lb-assistant__icon");
    var page = el.dataset.page || "";

    var LINES = {
        step_areas: [
            "Escolhe as áreas que fazem sentido pra sua fase agora — dá pra ajustar depois.",
            "Não precisa marcar tudo. Foco em poucas áreas costuma render mais que espalhar demais.",
        ],
        step_paideia: [
            "Sem meta física dessa vez? Tudo bem, essa etapa cobre isso de outro jeito.",
        ],
        step_goals: [
            "Quanto mais específico o objetivo, mais fácil eu meço seu progresso depois.",
            "Pode escolher mais de uma meta por área, se fizer sentido.",
        ],
        step_info: [
            "Seu dia de desenvolvimento soma 8h — o peso de cada área decide como isso se divide.",
            "O tempo livre que você marcar vira missão primária; o resto do dia, secundária.",
        ],
        step_panorama: [
            "Última etapa antes da build ficar pronta. Dá uma revisada com calma.",
        ],
        dashboard: [
            "Suas missões de hoje estão logo abaixo. Bateu o check, marca como feita.",
            "Se travar em alguma missão, dá pra registrar manualmente sem perder os pontos.",
            "Todo ciclo tem 14 dias — depois disso vem o checkpoint pra recalibrar o plano.",
        ],
        checkpoint: [
            "Sê honesto(a) aqui — isso ajusta o plano dos próximos 14 dias com mais precisão.",
        ],
        quiz: [
            "Sem pressa. Se travar, dá pra voltar e registrar essa missão de outro jeito.",
        ],
        plano: [
            "Esse é o mapa completo do seu ciclo — dia por dia, categoria por categoria.",
        ],
        register: [
            "Seu progresso atual continua exatamente como está — só passa a ficar salvo de verdade.",
        ],
        login: [
            "Entrando em outra conta, sua build de teste atual muda de dono automaticamente.",
        ],
    };

    var IDLE_LINES = [
        "Ainda por aqui? Bom sinal.",
        "Progresso não precisa ser rápido, só constante.",
        "Clica em mim se quiser uma dica.",
    ];

    function pick(list) {
        return list[Math.floor(Math.random() * list.length)];
    }

    var hideTimer = null;
    function say(text) {
        if (!text) return;
        textEl.textContent = text;
        el.classList.add("lb-assistant--speaking");
        clearTimeout(hideTimer);
        hideTimer = setTimeout(function () {
            el.classList.remove("lb-assistant--speaking");
        }, 5400);
    }

    function roam() {
        var x = 8 + Math.random() * 82;   // vw, evita colar nas bordas
        var y = 16 + Math.random() * 62;  // vh, evita o header e o rodapé
        el.style.left = x + "vw";
        el.style.top = y + "vh";
    }

    roam();
    setInterval(roam, 8000 + Math.random() * 5000);

    setTimeout(function () {
        var lines = LINES[page];
        if (lines && lines.length) say(pick(lines));
    }, 1500);

    setInterval(function () {
        if (el.classList.contains("lb-assistant--speaking")) return;
        if (Math.random() < 0.4) say(pick(IDLE_LINES));
    }, 40000);

    iconEl.addEventListener("click", function () {
        var lines = (LINES[page] && LINES[page].length) ? LINES[page] : IDLE_LINES;
        say(pick(lines));
    });
})();
