"""Demo: item + city -> bin, with the city's own rule quoted and checked verbatim against the official page.

  GW_URL=... GW_KEY=... python app.py      then open http://localhost:8000 (landing page) or /demo
"""
import html, json, os, re, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from baseline import GW, TASK
from bench import CLASSES
from extract import norm

CACHE = Path(__file__).with_name("cache")
SITE = Path(__file__).with_name("site") / "index.html"
MODEL = os.environ.get("APP_MODEL", "gemini/gemini-3.5-flash-lite")
BIN = {"recycle": "Recycling bin", "organics": "Food / green bin", "trash": "Garbage bin",
       "special": "Not a household bin: drop-off, take-back or hazardous collection"}


_calls, _lock = [], threading.Lock()


def budget(per_min=int(os.environ.get("CALLS_PER_MIN", "20"))):
    """Global cap on model calls: a public demo must not burn the whole API quota.
    ponytail: one global window, per-IP limits if one visitor starves the rest."""
    with _lock:
        now = time.time()
        _calls[:] = [t for t in _calls if now - t < 60]
        if len(_calls) >= per_min:
            return False
        _calls.append(now)
        return True


def answer(item, city):
    page = CACHE / f"{city}.txt"
    if not page.exists():
        return None
    text = page.read_text(encoding="utf-8")[:60000]
    if not budget():
        raise RuntimeError("busy")
    prompt = (TASK + f"Item: {item}\nOfficial waste pages published by this city:\n{text}\n"
              'Return JSON only: {"class": "...", "quote": "<one sentence copied exactly from the pages that names this item or its category, max 30 words>"}')
    body = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": 300,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(GW, body, {"Authorization": f"Bearer {os.environ['GW_KEY']}",
                                            "Content-Type": "application/json", "User-Agent": "arbiter-bench/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = json.load(r)["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt or "", re.S)
    a = json.loads(m.group(0)) if m else {}
    if a.get("class") not in CLASSES:
        return {"class": None, "quote": "", "verified": False}
    q = str(a.get("quote", ""))
    # a quote not found on the page is not shown as a rule
    return {"class": a["class"], "quote": q, "verified": bool(q) and norm(q) in norm(text)}


def identify(data_url):
    """Photo -> short item name (vision model). Only names the item; the bin still comes from the city's page."""
    if not budget():
        raise RuntimeError("busy")
    body = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": 30, "messages": [{"role": "user", "content": [
        {"type": "text", "text": "Name the single household item to throw away in this photo, in at most 6 words "
         "(material matters, e.g. 'greasy pizza box', 'disposable vape'). Reply with the name only."},
        {"type": "image_url", "image_url": {"url": data_url}}]}]}).encode()
    req = urllib.request.Request(GW, body, {"Authorization": f"Bearer {os.environ['GW_KEY']}",
                                            "Content-Type": "application/json", "User-Agent": "arbiter-bench/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return (json.load(r)["choices"][0]["message"]["content"] or "").strip().strip(".")[:100]


def page(item="", city="", result=""):
    cities = sorted(p.stem for p in CACHE.glob("*.txt"))
    opts = "".join(f'<option value="{c}"{" selected" if c == city else ""}>{c.replace("_", " ").title()}</option>' for c in cities)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Which bin?</title><style>body{{font:16px system-ui;max-width:36rem;margin:2rem auto;padding:0 16px}}
input,select,button{{font:inherit;padding:.5rem;width:100%;margin:.25rem 0 1rem}}blockquote{{border-left:4px solid #888;margin:0;padding-left:1rem}}</style>
<p><a href="/">← Which Bin</a></p><h1>Which bin?</h1><p>Answers follow your city's own published rules.</p>
<form action="/demo"><label for="i">Item</label><input id="i" name="item" required value="{html.escape(item)}" placeholder="disposable vape">
<label for="c">City</label><select id="c" name="city">{opts}</select><button>Check</button></form>
<label for="f">Or take a photo of the item</label><input id="f" type="file" accept="image/*" capture="environment">
<script>f.onchange=()=>{{const r=new FileReader();r.onload=async()=>{{i.value="Identifying...";
const t=await fetch("/identify",{{method:"POST",body:r.result}});i.value=t.ok?await t.text():"";
if(i.value)i.form.requestSubmit()}};r.readAsDataURL(f.files[0])}}</script>
<div role="status">{result}</div></html>"""


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n).decode() if 0 < n <= 8_000_000 else ""
        if self.path != "/identify" or not re.match(r"data:image/(png|jpeg|webp|heic);base64,", data):
            self.send_response(400); self.end_headers(); return
        try:
            name, code = identify(data).encode(), 200
        except Exception:
            name, code = b"", 502
        self.send_response(code); self.send_header("Content-Type", "text/plain; charset=utf-8"); self.end_headers()
        self.wfile.write(name)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/":
            out = SITE.read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
            self.wfile.write(out); return
        if url.path != "/demo":
            self.send_response(404); self.end_headers(); return
        q = urllib.parse.parse_qs(url.query)
        item, city = q.get("item", [""])[0][:100], q.get("city", [""])[0]
        result = ""
        if item and re.fullmatch(r"[a-z_]+", city):  # city names a cache file: no path tricks
            try:
                a = answer(item, city)
            except Exception as e:
                msg = "Too many people are asking right now. Try again in a minute." if str(e) == "busy" else "Lookup failed."
                a, result = None, f"<p>{msg}</p>"
            if a is None and not result:
                result = "<p>No official page for this city yet.</p>"
            elif a and a["class"] is None:
                result = "<p>The city's pages do not say clearly. Check with your city.</p>"
            elif a:
                rule = (f'<blockquote>{html.escape(a["quote"])}</blockquote><p>Quote found on the official page.</p>'
                        if a["verified"] else "<p>No exact rule found on the page: treat as a best guess.</p>")
                result = f'<h2>{BIN[a["class"]]}</h2>{rule}'
        out = page(item, city, result).encode()
        self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
        self.wfile.write(out)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8000"))), H).serve_forever()
