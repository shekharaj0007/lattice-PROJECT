/** Light / dark theme — runs before paint to avoid flash */
(function () {
  const KEY = "latticeTheme";
  const saved = localStorage.getItem(KEY);
  const theme = saved === "dark" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", theme);
})();

function initThemeToggle() {
  const KEY = "latticeTheme";
  const buttons = document.querySelectorAll(".theme-btn");

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(KEY, theme);
    buttons.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === theme);
      btn.setAttribute("aria-pressed", btn.dataset.theme === theme ? "true" : "false");
    });
  }

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => apply(btn.dataset.theme));
  });

  const current = document.documentElement.getAttribute("data-theme") || "light";
  buttons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.theme === current);
    btn.setAttribute("aria-pressed", btn.dataset.theme === current ? "true" : "false");
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initThemeToggle);
} else {
  initThemeToggle();
}
