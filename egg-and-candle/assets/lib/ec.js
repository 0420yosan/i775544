/* Shared animation kit for "an egg & a candle".
 *
 * Every page composition calls  const K = EC.kit(tl, { page, ART, PANELS, WASH })
 * and builds its scenes with K.actor / K.bubble / K.label / K.buildPage and
 * choreographs them with the motion helpers below. Everything is plain GSAP
 * property tweens on the page's one paused timeline (the renderer seeks with
 * events suppressed, so no onUpdate drawing), and all "randomness" is seeded.
 */
window.EC = (function () {
  const INK = "#2b1d17";
  const SVGNS = "http://www.w3.org/2000/svg";

  function rng(seed) {
    let a = seed >>> 0;
    return () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function el(tag, cls, parent, css) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (css) n.style.cssText = css;
    // light pools, backdrops and the page sheet overhang their parents on purpose
    if (cls && /\b(glow|abs|sheet|blank)\b/.test(cls)) n.setAttribute("data-layout-allow-overflow", "");
    if (parent) parent.appendChild(n);
    return n;
  }
  function img(src, cls, parent, css) {
    const n = el("img", cls, parent, css);
    n.src = src;
    n.alt = "";
    return n;
  }
  function svg(parent, w, h, css, inner) {
    const s = document.createElementNS(SVGNS, "svg");
    s.setAttribute("width", w);
    s.setAttribute("height", h);
    s.setAttribute("viewBox", `0 0 ${w} ${h}`);
    s.style.cssText = "position:absolute;overflow:visible;" + (css || "");
    s.innerHTML = inner;
    parent.appendChild(s);
    return s;
  }
  const SHAPES = {
    heart: '<path d="M30 52 C 8 36 2 22 10 12 C 18 2 28 8 30 16 C 32 8 42 2 50 12 C 58 22 52 36 30 52 Z" fill="#ff7f96" stroke="#2b1d17" stroke-width="4" stroke-linejoin="round"/><path d="M16 17 q 3 -5 8 -4" stroke="#ffd0da" stroke-width="4" fill="none" stroke-linecap="round"/>',
    star: '<path d="M30 4 L36 24 L56 30 L36 36 L30 56 L24 36 L4 30 L24 24 Z" fill="#ffd66b" stroke="#2b1d17" stroke-width="3.5" stroke-linejoin="round"/>',
    tear: '<path d="M15 2 C 15 2 4 18 4 26 C 4 33 9 38 15 38 C 21 38 26 33 26 26 C 26 18 15 2 15 2 Z" fill="#9fd0f2" stroke="#2b1d17" stroke-width="3" stroke-linejoin="round"/><path d="M10 26 q 0 5 4 7" stroke="#e6f5ff" stroke-width="3" fill="none" stroke-linecap="round"/>',
    sparkle: '<path d="M30 6 L34 26 L54 30 L34 34 L30 54 L26 34 L6 30 L26 26 Z" fill="#ffffff" stroke="#bcd6ea" stroke-width="3"/>',
  };
  // smooth hill silhouette as an SVG path (seeded)
  function ridge(w, y0, amp, seg, seed, x0 = -400, bottom = 1500) {
    const q = rng(seed);
    let d = `M${x0} ${bottom} L${x0} ${y0}`;
    for (let x = x0; x < w; x += seg) d += ` Q ${x + seg / 2} ${y0 - amp * (0.4 + q())} ${x + seg} ${y0 + amp * 0.25 * (q() - 0.5)}`;
    return d + ` L${w} ${bottom} Z`;
  }
  function pine(x, y, h, c, cap = "#f7fafc") {
    return `<g transform="translate(${x} ${y})"><path d="M0 ${-h} L${h * 0.32} ${-h * 0.45} L${h * 0.2} ${-h * 0.45} L${h * 0.42} 0 L${-h * 0.42} 0 L${-h * 0.2} ${-h * 0.45} L${-h * 0.32} ${-h * 0.45} Z" fill="${c}"/><path d="M0 ${-h} L${h * 0.14} ${-h * 0.75} L0 ${-h * 0.8} L${-h * 0.14} ${-h * 0.75} Z" fill="${cap}"/></g>`;
  }

  function kit(tl, cfg) {
    const { page, ART, PANELS, WASH } = cfg;
    const SRC = (id) => `assets/art/p${page}/${id}.svg`;

    // ------------------------------------------------------------ builders
    // actor: position (bottom-centre anchor) > hopper (jumps) > rig (squash/lean) > breath (idle)
    function actor(parent, id, art, k, x, y, opt = {}) {
      const a = ART[art];
      const [x0, y0, x1, y1] = a.b;
      const W = (x1 - x0) * k, H = (y1 - y0) * k;
      const root = el("div", "actor", parent, `left:${x - W / 2}px;top:${y - H}px;width:${W}px;height:${H}px`);
      root.id = id;
      if (opt.shadow !== false) el("div", "shadow", root);
      const hopper = el("div", "hopper", root);
      const rig = el("div", "rig", hopper);
      const breath = el("div", "breath", rig);
      const parts = {};
      let glow = null;
      if (a.p && a.p.flame) {
        const [fx0, fy0, fx1, fy1] = a.p.flame.b;
        const cx = ((fx0 + fx1) / 2 - x0) * k, cy = ((fy0 + fy1) / 2 - y0) * k, r = (opt.glow || 150) * (k / 2.5);
        glow = el("div", "glow", breath, `left:${cx - r}px;top:${cy - r}px;width:${2 * r}px;height:${2 * r}px;background:radial-gradient(circle, rgba(255,214,120,0.95) 0%, rgba(255,170,80,0.45) 32%, rgba(255,150,70,0) 70%)`);
      }
      img(SRC(art), "spr", breath);
      for (const [name, pa] of Object.entries(a.p || {})) {
        const [px0, py0, px1, py1] = pa.b;
        const pv = pa.pv || [(px0 + px1) / 2, py1];
        const ox = (pv[0] - px0) * k, oy = (pv[1] - py0) * k;
        const css = `left:${(px0 - x0) * k}px;top:${(py0 - y0) * k}px;width:${(px1 - px0) * k}px;height:${(py1 - py0) * k}px;transform-origin:${ox}px ${oy}px`;
        if (name === "flame") {
          // wrapper takes flares / dimming, inner image takes the constant flicker
          const wrap = el("div", "part", breath, css);
          parts.flame = img(SRC(`${art}--${name}`), "spr", wrap, `transform-origin:${ox}px ${oy}px`);
          parts.flameWrap = wrap;
        } else {
          parts[name] = img(SRC(`${art}--${name}`), "part", breath, css);
        }
      }
      if (opt.hidden) root.style.opacity = "0";
      return { root, hopper, rig, breath, parts, glow, W, H, k, art };
    }
    // local point (page px of the art) -> actor-local px, for attaching effects to a drawing's feature
    function at(a, px, py) {
      const [x0, y0] = ART[a.art].b;
      return [(px - x0) * a.k, (py - y0) * a.k];
    }
    function sprite(parent, cls, id, art, k, x, y) {
      const [x0, y0, x1, y1] = ART[art].b;
      const W = (x1 - x0) * k, H = (y1 - y0) * k;
      const root = el("div", cls, parent, `left:${x}px;top:${y}px;width:${W}px;height:${H}px`);
      root.id = id;
      return { root, W, H };
    }
    function bubble(parent, id, art, k, x, y, origin) {
      const b = sprite(parent, "bubble", id, art, k, x, y);
      b.root.style.transformOrigin = origin || "20% 100%";
      b.root.style.opacity = "0";
      img(SRC(art), "spr", b.root);
      return b.root;
    }
    function label(parent, id, art, k, x, y) {
      const b = sprite(parent, "label", id, art, k, x, y);
      b.root.style.opacity = "0";
      el("div", "card", b.root);
      img(SRC(art), "spr", b.root);
      const tape = el("div", "tape", b.root);
      return { root: b.root, tape };
    }
    // lettering / props drawn as plain sprites (no card), top-left placed
    function art(parent, id, name, k, x, y, css) {
      const b = sprite(parent, "abs", id, name, k, x, y);
      if (css) b.root.style.cssText += ";" + css;
      img(SRC(name), "spr", b.root);
      return b.root;
    }

    // the sheet in page pixels: washes under the page ink, colored sprites on top
    function buildPage(camEl, colored, only, bloomAt) {
      const sheet = el("div", "sheet", camEl);
      const washes = {};
      const tag = `p${page}w-${colored ? "o" : "i"}`;
      let defs = "<defs>";
      for (const [k, [a, b]] of Object.entries(WASH)) {
        defs += `<linearGradient id="${tag}-${k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient>`;
      }
      defs += "</defs>";
      const wsvg = svg(sheet, 1200, 1600, "", defs);
      for (const [k, poly] of Object.entries(PANELS)) {
        const p = document.createElementNS(SVGNS, "polygon");
        p.setAttribute("points", poly.map((q) => q.join(",")).join(" "));
        p.setAttribute("fill", `url(#${tag}-${k})`);
        p.style.opacity = colored ? "1" : "0";
        wsvg.appendChild(p);
        washes[k] = p;
      }
      img(SRC("page-ink"), "", sheet, "width:1200px;height:1600px");
      const layer = el("div", "", sheet, "width:1200px;height:1600px");
      const flames = [];
      const ids = only || Object.keys(ART).filter((id) => !id.startsWith("t-") && !id.startsWith("cap-") && !(ART[id].noPage));
      const group = el("div", colored ? "" : "bloom", layer, "position:absolute;left:0;top:0;width:1200px;height:1600px");
      if (!colored && bloomAt) {
        // colour blooms outward from the first panel's centre (page px)
        const m = `radial-gradient(circle at ${(bloomAt[0] / 12).toFixed(1)}% ${(bloomAt[1] / 16).toFixed(1)}%, #000 var(--r), rgba(0,0,0,0) calc(var(--r) + 18%))`;
        group.style.webkitMaskImage = m;
        group.style.maskImage = m;
      }
      for (const id of ids) {
        const [x0, y0, x1, y1] = ART[id].b;
        const holder = el("div", "", group, `position:absolute;left:${x0}px;top:${y0}px;width:${x1 - x0}px;height:${y1 - y0}px`);
        img(SRC(id), "spr", holder);
        for (const [name, pa] of Object.entries(ART[id].p || {})) {
          const [px0, py0, px1, py1] = pa.b;
          const pv = pa.pv || [(px0 + px1) / 2, py1];
          const p = img(SRC(`${id}--${name}`), "part", holder, `left:${px0 - x0}px;top:${py0 - y0}px;width:${px1 - px0}px;height:${py1 - py0}px;transform-origin:${pv[0] - px0}px ${pv[1] - py0}px`);
          if (name === "flame") flames.push(p);
        }
      }
      return { sheet, washes, group, flames };
    }
    // page camera: page point (cx, cy) at the screen centre, zoom z (outer layer carries rotation)
    function pageCam(inner, t, dur, cx, cy, z, ease = "power2.inOut") {
      const v = { x: -z * cx, y: -z * cy, scale: z };
      if (dur === 0) tl.set(inner, v, t);
      else tl.to(inner, { ...v, duration: dur, ease }, t);
    }
    // camera for a world layer (transform-origin 0 0): centre world point (cx, cy) at zoom z
    function cam(n, t, dur, cx, cy, z, ease = "power2.inOut") {
      const v = { x: 960 - z * cx, y: 540 - z * cy, scale: z, duration: dur, ease };
      if (dur === 0) tl.set(n, v, t);
      else tl.to(n, v, t);
    }

    // ------------------------------------------------------------ motion
    function flicker(flame, glow, t0, t1, seed, amp = 1) {
      const r = rng(seed);
      let t = t0;
      while (t < t1) {
        const d = 0.08 + r() * 0.12;
        tl.to(flame, { scaleY: 1 + (r() * 0.24 - 0.1) * amp, scaleX: 1 - (r() * 0.12 - 0.04) * amp, skewX: (r() * 10 - 5) * amp, duration: d, ease: "sine.inOut" }, t);
        if (glow) tl.to(glow, { scale: 0.94 + r() * 0.12 * amp, opacity: 0.78 + r() * 0.22, duration: d, ease: "sine.inOut" }, t);
        t += d;
      }
    }
    function breathe(a, t0, t1, amp = 0.012, period = 1.2) {
      const n = Math.max(0, Math.floor((t1 - t0) / period) - 1);
      tl.fromTo(a.breath, { scaleY: 1 }, { scaleY: 1 + amp, scaleX: 1 - amp * 0.4, duration: period, ease: "sine.inOut", yoyo: true, repeat: n }, t0);
    }
    function hop(a, t, h = 60, air = 0.46, sq = 0.12) {
      tl.to(a.rig, { scaleY: 1 - sq, scaleX: 1 + sq * 0.7, duration: 0.1, ease: "power1.out" }, t);
      tl.to(a.rig, { scaleY: 1 + sq * 0.8, scaleX: 1 - sq * 0.5, duration: 0.12, ease: "power2.out" }, t + 0.1);
      tl.to(a.hopper, { y: -h, duration: air / 2, ease: "power2.out" }, t + 0.1);
      tl.to(a.rig, { scaleY: 1, scaleX: 1, duration: 0.18, ease: "sine.out" }, t + 0.22);
      tl.to(a.hopper, { y: 0, duration: air / 2, ease: "power2.in" }, t + 0.1 + air / 2);
      tl.to(a.rig, { scaleY: 1 - sq, scaleX: 1 + sq * 0.7, duration: 0.07, ease: "power1.out" }, t + 0.1 + air);
      tl.to(a.rig, { scaleY: 1, scaleX: 1, duration: 0.32, ease: "back.out(3)" }, t + 0.17 + air);
      const s = a.root.querySelector(".shadow");
      if (s) {
        tl.to(s, { scale: 0.75, opacity: 0.6, duration: air / 2, ease: "power2.out" }, t + 0.1);
        tl.to(s, { scale: 1, opacity: 1, duration: air / 2, ease: "power2.in" }, t + 0.1 + air / 2);
      }
    }
    function wave(arm, t, n = 3, up = -38, down = -8, beat = 0.22) {
      tl.to(arm, { rotation: up, duration: 0.24, ease: "back.out(2)" }, t);
      tl.to(arm, { rotation: down, duration: beat, ease: "sine.inOut", yoyo: true, repeat: n * 2 - 1 }, t + 0.24);
      tl.to(arm, { rotation: 0, duration: 0.3, ease: "sine.inOut" }, t + 0.24 + beat * n * 2);
    }
    function waddle(a, t0, t1, step = 0.32, lift = 9, tilt = 2.2) {
      const n = Math.max(0, Math.floor((t1 - t0) / step) - 1);
      tl.to(a.hopper, { y: -lift, duration: step / 2, ease: "sine.out", yoyo: true, repeat: n * 2 + 1 }, t0);
      tl.fromTo(a.rig, { rotation: -tilt }, { rotation: tilt, duration: step, ease: "sine.inOut", yoyo: true, repeat: n }, t0);
      tl.to(a.rig, { rotation: 0, duration: 0.25 }, t0 + step * (n + 1));
    }
    // quick side-to-side tremble on the breath layer (crying, shivering, struggling)
    function tremble(a, t0, t1, amp = 3, rate = 0.05) {
      const n = Math.max(0, Math.floor((t1 - t0) / rate) - 1);
      tl.fromTo(a.breath, { x: -amp }, { x: amp, duration: rate, ease: "none", yoyo: true, repeat: n }, t0);
      tl.to(a.breath, { x: 0, duration: 0.06 }, t0 + rate * (n + 1));
    }
    function pop(b, t, hold, out = 0.3, again = false) {
      tl.fromTo(b, { opacity: 0, scale: 0.2, rotation: -6 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.42, ease: "back.out(2.2)", immediateRender: !again }, t);
      if (hold) tl.to(b, { opacity: 0, scale: 0.85, duration: out, ease: "power1.in" }, t + hold);
    }
    function dropLabel(lb, t, rot = -1.5, from = -60) {
      tl.fromTo(lb.root, { opacity: 0, y: from, rotation: rot + 5 }, { opacity: 1, y: 0, rotation: rot, duration: 0.6, ease: "back.out(1.6)" }, t);
      tl.fromTo(lb.tape, { scaleX: 0 }, { scaleX: 1, duration: 0.28, ease: "power2.out" }, t + 0.42);
    }
    function floatUp(n, t, dy = -170, dx = 20, dur = 1.5) {
      tl.fromTo(n, { opacity: 0, scale: 0.2, x: 0, y: 0 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(3)" }, t);
      tl.to(n, { y: dy, x: dx, duration: dur, ease: "sine.out" }, t + 0.05);
      tl.to(n, { opacity: 0, duration: 0.45, ease: "power1.in" }, t + dur - 0.35);
    }
    function twinkle(n, t, dur = 0.7) {
      tl.fromTo(n, { opacity: 0, scale: 0, rotation: -40 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.25, ease: "back.out(3)" }, t);
      tl.to(n, { opacity: 0, scale: 0.3, rotation: 30, duration: 0.3, ease: "power1.in" }, t + dur - 0.3);
    }
    function wipeIn(n, t, dur = 1, ease = "power1.inOut") {
      tl.fromTo(n, { clipPath: "inset(0% 100% 0% 0%)" }, { clipPath: "inset(0% 0% 0% 0%)", duration: dur, ease }, t);
    }
    // multi-line caption: rows appear top to bottom, one every `per` seconds
    function revealLines(n, t, rows, per = 0.9, dur = 0.5) {
      tl.set(n, { clipPath: "inset(0% 0% 100% 0%)" }, 0);
      for (let i = 1; i <= rows; i++) {
        tl.to(n, { clipPath: `inset(0% 0% ${(100 * (1 - i / rows)).toFixed(2)}% 0%)`, duration: dur, ease: "power1.out" }, t + (i - 1) * per);
      }
    }
    // a looping fall that is already `lead` seconds under way at t0. GSAP shifts a whole
    // timeline when a child starts before 0, so a pre-roll that would reach back past 0
    // starts mid-flight at 0 instead.
    function fallLoop(n, from, to, fall, lead, t0, t1) {
      let start = t0 - lead;
      let first = true;
      if (start < 0) {
        const p = -start / fall, mid = {};
        for (const k in from) mid[k] = from[k] + (to[k] - from[k]) * p;
        tl.fromTo(n, mid, { ...to, duration: fall * (1 - p), ease: "none" }, 0);
        start += fall;
        first = false;
      }
      const reps = Math.max(0, Math.floor((t1 - start) / fall));
      tl.fromTo(n, from, { ...to, duration: fall, ease: "none", repeat: reps, immediateRender: first }, start);
    }
    function snow(parent, n, seed, t0, t1, o) {
      const r = rng(seed);
      for (let i = 0; i < n; i++) {
        const s = o.size[0] + (o.size[1] - o.size[0]) * r();
        const f = el("div", "flake", parent, `width:${s}px;height:${s}px;left:${-60 + r() * 2040}px;top:${-40 - s}px;opacity:${o.alpha * (0.55 + 0.45 * r())}` + (o.blur ? `;filter:blur(${o.blur}px)` : ""));
        const fall = 1200 / (o.speed[0] + (o.speed[1] - o.speed[0]) * r());
        const lead = r() * fall;
        fallLoop(f, { y: 0 }, { y: 1200 }, fall, lead, t0, t1);
        const sway = 1.4 + r() * 1.8;
        tl.fromTo(f, { x: -o.drift * r() }, { x: o.drift * (0.4 + r()), duration: sway, ease: "sine.inOut", yoyo: true, repeat: Math.max(0, Math.floor((t1 - t0 + lead) / sway)) }, Math.max(0, t0 - lead));
      }
    }
    // rain: slanted streaks falling fast; `slant` is px of sideways travel per screen height
    function rain(parent, n, seed, t0, t1, o = {}) {
      const r = rng(seed);
      const len = o.len || [60, 120], w = o.width || [3, 5], speed = o.speed || [1700, 2400], slant = o.slant ?? -380, alpha = o.alpha ?? 0.75;
      const ang = (Math.atan2(-slant, 1200) * 180) / Math.PI;
      for (let i = 0; i < n; i++) {
        const L = len[0] + (len[1] - len[0]) * r(), W = w[0] + (w[1] - w[0]) * r();
        const d = el("div", "drop", parent, `width:${W}px;height:${L}px;left:${-100 + r() * 2300}px;top:${-L - 20}px;opacity:${alpha * (0.5 + 0.5 * r())};transform:rotate(${ang}deg)`);
        const fall = (1200 + L) / (speed[0] + (speed[1] - speed[0]) * r());
        const lead = r() * fall;
        fallLoop(d, { y: 0, x: 0 }, { y: 1200 + L, x: slant * ((1200 + L) / 1200) }, fall, lead, t0, t1);
      }
    }
    // splashes: little rings that open and fade on the ground
    function splashes(parent, n, seed, t0, t1, y0, y1, x0 = -40, x1 = 1960) {
      const r = rng(seed);
      for (let i = 0; i < n; i++) {
        const s = 22 + r() * 30;
        const sp = el("div", "splash", parent, `left:${x0 + r() * (x1 - x0)}px;top:${y0 + r() * (y1 - y0)}px;width:${s}px;height:${s * 0.45}px;opacity:0`);
        const per = 0.45 + r() * 0.5;
        const lead = r() * per;
        const reps = Math.max(0, Math.floor((t1 - t0 + lead) / per) - 1);
        tl.fromTo(sp, { scale: 0.2, opacity: 0.95 }, { scale: 1.4, opacity: 0, duration: per, ease: "power1.out", repeat: reps }, t0 + lead);
      }
    }
    // tears: drops sliding off a drawn face, relative to the actor's breath layer
    function tears(a, pts, t0, t1, seed, size = 26, fall = 150) {
      const r = rng(seed);
      pts.forEach(([px, py], i) => {
        const [lx, ly] = at(a, px, py);
        const s = svg(a.breath, 30, 40, `left:${lx - size / 2}px;top:${ly}px;width:${size}px;height:${size * 1.33}px;opacity:0;transform-origin:50% 0%`, SHAPES.tear);
        const per = 0.75 + r() * 0.35;
        const reps = Math.max(0, Math.floor((t1 - t0) / per) - 1);
        tl.fromTo(s, { y: 0, opacity: 1, scale: 0.6 }, { y: fall, opacity: 0, scale: 1, duration: per, ease: "power1.in", repeat: reps, immediateRender: false }, t0 + i * 0.23 + r() * 0.2);
      });
    }
    function puffBurst(parent, x, y, t, n, seed, spread = 160, size = 70) {
      const r = rng(seed);
      for (let i = 0; i < n; i++) {
        const s = size * (0.6 + r() * 0.8);
        const p = el("div", "puff", parent, `left:${x - s / 2}px;top:${y - s / 2}px;width:${s}px;height:${s}px;opacity:0`);
        const ang = Math.PI * (1 + r()), dist = spread * (0.5 + r() * 0.7);
        tl.fromTo(p, { opacity: 0.95, scale: 0.3, x: 0, y: 0 }, { opacity: 0, scale: 1.4, x: Math.cos(ang) * dist, y: Math.sin(ang) * dist * 0.45, duration: 0.7 + r() * 0.4, ease: "power2.out", immediateRender: false }, t + r() * 0.06);
      }
    }
    function shake(n, t, dur = 0.4, amp = 14, seed = 5) {
      const r = rng(seed);
      const steps = Math.floor(dur / 0.04);
      for (let i = 0; i < steps; i++) {
        const k = 1 - i / steps;
        tl.to(n, { x: (r() * 2 - 1) * amp * k, y: (r() * 2 - 1) * amp * k, duration: 0.04, ease: "none" }, t + i * 0.04);
      }
      tl.to(n, { x: 0, y: 0, duration: 0.05 }, t + steps * 0.04);
    }
    // lightning: a white overlay that double-strobes
    function flash(overlay, t, peak = 0.85) {
      tl.to(overlay, { opacity: peak, duration: 0.04, ease: "none" }, t);
      tl.to(overlay, { opacity: peak * 0.2, duration: 0.07, ease: "none" }, t + 0.05);
      tl.to(overlay, { opacity: peak * 0.8, duration: 0.04, ease: "none" }, t + 0.13);
      tl.to(overlay, { opacity: 0, duration: 0.45, ease: "power2.out" }, t + 0.18);
    }
    // the flame fades: shrink the wrapper, drop the glow
    function dimFlame(a, t, dur, to = 0) {
      tl.to(a.parts.flameWrap, { scale: 0.25 + 0.75 * to, opacity: to, duration: dur, ease: "power1.inOut" }, t);
      if (a.glow) tl.to(a.glow, { opacity: to * 0.8, scale: 0.5 + 0.5 * to, duration: dur, ease: "power1.inOut" }, t);
    }

    return {
      SRC, actor, at, sprite, bubble, label, art, buildPage, pageCam, cam,
      flicker, breathe, hop, wave, waddle, tremble, pop, dropLabel, floatUp, twinkle, wipeIn, revealLines,
      snow, rain, splashes, tears, puffBurst, shake, flash, dimFlame,
    };
  }

  return { INK, rng, el, img, svg, SHAPES, ridge, pine, kit };
})();
