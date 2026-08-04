(function () {
    "use strict";

    // cada area marcada mostra seu proprio grupo de objetivos, independente
    // das outras (multi-selecao de area, nao "uma ativa por vez").
    var areaCheckboxes = document.querySelectorAll(".js-quickstart-area");
    var goalGroups = document.querySelectorAll(".js-quickstart-goal-group");

    function goalGroupFor(areaKey) {
        for (var i = 0; i < goalGroups.length; i++) {
            if (goalGroups[i].dataset.areaKey === areaKey) return goalGroups[i];
        }
        return null;
    }

    function updateGoalGroup(checkbox) {
        var group = goalGroupFor(checkbox.value);
        if (!group) return;
        group.hidden = !checkbox.checked;
        group.querySelectorAll("input[type=checkbox]").forEach(function (input) {
            input.disabled = !checkbox.checked;
        });
    }

    areaCheckboxes.forEach(function (checkbox) {
        checkbox.addEventListener("change", function () { updateGoalGroup(checkbox); });
        updateGoalGroup(checkbox);
    });

    // slider de pratica fisica: legenda que muda com a faixa de valor, e 0
    // fica bloqueado (o Con comenta em vez de deixar zerar).
    var slider = document.getElementById("lb-pratica-fisica");
    var valueEl = document.getElementById("lb-pratica-fisica-value");
    var legendEl = document.getElementById("lb-pratica-fisica-legend");
    var lastNonZero = slider ? slider.value : "5";

    var LEGENDS = [
        { max: 3, text: "Leve — pouca ou nenhuma atividade hoje, começando aos poucos." },
        { max: 7, text: "Moderado — atividade física regular, sem exageros." },
        { max: 10, text: "Intenso — treino estruturado já faz parte da sua rotina." },
    ];

    function legendFor(value) {
        for (var i = 0; i < LEGENDS.length; i++) {
            if (value <= LEGENDS[i].max) return LEGENDS[i].text;
        }
        return LEGENDS[LEGENDS.length - 1].text;
    }

    function updateSlider() {
        if (!slider) return;
        if (slider.value === "0") {
            slider.value = lastNonZero;
            if (window.LBAssistant && window.LBAssistant.say) {
                window.LBAssistant.say(
                    "Mente e corpo caminham juntos — por isso essa barra não pode zerar. " +
                    "Pode ser um nível bem leve, mas precisa existir."
                );
            }
        }
        lastNonZero = slider.value;
        if (valueEl) valueEl.textContent = slider.value;
        if (legendEl) legendEl.textContent = legendFor(Number(slider.value));
    }

    if (slider) {
        slider.addEventListener("input", updateSlider);
        updateSlider();
    }
})();
