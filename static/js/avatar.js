// avatar.js -- traduz o progresso geral do usuario (0-100) em ajustes visuais do avatar
// wireframe. Uma unica dimensao dirige tudo: quanto mais perto da conclusao dos seus
// objetivos, mais "calibrado" (nitido, luminoso, robusto) o avatar fica.

const DIM_STROKE = { r: 0x1c, g: 0x3a, b: 0x5e };   // azul apagado (baixo progresso)
const NEON_STROKE = { r: 0x6f, g: 0xa8, b: 0xff };  // azul neon vivo (alto progresso)

function clamp01(x) {
    return Math.max(0, Math.min(1, x));
}

function lerpColor(a, b, t) {
    const r = Math.round(a.r + (b.r - a.r) * t);
    const g = Math.round(a.g + (b.g - a.g) * t);
    const b2 = Math.round(a.b + (b.b - a.b) * t);
    return `rgb(${r}, ${g}, ${b2})`;
}

function setTransform(el, scaleX, scaleY) {
    if (!el) return;
    el.style.transformBox = "fill-box";
    el.style.transformOrigin = "center";
    el.style.transform = `scale(${scaleX}, ${scaleY})`;
}

function renderAvatar(overallProgress) {
    if (overallProgress === null || overallProgress === undefined) return;
    const t = clamp01(overallProgress / 100);

    // corpo cresce sutilmente com o progresso geral
    setTransform(document.getElementById("torso"), 1 + t * 0.35, 1 + t * 0.1);
    setTransform(document.getElementById("arm-left"), 1 + t * 0.4, 1);
    setTransform(document.getElementById("arm-right"), 1 + t * 0.4, 1);
    setTransform(document.getElementById("leg-left"), 1 + t * 0.2, 1 + t * 0.06);
    setTransform(document.getElementById("leg-right"), 1 + t * 0.2, 1 + t * 0.06);

    // contorno filosofico (barba) e brilho no olhar aparecem gradualmente
    const beard = document.getElementById("beard");
    if (beard) beard.setAttribute("opacity", clamp01((t - 0.2) / 0.6).toFixed(2));

    const glint = document.getElementById("glint");
    if (glint) glint.setAttribute("opacity", clamp01((t - 0.1) / 0.7).toFixed(2));

    // objeto geometrico girando atras da cabeca -- mais visivel e mais rapido com o progresso
    const aura = document.getElementById("aura");
    if (aura) {
        aura.setAttribute("opacity", (0.15 + t * 0.85).toFixed(2));
        const duration = Math.max(4, 12 - t * 8);
        aura.style.animation = `lb-spin ${duration}s linear infinite`;
        aura.style.transformBox = "fill-box";
        aura.style.transformOrigin = "center";
    }

    // contorno geral vai de azul apagado a neon vivo, com glow crescente
    const strokeColor = lerpColor(DIM_STROKE, NEON_STROKE, t);
    const glowStrength = 1 + t * 3;
    ["torso", "arm-left", "arm-right", "leg-left", "leg-right", "head"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) {
            el.setAttribute("stroke", strokeColor);
            el.style.filter = `drop-shadow(0 0 ${glowStrength.toFixed(1)}px ${strokeColor})`;
        }
    });
}

(function injectKeyframes() {
    const style = document.createElement("style");
    style.textContent = `@keyframes lb-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`;
    document.head.appendChild(style);
})();

if (typeof window.LB_OVERALL_PROGRESS !== "undefined") {
    renderAvatar(window.LB_OVERALL_PROGRESS);
}
