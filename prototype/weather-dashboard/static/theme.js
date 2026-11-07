/* Runs before CSS to avoid displaying the opposite theme at startup. */
(function(root) {
  'use strict';
  const valid = theme => theme === 'light' || theme === 'dark';
  function selectTheme(urlTheme, storedTheme, prefersDark) {
    return valid(urlTheme) ? urlTheme : valid(storedTheme) ? storedTheme : prefersDark ? 'dark' : 'light';
  }
  if(typeof module === 'object' && module.exports) { module.exports = {selectTheme}; return; }
  const media = root.matchMedia('(prefers-color-scheme: dark)');
  const urlTheme = new URLSearchParams(root.location.search).get('theme');
  let saved;
  try { saved = root.localStorage.getItem('weather-theme'); } catch (_) { /* Storage may be blocked in WebViews. */ }
  let explicit = valid(urlTheme) || valid(saved);
  function apply(theme) {
    root.document.documentElement.dataset.theme = theme;
    const meta = root.document.querySelector('meta[name="theme-color"]');
    if(meta) meta.content = theme === 'dark' ? '#101b19' : '#f3f4ee';
    const button = root.document.getElementById('theme-toggle');
    if(button) {
      const label = theme === 'dark' ? 'Mode clair' : 'Mode sombre';
      button.textContent = label;
      button.setAttribute('aria-label', 'Activer le ' + label.toLowerCase());
      button.hidden = false;
    }
  }
  apply(selectTheme(urlTheme, saved, media.matches));
  root.document.addEventListener('DOMContentLoaded', () => {
    apply(root.document.documentElement.dataset.theme);
    root.document.getElementById('theme-toggle').addEventListener('click', () => {
      const theme = root.document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      explicit = true;
      try { root.localStorage.setItem('weather-theme', theme); } catch (_) {}
      // Preserve other query parameters and the chosen mode when sharing/reloading.
      const url = new URL(root.location.href);
      url.searchParams.set('theme', theme);
      try { root.history.replaceState(null, '', url); } catch (_) {}
      apply(theme);
    });
  });
  const onChange = e => { if(!explicit) apply(e.matches ? 'dark' : 'light'); };
  if(media.addEventListener) media.addEventListener('change', onChange);
  else if(media.addListener) media.addListener(onChange);
})(typeof window === 'undefined' ? globalThis : window);
