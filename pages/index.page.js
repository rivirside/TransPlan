/**
 * Extracted from index.html (#250).
 *
 * Inline <script> blocks force script-src 'unsafe-inline', which removes
 * most of what a Content-Security-Policy is for. Behaviour is unchanged:
 * the file is loaded at the same position the block occupied, so execution
 * order and DOM readiness are the same.
 */
// Editorial carousel
    (function() {
      var carousel = document.querySelector('.hero-pull-carousel');
      if (!carousel) return;
      var stack = carousel.querySelector('.pull-stack');
      var cards = Array.from(carousel.querySelectorAll('.pull-card'));
      var dots = Array.from(carousel.querySelectorAll('.pull-dot'));
      var total = cards.length;
      var current = 0;
      var animating = false;
      var DURATION = 360;

      function sizeCards() {
        cards.forEach(function(c) { c.style.height = 'auto'; });
        var maxH = Math.max.apply(null, cards.map(function(c) { return c.scrollHeight; }));
        cards.forEach(function(c) { c.style.height = maxH + 'px'; });
        stack.style.height = (maxH + 36) + 'px';
      }

      function updateLayers() {
        cards.forEach(function(c) { c.style.transition = 'none'; });
        void stack.offsetWidth;
        cards.forEach(function(card, i) {
          var layer = (i - current + total) % total;
          card.setAttribute('data-layer', Math.min(layer, 3));
          card.style.removeProperty('transform');
          card.style.removeProperty('opacity');
          card.style.removeProperty('z-index');
          card.style.removeProperty('pointer-events');
        });
        void stack.offsetWidth;
        cards.forEach(function(c) { c.style.removeProperty('transition'); });
        dots.forEach(function(dot, i) { dot.classList.toggle('active', i === current); });
      }

      function go(idx, dir) {
        if (animating) return;
        var newIdx = (idx + total) % total;
        if (newIdx === current) return;
        animating = true;
        stack.style.overflow = 'hidden';
        var outCard = cards[current];
        var inCard = cards[newIdx];
        var slideIn = dir === 'next' ? '105%' : '-105%';
        var slideOut = dir === 'next' ? '-105%' : '105%';
        inCard.style.transition = 'none';
        inCard.style.transform = 'translateX(' + slideIn + ')';
        inCard.style.opacity = '1';
        inCard.style.zIndex = '5';
        inCard.style.pointerEvents = 'none';
        void inCard.offsetWidth;
        var t = 'transform ' + DURATION + 'ms cubic-bezier(0.4,0,0.2,1)';
        inCard.style.transition = t;
        inCard.style.transform = 'translateX(0)';
        outCard.style.transition = t;
        outCard.style.transform = 'translateX(' + slideOut + ')';
        outCard.style.zIndex = '4';
        current = newIdx;
        dots.forEach(function(dot, i) { dot.classList.toggle('active', i === current); });
        setTimeout(function() {
          stack.style.overflow = '';
          animating = false;
          updateLayers();
        }, DURATION + 30);
      }

      carousel.querySelector('.carousel-prev').addEventListener('click', function() { go(current - 1, 'prev'); });
      carousel.querySelector('.carousel-next').addEventListener('click', function() { go(current + 1, 'next'); });
      dots.forEach(function(dot, i) {
        dot.addEventListener('click', function() { go(i, i > current ? 'next' : 'prev'); });
      });

      var tx = 0;
      carousel.addEventListener('touchstart', function(e) { tx = e.touches[0].clientX; }, { passive: true });
      carousel.addEventListener('touchend', function(e) {
        var dx = tx - e.changedTouches[0].clientX;
        if (Math.abs(dx) > 40) go(dx > 0 ? current + 1 : current - 1, dx > 0 ? 'next' : 'prev');
      });

      updateLayers();
      sizeCards();
      window.addEventListener('resize', sizeCards);
    })();
