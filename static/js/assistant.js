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
            "A primeira área marcada vira seu objetivo principal (destaque amarelo) — nas outras, escolhe se ficam secundárias ou só plano de fundo.",
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
        updateBubbleDirection(lastX, lastY);
        el.classList.add("lb-assistant--speaking");
        clearTimeout(hideTimer);
        hideTimer = setTimeout(function () {
            el.classList.remove("lb-assistant--speaking");
        }, 5400);
    }

    var bubbleEl = document.getElementById("lb-assistant-bubble");
    var lastX = window.innerWidth / 2;
    var lastY = window.innerHeight / 2;
    var EDGE_SAFE = 10; // respiro minimo entre o balao e a borda da tela

    // --- Pergunta interativa (hoje só sono, mas dá pra reaproveitar o
    // padrão pra outras perguntas rápidas que o assistente possa fazer). ---
    var sleepPromptActive = el.dataset.sleepPrompt === "1";
    var sleepUrl = el.dataset.sleepUrl || "/log_sleep";
    var userName = el.dataset.userName || "";

    function restoreBubble() {
        bubbleEl.classList.remove("lb-assistant__bubble--interactive");
        bubbleEl.innerHTML = '<p id="lb-assistant-text"></p>';
        textEl = document.getElementById("lb-assistant-text");
    }

    function showSleepPrompt() {
        clearTimeout(hideTimer);
        el.classList.add("lb-assistant--speaking");
        bubbleEl.classList.add("lb-assistant__bubble--interactive");
        bubbleEl.innerHTML =
            "<p>Bom te ver de novo" + (userName ? ", " + userName : "") + ". Quantas horas você dormiu essa noite?</p>" +
            '<div class="lb-assistant__prompt-row">' +
            '<input type="number" class="lb-assistant__prompt-input" min="0" max="14" step="0.5" placeholder="ex: 7" id="lb-sleep-input">' +
            '<button type="button" class="lb-assistant__prompt-submit" id="lb-sleep-submit">Registrar</button>' +
            "</div>";
        updateBubbleDirection(lastX, lastY);

        var input = document.getElementById("lb-sleep-input");
        var btn = document.getElementById("lb-sleep-submit");
        if (input) input.focus();

        function submit() {
            var val = parseFloat(input.value);
            if (isNaN(val) || val < 0 || val > 14) {
                input.focus();
                return;
            }
            btn.disabled = true;
            btn.textContent = "...";
            fetch(sleepUrl, {
                method: "POST",
                headers: { "X-Requested-With": "fetch" },
                body: new URLSearchParams({ horas: String(val) }),
            })
                .then(function (res) { return res.json ? res.json() : { ok: true }; })
                .catch(function () { return { ok: true }; })
                .then(function () {
                    sleepPromptActive = false;
                    restoreBubble();
                    say("Anotado — " + val + "h. Isso ajuda a calibrar o ritmo das próximas missões.");
                })
                .catch(function () {
                    btn.disabled = false;
                    btn.textContent = "Registrar";
                });
        }

        if (btn) btn.addEventListener("click", submit);
        if (input) {
            input.addEventListener("keydown", function (e) {
                if (e.key === "Enter") { e.preventDefault(); submit(); }
            });
        }
    }

    // Escolhe pra que lado o balao abre (acima/abaixo, esquerda/centro/direita)
    // com base em quanto espaco sobra entre o icone e cada borda da tela --
    // assim ele nunca fica cortado, seja no topo (perto do cabecalho) ou nas
    // laterais (telas estreitas, como um tablet fixado numa bancada).
    function updateBubbleDirection(x, y) {
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        var iconHalf = (el.offsetWidth || 60) / 2;
        var bw = (bubbleEl && bubbleEl.offsetWidth) || (vw <= 640 ? 190 : 240);
        var bh = (bubbleEl && bubbleEl.offsetHeight) || 80;

        var spaceAbove = y - iconHalf;
        var spaceBelow = vh - (y + iconHalf);
        el.classList.toggle("lb-assistant--bubble-below", spaceAbove < bh + 16 && spaceBelow > spaceAbove);

        var overflowsLeft = (x - bw / 2) < EDGE_SAFE;
        var overflowsRight = (x + bw / 2) > (vw - EDGE_SAFE);
        el.classList.toggle("lb-assistant--bubble-start", overflowsLeft && !overflowsRight);
        el.classList.toggle("lb-assistant--bubble-end", overflowsRight && !overflowsLeft);
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
        lastX = x;
        lastY = y;
        updateBubbleDirection(x, y);
    }

    // --- Modo "palco": o Con cresce e vira a tela ------------------------
    // Usado na tela de geracao da build (ver step_build.js): em vez de
    // desenhar um segundo hexagono grande na pagina (o que fazia o Con
    // aparecer duplicado), o proprio assistente flutuante para de circular,
    // vai pro centro e cresce. Ao sair, volta a circular normalmente.
    var stageMode = false;
    var roamTimer = null;

    function startRoaming() {
        if (roamTimer) clearInterval(roamTimer);
        roamTimer = setInterval(roam, 8000 + Math.random() * 5000);
    }

    function enterStage() {
        if (stageMode) return;
        stageMode = true;
        if (roamTimer) { clearInterval(roamTimer); roamTimer = null; }
        clearTimeout(hideTimer);
        el.classList.remove("lb-assistant--speaking");
        // limpa o posicionamento inline que o roam() aplica -- sem isso o
        // estilo inline venceria as regras de .lb-assistant--stage.
        el.style.left = "";
        el.style.top = "";
        el.classList.add("lb-assistant--stage");
    }

    function exitStage() {
        if (!stageMode) return;
        stageMode = false;
        el.classList.remove("lb-assistant--stage");
        roam();
        startRoaming();
    }

    window.addEventListener("resize", function () { if (!stageMode) roam(); });

    roam();
    startRoaming();

    setTimeout(function () {
        if (stageMode) return;
        if (sleepPromptActive) { showSleepPrompt(); return; }
        var lines = LINES[page];
        if (lines && lines.length) say(pick(lines));
    }, 1500);

    setInterval(function () {
        if (stageMode) return;
        if (el.classList.contains("lb-assistant--speaking")) return;
        if (sleepPromptActive) { showSleepPrompt(); return; }
        if (Math.random() < 0.4) say(pick(IDLE_LINES));
    }, 40000);

    iconEl.addEventListener("click", function () {
        if (stageMode) return;  // no palco quem fala e a propria tela
        if (sleepPromptActive) { showSleepPrompt(); return; }
        var lines = (LINES[page] && LINES[page].length) ? LINES[page] : IDLE_LINES;
        say(pick(lines));
    });

    // exposto pra outras telas (ex.: o slider de pratica fisica na etapa 1,
    // e a tela de geracao da build) usarem o assistente que ja existe, sem
    // duplicar a logica de "falar" nem desenhar um segundo Con.
    window.LBAssistant = { say: say, enterStage: enterStage, exitStage: exitStage };
})();
