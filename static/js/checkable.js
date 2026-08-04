// checkable.js -- mantem uma classe `is-checked` nos wrappers de checkbox/
// radio (cards de area, pills de objetivo) em sincronia com o input de
// dentro.
//
// Por que uma classe em vez de depender so de `:has(input:checked)`: deixa o
// estado visual explicito e inspecionavel (da pra ver no DevTools qual card
// esta ativo), funciona em navegador sem suporte a `:has()`, e deixa o CSS
// legivel -- `.lb-area-card.is-checked` em vez de um seletor aninhado que
// precisa alcancar o input escondido la dentro.
(function () {
    "use strict";

    var WRAPPERS = ".lb-area-card, .lb-radio-pill, .lb-goal-option";

    function sync(input) {
        var checked = !!input.checked;
        var seen = [];
        var el = input.parentElement;
        while (el && el !== document.body) {
            if (el.matches && el.matches(WRAPPERS)) {
                el.classList.toggle("is-checked", checked);
                seen.push(el);
            }
            el = el.parentElement;
        }
        return seen;
    }

    function syncGroup(input) {
        // radio: marcar um desmarca os outros do mesmo name, e esses outros
        // nao disparam evento proprio -- entao sincroniza o grupo inteiro.
        if (input.type === "radio" && input.name) {
            document.querySelectorAll('input[type="radio"][name="' + CSS.escape(input.name) + '"]')
                .forEach(function (other) { sync(other); });
        } else {
            sync(input);
        }
    }

    function syncAll() {
        document.querySelectorAll('input[type="checkbox"], input[type="radio"]').forEach(sync);
    }

    document.addEventListener("change", function (event) {
        var t = event.target;
        if (t && (t.type === "checkbox" || t.type === "radio")) syncGroup(t);
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", syncAll);
    } else {
        syncAll();
    }
})();
