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

    var MAIN_MAX_WIDTH = 1180; // precisa bater com --lb-main max-width no CSS
    var EDGE_GAP = 14;         // respiro entre o assistente e a borda da tela
    var mainEl = document.querySelector(".lb-main");
    var headerEl = document.querySelector(".lb-header");

    // Calcula as faixas "fora" da interface (fora do miolo central onde ficam
    // os cards/botões) onde o assistente pode ficar parado. Ele ainda pode
    // atravessar por cima da interface durante a transição (é só o destino
    // final que respeita essas faixas) -- a transição CSS do .lb-assistant
    // cuida de deslizar suavemente de um lado a outro.
    function safeZones() {
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        var half = (el.offsetWidth || 60) / 2;
        var sideGap = Math.max(0, (vw - MAIN_MAX_WIDTH) / 2);
        var headerH = (headerEl && headerEl.offsetHeight) || 70;
        var yMin = headerH + EDGE_GAP + half;
        var yMax = vh - EDGE_GAP - half;
        var zones = [];

        if (sideGap > half * 2 + EDGE_GAP && yMax > yMin) {
            zones.push({ xMin: EDGE_GAP + half, xMax: sideGap - EDGE_GAP - half, yMin: yMin, yMax: yMax });
            zones.push({ xMin: vw - sideGap + EDGE_GAP + half, xMax: vw - EDGE_GAP - half, yMin: yMin, yMax: yMax });
        }

        // Tela estreita (sem margem lateral livre): usa a faixa abaixo do
        // conteúdo principal quando ele for mais baixo que a viewport.
        if (!zones.length && mainEl) {
            var mainBottom = mainEl.getBoundingClientRect().bottom;
            if (mainBottom + half + EDGE_GAP < vh) {
                zones.push({
                    xMin: EDGE_GAP + half, xMax: vw - EDGE_GAP - half,
                    yMin: mainBottom + EDGE_GAP + half, yMax: vh - EDGE_GAP - half,
                });
            }
        }

        return zones;
    }

    function roam() {
        var zones = safeZones();
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        var half = (el.offsetWidth || 60) / 2;
        var x, y;

        if (zones.length) {
            var zone = zones[Math.floor(Math.random() * zones.length)];
            x = zone.xMin + Math.random() * Math.max(0, zone.xMax - zone.xMin);
            y = zone.yMin + Math.random() * Math.max(0, zone.yMax - zone.yMin);
        } else {
            // Sem faixa livre (mobile/tela pequena): mantém o guia discreto
            // num canto, fora do caminho dos botões.
            x = vw - EDGE_GAP - half;
            y = vh - EDGE_GAP - half;
        }

        el.style.left = x + "px";
        el.style.top = y + "px";
    }

    window.addEventListener("resize", roam);

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
