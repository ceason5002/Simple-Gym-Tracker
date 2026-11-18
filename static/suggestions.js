/* Suggested workouts: "Watch how" video sheet, and filling the log form from a planned exercise. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- video sheet ---------- */
  const sheet = $("#video-sheet");
  if (sheet) {
    const list = $("#v-list"), player = $("#v-player"), more = $("#v-search");
    const cache = {};

    function open() {
      if (typeof sheet.showModal === "function") sheet.showModal(); else sheet.setAttribute("open", "");
    }
    function close() {
      sheet.classList.add("is-closing");
      setTimeout(() => {
        sheet.classList.remove("is-closing");
        player.innerHTML = ""; player.hidden = true;        // stops playback
        sheet.close ? sheet.close() : sheet.removeAttribute("open");
      }, reduceMotion ? 0 : 200);
    }
    $$("[data-close-video]").forEach((b) => b.addEventListener("click", close));
    sheet.addEventListener("click", (e) => { if (e.target === sheet) close(); });
    sheet.addEventListener("cancel", (e) => { e.preventDefault(); close(); });

    function play(id, title) {
      // youtube-nocookie: no tracking cookies until the viewer presses play
      player.innerHTML = `<iframe src="https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?autoplay=1&rel=0&playsinline=1&modestbranding=1"
        title="${esc(title)}" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>`;
      player.hidden = false;
      $$(".v-item", list).forEach((b) => b.classList.toggle("is-playing", b.dataset.id === id));
      player.scrollIntoView({ block: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    }

    function render(data) {
      more.href = data.search_url;
      if (!data.videos.length) {
        list.innerHTML = `<div class="v-empty">
            <p>Search YouTube for form tutorials on <b>${esc(data.exercise)}</b>.</p>
            <a class="start-btn" href="${esc(data.search_url)}" target="_blank" rel="noopener">Open YouTube</a>
          </div>`;
        more.hidden = true;
        return;
      }
      more.hidden = false;
      list.innerHTML = data.videos.map((v) => `<button type="button" class="v-item" data-id="${esc(v.id)}" data-title="${esc(v.title)}">
          <span class="v-thumb"><img src="${esc(v.thumb)}" alt="" loading="lazy"><span class="v-play" aria-hidden="true"></span></span>
          <span class="v-text"><span class="v-title">${esc(v.title)}</span><span class="muted v-channel">${esc(v.channel)}</span></span>
        </button>`).join("");
    }

    list.addEventListener("click", (e) => {
      const b = e.target.closest(".v-item");
      if (b) play(b.dataset.id, b.dataset.title);
    });

    async function show(exId, name) {
      $("#v-title").textContent = name;
      player.innerHTML = ""; player.hidden = true;
      list.innerHTML = `<div class="v-skel"></div><div class="v-skel"></div><div class="v-skel"></div>`;
      more.hidden = true;
      open();
      const key = exId || name;
      try {
        if (!cache[key]) {
          const qs = exId ? `ex=${encodeURIComponent(exId)}` : `name=${encodeURIComponent(name)}`;
          const r = await fetch(`${window.SUGGEST.videos}?${qs}`, { credentials: "same-origin" });
          if (!r.ok) throw new Error();
          cache[key] = await r.json();
        }
        render(cache[key]);
      } catch (e) {
        list.innerHTML = `<div class="v-empty"><p>Couldn't load videos right now.</p>
          <a class="start-btn" href="https://www.youtube.com/results?search_query=${encodeURIComponent(name + " proper form tutorial")}" target="_blank" rel="noopener">Search YouTube</a></div>`;
      }
    }

    document.addEventListener("click", (e) => {
      const b = e.target.closest("[data-watch]");
      if (!b) return;
      e.preventDefault();
      show(b.dataset.watch, b.dataset.name);
    });
  }

  /* ---------- workout page: tap a planned exercise to fill the log form ---------- */
  $$("[data-fill]").forEach((b) => b.addEventListener("click", () => {
    const f = JSON.parse(b.dataset.fill);
    const set = (id, v) => { const el = document.getElementById(id); if (el && v !== null && v !== undefined && v !== "") el.value = v; };
    set("f_ex", f.name); set("f_w", f.weight); set("f_s", f.sets);
    const reps = String(f.reps).match(/\d+/g);           // "8-12" -> 8 (the bottom of the range)
    set("f_r", reps ? reps[0] : "");
    const form = $("#log-form");
    form.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" });
    form.classList.remove("flash"); void form.offsetWidth; form.classList.add("flash");
    setTimeout(() => (document.getElementById(f.weight ? "f_r" : "f_w") || {}).focus?.({ preventScroll: true }), reduceMotion ? 0 : 350);
  }));
})();
