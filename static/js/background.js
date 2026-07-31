// Life Builder -- fundo animado bem sutil, inspirado nas bolhas flutuantes
// da BIOS do PS2: poucas formas suaves, deriva lenta, quicando nas bordas.
// Roda em <canvas> fixo atrás de tudo, com opacidade muito baixa para nunca
// competir com o conteúdo. Respeita prefers-reduced-motion.
(function () {
    const canvas = document.getElementById("bg-canvas");
    if (!canvas) return;

    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        canvas.remove();
        return;
    }

    const ctx = canvas.getContext("2d");
    let w, h, dpr;

    function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        w = window.innerWidth;
        h = window.innerHeight;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = w + "px";
        canvas.style.height = h + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);

    // paleta discreta: azul neon do tema + um prata frio, bem baixa opacidade
    const palette = [
        "rgba(47, 123, 255, 0.10)",
        "rgba(111, 168, 255, 0.07)",
        "rgba(154, 160, 168, 0.06)",
    ];

    const COUNT = 5;
    const orbs = Array.from({ length: COUNT }, (_, i) => ({
        x: Math.random() * w,
        y: Math.random() * h,
        r: 140 + Math.random() * 180,
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        color: palette[i % palette.length],
    }));

    function tick() {
        ctx.clearRect(0, 0, w, h);
        orbs.forEach((o) => {
            o.x += o.vx;
            o.y += o.vy;
            if (o.x < -o.r) o.x = w + o.r;
            if (o.x > w + o.r) o.x = -o.r;
            if (o.y < -o.r) o.y = h + o.r;
            if (o.y > h + o.r) o.y = -o.r;

            const grad = ctx.createRadialGradient(o.x, o.y, 0, o.x, o.y, o.r);
            grad.addColorStop(0, o.color);
            grad.addColorStop(1, "rgba(0,0,0,0)");
            ctx.fillStyle = grad;
            ctx.fillRect(o.x - o.r, o.y - o.r, o.r * 2, o.r * 2);
        });
        requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
})();
