// Build every page composition in headless Chromium and check its GSAP timeline.
// GSAP silently shifts a whole timeline forward when any tween is placed before
// time 0 (Timeline.shiftChildren), which delays every cue on the page; this reports
// any such shift, plus the timeline length against the composition's data-duration
// (looping effects may legitimately run past the end; their set hides them).
//
// Usage: node scripts/check_timelines.mjs            (needs the global playwright package)
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const require = createRequire(import.meta.url);
let chromium;
try {
  ({ chromium } = require("playwright"));
} catch {
  const globalRoot = require("node:child_process").execSync("npm root -g").toString().trim();
  ({ chromium } = require(path.join(globalRoot, "playwright")));
}
const pages = fs.readdirSync(path.join(root, "compositions")).filter((f) => /^page\d+\.html$/.test(f)).sort();
const harness = `<!doctype html><html><head><link rel="stylesheet" href="/assets/lib/ec.css">
<script src="/assets/vendor/gsap.min.js"></script><script src="/assets/lib/ec.js"></script></head><body>
<script>window.__timelines = {}; window.__shifts = [];
const T = gsap.core.Timeline.prototype, orig = T.shiftChildren;
T.shiftChildren = function (amount, ...rest) { window.__shifts.push(amount); return orig.call(this, amount, ...rest); };
</script></body></html>`;
const types = { ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".html": "text/html", ".png": "image/png", ".woff2": "font/woff2" };
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split("?")[0]);
  if (url === "/harness.html") return res.writeHead(200, { "content-type": "text/html" }).end(harness);
  const file = path.join(root, url);
  if (!file.startsWith(root) || !fs.existsSync(file)) return res.writeHead(404).end();
  res.writeHead(200, { "content-type": types[path.extname(file)] || "application/octet-stream" }).end(fs.readFileSync(file));
});
await new Promise((r) => server.listen(0, r));
const port = server.address().port;
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(`http://127.0.0.1:${port}/harness.html`);
let bad = 0;
for (const f of pages) {
  const res = await page.evaluate(async (file) => {
    const html = await (await fetch("/compositions/" + file)).text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const tpl = doc.querySelector("template");
    const host = document.createElement("div");
    host.style.cssText = "position:relative;width:1920px;height:1080px;overflow:hidden";
    document.body.appendChild(host);
    const frag = tpl.content.cloneNode(true);
    const scripts = [...frag.querySelectorAll("script")];
    scripts.forEach((s) => s.remove());
    host.appendChild(frag);
    window.__shifts = [];
    for (const s of scripts) new Function(s.textContent)();
    const rootEl = host.querySelector("[data-composition-id]");
    const id = rootEl.getAttribute("data-composition-id");
    const tl = window.__timelines[id];
    const got = tl ? tl.duration() : null; // GSAP applies any pending shift here
    const shift = window.__shifts.filter((a) => a > 0).reduce((a, b) => a + b, 0);
    return { id, want: Number(rootEl.getAttribute("data-duration")), got, shift };
  }, f);
  const flag = res.got == null ? "MISSING TIMELINE" : res.shift > 0 ? `SHIFTED by ${res.shift.toFixed(2)} s (a tween starts before 0)` : "ok";
  if (flag !== "ok") bad++;
  console.log(`${f}: timeline ${res.got?.toFixed(2)} s (composition ${res.want} s) -> ${flag}`);
}
if (errors.length) console.log("page errors:\n  " + errors.join("\n  "));
await browser.close();
server.close();
process.exit(bad || errors.length ? 1 : 0);
