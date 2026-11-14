# Graph Report - Arbiter Hacks V1  (2026-11-14)

## Corpus Check
- 9 files · ~5,351 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: .csv 17, (none) 2)

## Summary
- 34 nodes · 43 edges · 5 communities (2 shown, 3 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `58b7f239`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- answer
- page
- Which bin? A local-rules disposal benchmark
- budget

## God Nodes (most connected - your core abstractions)
1. `Which bin? A local-rules disposal benchmark` - 8 edges
2. `answer()` - 5 edges
3. `budget()` - 5 edges
4. `identify()` - 5 edges
5. `H` - 4 edges
6. `page()` - 4 edges
7. `Files` - 2 edges
8. `Results (gemini-3.5-flash-lite)` - 1 edges
9. `Guidance gaps` - 1 edges
10. `Use from an AI assistant` - 1 edges

## Surprising Connections (you probably didn't know these)
- `Files` --references--> `page()`  [INFERRED]
  README.md → app.py

## Import Cycles
- None detected.

## Communities (5 total, 3 thin omitted)

### Community 1 - "answer"
Cohesion: 0.25
Nodes (3): answer(), H, identify()

### Community 3 - "Which bin? A local-rules disposal benchmark"
Cohesion: 0.25
Nodes (7): Add your city, Guidance gaps, Limits, Results (gemini-3.5-flash-lite), Run, Use from an AI assistant, Which bin? A local-rules disposal benchmark

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `page()` connect `page` to `app.py`, `answer`?**
  _High betweenness centrality (0.419) - this node is a cross-community bridge._
- **Why does `Which bin? A local-rules disposal benchmark` connect `Which bin? A local-rules disposal benchmark` to `page`?**
  _High betweenness centrality (0.384) - this node is a cross-community bridge._
- **Why does `Files` connect `page` to `Which bin? A local-rules disposal benchmark`?**
  _High betweenness centrality (0.379) - this node is a cross-community bridge._