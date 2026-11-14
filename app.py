"""Website + JSON API: item + city -> bin, with the city's own rule quoted and checked verbatim against the official page.

  GW_URL=... GW_KEY=... python app.py      then open http://localhost:8000

  GET  /api/which-bin?item=disposable+vape&city=camden
  GET  /api/cities        cities, sources, rules and gaps
  GET  /api/stats         benchmark headline numbers and the model audit, computed from data/ and preds/
  POST /api/identify      body: image data URL -> {"item": "..."}
Pages are the static files in site/ (/about serves site/about.html).
"""
import csv, json, os, re, threading, time, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from baseline import GW, NAMES, TASK
from bench import CLASSES, HAZARD, RULES, blind_best, by_item, load, score
from extract import norm

ROOT = Path(__file__).parent
CACHE, SITE = ROOT / "cache", ROOT / "site"
MODEL = os.environ.get("APP_MODEL", "gemini/gemini-3.5-flash-lite")
BIN = {"recycle": "Recycling bin", "organics": "Food / green bin", "trash": "Garbage bin",
       "special": "Not a household bin: drop-off, take-back or hazardous collection"}
NICE = {"nyc": "New York City", "city_of_london": "City of London", "st_louis": "St. Louis",
        "dumfries_galloway": "Dumfries & Galloway", "saint_paul": "Saint Paul"}
COUNTRY = {"CA": "Canada", "US": "United States", "JP": "Japan", "DE": "Germany", "GB": "United Kingdom",
           "AU": "Australia", "AT": "Austria", "ID": "Indonesia"}
TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript",
         ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}

# sources that are not a resident guide (a quiz sheet, an office guideline): rules count, gaps don't
NOT_RESIDENT = {"vienna", "yogyakarta"}

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


