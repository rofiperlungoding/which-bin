"""Guidance gap report: which items each city's official pages give no clear rule for.

  python gaps.py        (cities in data/rules_auto.csv only)
Those cities were extracted from one main "what goes where" page for all items, so a missing row means
that page gives no clear, quotable rule. Hand-checked cities were collected for chosen items only: not a gap signal.
"""
from bench import HAZARD, RULES, load
from baseline import NAMES

gold = load(RULES.with_name("rules_auto.csv"))
cities = sorted({c for c, _ in gold})
print(f"{len(cities)} cities, {len(NAMES)} items")
for item in sorted(NAMES, key=lambda i: sum((c, i) in gold for c in cities)):
    silent = [c for c in cities if (c, item) not in gold]
    tag = " HAZARD" if item in HAZARD else ""
    print(f"{item:<18}{tag:<7} silent in {len(silent):>2}/{len(cities)}: {', '.join(silent)}")
cover = {c: sum((c, i) in gold for i in NAMES) for c in cities}
print("\ncoverage per city:", ", ".join(f"{c} {n}/{len(NAMES)}" for c, n in sorted(cover.items(), key=lambda x: x[1])))
