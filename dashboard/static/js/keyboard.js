/**
 * Shared M / R / S keyboard shortcuts for pair review screens.
 * The page must define window.onMatch, window.onReject, window.onSkip.
 */
(function () {
    function flashKbd(key) {
        const el = document.querySelector(`[data-kbd="${key}"]`);
        if (!el) return;
        el.classList.add("bg-primary", "text-white");
        setTimeout(() => el.classList.remove("bg-primary", "text-white"), 150);
    }

    document.addEventListener("keydown", (e) => {
        if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
        const key = e.key.toLowerCase();
        if (key === "m" && typeof window.onMatch === "function") {
            flashKbd("m");
            window.onMatch();
        } else if (key === "r" && typeof window.onReject === "function") {
            flashKbd("r");
            window.onReject();
        } else if (key === "s" && typeof window.onSkip === "function") {
            flashKbd("s");
            window.onSkip();
        }
    });
})();
