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
    var choicesEl = document.getElementById("lb-con-choices");
    var writeBtn = document.getElementById("lb-con-choice-write");
    var autoBtn = document.getElementById("lb-con-choice-auto");
    var inputRow = document.getElementById("lb-con-input-row");
    var input = document.getElementById("lb-con-input");
    var confirmBtn = document.getElementById("lb-con-input-confirm");

    var index = 0;

    function submitBuild() {
        if (form.requestSubmit) {
            form.requestSubmit();
        } else {
            form.dispatchEvent(new Event("submit", { cancelable: true }));
        }
    }

    function showQuestion(i) {
        var q = questions[i];
        if (!q) { submitBuild(); return; }

        progressEl.hidden = false;
        progressEl.textContent = "Pergunta " + (i + 1) + " de " + questions.length;
        questionEl.textContent = q.prompt + " (" + q.area_label + " — " + q.goal_label + ")";

        inputRow.hidden = true;
        input.value = "";
        input.placeholder = q.placeholder || "";
        choicesEl.hidden = false;
    }

    function answerAndAdvance(value) {
        var q = questions[index];
        if (q && value) {
            var field = document.getElementById("detail_" + q.area + "_" + q.goal);
            if (field) field.value = value;
        }
        index += 1;
        if (index >= questions.length) {
            submitBuild();
        } else {
            showQuestion(index);
        }
    }

    writeBtn.addEventListener("click", function () {
        choicesEl.hidden = true;
        inputRow.hidden = false;
        input.focus();
    });

    autoBtn.addEventListener("click", function () {
        answerAndAdvance(null);
    });

    function confirmInput() {
        var val = input.value.trim();
        if (!val) { input.focus(); return; }
        answerAndAdvance(val);
    }

    confirmBtn.addEventListener("click", confirmInput);
    input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") { e.preventDefault(); confirmInput(); }
    });

    if (!questions.length) {
        submitBuild();
    } else {
        showQuestion(0);
    }
})();
