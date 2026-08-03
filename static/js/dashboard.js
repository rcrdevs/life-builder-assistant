// dashboard.js -- liga os sliders de missao (registro por %) e de checkpoint (autoavaliacao)
// ao backend, e atualiza os labels de valor em tempo real.

document.addEventListener("DOMContentLoaded", () => {
    // sliders de missao: atualizam o texto "%X" ao lado ao arrastar
    document.querySelectorAll(".lb-mission__logger").forEach((logger) => {
        const slider = logger.querySelector(".lb-mission__slider");
        const valueLabel = logger.querySelector(".lb-mission__slider-value");
        if (slider && valueLabel) {
            slider.addEventListener("input", () => {
                valueLabel.textContent = `${slider.value}%`;
            });
        }
    });

    // botao "Registrar" de cada missao
    document.querySelectorAll(".lb-mission__confirm").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const missionId = btn.dataset.missionId;
            const logger = btn.closest(".lb-mission__logger");
            const slider = logger.querySelector(".lb-mission__slider");
            const pct = slider ? slider.value : 0;

            btn.disabled = true;
            try {
                const res = await fetch(`/api/log_mission/${missionId}`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pct: Number(pct) }),
                });
                const data = await res.json();
                if (!res.ok) {
                    alert(data.error || "Não foi possível registrar a missão.");
                    btn.disabled = false;
                    return;
                }
                const li = btn.closest(".lb-mission");
                li.classList.add("lb-mission--done");
                logger.outerHTML = `<span class="lb-mission__done-tag">${Math.round(data.pct)}% registrado</span>`;

                const toast = document.createElement("div");
                toast.className = "lb-toast";
                toast.textContent = `Registrado: ${Math.round(data.pct)}% (será somado ao progresso no fim do dia)`;
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2600);
            } catch (err) {
                console.error(err);
                btn.disabled = false;
            }
        });
    });

    // sliders de checkpoint (autoavaliacao 0-10): atualizam o numero ao lado
    document.querySelectorAll(".lb-checkpoint-item").forEach((item) => {
        const slider = item.querySelector(".lb-volume-slider");
        const valueLabel = item.querySelector(".lb-checkpoint-item__value");
        if (slider && valueLabel) {
            slider.addEventListener("input", () => {
                valueLabel.textContent = slider.value;
            });
        }
    });

    // peso/altura (passo III): só fazem sentido se o usuário pediu sugestões
    // de dieta -- mostra/esconde o bloco conforme o radio "dieta" muda.
    const dietMeasures = document.getElementById("lb-diet-measures");
    if (dietMeasures) {
        const dietRadios = document.querySelectorAll('input[name="dieta"]');
        dietRadios.forEach((radio) => {
            radio.addEventListener("change", () => {
                const checked = document.querySelector('input[name="dieta"]:checked');
                dietMeasures.classList.toggle("lb-diet-measures--hidden", !checked || checked.value !== "sim");
            });
        });
    }

    // filtro de missoes de hoje: controle segmentado de tier (selecao unica,
    // "Todas" e o padrao) cruzado com o dropdown de areas (selecao multipla,
    // nenhuma marcada = todas as areas). Os blocos de categoria sao <details>
    // colapsaveis; ao filtrar, os que tiverem resultado abrem automaticamente.
    const tierFilter = document.getElementById("tier-filter");
    const areaDropdown = document.getElementById("area-dropdown");
    if (tierFilter) {
        const tierOpts = Array.from(tierFilter.querySelectorAll(".lb-segmented__opt"));
        let activeTier = "todas";

        let activeAreas = [];
        let areaCheckboxes = [];
        if (areaDropdown) {
            areaCheckboxes = Array.from(areaDropdown.querySelectorAll('input[type="checkbox"]'));
            const trigger = areaDropdown.querySelector(".lb-area-dropdown__trigger");
            const countLabel = document.getElementById("area-dropdown-count");
            trigger.addEventListener("click", () => {
                areaDropdown.classList.toggle("lb-area-dropdown--open");
            });
            document.addEventListener("click", (e) => {
                if (!areaDropdown.contains(e.target)) areaDropdown.classList.remove("lb-area-dropdown--open");
            });
            areaCheckboxes.forEach((cb) => {
                cb.addEventListener("change", () => {
                    activeAreas = areaCheckboxes.filter((c) => c.checked).map((c) => c.value);
                    countLabel.textContent = activeAreas.length ? ` (${activeAreas.length})` : "";
                    applyFilters();
                });
            });
        }

        function applyFilters() {
            document.querySelectorAll(".lb-mission").forEach((li) => {
                const area = li.dataset.area;
                const tier = li.dataset.tier;
                const tierMatch = activeTier === "todas" || `tier:${tier}` === activeTier;
                const areaMatch = activeAreas.length === 0 || activeAreas.includes(area);
                li.style.display = tierMatch && areaMatch ? "" : "none";
            });

            document.querySelectorAll(".lb-category-block").forEach((block) => {
                const missions = Array.from(block.querySelectorAll(".lb-mission"));
                const visible = missions.some((li) => li.style.display !== "none");
                block.style.display = visible ? "" : "none";
                if (visible && (activeTier !== "todas" || activeAreas.length)) block.open = true;
            });
        }

        tierOpts.forEach((opt) => {
            opt.addEventListener("click", () => {
                tierOpts.forEach((o) => o.classList.remove("lb-segmented__opt--active"));
                opt.classList.add("lb-segmented__opt--active");
                activeTier = opt.dataset.filter;
                applyFilters();
            });
        });
    }
});
