(function () {
    "use strict";

    var stage = document.getElementById("lb-con-stage");
    var form = document.getElementById("lb-build-form");
    if (!stage || !form) return;

    var dataEl = document.getElementById("lb-con-questions-data");
    var questions = [];
    try {
        questions = dataEl ? JSON.parse(dataEl.textContent) : [];
    } catch (e) {
        questions = [];
    }

    var progressEl = document.getElementById("lb-con-progress");
    var questionEl = document.getElementById("lb-con-question");
    var contextEl = document.getElementById("lb-con-context");
    var optionsEl = document.getElementById("lb-con-options");
    var actionsEl = document.getElementById("lb-con-actions");
    var writeEl = document.getElementById("lb-con-write");
    var input = document.getElementById("lb-con-input");
    var confirmBtn = document.getElementById("lb-con-input-confirm");

    var index = 0;
    var onConfirm = null;      // handler do campo de texto, trocado por pergunta
    var onEnterFinal = null;   // Enter na pergunta final = "Gerar minha build"

    // o proprio assistente flutuante cresce e vira esta tela (ver
    // enterStage() em assistant.js) -- nao ha um segundo Con desenhado aqui.
    if (window.LBAssistant && window.LBAssistant.enterStage) {
        window.LBAssistant.enterStage();
    }

    function fieldFor(q) {
        return document.getElementById("field_" + q.key.replace(":", "_"));
    }

    function submitBuild() {
        if (form.requestSubmit) {
            form.requestSubmit();
        } else {
            form.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    }

    function clearPanel() {
        optionsEl.innerHTML = "";
        actionsEl.innerHTML = "";
        optionsEl.hidden = true;
        actionsEl.hidden = true;
        writeEl.hidden = true;
        contextEl.hidden = true;
        input.value = "";
        onConfirm = null;
        onEnterFinal = null;
    }

    function addButton(container, label, variant, handler) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "lb-btn lb-btn--sm " + variant;
        btn.textContent = label;
        btn.addEventListener("click", handler);
        container.appendChild(btn);
        container.hidden = false;
        return btn;
    }

    function addChip(container, label, handler) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "lb-con-chip";
        chip.textContent = label;
        chip.addEventListener("click", function () { handler(chip); });
        container.appendChild(chip);
        container.hidden = false;
        return chip;
    }

    function showWriteField(placeholder, handler) {
        writeEl.hidden = false;
        input.placeholder = placeholder || "";
        onConfirm = handler;
        // na pergunta final o campo e opcional e quem envia e o botao
        // "Gerar minha build" -- um "Confirmar" ao lado so confundiria.
        confirmBtn.hidden = !handler;
        input.focus();
    }

    function answer(value) {
        var q = questions[index];
        if (q && value) {
            var field = fieldFor(q);
            if (field) field.value = value;
        }
        index += 1;
        if (index >= questions.length) {
            submitBuild();
        } else {
            showQuestion(index);
        }
    }

    function showQuestion(i) {
        var q = questions[i];
        if (!q) { submitBuild(); return; }

        clearPanel();
        progressEl.hidden = false;
        progressEl.textContent = "Pergunta " + (i + 1) + " de " + questions.length;
        questionEl.textContent = q.prompt;

        if (q.area_label) {
            contextEl.hidden = false;
            contextEl.textContent = q.area_label + " · " + q.goal_label;
        }

        if (q.type === "detalhe") {
            addButton(actionsEl, "Escrever", "lb-btn--primary", function () {
                actionsEl.hidden = true;
                showWriteField(q.placeholder, function (val) { answer(val); });
            });
            addButton(actionsEl, "Deixar que o Con escolha", "lb-btn--ghost", function () {
                answer(null);
            });

        } else if (q.type === "direcao") {
            (q.options || []).forEach(function (opt) {
                addChip(optionsEl, opt, function () { answer(opt); });
            });
            addButton(actionsEl, "Outro…", "lb-btn--ghost", function () {
                showWriteField("Escreva o direcionamento que faz sentido pra você", function (val) {
                    answer(val);
                });
            });
            addButton(actionsEl, q.free_label || "Livre", "lb-btn--ghost", function () {
                answer(null);
            });

        } else if (q.type === "final") {
            var picked = [];
            (q.suggestions || []).forEach(function (s) {
                addChip(optionsEl, s, function (chip) {
                    var at = picked.indexOf(s);
                    if (at >= 0) { picked.splice(at, 1); chip.classList.remove("lb-con-chip--on"); }
                    else { picked.push(s); chip.classList.add("lb-con-chip--on"); }
                });
            });
            showWriteField(q.placeholder, null);
            var gerar = function () {
                var livre = input.value.trim();
                var partes = picked.slice();
                if (livre) partes.push(livre);
                answer(partes.length ? partes.join("; ") : null);
            };
            addButton(actionsEl, "Gerar minha build →", "lb-btn--primary", gerar);
            onEnterFinal = gerar;
        }
    }

    function confirmWrite() {
        if (onEnterFinal) { onEnterFinal(); return; }
        if (!onConfirm) return;
        var val = input.value.trim();
        if (!val) { input.focus(); return; }
        onConfirm(val);
    }

    confirmBtn.addEventListener("click", confirmWrite);
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); confirmWrite(); }
    });

    if (!questions.length) {
        submitBuild();
    } else {
        showQuestion(0);
    }
})();
