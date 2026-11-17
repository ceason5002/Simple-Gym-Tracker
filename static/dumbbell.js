// Revolving 3D cast-iron hex dumbbell for the landing hero.
// Procedural geometry (no model file): chrome knurled handle, collars, beveled hex heads with cast "25 LB" faces.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const easeOutExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));

/* ---------- Procedural textures ---------- */
function canvasTex(size, draw, { repeat = [1, 1], srgb = false } = {}) {
  const c = document.createElement("canvas");
  c.width = c.height = size;
  draw(c.getContext("2d"), size);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...repeat);
  t.anisotropy = 8;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Diamond knurl pattern for the grip
const knurl = () =>
  canvasTex(256, (g, s) => {
    g.fillStyle = "#fff";
    g.fillRect(0, 0, s, s);
    g.strokeStyle = "#000";
    g.lineWidth = 3;
    const step = s / 8;
    for (let i = -s; i < s * 2; i += step) {
      g.beginPath(); g.moveTo(i, 0); g.lineTo(i + s, s); g.stroke();
      g.beginPath(); g.moveTo(i, s); g.lineTo(i + s, 0); g.stroke();
    }
  }, { repeat: [10, 6] });

// Sand-cast speckle for the iron heads (roughness + bump)
const castNoise = () =>
  canvasTex(512, (g, s) => {
    const img = g.createImageData(s, s);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = 150 + Math.random() * 90;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    for (let k = 0; k < 900; k++) {           // pits
      g.fillStyle = `rgba(0,0,0,${0.15 + Math.random() * 0.3})`;
      g.beginPath(); g.arc(Math.random() * s, Math.random() * s, Math.random() * 2.2, 0, 7); g.fill();
    }
  }, { repeat: [2, 2] });

// End face: raised rim + cast weight label (used as bump map, so it reads as relief)
const faceLabel = () => {
  const t = canvasTex(512, (g, s) => {
    g.fillStyle = "#808080";
    g.fillRect(0, 0, s, s);
    g.translate(s / 2, s / 2);
    g.strokeStyle = "#fff";
    g.lineWidth = 10;
    g.beginPath();
    for (let i = 0; i < 6; i++) {
      const a = (Math.PI / 3) * i + Math.PI / 6;
      g[i ? "lineTo" : "moveTo"](Math.cos(a) * s * 0.4, Math.sin(a) * s * 0.4);
    }
    g.closePath(); g.stroke();
    g.fillStyle = "#fff";
    g.textAlign = "center"; g.textBaseline = "middle";
    g.font = `700 ${s * 0.2}px Inter, Arial, sans-serif`;
    g.fillText("25", 0, -s * 0.04);
    g.font = `600 ${s * 0.075}px Inter, Arial, sans-serif`;
    g.fillText("L B", 0, s * 0.12);
  });
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  return t;
};

/* ---------- Model ---------- */
function buildDumbbell() {
  const group = new THREE.Group();
  const halfGrip = 0.62, gripR = 0.085, headR = 0.5, headDepth = 0.44;

  const chrome = new THREE.MeshStandardMaterial({
    color: 0xd9d9dc, metalness: 1, roughness: 0.28,
    bumpMap: knurl(), bumpScale: 1.2,
  });
  const collarMat = new THREE.MeshStandardMaterial({ color: 0xe4e4e6, metalness: 1, roughness: 0.18 });

  const noise = castNoise();
  const iron = new THREE.MeshStandardMaterial({
    color: 0x2b2c2f, metalness: 0.75, roughness: 0.62,
    roughnessMap: noise, bumpMap: noise, bumpScale: 0.6,
  });
  const label = faceLabel();
  label.offset.set(0.5, 0.5);              // extrude cap UVs run -0.5..0.5
  const ironFace = iron.clone();
  label.center.set(0, 0);                  // rotate about the hex centre (uv origin)
  label.rotation = -Math.PI / 6;           // cancel the head's 30° roll so the text sits level
  ironFace.bumpMap = label;
  ironFace.bumpScale = 3;
  ironFace.roughness = 0.5;

  // Grip
  const grip = new THREE.Mesh(new THREE.CylinderGeometry(gripR, gripR, halfGrip * 2 + 0.2, 48, 1), chrome);
  grip.rotation.z = Math.PI / 2;
  group.add(grip);

  // Hex head: beveled extrusion of a hexagon
  const hex = new THREE.Shape();
  const r = headR - 0.05;
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i;
    hex[i ? "lineTo" : "moveTo"](Math.cos(a) * r, Math.sin(a) * r);
  }
  hex.closePath();
  const headGeo = new THREE.ExtrudeGeometry(hex, {
    depth: headDepth - 0.1, bevelEnabled: true, bevelThickness: 0.05, bevelSize: 0.05, bevelSegments: 4, curveSegments: 1,
  });
  headGeo.translate(0, 0, 0.05);           // bevel starts at z=0

  const collarGeo = new THREE.CylinderGeometry(0.15, 0.17, 0.08, 48);
  [1, -1].forEach((side) => {
    const head = new THREE.Mesh(headGeo, [ironFace, iron]);
    head.rotation.y = side * Math.PI / 2;  // +Z (outer cap) points away from the grip
    head.rotation.z = Math.PI / 6;
    head.position.x = side * (halfGrip + 0.08);
    group.add(head);

    const collar = new THREE.Mesh(collarGeo, collarMat);
    collar.rotation.z = side * Math.PI / 2;
    collar.position.x = side * (halfGrip + 0.04);
    group.add(collar);
  });

  return group;
}

