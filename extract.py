"""Draft rule rows from an official city page with an LLM; keep only rows whose quote is verbatim on the page.

  GW_KEY=... python extract.py <city_id> <country> <url> [more urls...]
  -> appends to data/rules_auto.csv (unreviewed; promote rows to rules.csv after a human check)
"""
import csv, html, io, json, re, sys, urllib.request
from pathlib import Path
from bench import CLASSES
from baseline import NAMES, GW
import os

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
OUT = Path(__file__).with_name("data") / "rules_auto.csv"
MODEL = os.environ.get("EXTRACT_MODEL", "gemini/gemini-3.5-flash-lite")


def page_text(url):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()
    if raw[:4] == b"%PDF":
        import pypdf
        return " ".join(p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(raw)).pages)
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|nav|header|footer).*?</\1>", " ", t)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def norm(s):
    return re.sub(r"\W+", " ", s).strip().lower()


def ask(prompt, model=MODEL):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 4000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(GW, body, {"Authorization": f"Bearer {os.environ['GW_KEY']}",
                                            "Content-Type": "application/json", "User-Agent": "arbiter-bench/0.1"})
    with urllib.request.urlopen(req, timeout=180) as r:
        txt = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))


def main():
    city, country, urls = sys.argv[1], sys.argv[2], sys.argv[3:]
    texts = {u: re.sub(r"\s+", " ", page_text(u)) for u in urls}
    corpus = "\n\n".join(f"SOURCE {i}: {u}\n{t[:120000]}" for i, (u, t) in enumerate(texts.items()))
    items = "\n".join(f"- {k}: {v}" for k, v in NAMES.items())
    prompt = (
        "You read official household waste guidance published by one city. For each item below, say where the "
        "text tells residents to put it. Use ONLY the text. If the text does not clearly cover the item, use null.\n"
        "class must be one of: recycle (curbside recycling), organics (food/garden bin), trash (general waste), "
        "special (drop-off, take-back, deposit, hazardous collection, not a household bin).\n"
        "quote must be copied EXACTLY from the text (max 25 words) and must mention the item or its category.\n"
        'Return JSON only: {"item_id": {"class": "...", "local_stream": "...", "quote": "...", "source": 0} or null, ...}\n\n'
        f"Items:\n{items}\n\n{corpus}")
    ans = ask(prompt)
    # a quote reused for 4+ items is a category line, not an item rule
    reuse = {}
    for v in ans.values():
        if v and v.get("quote"):
            reuse[v["quote"]] = reuse.get(v["quote"], 0) + 1
    ans = {k: v for k, v in ans.items() if v and reuse.get(v.get("quote"), 0) < 4}
    kept = dropped = 0
    new = not OUT.exists()
    with open(OUT, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["city", "country", "item", "class", "local_stream", "quote", "url"])
        for item, v in ans.items():
            if item not in NAMES or not v:
                continue
            url = urls[int(v.get("source", 0) or 0)] if str(v.get("source", 0)).isdigit() else urls[0]
            ok = v.get("class") in CLASSES and v.get("quote") and norm(v["quote"]) in norm(texts[url])
            if ok:
                w.writerow([city, country, item, v["class"], v.get("local_stream", ""), v["quote"], url]); kept += 1
            else:
                dropped += 1
    print(f"{city}: kept {kept}, dropped {dropped} (quote not verbatim or bad class), page chars {sum(map(len, texts.values()))}")


if __name__ == "__main__":
    main()
