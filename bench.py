"""Bin benchmark: item + city -> class, scored against official city rules.

  python bench.py stats              disagreement + best possible location-blind score
  python bench.py score preds.csv    preds.csv columns: city,item,class
"""
import csv, sys
from collections import Counter
from itertools import combinations
from pathlib import Path

CLASSES = {"recycle", "organics", "trash", "special"}
HAZARD = {"vape", "aa_battery", "led_bulb"}  # wrong bin can start a fire or leak toxics
RULES = Path(__file__).with_name("data") / "rules.csv"


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    gold = {}
    for r in rows:
        key = (r["city"], r["item"])
        assert r["class"] in CLASSES, f"bad class {r['class']} at {key}"
        assert key not in gold, f"duplicate {key}"
        assert r.get("url", "x").startswith("http"), f"missing source url at {key}"
        gold[key] = r["class"]
    return gold


def by_item(gold):
    items = {}
    for (city, item), c in gold.items():
        items.setdefault(item, {})[city] = c
    return items


def blind_best(gold):
    """Answer every item the same way in every city (majority class): the ceiling for any location-blind model."""
    return {(city, item): Counter(v.values()).most_common(1)[0][0]
            for item, v in by_item(gold).items() for city in v}


def score(gold, pred):
    keys = list(gold)
    acc = sum(pred.get(k) == gold[k] for k in keys) / len(keys)
    haz = [k for k in keys if k[1] in HAZARD]
    haz_acc = sum(pred.get(k) == gold[k] for k in haz) / len(haz)
    # unsafe: city says special handling, model says a normal bin
    sp = [k for k in keys if gold[k] == "special"]
    unsafe = sum(pred.get(k) in {"recycle", "trash", "organics"} for k in sp) / len(sp)
    return acc, haz_acc, unsafe, len(keys)


def stats(gold):
    items = by_item(gold)
    comp = {i: v for i, v in items.items() if len(v) >= 2}
    dis = sorted(i for i, v in comp.items() if len(set(v.values())) > 1)
    print(f"cities: {len({c for c, _ in gold})}  rows: {len(gold)}  items comparable: {len(comp)}")
    print(f"items where cities disagree: {len(dis)}/{len(comp)} -> {', '.join(dis)}")
    acc, haz, unsafe, n = score(gold, blind_best(gold))
    print(f"best location-blind model: accuracy {acc:.1%}, hazard-item accuracy {haz:.1%}, "
          f"unsafe on special-handling items {unsafe:.1%} (n={n})")
    cities = sorted({c for c, _ in gold})
    print("pairwise disagreement (shared items):")
    for a, b in combinations(cities, 2):
        shared = [i for i, v in items.items() if a in v and b in v]
        if len(shared) >= 5:
            d = sum(items[i][a] != items[i][b] for i in shared)
            print(f"  {a:>14} vs {b:<14} {d}/{len(shared)}")


def main():
    gold = load(RULES)
    if len(sys.argv) > 2 and sys.argv[1] == "stats":  # extra rule files, e.g. data/rules_auto.csv
        for p in sys.argv[2:]:
            gold = {**load(p), **gold}  # hand-checked rows win
    assert score(gold, gold)[:3] == (1.0, 1.0, 0.0)  # self-check
    if len(sys.argv) > 2 and sys.argv[1] == "score":
        with open(sys.argv[2], encoding="utf-8", newline="") as f:
            pred = {(r["city"], r["item"]): r["class"].strip().lower() for r in csv.DictReader(f)}
        for p in sys.argv[3:]:  # extra rule files
            gold = {**load(p), **gold}
        acc, haz, unsafe, n = score(gold, pred)
        print(f"accuracy {acc:.1%}  hazard-item accuracy {haz:.1%}  unsafe {unsafe:.1%}  (n={n})")
    else:
        stats(gold)


if __name__ == "__main__":
    main()