/* ---------- Hero controller ---------- */
function dumbbellHero(root) {
  const canvas = root.querySelector(".hero3d__canvas");
  const stage = root.querySelector("[data-stage]");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  let renderer, raf = 0, visible = true, dead = false;

  const fail = () => {
    dead = true; cancelAnimationFrame(raf);
    root.classList.remove("is-ready"); root.classList.add("is-fallback");
  };
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
  } catch (e) { fail(); return; }
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  canvas.addEventListener("webglcontextlost", (e) => { e.preventDefault(); fail(); });

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(3, 4, 5);
  const rim = new THREE.DirectionalLight(0xffffff, 1.4);
  rim.position.set(-4, 1.5, -3);
  scene.add(key, rim);

  const camera = new THREE.PerspectiveCamera(30, 1, 0.05, 100);

  // Rig: pivot (tilt + intro) > spin (revolve + drag) > holder (centre + unit scale) > model
  const pivot = new THREE.Group(), spin = new THREE.Group(), holder = new THREE.Group();
  const model = buildDumbbell();
  const sphere = new THREE.Box3().setFromObject(model).getBoundingSphere(new THREE.Sphere());
  model.position.sub(sphere.center);
  holder.scale.setScalar(1 / sphere.radius);
  holder.add(model); spin.add(holder); pivot.add(spin); scene.add(pivot);
  pivot.rotation.set(0.32, 0, -0.14);

  let baseDist = 10;
  let yaw = reduce.matches ? 0.65 : 0, pitch = 0;
  let vx = 0, vy = 0, dragging = false, last = 0, lastInput = 0;
  const introStart = performance.now();
  const REVOLVE = 0.38;                     // rad/s ambient revolve

  function layout() {
    const W = canvas.clientWidth, H = canvas.clientHeight;
    if (!W || !H) return;
    const narrow = window.innerWidth < 860;
    // Phones: cap pixel density lower; the canvas is small and fill-rate is the bottleneck
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, narrow ? 1.5 : 2));
    renderer.setSize(W, H, false);
    const c = canvas.getBoundingClientRect();
    let s = stage.getBoundingClientRect();
    if (!s.width || !s.height) s = c;
    const sx = s.left - c.left + s.width / 2, sy = s.top - c.top + s.height / 2;
    camera.aspect = W / H;
    camera.setViewOffset(W, H, W / 2 - sx, H / 2 - sy, W, H);
    // On a near-square phone stage the bar's ends would swing past the screen edge when side-on
    const fitPx = (narrow ? 0.86 : 1.08) * Math.min(s.width, s.height);
    baseDist = H / (fitPx * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    camera.position.set(0, 0, baseDist);
    camera.updateProjectionMatrix();
    wake();
  }

  function tick(now) {
    raf = 0;
    const dt = Math.min(0.05, Math.max(0, (now - last) / 1000)); last = now;
    const rm = reduce.matches;
    if (!dragging) {
      if (rm) { vx = vy = 0; }
      else {
        // inertia blends back into the steady revolve
        const k = Math.exp(-3 * dt);
        vx = REVOLVE + (vx - REVOLVE) * k;
        vy *= k;
        pitch += (0 - pitch) * (1 - Math.exp(-dt * 1.5));   // settle back to the base tilt
      }
      yaw += vx * dt;
      pitch = clamp(pitch + vy * dt, -0.7, 0.7);
    }
    spin.rotation.set(pitch, yaw, 0, "XYZ");

    const intro = rm ? 1 : easeOutExpo(Math.min(1, (now - introStart) / 1800));
    pivot.position.y = rm ? 0 : 0.03 * Math.sin(now / 1000 * 1.1);
    pivot.scale.setScalar(0.88 + 0.12 * intro);
    spin.rotation.y = yaw + (1 - intro) * -1.4;

    renderer.render(scene, camera);
    if (visible && !dead && (!rm || dragging || intro < 1)) raf = requestAnimationFrame(tick);
  }
  function wake() { if (!raf && visible && !dead) { last = performance.now(); raf = requestAnimationFrame(tick); } }

  // Drag to spin
  // Touch only grabs the dumbbell once the finger clearly moves sideways, so a vertical
  // page scroll that starts on it doesn't freeze the spin and snap it back.
  let lastX = 0, lastY = 0, lastT = 0, pending = null;
  const grab = (e) => {
    dragging = true; vx = vy = 0; pending = null;
    lastX = e.clientX; lastY = e.clientY; lastT = e.timeStamp;
    wake();
  };
  stage.addEventListener("pointerdown", (e) => {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    if (e.pointerType === "touch") { pending = { id: e.pointerId, x: e.clientX, y: e.clientY }; return; }
    stage.setPointerCapture(e.pointerId);
    grab(e);
  });
  stage.addEventListener("pointermove", (e) => {
    if (pending && e.pointerId === pending.id) {
      const mx = Math.abs(e.clientX - pending.x), my = Math.abs(e.clientY - pending.y);
      if (mx > 8 && mx > my * 1.2) { stage.setPointerCapture(e.pointerId); grab(e); }
      else if (my > 8) pending = null;        // vertical: let the page scroll
      return;
    }
    if (!dragging) return;
    const dx = e.clientX - lastX, dy = e.clientY - lastY, dms = Math.max(1, e.timeStamp - lastT);
    lastX = e.clientX; lastY = e.clientY; lastT = e.timeStamp;
    const ax = dx * 0.008, ay = e.pointerType === "touch" ? 0 : dy * 0.005;
    yaw += ax; pitch = clamp(pitch + ay, -0.7, 0.7);
    vx = 0.75 * vx + 0.25 * (ax / dms) * 1000;
    vy = 0.75 * vy + 0.25 * (ay / dms) * 1000;
    wake();
  });
  const release = (e) => {
    pending = null;
    if (!dragging) return;
    dragging = false;
    if (e.type === "pointercancel" || e.timeStamp - lastT > 90) { vx = REVOLVE; vy = 0; }
    vx = clamp(vx, -14, 14); vy = clamp(vy, -6, 6);
    wake();
  };
  stage.addEventListener("pointerup", release);
  stage.addEventListener("pointercancel", release);
  stage.addEventListener("keydown", (e) => {
    const turns = { ArrowLeft: [-0.3, 0], ArrowRight: [0.3, 0], ArrowUp: [0, -0.2], ArrowDown: [0, 0.2] };
    if (!turns[e.key]) return;
    e.preventDefault();
    yaw += turns[e.key][0]; pitch = clamp(pitch + turns[e.key][1], -0.7, 0.7);
    wake();
  });

  new ResizeObserver(layout).observe(canvas);
  new ResizeObserver(layout).observe(stage);
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; if (visible) wake(); }).observe(root);
  reduce.addEventListener("change", wake);
  document.fonts?.ready.then(layout);

  layout();
  const reveal = () => { if (!dead) { root.classList.add("is-ready"); wake(); } };
  renderer.compileAsync ? renderer.compileAsync(scene, camera).then(reveal, reveal) : reveal();
}

const el = document.querySelector(".hero3d");
if (el) dumbbellHero(el);
