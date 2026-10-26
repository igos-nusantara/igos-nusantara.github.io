/* IGN 26 landing page — hero slider, mobile nav, copy buttons. */
(function () {
  "use strict";

  /* ---- Mobile navigation ---- */
  var toggle = document.querySelector(".nav-toggle");
  var links = document.getElementById("nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      var open = links.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
    links.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        links.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---- Hero slider ---- */
  var slider = document.querySelector("[data-slider]");
  if (slider) {
    var slides = Array.prototype.slice.call(
      slider.querySelectorAll(".slider-stage img")
    );
    var thumbs = Array.prototype.slice.call(
      slider.querySelectorAll(".slider-thumbs button")
    );
    var current = slider.querySelector("[data-slide-current]");
    var total = slider.querySelector("[data-slide-total]");
    var label = slider.querySelector("[data-slide-label]");
    var index = 0;
    var timer = null;
    var AUTOPLAY = 6000;

    var reduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function pad(n) {
      return (n < 10 ? "0" : "") + n;
    }

    function show(next) {
      index = (next + slides.length) % slides.length;
      slides.forEach(function (img, i) {
        img.classList.toggle("is-active", i === index);
        // Load the neighbours eagerly so a click never shows a blank frame.
        if (Math.abs(i - index) <= 1 && img.dataset.src) {
          img.src = img.dataset.src;
          delete img.dataset.src;
        }
      });
      thumbs.forEach(function (b, i) {
        b.setAttribute("aria-selected", String(i === index));
      });
      if (current) current.textContent = pad(index + 1);
      if (label) label.textContent = thumbs[index].dataset.label || "";
    }

    function step(delta) {
      show(index + delta);
      restart();
    }

    function restart() {
      if (reduced) return;
      window.clearInterval(timer);
      timer = window.setInterval(function () {
        show(index + 1);
      }, AUTOPLAY);
    }

    slider
      .querySelector(".slider-prev")
      .addEventListener("click", function () {
        step(-1);
      });
    slider
      .querySelector(".slider-next")
      .addEventListener("click", function () {
        step(1);
      });

    thumbs.forEach(function (b, i) {
      b.addEventListener("click", function () {
        show(i);
        restart();
      });
    });

    slider.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        step(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        step(1);
      }
    });

    slider.addEventListener("mouseenter", function () {
      window.clearInterval(timer);
    });
    slider.addEventListener("mouseleave", restart);

    // Touch swipe.
    var startX = null;
    slider.addEventListener(
      "touchstart",
      function (e) {
        startX = e.touches[0].clientX;
      },
      { passive: true }
    );
    slider.addEventListener(
      "touchend",
      function (e) {
        if (startX === null) return;
        var dx = e.changedTouches[0].clientX - startX;
        if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
        startX = null;
      },
      { passive: true }
    );

    if (total) total.textContent = pad(slides.length);
    show(0);
    restart();
  }

  /* ---- Copy buttons ---- */
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = document.getElementById(btn.dataset.copy);
      if (!target || !navigator.clipboard) return;
      var text = Array.prototype.map
        .call(target.querySelectorAll("p"), function (p) {
          return p.textContent.trim();
        })
        .join("\n");
      navigator.clipboard.writeText(text).then(function () {
        var original = btn.textContent;
        btn.textContent = btn.dataset.copied || "Copied";
        window.setTimeout(function () {
          btn.textContent = original;
        }, 1600);
      });
    });
  });
})();

/* ---- Docs sidebar: always open on wide screens, a menu on narrow ones ---- */
(function () {
  var nav = document.querySelector(".docs-nav");
  if (nav && window.matchMedia("(min-width: 961px)").matches) nav.open = true;
})();
