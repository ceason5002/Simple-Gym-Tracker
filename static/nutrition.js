/* NutrientAI dashboard: rings, food log, add-food sheet (search / barcode scan / saved / manual), water. */
(function () {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const API = window.NUTRI.api;
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let day = JSON.parse($("#day-data").textContent);
  let saved = JSON.parse($("#saved-data").textContent);

  /* ---------- utils ---------- */
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (n, d = 0) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: 0 });
  const csrf = () => (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";

  async function api(url, body) {
    const opts = body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf()) },
      body: JSON.stringify(body),
    };
    const r = await fetch(url, { credentials: "same-origin", ...opts });
    let data = {};
    try { data = await r.json(); } catch (e) { /* non-JSON error page */ }
    if (!r.ok) throw Object.assign(new Error(data.error || "Something went wrong. Try again."), { status: r.status, data });
    return data;
  }

  let toastTimer;
  function toast(msg, isError) {
    const t = $("#toast");
    t.textContent = msg;
    t.classList.toggle("is-error", !!isError);
    t.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("is-on"), 2600);
  }

  /* ---------- rings ---------- */
  const METRICS = {
    calories: { total: () => day.totals.calories, goal: () => day.targets.calories, unit: "kcal" },
    protein: { total: () => day.totals.protein, goal: () => day.targets.protein, unit: "g" },
    carbs: { total: () => day.totals.carbs, goal: () => day.targets.carbs, unit: "g" },
    fat: { total: () => day.totals.fat, goal: () => day.targets.fat, unit: "g" },
    water: { total: () => day.water_oz, goal: () => day.targets.water_oz, unit: "oz" },
  };
  const modes = store.get("nutri-modes", {});
  const shown = {};   // last displayed number per metric, for count-up animation

  function countTo(el, from, to) {
    if (reduceMotion || from === to) { el.textContent = fmt(to); return; }
    const start = performance.now(), dur = 650;
    const step = (now) => {
      const t = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - t, 3);
      el.textContent = fmt(from + (to - from) * e);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function renderRing(card) {
    const key = card.dataset.metric, m = METRICS[key];
    const total = m.total(), goal = Math.max(1, m.goal());
    const remaining = goal - total, over = remaining < 0;
    const mode = modes[key] === "remaining" ? "remaining" : "consumed";
    const value = mode === "remaining" ? Math.abs(Math.round(remaining)) : Math.round(total);

    const bar = $(".bar", card), r = +bar.getAttribute("r"), C = 2 * Math.PI * r;
    bar.style.strokeDasharray = C;
    bar.style.strokeDashoffset = C * (1 - Math.min(1, total / goal));
    card.classList.toggle("is-over", over);
    card.setAttribute("aria-pressed", mode === "remaining");

    const valueEl = $("[data-value]", card);
    countTo(valueEl, shown[key] ?? 0, value);
    shown[key] = value;
    $("[data-mode]", card).textContent = mode === "remaining" ? (over ? "over goal" : "remaining") : "consumed";
    $("[data-of]", card).textContent = mode === "remaining"
      ? `${fmt(total)} of ${fmt(goal)} ${m.unit}`
      : `of ${fmt(goal)} ${m.unit}`;
    card.setAttribute("aria-label",
      `${key}: ${fmt(total)} of ${fmt(goal)} ${m.unit} consumed, ${over ? fmt(-remaining) + " over" : fmt(remaining) + " remaining"}. Tap to switch.`);
  }

  function renderRings() { $$("[data-metric]").forEach(renderRing); }

  $$("[data-metric]").forEach((card) => card.addEventListener("click", () => {
    const key = card.dataset.metric;
    modes[key] = modes[key] === "remaining" ? "consumed" : "remaining";
    store.set("nutri-modes", modes);
    card.classList.remove("flip"); void card.offsetWidth; card.classList.add("flip");
    shown[key] = 0;
    renderRing(card);
  }));

  /* ---------- log ---------- */
  const MEAL_LABELS = { breakfast: "Breakfast", lunch: "Lunch", dinner: "Dinner", snack: "Snacks" };
  function renderLog() {
    const body = $("#log-body");
    if (!day.entries.length) {
      body.innerHTML = `<div class="empty muted">Nothing logged ${day.is_today ? "yet today" : "on this day"}. Tap <b>+ Add food</b> to search, scan a barcode, or pick a saved food.</div>`;
      return;
    }
    body.innerHTML = Object.keys(MEAL_LABELS).map((meal) => {
      const items = day.entries.filter((e) => e.meal === meal);
      if (!items.length) return "";
      const kcal = items.reduce((a, e) => a + e.calories, 0);
      return `<div class="meal">
        <div class="meal-head"><span>${MEAL_LABELS[meal]}</span><span class="muted">${fmt(kcal)} kcal</span></div>
        ${items.map((e) => `<div class="entry">
          <div class="entry-main">
            <span class="entry-name">${esc(e.name)}</span>
            <span class="entry-sub muted">${esc(e.brand ? e.brand + " · " : "")}${fmt(e.servings, 2)} × ${esc(e.serving_desc)}</span>
          </div>
          <div class="entry-macros"><b>${fmt(e.calories)}</b><span class="muted">P ${fmt(e.protein)} · C ${fmt(e.carbs)} · F ${fmt(e.fat)}</span></div>
          <button class="n-icon entry-del" data-del="${e.id}" aria-label="Remove ${esc(e.name)}">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 4.5h10M6.5 4.5V3h3v1.5M5 4.5l.6 8.5h4.8l.6-8.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>`).join("")}
      </div>`;
    }).join("");
  }

  $("#log-body").addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-del]");
    if (!btn) return;
    btn.disabled = true;
    try {
      day = await api(`${API.log}${btn.dataset.del}/delete/`, {});
      render();
      toast("Removed from log");
    } catch (e) { btn.disabled = false; toast(e.message, true); }
  });

  function render() {
    $("#day-label").textContent = day.label;
    $("#profile-nudge").hidden = day.targets.complete;
    $('[data-shift="1"]').disabled = day.is_today;
    renderRings();
    renderLog();
  }

  /* ---------- date navigation ---------- */
  $$("[data-shift]").forEach((b) => b.addEventListener("click", async () => {
    const d = new Date(day.date + "T12:00:00");
    d.setDate(d.getDate() + Number(b.dataset.shift));
    const iso = d.toISOString().slice(0, 10);
    try {
      day = await api(`${API.day}?d=${iso}`);
      $$("[data-metric]").forEach((c) => (shown[c.dataset.metric] = 0));
      render();
      history.replaceState(null, "", day.is_today ? API.page : `${API.page}?d=${day.date}`);
    } catch (e) { toast(e.message, true); }
  }));

  /* ---------- water ---------- */
  $$("[data-water]").forEach((b) => b.addEventListener("click", async () => {
    let oz = b.dataset.water;
    if (oz === "custom") {
      oz = prompt("How many ounces?", "12");
      if (oz === null) return;
      oz = parseFloat(oz);
      if (!(oz > 0 && oz <= 200)) { toast("Enter an amount between 0.5 and 200 oz", true); return; }
    }
    try {
      day = await api(API.water, { date: day.date, oz: Number(oz) });
      renderRings();
      toast(`+${fmt(oz, 1)} oz water`);
    } catch (e) { toast(e.message, true); }
  }));
  $("[data-water-undo]").addEventListener("click", async () => {
    try { day = await api(API.waterUndo, { date: day.date }); renderRings(); toast("Last water entry removed"); }
    catch (e) { toast(e.message, true); }
  });

  /* ---------- sheet ---------- */
  const sheet = $("#sheet");
  function openSheet() {
    showView("pick");
    if (typeof sheet.showModal === "function") sheet.showModal(); else sheet.setAttribute("open", "");
    requestAnimationFrame(() => { positionTabInd(); if (activeTab === "search") $("#search-input").focus(); });
  }
  function closeSheet() {
    stopScan();
    sheet.classList.add("is-closing");
    setTimeout(() => { sheet.classList.remove("is-closing"); sheet.close ? sheet.close() : sheet.removeAttribute("open"); }, reduceMotion ? 0 : 220);
  }
  $$("[data-open-sheet]").forEach((b) => b.addEventListener("click", openSheet));
  $("[data-close-sheet]").addEventListener("click", closeSheet);
  sheet.addEventListener("click", (e) => { if (e.target === sheet) closeSheet(); });
  sheet.addEventListener("cancel", (e) => { e.preventDefault(); closeSheet(); });

  function showView(name) {
    $$("[data-view]", sheet).forEach((v) => (v.hidden = v.dataset.view !== name));
    $("#sheet-title").textContent = name === "detail" ? "Log food" : "Add food";
    if (name !== "pick") stopScan();
  }
  $("[data-back]").addEventListener("click", () => { showView("pick"); requestAnimationFrame(positionTabInd); });

  /* tabs with sliding indicator */
  let activeTab = "search";
  function positionTabInd() {
    const t = $(`.tab[data-tab="${activeTab}"]`), ind = $(".tab-ind");
    if (!t || !t.offsetWidth) return;
    ind.style.width = t.offsetWidth + "px";
    ind.style.transform = `translateX(${t.offsetLeft}px)`;
  }
  function selectTab(name) {
    activeTab = name;
    $$(".tab").forEach((t) => t.setAttribute("aria-selected", t.dataset.tab === name));
    $$(".tab-panel").forEach((p) => (p.hidden = p.dataset.panel !== name));
    positionTabInd();
    if (name !== "scan") stopScan();
    if (name === "saved") renderSaved();
    if (name === "search") $("#search-input").focus();
  }
  $$(".tab").forEach((t) => t.addEventListener("click", () => selectTab(t.dataset.tab)));
  addEventListener("resize", positionTabInd);

  /* result rows */
  const foodRow = (f, i, kind) => `<button class="result" data-kind="${kind}" data-i="${i}">
      <span class="result-main"><span class="result-name">${esc(f.name)}</span>
      <span class="muted result-sub">${esc(f.brand ? f.brand + " · " : "")}${esc(f.serving_desc)}</span></span>
      <span class="result-kcal"><b>${fmt(f.calories)}</b><span class="muted">kcal</span></span>
    </button>`;

  /* search */
  let searchResults = [], searchSaved = [], searchSeq = 0, searchTimer;
  $("#search-input").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    const q = e.target.value.trim();
    const box = $("#search-results");
    if (q.length < 2) { box.innerHTML = ""; return; }
    box.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>`;
    searchTimer = setTimeout(() => runSearch(q), 350);
  });
  async function runSearch(q) {
    const seq = ++searchSeq, box = $("#search-results");
    try {
      const data = await api(`${API.search}?q=${encodeURIComponent(q)}`);
      if (seq !== searchSeq) return;
      searchResults = data.results; searchSaved = data.saved;
      renderSearch();
    } catch (e) {
      if (seq !== searchSeq) return;
      searchResults = []; searchSaved = (e.data && e.data.saved) || [];
      renderSearch(e.message);
    }
  }
  function renderSearch(error) {
    const box = $("#search-results");
    let html = "";
    if (searchSaved.length) html += `<div class="results-label">Your foods</div>` + searchSaved.map((f, i) => foodRow(f, i, "ssaved")).join("");
    if (searchResults.length) html += `<div class="results-label">Database</div>` + searchResults.map((f, i) => foodRow(f, i, "search")).join("");
    if (error) html += `<div class="empty muted">${esc(error)}</div>`;
    else if (!html) html = `<div class="empty muted">No foods found. Try fewer words, or add it under <b>Manual</b>.</div>`;
    box.innerHTML = html;
  }
  $("#search-results").addEventListener("click", (e) => {
    const r = e.target.closest(".result");
    if (r) openDetail(r.dataset.kind === "ssaved" ? searchSaved[+r.dataset.i] : searchResults[+r.dataset.i]);
  });

  /* saved list */
  function renderSaved() {
    const box = $("#saved-list");
    box.innerHTML = saved.length ? saved.map((f, i) => foodRow(f, i, "saved")).join("")
      : `<div class="empty muted">No saved foods yet. Tap the star on any food to save it here.</div>`;
  }
  $("#saved-list").addEventListener("click", (e) => {
    const r = e.target.closest(".result");
    if (r) openDetail(saved[+r.dataset.i]);
  });

  /* manual */
  $("#manual-form").addEventListener("submit", (e) => {
    e.preventDefault();
    openDetail({
      name: $("#m-name").value.trim(), brand: "", barcode: "", serving_desc: $("#m-serving").value.trim() || "1 serving",
      calories: +$("#m-cal").value || 0, protein: +$("#m-p").value || 0, carbs: +$("#m-c").value || 0, fat: +$("#m-f").value || 0,
      source: "manual", source_id: "",
    });
  });

  /* ---------- barcode scanning ---------- */
  let stream = null, scanLoop = 0, zxingReader = null, lookingUp = false;
  const video = $("#scan-video");
  const setScanStatus = (t) => ($("#scan-status").textContent = t);

  function loadScript(src) {
    return new Promise((res, rej) => {
      const s = document.createElement("script");
      s.src = src; s.onload = res; s.onerror = () => rej(new Error("Scanner library failed to load"));
      document.head.appendChild(s);
    });
  }

  async function startScan() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setScanStatus("Camera isn't available here (it needs HTTPS). Type the barcode below instead.");
      return;
    }
    $("#scan-idle").hidden = true;
    sheet.classList.add("is-scanning");
    setScanStatus("Starting camera…");
    try {
      const native = "BarcodeDetector" in window &&
        (await BarcodeDetector.getSupportedFormats()).some((f) => f === "ean_13" || f === "upc_a");
      if (native) {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
        video.srcObject = stream;
        await video.play();
        const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e"] });
        setScanStatus("Point your camera at a barcode.");
        const tick = async () => {
          if (!stream) return;
          try {
            const codes = await detector.detect(video);
            if (codes.length) { onCode(codes[0].rawValue); return; }
          } catch (e) { /* frame not ready */ }
          scanLoop = setTimeout(tick, 180);
        };
        tick();
      } else {
        if (!window.ZXing) await loadScript(window.NUTRI.zxing);
        const hints = new Map();
        hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [ZXing.BarcodeFormat.EAN_13, ZXing.BarcodeFormat.EAN_8, ZXing.BarcodeFormat.UPC_A, ZXing.BarcodeFormat.UPC_E]);
        zxingReader = new ZXing.BrowserMultiFormatReader(hints);
        setScanStatus("Point your camera at a barcode.");
        await zxingReader.decodeFromConstraints({ video: { facingMode: { ideal: "environment" } } }, video, (result) => {
          if (result) onCode(result.getText());
        });
      }
    } catch (e) {
      stopScan();
      setScanStatus(e && e.name === "NotAllowedError"
        ? "Camera permission was blocked. Allow it in your browser settings, or type the barcode below."
        : "Couldn't start the camera. Type the barcode below instead.");
    }
  }

  function stopScan() {
    clearTimeout(scanLoop);
    if (zxingReader) { try { zxingReader.reset(); } catch (e) { /* already stopped */ } zxingReader = null; }
    if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
    video.srcObject = null;
    sheet.classList.remove("is-scanning");
    $("#scan-idle").hidden = false;
  }

  async function onCode(code) {
    if (lookingUp) return;
    code = String(code).replace(/\D/g, "");
    stopScan();
    if (navigator.vibrate) navigator.vibrate(30);
    await lookupBarcode(code);
  }

  async function lookupBarcode(code) {
    if (!/^\d{6,14}$/.test(code)) { setScanStatus("Barcodes are 6 to 14 digits."); return; }
    lookingUp = true;
    setScanStatus(`Looking up ${code}…`);
    try {
      const data = await api(API.barcode + code + "/");
      setScanStatus("Point your camera at a barcode.");
      openDetail(data.food);
    } catch (e) {
      setScanStatus(e.message);
    } finally { lookingUp = false; }
  }

  $("#scan-start").addEventListener("click", startScan);
  $("#barcode-form").addEventListener("submit", (e) => { e.preventDefault(); lookupBarcode($("#barcode-input").value.trim()); });

  /* ---------- detail ---------- */
  let current = null, unit = "serv";
  const gramsIn = (desc) => {
    const m = /(\d+(?:\.\d+)?)\s*(g|ml)\b/i.exec(desc || "");
    return m ? parseFloat(m[1]) : null;
  };
  const defaultMeal = () => {
    const h = new Date().getHours();
    return h < 11 ? "breakfast" : h < 15 ? "lunch" : h < 21 ? "dinner" : "snack";
  };
  const isSaved = (f) => f.source === "saved" || saved.some((s) => s.name === f.name && s.brand === f.brand && s.serving_desc === f.serving_desc);

  function openDetail(food) {
    if (!food) return;
    current = food;
    const g = gramsIn(food.serving_desc);
    unit = "serv";
    $("#d-name").textContent = food.name;
    $("#d-sub").textContent = [food.brand, food.source === "off" ? "Open Food Facts" : food.source === "usda" ? "USDA" : food.source === "saved" ? "Saved food" : "Manual"].filter(Boolean).join(" · ");
    $("#d-amount").value = 1;
    $("#d-unit").hidden = !g;
    $$("#d-unit [data-unit]").forEach((b) => b.setAttribute("aria-checked", b.dataset.unit === "serv"));
    $("#d-meal").value = defaultMeal();
    const sv = isSaved(food);
    $("#d-save").setAttribute("aria-pressed", sv);
    $("#d-save").disabled = food.source === "saved";
    showView("detail");
    updatePreview();
    $("#d-amount").focus();
  }

  function servings() {
    const v = parseFloat($("#d-amount").value);
    if (!(v > 0)) return 0;
    if (unit === "g") { const g = gramsIn(current.serving_desc); return g ? v / g : 0; }
    return v;
  }
  function updatePreview() {
    const s = servings();
    $("#d-cal").textContent = fmt(current.calories * s);
    $("#d-p").textContent = fmt(current.protein * s, 1) + "g";
    $("#d-c").textContent = fmt(current.carbs * s, 1) + "g";
    $("#d-f").textContent = fmt(current.fat * s, 1) + "g";
    const g = gramsIn(current.serving_desc);
    $("#d-serving").textContent = unit === "g"
      ? `${fmt(s, 2)} × ${current.serving_desc}`
      : `1 serving = ${current.serving_desc}${g && s ? ` · ${fmt(g * s)} ${/ml/i.test(current.serving_desc) ? "ml" : "g"} total` : ""}`;
    $("#d-add").disabled = !(s > 0);
  }
  $("#d-amount").addEventListener("input", updatePreview);
  $$("[data-step]").forEach((b) => b.addEventListener("click", () => {
    const inp = $("#d-amount"), step = unit === "g" ? 10 : 0.5;
    inp.value = Math.max(unit === "g" ? 1 : 0.25, +(parseFloat(inp.value || 0) + step * Number(b.dataset.step)).toFixed(2));
    updatePreview();
  }));
  $$("#d-unit [data-unit]").forEach((b) => b.addEventListener("click", () => {
    if (b.dataset.unit === unit) return;
    const s = servings(), g = gramsIn(current.serving_desc);
    unit = b.dataset.unit;
    $$("#d-unit [data-unit]").forEach((x) => x.setAttribute("aria-checked", x.dataset.unit === unit));
    $("#d-amount").step = unit === "g" ? 1 : 0.25;
    $("#d-amount").value = unit === "g" ? Math.round(s * g) : +s.toFixed(2);
    updatePreview();
  }));

  $("#d-save").addEventListener("click", async () => {
    if (isSaved(current)) { toast("Already in your saved foods"); return; }
    try {
      const data = await api(API.saved, { food: current });
      saved.push(data.food);
      saved.sort((a, b) => a.name.localeCompare(b.name));
      $("#d-save").setAttribute("aria-pressed", "true");
      toast("Saved to your foods");
    } catch (e) { toast(e.message, true); }
  });

  $("#d-add").addEventListener("click", async () => {
    const btn = $("#d-add");
    btn.disabled = true;
    try {
      day = await api(API.log, { date: day.date, meal: $("#d-meal").value, servings: +servings().toFixed(4), food: current });
      closeSheet();
      render();
      toast(`Added ${current.name}`);
    } catch (e) { toast(e.message, true); }
    finally { btn.disabled = false; }
  });

  /* floating + appears once the header (with its Add button) scrolls away */
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([en]) => document.body.classList.toggle("fab-on", !en.isIntersecting)).observe($(".n-head"));
  } else document.body.classList.add("fab-on");

  render();
})();
