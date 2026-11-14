"""LLM baselines for bench.py. Writes preds/<model>__<mode>.csv.

  GW_KEY=... python baseline.py [blind|city|rules] [model]

  blind  item only, no location
  city   item + city name (model must rely on what it already knows)
  rules  item + city name + every official rule snippet for that city, shuffled
         (simulates retrieval of the city's page; the model must pick the right rule)
  page   item + city name + the city's whole official pages from cache/ (python fetch.py);
         end to end, no gold quotes. A city with no snapshot falls back to the city prompt.
"""
import csv, json, os, random, sys, time, urllib.request
from pathlib import Path
from bench import CLASSES, RULES, load

GW = os.environ.get("GW_URL", "")  # any OpenAI-compatible /chat/completions URL
NAMES = {
    "pizza_box_greasy": "greasy pizza box", "plastic_bag": "plastic shopping bag",
    "paper_cup": "disposable paper coffee cup", "alu_foil": "clean aluminium foil",
    "glass_jar": "empty glass jar", "pet_bottle": "plastic water bottle",
    "eps_takeaway": "polystyrene (styrofoam) takeaway container", "vape": "disposable vape",
    "aa_battery": "AA alkaline battery", "charging_cable": "phone charging cable",
    "carton": "juice/milk drink carton", "pet_clamshell": "clear plastic berry clamshell",
    "pp_cup": "plastic yoghurt cup", "shredded_paper": "shredded paper",
    "led_bulb": "LED light bulb", "paper_towel": "used paper towel",
    "aerosol_empty": "empty aerosol can", "drinking_glass": "broken drinking glass",
    "toothpaste_tube": "empty toothpaste tube", "plastic_cap": "loose plastic bottle cap",
}
CITY = {"toronto": "Toronto, Canada", "nyc": "New York City, USA", "vancouver": "Vancouver, Canada",
        "shibuya": "Shibuya, Tokyo, Japan", "berlin": "Berlin, Germany", "camden": "Camden, London, UK",
        "san_francisco": "San Francisco, USA", "phoenix": "Phoenix, USA"}
TASK = ("Classify where a household should put this item. Answer with exactly one word:\n"
        "recycle (curbside recycling), organics (food/green bin), trash (general garbage, including "
        "non-combustible garbage), special (drop-off, take-back, deposit return or hazardous collection; "
        "not any household bin).\n")


def ask(key, model, prompt):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 20,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for attempt in range(5):
        req = urllib.request.Request(GW, body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                                    "User-Agent": "arbiter-bench/0.1"})  # Cloudflare blocks urllib's default UA
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                text = json.load(r)["choices"][0]["message"]["content"] or ""
            word = text.strip().lower().split()[0].strip(".,:;*\"'") if text.strip() else ""
            word = {"organic": "organics", "recycling": "recycle", "garbage": "trash"}.get(word, word)
            return word if word in CLASSES else "invalid"
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                time.sleep(10 * (attempt + 1)); continue
            raise
    return "error"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "blind"
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini/gemini-3.5-flash-lite"
    assert mode in {"blind", "city", "rules", "page"}
    key = os.environ["GW_KEY"]
    assert GW, "set GW_URL to an OpenAI-compatible /chat/completions endpoint"
    files = [RULES] + [Path(x) for x in os.environ.get("EXTRA_RULES", "").split(",") if x]
    rows, gold = [], {}
    for fp in files:
        with open(fp, encoding="utf-8", newline="") as f:
            rows += list(csv.DictReader(f))
        gold = {**load(fp), **gold}
    country = {r["city"]: r["country"] for r in rows}
    snippets = {}
    for r in rows:
        snippets.setdefault(r["city"], []).append(f'- [{r["local_stream"]}] {r["quote"]}')
    tag = "__v1" if len(files) > 1 else ""
    out = Path("preds") / f'{model.replace("/", "_")}__{mode}{tag}.csv'
    out.parent.mkdir(exist_ok=True)
    done = {}
    if out.exists():  # resume
        with open(out, encoding="utf-8", newline="") as f:
            done = {(r["city"], r["item"]): r["class"] for r in csv.DictReader(f) if r["class"] not in {"error", "invalid"}}
    rng = random.Random(0)
    for city, item in gold:
        if (city, item) in done:
            continue
        p = TASK + f"Item: {NAMES[item]}\n"
        if mode in {"city", "rules", "page"}:
            p += f"City: {CITY.get(city, city.replace('_', ' ').title() + ', ' + country[city])}\n"
        if mode == "rules":
            s = snippets[city][:]; rng.shuffle(s)
            p += "Official rules published by this city (some lines are about other items):\n" + "\n".join(s) + "\n"
        page = Path("cache") / f"{city}.txt"
        if mode == "page" and page.exists():  # ponytail: whole page in context (max ~40k chars today); chunk retrieval if pages grow
            p += "Official waste pages published by this city:\n" + page.read_text(encoding="utf-8")[:60000] + "\n"
        done[(city, item)] = ask(key, model, p + "Answer:")
        print(city, item, done[(city, item)], "gold:", gold[(city, item)], flush=True)
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["city", "item", "class"])
            w.writerows((c, i, v) for (c, i), v in done.items())
        time.sleep(1)
    print("wrote", out)


if __name__ == "__main__":
    main()
