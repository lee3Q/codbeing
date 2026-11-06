# codbeing compared with similar open-source tools

Read on 2026-11-06 from each project's public GitHub page. These are small,
young projects and they change. Check the linked pages before relying on a
row. This is a fit guide, not a quality ranking, and no tool was benchmarked.

| Tool | Main use | Storage | Model use | License shown |
|---|---|---|---|---|
| codbeing | Record a decision, its reasoning and options, then add a later observation and compare | Local JSON files in your working folder | Local report by default; GLM only if you choose it and confirm | None selected yet |
| [Regret Ledger](https://github.com/theglitcharchitect/Regret-ledger) | Log decisions with a confidence score, score outcomes later, check calibration | Local SQLite file | Claude API key needed for its `insights` command | Not shown on the page |
| [Sage](https://github.com/divijg19/Sage) | Developer decision and reasoning journal as an append-only event log | Local event log | Not part of its stated core | Not shown on the page |
| [dictum](https://github.com/teekay/dictum) | Project decisions as a linked graph, aimed at coding agents and teams | `.dictum/` folder with SQLite | Not required | MIT |

## Where codbeing fits

- It is for one person's own consequential choices, not project or team
  decisions. Dictum and Sage target developers and codebases.
- It keeps the original record untouched and writes later observations to a
  separate file with a digest. Edits to that file stay possible, so it is
  not proof of what you knew beforehand.
- Reports only restate the fields you recorded. They make no personality
  claims and no prediction of accuracy for a person.

## Where the others are ahead

- Regret Ledger has outcome scoring, a confidence-versus-outcome view and a
  reminder date. codbeing has none of these.
- Dictum and Sage have search, links between records and a TUI or HTML view.
  codbeing has `list` and `show` only.
- Dictum is published under MIT. codbeing has no license yet, so others have
  no stated right to reuse it.

## Choose another tool if

- You want calibration statistics over many scored decisions.
- You track team or code decisions.
- You need a license that allows reuse today.
