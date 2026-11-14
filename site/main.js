// Shared header, footer and motion for every page. Pages work without it (content is plain HTML).
window.esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
window.TAG = { recycle: "Recycling", organics: "Compost", trash: "Garbage", special: "Drop-off" };
window.pct = v => (v * 100).toFixed(1) + "%";
const NAV = [["/", "Home"], ["/tour", "Tour"], ["/demo", "Try it"], ["/audit", "Audit"], ["/cities", "Cities"], ["/developers", "Developers"], ["/about", "About"]];
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


// one answer card, shared by the checker and the judge tour
const GLYPH = { recycle: ["♻", "#cfe2f3", "inherit"], organics: ["🌱", "#d7ebc9", "inherit"], trash: ["🗑", "#ebe5dc", "inherit"], special: ["⚠", "#211c15", "#f9d9b4"] };
window.resultCard = (a, item, city) => {
  if (a.error) return `<div class="result"><h3>${a.error === "busy" ? "Lots of people are checking right now. Try again in a minute." : a.error.startsWith("no official") ? `We don't have ${esc(city)}'s official page yet.` : "Something went wrong. Try again."}</h3></div>`;
  if (!a.class) return `<div class="result"><div style="font-size:13px;color:var(--muted)">${esc(item)} · ${esc(city)}</div><h3>${esc(city)}'s page doesn't say</h3><p style="color:var(--ink2);margin:8px 0 0;font-size:14px">Check with the city before throwing it away. We won't guess.</p></div>`;
  const [g, bg, fg] = GLYPH[a.class], c = a.context;
  return `<div class="result" data-class="${a.class}"><div class="kind"><div class="glyph" style="background:${bg};color:${fg}" aria-hidden="true">${g}</div>
   <div><div style="font-size:13px;color:var(--muted)">${esc(item)} · ${esc(city)}</div><h3>${esc(a.bin)}</h3></div></div>
   ${a.verified ? `<blockquote>"${esc(a.quote)}"</blockquote>
     <div class="meta">✓ Found word for word on <a href="${esc(a.source)}" target="_blank" rel="noopener">${esc(new URL(a.source).hostname)}</a></div>
     ${c ? `<details class="onpage"><summary>Show it on the page</summary><div class="pagesnip"><div class="src">${esc(a.source)}</div>…${esc(c.before)}<mark>${esc(c.match)}</mark>${esc(c.after)}…</div></details>` : ""}`
   : `<div class="meta warn">No exact rule found on the page. Treat this as a best guess and check with the city.</div>`}</div>`;
};
window.askBin = (item, city) => fetch(`/api/which-bin?item=${encodeURIComponent(item)}&city=${city}`).then(r => r.json()).catch(() => ({ error: "failed" }));
