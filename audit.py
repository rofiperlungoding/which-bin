"""Audit many models on the hand-checked rows, cheaply: one request per city, all items at once.

  GW_KEY=... python audit.py model [model ...]   -> preds/audit/<model>__<mode>.csv, then a score table
  blind: one request for all 20 items (no location). city: one request per city.
Batched prompting is not the same as one question per item; it lets low-quota models be audited.
"""
import csv, sys, time
from pathlib import Path
from baseline import NAMES, CITY, TASK
from bench import CLASSES, RULES, load, score
from extract import ask

OUT = Path("preds") / "audit"


def run(model, mode, gold):
    out = OUT / f'{model.replace("/", "_")}__{mode}.csv'
    if out.exists():
        with open(out, encoding="utf-8", newline="") as f:
            return {(r["city"], r["item"]): r["class"] for r in csv.DictReader(f)}
    cities = sorted({c for c, _ in gold})
    items = "\n".join(f"- {k}: {v}" for k, v in NAMES.items())
    pred = {}
    for where in ([None] if mode == "blind" else cities):
        p = TASK.replace("Answer with exactly one word", "For each item answer with one word") + (
            f"City: {CITY[where]}\n" if where else "") + f"Items:\n{items}\n" + 'Return JSON only: {"item_id": "class", ...}'
        for attempt in range(3):
            try:
                ans = ask(p, model); break
            except Exception as e:
                print(model, where, type(e).__name__, getattr(e, "code", ""), flush=True); time.sleep(20)
        else:
            return None  # quota or outage: skip this model, rerun later
        for c in (cities if mode == "blind" else [where]):
            for i in NAMES:
                v = str(ans.get(i, "")).strip().lower()
                pred[(c, i)] = {"organic": "organics", "recycling": "recycle", "garbage": "trash"}.get(v, v)
        time.sleep(2)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["city", "item", "class"])
        w.writerows((c, i, v) for (c, i), v in pred.items())
    return pred


def main():
    gold = load(RULES)
    print(f"{'model':<42} {'mode':<6} accuracy  hazard  unsafe")
    for model in sys.argv[1:]:
        for mode in ("blind", "city"):
            pred = run(model, mode, gold)
            if pred is None:
                print(f"{model:<42} {mode:<6} skipped"); continue
            acc, haz, unsafe, n = score(gold, pred)
            bad = sum(pred.get(k) not in CLASSES for k in gold)
            print(f"{model:<42} {mode:<6} {acc:7.1%} {haz:7.1%} {unsafe:7.1%}  invalid {bad}", flush=True)


if __name__ == "__main__":
    main()