def chat(content, max_tokens):
    if not budget():
        raise RuntimeError("busy")
    body = json.dumps({"model": MODEL, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": content}]}).encode()
    req = urllib.request.Request(GW, body, {"Authorization": f"Bearer {os.environ['GW_KEY']}",
                                            "Content-Type": "application/json", "User-Agent": "arbiter-bench/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"] or ""


ANSWERS = Path(os.environ.get("ANSWER_CACHE", ROOT / "answers.json"))
try:
    _memo = json.loads(ANSWERS.read_text(encoding="utf-8"))
except (OSError, ValueError):
    _memo = {}


def context(text, quote, pad=240):
    """Where the quote sits on the page: (before, quote as printed, after). Whitespace and punctuation may differ."""
    words = re.findall(r"\w+", quote)
    m = words and re.search(r"\W+".join(map(re.escape, words)), text, re.I)
    if not m:
        return None
    return {"before": text[max(0, m.start() - pad):m.start()], "match": m.group(0), "after": text[m.end():m.end() + pad]}


def answer(item, city):
    """Cached per (city, item): repeat questions cost no quota and the judge tour stays instant."""
    key = f"{city}|{norm(item)}"
    if key not in _memo:
        a = _answer(item, city)
        if a is None or a["class"] is None and not a.get("silent"):
            return a
        with _lock:
            _memo[key] = a
            ANSWERS.write_text(json.dumps(_memo), encoding="utf-8")
    return _memo[key]


def _answer(item, city):
    page = CACHE / f"{city}.txt"
    if not page.exists():
        return None
    text = page.read_text(encoding="utf-8")[:60000]
    txt = chat(TASK + f"Item: {item}\nOfficial waste pages published by this city:\n{text}\n"
               'Return JSON only: {"class": "...", "quote": "<one sentence copied exactly from the pages that names '
               'this item or its category, max 30 words>"}', 300)
    m = re.search(r"\{.*\}", txt, re.S)
    a = json.loads(m.group(0)) if m else {}
    if a.get("class") not in CLASSES:
        return {"class": None, "bin": None, "quote": "", "verified": False, "source": None, "context": None,
                "silent": bool(m)}  # a parsed reply without a class means the page doesn't say: worth caching
    q = str(a.get("quote", ""))
    # a quote not found on the page is not shown as a rule
    seg = next((s for s in text.split("SOURCE ")[1:] if q and norm(q) in norm(s)), None)
    return {"class": a["class"], "bin": BIN[a["class"]], "quote": q if seg else "", "verified": bool(seg),
            "source": seg.split(None, 1)[0] if seg else None, "context": context(seg, q) if seg else None}


def identify(data_url):
    """Photo -> short item name (vision model). Only names the item; the bin still comes from the city's page."""
    return chat([{"type": "text", "text": "Name the single household item to throw away in this photo, in at most 6 words "
                  "(material matters, e.g. 'greasy pizza box', 'disposable vape'). Reply with the name only."},
                 {"type": "image_url", "image_url": {"url": data_url}}], 30).strip().strip(".")[:100]


def build():
    """Everything the site shows, computed once from data/ and preds/ so pages never drift from the benchmark."""
    hand, auto = load(RULES), load(RULES.with_name("rules_auto.csv"))
    gold = {**auto, **hand}
    rows = []
    for name in ("rules.csv", "rules_auto.csv", "sources.csv"):
        with open(RULES.with_name(name), encoding="utf-8", newline="") as f:
            rows += [dict(r, file=name) for r in csv.DictReader(f)]
    cities = {}
    for r in rows:
        c = cities.setdefault(r["city"], {"id": r["city"], "name": NICE.get(r["city"], r["city"].replace("_", " ").title()),
                                          "country": COUNTRY.get(r["country"], r["country"]), "sources": [], "rules": []})
        if r["url"] not in c["sources"]:
            c["sources"].append(r["url"])
        if r["file"] != "sources.csv" and (r["city"], r["item"]) in gold and gold[(r["city"], r["item"])] == r["class"]:
            c["rules"].append({"item": r["item"], "name": NAMES[r["item"]], "class": r["class"], "quote": r["quote"],
                               "url": r["url"], "checked": r["file"] == "rules.csv"})
    auto_cities = {c for c, _ in auto}
    for c in cities.values():
        c["live"] = (CACHE / f"{c['id']}.txt").exists()
        c["checked"] = c["id"] not in auto_cities and bool(c["rules"])
        have = {r["item"] for r in c["rules"]}
        # gaps only mean something where the whole main page was read for every item
        c["silent"] = sorted(i for i in NAMES if i not in have) if c["id"] in auto_cities - NOT_RESIDENT else None
    acc, haz, unsafe, n = score(gold, blind_best(gold))
    items = {i: {"name": NAMES[i], "hazard": i in HAZARD, "by_class": {k: sorted(c for c, v in cs.items() if v == k)
             for k in CLASSES if k in cs.values()}} for i, cs in by_item(gold).items()}
    audit = []
    for f in sorted((ROOT / "preds" / "audit").glob("*.csv")) + [ROOT / "preds" / f"{MODEL.replace('/', '_')}__page__v1.csv"]:
        with open(f, encoding="utf-8", newline="") as fh:
            pred = {(r["city"], r["item"]): r["class"] for r in csv.DictReader(fh)}
        a, h, u, _ = score(hand, pred)
        model, mode = f.stem.split("__")[:2]
        audit.append({"model": model.split("_", 1)[1], "mode": mode, "accuracy": a, "hazard": h, "unsafe": u})
    stats = {"cities": len({c for c, _ in gold}), "rules": len(gold), "checked_rules": len(hand), "items": len(NAMES),
             "items_disagree": sum(len(set(v.values())) > 1 for v in by_item(gold).values()),
             "blind_ceiling": acc, "blind_unsafe": unsafe, "hand_blind_ceiling": score(hand, blind_best(hand))[0],
             "audit": audit}
    return sorted(cities.values(), key=lambda c: c["name"]), items, stats


CITIES, ITEMS, STATS = build()
assert STATS["items_disagree"] <= STATS["items"] and all(0 <= a["accuracy"] <= 1 for a in STATS["audit"])


class H(BaseHTTPRequestHandler):
    def send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-cache")  # small site: always revalidate so redeploys show at once
        self.end_headers()
        self.wfile.write(body)

    def json(self, obj, code=200):
        self.send(code, json.dumps(obj).encode())

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n).decode() if 0 < n <= 8_000_000 else ""
        if self.path != "/api/identify" or not re.match(r"data:image/(png|jpeg|webp|heic);base64,", data):
            return self.json({"error": "send an image data URL"}, 400)
        try:
            self.json({"item": identify(data)})
        except Exception as e:
            self.json({"error": "busy" if str(e) == "busy" else "failed"}, 429 if str(e) == "busy" else 502)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        if url.path == "/api/cities":
            return self.json({"cities": CITIES, "items": ITEMS})
        if url.path == "/api/stats":
            return self.json(STATS)
        if url.path == "/api/which-bin":
            item, city = q.get("item", "").strip()[:100], q.get("city", "")
            if not item or not re.fullmatch(r"[a-z_]+", city):  # city names a cache file: no path tricks
                return self.json({"error": "need item and a city id from /api/cities"}, 400)
            try:
                a = answer(item, city)
            except Exception as e:
                return self.json({"error": "busy" if str(e) == "busy" else "failed"}, 429 if str(e) == "busy" else 502)
            return self.json(a if a else {"error": "no official page for this city yet"}, 200 if a else 404)
        name = url.path.strip("/") or "index"
        f = SITE / (name if "." in name else name + ".html")
        if re.fullmatch(r"[a-z0-9_-]+(\.[a-z]+)?", name) and f.is_file() and f.suffix in TYPES:
            return self.send(200, f.read_bytes(), TYPES[f.suffix])
        self.send(404, (SITE / "404.html").read_bytes(), TYPES[".html"])


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT", "8000"))), H).serve_forever()
