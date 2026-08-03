// outro.js -- controla o dialogo modal usado pelas opcoes "Outro" (areas e objetivos).
// Cada gatilho (.js-outro-trigger) aponta, via data-attributes, para o checkbox/radio
// real que deve ser marcado, o input oculto que recebe o texto, e o span que mostra
// o texto escolhido no proprio card/pill.

document.addEventListener("DOMContentLoaded", () => {
    const dialog = document.getElementById("outro-dialog");
    if (!dialog) return;

    const input = document.getElementById("outro-dialog-input");
    const confirmBtn = document.getElementById("outro-dialog-confirm");
    const cancelBtn = document.getElementById("outro-dialog-cancel");
    let currentTrigger = null;

    document.querySelectorAll(".js-outro-trigger").forEach((trigger) => {
        trigger.addEventListener("click", (ev) => {
            ev.preventDefault();
            currentTrigger = trigger;
            const textInput = document.getElementById(trigger.dataset.textinput);
            input.value = (textInput && textInput.value) || "";
            dialog.showModal();
            input.focus();
        });
    });

    function confirmDialog() {
        if (!currentTrigger) return;
        const texto = input.value.trim();
        if (!texto) {
            input.focus();
            return;
        }
        const checkbox = document.getElementById(currentTrigger.dataset.checkbox);
        const textInput = document.getElementById(currentTrigger.dataset.textinput);
        const labelEl = document.getElementById(currentTrigger.dataset.label);
        if (checkbox) {
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event("change", { bubbles: true }));
        }
        if (textInput) textInput.value = texto;
        if (labelEl) labelEl.textContent = texto;
        currentTrigger.classList.add("js-outro-trigger--filled");
        dialog.close();
    }

    confirmBtn.addEventListener("click", confirmDialog);
    input.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter") {
            ev.preventDefault();
            confirmDialog();
        }
    });
    cancelBtn.addEventListener("click", () => dialog.close());
});
