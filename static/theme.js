(() => {
  const root = document.documentElement;
  const preference = window.matchMedia('(prefers-color-scheme: dark)');
  let saved;
  try { saved = localStorage.getItem('uniguide-theme'); } catch {}
  if (!['light', 'dark'].includes(saved)) saved = null;
  function apply(theme) {
    root.dataset.theme = theme;
    const button = document.querySelector('#theme-toggle');
    if (button) {
      const dark = theme === 'dark';
      button.textContent = dark ? '☀ Chế độ sáng' : '☾ Chế độ tối';
      button.setAttribute('aria-label', dark ? 'Chuyển sang chế độ sáng' : 'Chuyển sang chế độ tối');
      button.setAttribute('aria-pressed', String(dark));
    }
  }
  apply(saved || (preference.matches ? 'dark' : 'light'));
  preference.addEventListener('change', event => {
    if (!saved) apply(event.matches ? 'dark' : 'light');
  });
  document.addEventListener('DOMContentLoaded', () => {
    apply(root.dataset.theme);
    document.querySelector('#theme-toggle').addEventListener('click', () => {
      saved = root.dataset.theme === 'dark' ? 'light' : 'dark';
      apply(saved);
      try { localStorage.setItem('uniguide-theme', saved); } catch {}
    });
  });
})();
