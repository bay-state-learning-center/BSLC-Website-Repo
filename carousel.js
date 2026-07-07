/* =========================================================================
   SHARED CAROUSEL ENGINE
   Drives every .carousel on the page. One carousel can differ from
   another via data attributes on the outer .carousel element:

     data-per-view="3"      how many slides show at once on desktop
                             (default 1 — a single-item carousel, e.g.
                             the how-it-works photo carousel)
     data-mobile-break="640" width (px) below which per-view drops to 1,
                             regardless of data-per-view
     data-autoplay="true"   auto-advance on a timer, pause on hover
                             (default false)
     data-loop="true"       wrap from the last slide back to the first
                             (default false — arrows disable at the ends
                             instead, which is what the testimonial
                             carousel wants so it doesn't need cloned
                             slides for a seamless wrap)

   Markup expected inside .carousel:
     .carousel-track-wrap > .carousel-track > .carousel-slide (one per item)
     .carousel-prev / .carousel-next  (optional)
     .carousel-dots                   (optional — dots are generated here,
                                        since the number of stops depends
                                        on per-view, which can change
                                        between mobile and desktop)
   ========================================================================= */

(function () {

  function initCarousel(carousel) {
    var wrap = carousel.querySelector('.carousel-track-wrap');
    var track = carousel.querySelector('.carousel-track');
    var slides = Array.prototype.slice.call(carousel.querySelectorAll('.carousel-slide'));
    var prevBtn = carousel.querySelector('.carousel-prev');
    var nextBtn = carousel.querySelector('.carousel-next');
    var dotsWrap = carousel.querySelector('.carousel-dots');
    var total = slides.length;
    if (!wrap || !track || !total) return;

    var autoplay = carousel.dataset.autoplay === 'true';
    var loop = carousel.dataset.loop === 'true';
    var desktopPerView = parseInt(carousel.dataset.perView || '1', 10);
    var mobileBreak = parseInt(carousel.dataset.mobileBreak || '640', 10);

    var current = 0;
    var perView = 1;
    var maxIndex = 0;
    var autoTimer;

    function getPerView() {
      return window.innerWidth <= mobileBreak ? 1 : desktopPerView;
    }

    function slideWidth() {
      return wrap.clientWidth / perView;
    }

    function buildDots() {
      if (!dotsWrap) return;
      dotsWrap.innerHTML = '';
      for (var i = 0; i <= maxIndex; i++) {
        var dot = document.createElement('button');
        dot.className = 'carousel-dot';
        dot.setAttribute('aria-label', 'Go to slide ' + (i + 1));
        dot.addEventListener('click', (function (idx) {
          return function () { goTo(idx); resetAuto(); };
        })(i));
        dotsWrap.appendChild(dot);
      }
    }

    function updateControls() {
      if (prevBtn) prevBtn.disabled = !loop && current <= 0;
      if (nextBtn) nextBtn.disabled = !loop && current >= maxIndex;
      if (dotsWrap) {
        Array.prototype.forEach.call(dotsWrap.children, function (dot, i) {
          dot.classList.toggle('active', i === current);
        });
      }
    }

    function goTo(n) {
      current = loop ? (n + total) % total : Math.max(0, Math.min(n, maxIndex));
      track.style.transform = 'translateX(-' + (current * slideWidth()) + 'px)';
      updateControls();
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    function startAuto() {
      if (!autoplay) return;
      autoTimer = setInterval(next, 4500);
    }
    function resetAuto() {
      clearInterval(autoTimer);
      startAuto();
    }

    function layout() {
      var newPerView = getPerView();
      var perViewChanged = newPerView !== perView;
      perView = newPerView;
      maxIndex = Math.max(0, total - perView);
      if (current > maxIndex) current = maxIndex;

      var w = slideWidth();
      slides.forEach(function (slide) {
        slide.style.flex = '0 0 ' + w + 'px';
      });

      if (perViewChanged) buildDots();
      goTo(current);
    }

    if (nextBtn) nextBtn.addEventListener('click', function () { next(); resetAuto(); });
    if (prevBtn) prevBtn.addEventListener('click', function () { prev(); resetAuto(); });

    if (autoplay) {
      carousel.addEventListener('mouseenter', function () { clearInterval(autoTimer); });
      carousel.addEventListener('mouseleave', startAuto);
      // Keyboard users can't trigger mouseenter/mouseleave, so pause on
      // focus too — otherwise slides can advance out from under someone
      // tabbing through the prev/next/dot buttons.
      carousel.addEventListener('focusin', function () { clearInterval(autoTimer); });
      carousel.addEventListener('focusout', function (e) {
        if (!carousel.contains(e.relatedTarget)) startAuto();
      });
    }

    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(layout, 150);
    });

    perView = getPerView();
    maxIndex = Math.max(0, total - perView);
    buildDots();
    layout();
    startAuto();
  }

  document.querySelectorAll('.carousel').forEach(initCarousel);

})();
