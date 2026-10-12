/* Progressive enhancements only. Navigation and all content work without JS. */
(() => {
  'use strict';

  const root = document.documentElement;
  const themeButton = document.querySelector('.theme-toggle');
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');

  function syncThemeControl() {
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : systemTheme.matches;
    const label = `Switch to ${dark ? 'light' : 'dark'} theme`;
    themeButton.setAttribute('aria-label', label);
    themeButton.title = label;
    document.querySelectorAll('meta[name="theme-color"]').forEach(meta => {
      meta.content = dark ? '#151e1c' : '#f7f7f2';
    });
  }

  themeButton.hidden = false;
  syncThemeControl();
  themeButton.addEventListener('click', () => {
    const dark = root.dataset.theme ? root.dataset.theme === 'dark' : systemTheme.matches;
    const next = dark ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('hannah-theme', next); } catch { /* Still works for this visit. */ }
    syncThemeControl();
  });
  systemTheme.addEventListener('change', syncThemeControl);
  window.addEventListener('storage', event => {
    if (event.key !== 'hannah-theme' && event.key !== null) return;
    if (event.newValue === 'light' || event.newValue === 'dark') {
      root.dataset.theme = event.newValue;
    } else {
      delete root.dataset.theme;
    }
    syncThemeControl();
  });

  // Native anchors preserve deep links, keyboard behavior, and browser history.
  const navLinks = [...document.querySelectorAll('.navigation a')];
  const sections = navLinks.map(link => document.querySelector(link.getAttribute('href')));
  const header = document.querySelector('.site-header');
  let scheduled = false;

  function updateNavigation() {
    const threshold = header.getBoundingClientRect().height + 100;
    let active = 0;
    sections.forEach((section, index) => {
      if (section.getBoundingClientRect().top <= threshold) active = index;
    });
    if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) {
      active = sections.length - 1;
    }
    navLinks.forEach((link, index) => {
      if (index === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    scheduled = false;
  }

  function scheduleNavigation() {
    if (!scheduled) {
      scheduled = true;
      requestAnimationFrame(updateNavigation);
    }
  }
  window.addEventListener('scroll', scheduleNavigation, { passive: true });
  window.addEventListener('resize', scheduleNavigation, { passive: true });
  window.addEventListener('pageshow', scheduleNavigation);
  window.addEventListener('load', scheduleNavigation);
  updateNavigation();

  // Never hide content in advance; a missing observer cannot hide the page.
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('revealed');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.about-details, .research-card, .current-project, .education, .contact-grid').forEach(element => observer.observe(element));
  }
  // Research figures open larger in a modal lightbox. Without JavaScript the
  // same anchor opens the full-size image directly, so nothing is lost.
  const figureLinks = document.querySelectorAll('.research-image');
  if (figureLinks.length && typeof HTMLDialogElement === 'function') {
    const lightbox = document.createElement('dialog');
    lightbox.className = 'lightbox';
    lightbox.setAttribute('aria-label', 'Expanded image');

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'lightbox-close';
    closeButton.setAttribute('aria-label', 'Close expanded image');
    closeButton.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>';

    const figure = document.createElement('img');
    figure.alt = '';
    const caption = document.createElement('p');
    caption.className = 'lightbox-caption';
    caption.hidden = true;

    lightbox.append(closeButton, figure, caption);
    document.body.append(lightbox);

    figureLinks.forEach(link => {
      link.addEventListener('click', event => {
        // Let modified clicks (new tab, download, etc.) behave natively.
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const thumbnail = link.querySelector('img');
        figure.src = link.getAttribute('href');
        figure.alt = thumbnail ? thumbnail.alt : '';
        const label = link.querySelector('.image-caption');
        caption.textContent = label ? label.textContent.replace(/\s+/g, ' ').trim() : '';
        caption.hidden = !caption.textContent;
        document.body.classList.add('lightbox-open');
        lightbox.showModal();
        event.preventDefault();
      });
    });

    closeButton.addEventListener('click', () => lightbox.close());
    // A click landing on the dialog itself is a click on the backdrop.
    lightbox.addEventListener('click', event => {
      if (event.target === lightbox) lightbox.close();
    });
    lightbox.addEventListener('close', () => {
      document.body.classList.remove('lightbox-open');
      figure.removeAttribute('src');
    });
  }
})();
