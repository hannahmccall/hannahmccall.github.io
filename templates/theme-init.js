// Apply a saved preference before first paint; system colors work without JavaScript.
(() => {
  try {
    const saved = localStorage.getItem('hannah-theme');
    if (saved === 'light' || saved === 'dark') document.documentElement.dataset.theme = saved;
  } catch { /* Storage may be unavailable in private or restricted contexts. */ }
})();
