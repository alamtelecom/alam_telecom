/* ==========================================================================
   Alam Telecom — site script
   Sections: mobile nav, scroll-reveal, footer year, EN/HI language toggle
   ========================================================================== */

document.addEventListener('DOMContentLoaded', function () {

  /* --------------------------------------------------------------------
     Mobile nav (hamburger / sidebar)
     -------------------------------------------------------------------- */
  (function initNav() {
    var nav = document.getElementById('siteNav');
    var toggleBtn = document.getElementById('navToggle');
    var closeBtn = document.getElementById('navClose');
    var backdrop = document.getElementById('navBackdrop');

    if (!nav || !toggleBtn || !backdrop) return;

    function openNav() {
      nav.classList.add('open');
      backdrop.classList.add('open');
      toggleBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }

    function closeNav() {
      nav.classList.remove('open');
      backdrop.classList.remove('open');
      toggleBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    toggleBtn.addEventListener('click', openNav);
    if (closeBtn) closeBtn.addEventListener('click', closeNav);
    backdrop.addEventListener('click', closeNav);

    // close automatically when a nav link is clicked (mobile)
    nav.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', closeNav);
    });

    // Esc key closes it
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeNav();
    });

    // Safety net: if the window is resized/rotated back to desktop width
    // while the mobile menu happens to be open, force it closed so it can
    // never sit on top of (or fight with) the desktop nav layout.
    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        if (window.innerWidth > 720) closeNav();
      }, 150);
    });
  })();

  /* --------------------------------------------------------------------
     Scroll-reveal animation for .reveal sections
     -------------------------------------------------------------------- */
  (function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (!items.length) return;

    if (!('IntersectionObserver' in window)) {
      // no IO support — just show everything
      items.forEach(function (el) { el.classList.add('in-view'); });
      return;
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });

    items.forEach(function (el) { io.observe(el); });
  })();

  /* --------------------------------------------------------------------
     Footer year
     -------------------------------------------------------------------- */
  (function initYear() {
    var y = document.getElementById('year');
    if (y) y.textContent = new Date().getFullYear();
  })();

  /* --------------------------------------------------------------------
     EN / HI language toggle
     Any element with a data-en attribute is switchable; data-hi is the
     Hindi text to show. If data-hi is missing, English is used as a
     fallback (safe no-op) so nothing ever ends up blank.
     Preference is remembered per-browser via localStorage.
     -------------------------------------------------------------------- */
  (function initLangToggle() {
    var STORAGE_KEY = 'siteLang';
    var btn = document.getElementById('langToggle');
    var nodes = document.querySelectorAll('[data-en]');

    function applyLang(lang) {
      nodes.forEach(function (el) {
        var text = lang === 'hi'
          ? (el.getAttribute('data-hi') || el.getAttribute('data-en'))
          : el.getAttribute('data-en');
        if (text !== null) el.textContent = text;
      });
      document.documentElement.setAttribute('lang', lang === 'hi' ? 'hi' : 'en');
      if (btn) btn.textContent = lang === 'hi' ? 'English' : 'हिंदी';
      try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) { /* storage blocked, ignore */ }
    }

    if (btn) {
      btn.addEventListener('click', function () {
        var current = document.documentElement.getAttribute('lang') === 'hi' ? 'hi' : 'en';
        applyLang(current === 'hi' ? 'en' : 'hi');
      });
    }

    var saved = 'en';
    try { saved = localStorage.getItem(STORAGE_KEY) || 'en'; } catch (e) { /* ignore */ }
    applyLang(saved);
  })();

});
