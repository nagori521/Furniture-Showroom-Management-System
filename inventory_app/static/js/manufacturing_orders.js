(function () {
  const confirmButtons = document.querySelectorAll("[data-confirm-delivery='true']");

  confirmButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const confirmed = window.confirm("Are you sure you want to receive this delivery?");
      if (!confirmed) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  // Optional: progress bar animation hook (non-blocking)
  const bars = document.querySelectorAll(".js-mfg-progress-bar");
  bars.forEach((bar) => {
    const pct = Number.parseFloat(bar.getAttribute("data-progress") || "0");
    if (!Number.isNaN(pct)) {
      bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    }
  });
})();

