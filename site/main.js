// Shared header, footer and motion for every page. Pages work without it (content is plain HTML).
window.esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
window.TAG = { recycle: "Recycling", organics: "Compost", trash: "Garbage", special: "Drop-off" };
window.pct = v => (v * 100).toFixed(1) + "%";
const NAV = [["/", "Home"], ["/demo", "Try it"], ["/audit", "Audit"], ["/cities", "Cities"], ["/developers", "Developers"], ["/about", "About"]];
const REPO = "https://github.com/rofiperlungoding/which-bin";
const here = location.pathname.replace(/\.html$/, "").replace(/\/$/, "") || "/";
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

const head = document.querySelector("header.top");
if (head) {
  head.innerHTML = `<div class="wrap"><nav class="main" aria-label="Main">
    <a class="logo" href="/"><b aria-hidden="true">♻</b>Which Bin</a>
    <ul id="navlist">${NAV.map(([h, t]) => `<li><a href="${h}"${h === here ? ' aria-current="page"' : ""}>${t}</a></li>`).join("")}</ul>
    <a class="btn" href="/demo">Check an item <i aria-hidden="true"></i></a>
    <button class="menu" aria-label="Menu" aria-expanded="false" aria-controls="navlist"><span></span><span></span></button>
  </nav></div>`;
  const btn = head.querySelector(".menu");
  btn.onclick = () => btn.setAttribute("aria-expanded", head.classList.toggle("open"));
  const onScroll = () => head.classList.toggle("scrolled", scrollY > 8);
  addEventListener("scroll", onScroll, { passive: true }); onScroll();
}

const foot = document.querySelector("footer");
if (foot) {
  foot.innerHTML = `<div class="wrap"><div class="fgrid">
    <div><a class="logo" href="/"><b aria-hidden="true">♻</b>Which Bin</a><p>Recycling answers grounded in each city's own published rules. Open data, open code.</p></div>
    <div><h4>Product</h4><ul><li><a href="/demo">Try it</a></li><li><a href="/developers">API & MCP</a></li><li><a href="/cities">Cities</a></li></ul></div>
    <div><h4>Research</h4><ul><li><a href="/audit">Model audit</a></li><li><a href="/audit#method">Method</a></li><li><a href="/cities#gaps">Guidance gaps</a></li></ul></div>
    <div><h4>Project</h4><ul><li><a href="/about">About</a></li><li><a href="${REPO}">GitHub</a></li><li><a href="${REPO}/blob/main/data/rules.csv">Dataset (CC BY 4.0)</a></li></ul></div>
  </div><div class="fbase"><span>Built for Arbiter Hacks V1 · Theme: Rethinking Waste</span><span>Code MIT · Data CC BY 4.0 · Rules quoted from official city pages</span></div></div>`;
}

// reveal on scroll; also starts counters and bar fills inside the revealed block
const fmt = (el, v) => el.textContent = (el.dataset.prefix || "") + (+v).toFixed(+(el.dataset.dec || 0)) + (el.dataset.suffix || "");
function count(el) {
  const to = +el.dataset.count;
  if (reduce) return fmt(el, to);
  const t0 = performance.now(), dur = 1400;
  const step = t => { const p = Math.min(1, (t - t0) / dur); fmt(el, to * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
function play(el) {
  el.classList.add("in");
  el.querySelectorAll("[data-count]").forEach(count);
  el.querySelectorAll("[data-w]").forEach(b => b.style.width = b.dataset.w + "%");
}
window.reveal = root => {
  const els = (root || document).querySelectorAll(".rv:not(.in)");
  if (!("IntersectionObserver" in window)) return els.forEach(play);
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { play(e.target); io.unobserve(e.target); } }), { threshold: .15 });
  els.forEach(el => io.observe(el));
};
reveal();

// auto-advancing steps: click to pick, advances every 4.5s
document.querySelectorAll("ol.st").forEach(list => {
  const items = [...list.children], show = window[list.dataset.onstep] || (() => {});
  let i = 0, timer;
  const go = n => {
    items.forEach((li, k) => { li.classList.toggle("on", k === n); li.setAttribute("aria-current", k === n ? "step" : "false"); });
    i = n; show(n);
    clearTimeout(timer); if (!reduce) timer = setTimeout(() => go((i + 1) % items.length), 4500);
  };
  items.forEach((li, k) => { li.tabIndex = 0; li.onclick = () => go(k); li.onkeydown = e => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), go(k)); });
  go(0);
});

// carousels: arrows + dots synced to scroll position
document.querySelectorAll(".carousel").forEach(c => {
  const s = c.querySelector(".slides"), dots = c.querySelector(".dots");
  const n = () => s.children.length, w = () => s.children[0].getBoundingClientRect().width + 20;
  const sync = () => { if (!s.children.length) return; const k = Math.round(s.scrollLeft / w()); [...dots.children].forEach((d, j) => d.classList.toggle("on", j === k)); };
  const build = () => { dots.innerHTML = Array.from({ length: n() }, () => "<i></i>").join(""); sync(); };
  c.querySelector(".prev").onclick = () => s.scrollBy({ left: -w(), behavior: "smooth" });
  c.querySelector(".next").onclick = () => s.scrollBy({ left: w(), behavior: "smooth" });
  s.addEventListener("scroll", () => requestAnimationFrame(sync), { passive: true });
  new MutationObserver(build).observe(s, { childList: true }); build();
});

