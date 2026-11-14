"""Snapshot every official page in the registry (rules.csv + rules_auto.csv + sources.csv urls) to cache/<city>.txt.

  python fetch.py
Pages change; the snapshot keeps runs reproducible. cache/ is not committed (third-party text).
"""
import csv, re
from pathlib import Path
from extract import page_text

DATA = Path(__file__).with_name("data")
CACHE = Path(__file__).with_name("cache")


def registry():
    urls = {}
    for name in ("rules.csv", "rules_auto.csv", "sources.csv"):
        with open(DATA / name, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                urls.setdefault(r["city"], set()).add(r["url"])
    return urls


def main():
    CACHE.mkdir(exist_ok=True)
    for city, urls in registry().items():
        out = CACHE / f"{city}.txt"
        if out.exists():
            continue
        parts = []
        for u in sorted(urls):
            try:
                parts.append(f"SOURCE {u}\n" + re.sub(r"\s+", " ", page_text(u)))
            except Exception as e:
                print("FAIL", city, u, type(e).__name__, getattr(e, "code", ""))
        if parts:
            out.write_text("\n\n".join(parts), encoding="utf-8")
        print(city, len(urls), "urls", sum(map(len, parts)), "chars")


if __name__ == "__main__":
    main()
