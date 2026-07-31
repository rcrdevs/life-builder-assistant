// Life Builder -- painel de dieta com substituições no plano completo.
// Tudo roda no cliente: nenhuma chamada ao servidor é feita ao trocar uma
// refeição, o total nutricional é recalculado na hora a partir dos dados
// (reais e curados) já embutidos na página.
(function () {
    const dataEl = document.getElementById("diet-data");
    if (!dataEl) return;
    const dietData = JSON.parse(dataEl.textContent);
    const mealsWrap = document.getElementById("diet-meals");

    const MEAL_LABELS = { cafe: "Café da manhã", almoco: "Almoço", lanche: "Lanche", jantar: "Jantar" };
    const MEAL_ORDER = ["cafe", "almoco", "lanche", "jantar"];

    const selected = {}; // meal_type -> option object atualmente escolhida

    function findOption(mealType, nome) {
        return (dietData.menu[mealType] || []).find((o) => o.nome === nome);
    }

    function renderMeal(mealType) {
        const options = dietData.menu[mealType] || [];
        if (!options.length) return null;

        const defaultNome = dietData.default_selection[mealType];
        const current = findOption(mealType, defaultNome) || options[0];
        selected[mealType] = current;

        const card = document.createElement("div");
        card.className = "lb-diet-meal";

        const header = document.createElement("div");
        header.className = "lb-diet-meal__header";
        header.innerHTML =
            '<span class="lb-diet-meal__slot">' + MEAL_LABELS[mealType] + "</span>";

        const select = document.createElement("select");
        select.className = "lb-diet-meal__select";
        options.forEach((opt) => {
            const el = document.createElement("option");
            el.value = opt.nome;
            el.textContent = opt.nome + " — " + opt.dieta_label;
            if (opt.nome === current.nome) el.selected = true;
            select.appendChild(el);
        });
        header.appendChild(select);
        card.appendChild(header);

        const ingredientList = document.createElement("ul");
        ingredientList.className = "lb-diet-meal__ingredients";
        card.appendChild(ingredientList);

        const macros = document.createElement("p");
        macros.className = "lb-diet-meal__macros";
        card.appendChild(macros);

        function paint(opt) {
            ingredientList.innerHTML = "";
            opt.ingredientes.forEach((ing) => {
                const li = document.createElement("li");
                li.textContent = ing;
                ingredientList.appendChild(li);
            });
            macros.textContent =
                opt.kcal + " kcal · " + opt.proteina_g + "g proteína · " +
                opt.carboidrato_g + "g carboidrato · " + opt.gordura_g + "g gordura";
        }
        paint(current);

        select.addEventListener("change", () => {
            const opt = findOption(mealType, select.value);
            selected[mealType] = opt;
            paint(opt);
            recomputeTotals();
        });

        return card;
    }

    function recomputeTotals() {
        let kcal = 0, prot = 0, carb = 0, gord = 0;
        Object.values(selected).forEach((opt) => {
            if (!opt) return;
            kcal += opt.kcal; prot += opt.proteina_g; carb += opt.carboidrato_g; gord += opt.gordura_g;
        });
        document.getElementById("total-kcal").textContent = kcal;
        document.getElementById("total-prot").textContent = prot + "g";
        document.getElementById("total-carb").textContent = carb + "g";
        document.getElementById("total-gord").textContent = gord + "g";
    }

    MEAL_ORDER.forEach((mealType) => {
        const card = renderMeal(mealType);
        if (card) mealsWrap.appendChild(card);
    });
    recomputeTotals();
})();
