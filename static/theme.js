/* Theme settings: Presets / Custom tabs, live whole-page preview of custom colours. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const root = document.documentElement;
  const FIELDS = ["bg", "card", "text", "accent"];
  const HEX = /^#[0-9a-f]{6}$/i;

  /* ---------- tabs ---------- */
  const tabs = $(".t-tabs"), ind = $(".t-tab-ind");
  function moveInd() {
    const t = $(`.t-tab[aria-selected="true"]`);
    if (!t) return;
    ind.style.width = t.offsetWidth + "px";
    ind.style.transform = `translateX(${t.offsetLeft}px)`;
  }
  function selectTab(name) {
    $$(".t-tab").forEach((t) => t.setAttribute("aria-selected", t.dataset.tab === name));
    $$(".t-panel").forEach((p) => (p.hidden = p.dataset.panel !== name));
    moveInd();
    if (name === "custom") applyPreview(); else restorePage();
  }
  $$(".t-tab").forEach((t) => t.addEventListener("click", () => selectTab(t.dataset.tab)));
  addEventListener("resize", moveInd);
  requestAnimationFrame(moveInd);

  /* ---------- colour maths (mirrors tracker/theme.py) ---------- */
  const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const hex = (c) => "#" + c.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
  const mix = (a, b, t) => { const x = rgb(a), y = rgb(b); return hex(x.map((v, i) => v + (y[i] - v) * t)); };
  const lum = (h) => {
    const [r, g, b] = rgb(h).map((c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };

  /* ---------- state ---------- */
  const original = {};   // the page's current (saved) tokens, restored on Reset / leaving the tab
  ["bg", "card", "text", "accent", "muted", "border"].forEach((k) => {
    original[k] = getComputedStyle(root).getPropertyValue("--" + k).trim();
  });
  const current = () => {
    const c = {};
    FIELDS.forEach((f) => (c[f] = $(`[data-hex="${f}"]`).value.trim()));
    return c;
  };

  function applyPreview() {
    if (typeof paint === "function") paint();
    const c = current();
    if (!FIELDS.every((f) => HEX.test(c[f]))) return;
    const tokens = { ...c, muted: mix(c.text, c.bg, 0.38), border: mix(c.bg, c.text, 0.14) };
    Object.entries(tokens).forEach(([k, v]) => root.style.setProperty("--" + k, v));
    const ratio = contrast(c.text, c.bg);
    const badge = $("#contrast"), save = $("#save-custom");
    badge.textContent = `Contrast ${ratio.toFixed(1)}:1 · ${ratio >= 7 ? "Excellent" : ratio >= 4.5 ? "Good" : ratio >= 3 ? "Low" : "Too low"}`;
    badge.dataset.level = ratio >= 4.5 ? "ok" : ratio >= 3 ? "warn" : "bad";
    save.disabled = ratio < 3;
  }
  function restorePage() {
    Object.keys(original).forEach((k) => root.style.removeProperty("--" + k));
  }

  /* ---------- inputs ---------- */
  const paint = () => FIELDS.forEach((f) => {
    const color = $(`[data-color="${f}"]`);
    color.parentElement.style.setProperty("--swatch", color.value);
  });
  FIELDS.forEach((f) => {
    const color = $(`[data-color="${f}"]`), text = $(`[data-hex="${f}"]`);
    if (!HEX.test(text.value)) text.value = color.value;
    color.addEventListener("input", () => { text.value = color.value; text.classList.remove("is-bad"); applyPreview(); });
    text.addEventListener("input", () => {
      let v = text.value.trim();
      if (v && v[0] !== "#") v = "#" + v;
      const ok = HEX.test(v);
      text.classList.toggle("is-bad", !ok && v.length >= 7);
      if (ok) { color.value = v.toLowerCase(); applyPreview(); }
    });
    text.addEventListener("blur", () => {
      let v = text.value.trim();
      if (v && v[0] !== "#") v = "#" + v;
      text.value = HEX.test(v) ? v.toLowerCase() : color.value;
      text.classList.remove("is-bad");
    });
  });

  $$("[data-starter]").forEach((b) => b.addEventListener("click", () => {
    const c = JSON.parse(b.dataset.starter);
    FIELDS.forEach((f) => { $(`[data-hex="${f}"]`).value = c[f]; $(`[data-color="${f}"]`).value = c[f]; });
    $$("[data-starter]").forEach((x) => x.classList.toggle("is-on", x === b));
    applyPreview();
  }));

  const initial = current();
  $("#reset-preview").addEventListener("click", () => {
    FIELDS.forEach((f) => { $(`[data-hex="${f}"]`).value = initial[f]; $(`[data-color="${f}"]`).value = initial[f]; });
    $$("[data-starter]").forEach((x) => x.classList.remove("is-on"));
    applyPreview();
  });

  $("#custom-form").addEventListener("submit", (e) => {
    const c = current();
    if (!FIELDS.every((f) => HEX.test(c[f]))) { e.preventDefault(); return; }
  });

  paint();
  if (tabs.dataset.active === "custom") applyPreview();
})();
