// area_tiers.js -- controla a prioridade (principal/secundaria/plano de
// fundo) de cada area no Passo I. So pode existir UM card "principal" por
// vez (o primeiro marcado vira principal automaticamente; marcar outro como
// principal rebaixa o antigo pra secundaria); secundaria/plano de fundo sao
// livres, quantas areas o usuario quiser. O valor escolhido aqui e enviado
// direto no form (tier_<area>) e o backend transforma isso no peso da area
// -- ninguem precisa mexer em slider de peso depois, no Passo III.

document.addEventListener("DOMContentLoaded", () => {
    const grid = document.getElementById("lb-area-grid");
    if (!grid) return;

    const TIER_LABELS = {
        principal: "Principal",
        secundario: "Secundária",
        fundo: "Plano de fundo",
    };

    const cards = Array.from(grid.querySelectorAll(".lb-area-card"));

    function checkbox(card) {
        return card.querySelector(".lb-area-card__hit input[type='checkbox']");
    }
    function tierInput(card) {
        return card.querySelector(".lb-area-tier-input");
    }
    function isChecked(card) {
        const cb = checkbox(card);
        return !!cb && cb.checked;
    }
    function currentTier(card) {
        return tierInput(card).value || "";
    }

    function hasCheckedPrincipal(exceptCard) {
        return cards.some((c) => c !== exceptCard && isChecked(c) && currentTier(c) === "principal");
    }

    const TIER_CLASSES = ["is-tier-principal", "is-tier-secundario", "is-tier-fundo"];

    function paintCard(card) {
        const tier = currentTier(card);
        const tag = card.querySelector("[data-tier-tag]");
        if (tag) tag.textContent = TIER_LABELS[tier] || "";
        card.querySelectorAll(".lb-area-tier-btn").forEach((btn) => {
            btn.classList.toggle("lb-area-tier-btn--active", btn.dataset.tier === tier);
        });
        // O estado visual do card vem dessa classe (ver checkable.js): o
        // valor do input escondido continua existindo so pro submit do form.
        TIER_CLASSES.forEach((cls) => card.classList.remove(cls));
        if (tier) card.classList.add("is-tier-" + tier);
    }

    // Mantem o atributo `value` (nao so a propriedade) em sincronia -- o
    // atributo e o que vai no submit do form, e atributo != propriedade em
    // inputs assim que a gente mexe neles via JS.
    function setTier(card, tier, demoteOthers) {
        if (tier === "principal" && demoteOthers) {
            cards.forEach((c) => {
                if (c !== card && currentTier(c) === "principal") {
                    const input = tierInput(c);
                    input.value = "secundario";
                    input.setAttribute("value", "secundario");
                    paintCard(c);
                }
            });
        }
        const input = tierInput(card);
        input.value = tier;
        input.setAttribute("value", tier);
        paintCard(card);
    }

    function defaultTierFor(card) {
        return hasCheckedPrincipal(card) ? "secundario" : "principal";
    }

    cards.forEach((card) => {
        const cb = checkbox(card);
        if (!cb) return;

        // Estado inicial (edicao de build ja existente, ou GET apos erro de
        // validacao): se a area ja vem marcada mas sem prioridade definida,
        // atribui um default sensato sem sobrescrever o que ja foi salvo.
        if (isChecked(card) && !currentTier(card)) {
            setTier(card, defaultTierFor(card), true);
        } else {
            paintCard(card);
        }

        cb.addEventListener("change", () => {
            if (!cb.checked) {
                // Desmarcar precisa LIMPAR a prioridade, nao so repintar --
                // era esse o bug do card que continuava com a cor/selo de
                // "principal" depois de desmarcado: o tier ficava salvo e o
                // estilo seguia esse valor, nao o checkbox. Tambem evita
                // mandar tier_<area> de uma area que o usuario nao escolheu.
                setTier(card, "", false);
                return;
            }
            if (!currentTier(card)) {
                setTier(card, defaultTierFor(card), true);
            } else {
                paintCard(card);
            }
        });

        card.querySelectorAll(".lb-area-tier-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                setTier(card, btn.dataset.tier, true);
            });
        });
    });
});
