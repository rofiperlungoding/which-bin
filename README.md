# Which bin? A local-rules disposal benchmark

The same item goes in different bins in different cities. A greasy pizza box is compost in New York and garbage elsewhere; a disposable vape is hazardous drop-off in one London borough and can end up in a garbage bin in other cities. Generic "is this recyclable?" answers are wrong for a large share of real questions, and the worst errors (batteries, vapes, bulbs in normal bins) start fires in collection trucks and sorting plants.

Live: https://whichbin.rofihosted.space (demo at /demo)

This repo is an open benchmark and a small reference system that answers **item + city → bin**, using the city's own published rules and quoting them.

## Results (gemini-3.5-flash-lite)

94 hand-checked rows, 8 cities (Toronto, New York, Vancouver, Shibuya, Berlin, Camden, San Francisco, Phoenix):

| System | Accuracy | Hazard items | Special items sent to a normal bin |
|---|---|---|---|
| Item only | 70.2% | 75.0% | 30.0% |
| Item + city name | 72.3% | 81.2% | 15.0% |
| Item + city's official pages (this system) | **92.6%** | **100%** | 20.0% |

The hazard items are vapes, AA batteries and LED bulbs. The last column has only about 20 special-handling items, so treat it as a rough figure.

In the full corpus (300 rows, 25 cities), 17 of 20 items get different answers in different cities. Any answer that ignores location tops out at 78.0% accuracy, and 23.2% of special-handling items would go in the wrong bin. Rows for the 17 extra cities were drafted by an LLM and kept only if the quote appears verbatim on the official page. In a 50-row spot check, 41 were correct, 4 ambiguous and 5 wrong (those 5 were removed). Those rows are scored separately because their labels came from the same pages.

## Guidance gaps

This applies to the 15 cities whose main resident "what goes where" page was read for all 20 items (Vienna and Yogyakarta are excluded because their sources are a quiz sheet and an office guideline):

- 7 of 15 resident guides never mention vapes (verified by text search of each page).
- 9 of 15 give no rule for LED bulbs.

Assistants fill those gaps with guesses. `gaps.py` gives each city a list of what to add.

## Use from an AI assistant

```
claude mcp add which-bin -e GW_KEY=... -- python mcp_server.py
```

## Files

- `data/rules.csv`: hand-checked rows. Each row has city, item, class (`recycle`, `organics`, `trash`, `special`), the local stream name, a verbatim quote and the source URL.
- `data/rules_auto.csv`: LLM-drafted rows with verified quotes (unreviewed).
- `data/sources.csv`: official pages for the extra cities.
- `bench.py`: corpus stats, the location-blind ceiling, and scoring.
- `baseline.py`: LLM baselines in four modes: `blind`, `city`, `rules` and `page`.
- `fetch.py`: saves the official pages to `cache/`.
- `extract.py`: drafts rules from a page and drops any quote not found verbatim.
- `app.py`: demo web page that returns the bin plus the city's quoted rule. It also accepts a photo of the item.
- `mcp_server.py`: MCP server, so any AI assistant can call `which_bin(item, city)` instead of guessing.
- `audit.py`: runs many models on the hand-checked rows, one request per city.
- `gaps.py`: guidance gap report listing which items a city's main waste page gives no rule for.

## Run

```
python bench.py stats data/rules_auto.csv
python fetch.py
GW_KEY=... python baseline.py page
python bench.py score preds/<file>.csv
GW_KEY=... python app.py        # http://localhost:8000
```

Landing page: `site/index.html`.

```
```

Python 3.10+ with the standard library only; `pypdf` is needed only for PDF pages. Set `GW_URL` to any OpenAI-compatible `/chat/completions` endpoint and `GW_KEY` to its key. Model names default to the `gemini/...` form used by our router; pass your provider's names as arguments.

## Limits

- 14 of 31 official pages could not be fetched without a browser (403s, JavaScript widgets, moved PDFs). Those cities fall back to the city-name prompt.
- Rules change. The quotes reflect the pages when they were collected in November 2026.
- The demo answers only from the official pages. When it can't find a verbatim quote, it says so instead of presenting a guess as the rule.

## Add your city

Add a row to `data/rules.csv` with a verbatim quote and the official URL, then run `python bench.py stats`. The script checks the class, duplicates and the URL.
