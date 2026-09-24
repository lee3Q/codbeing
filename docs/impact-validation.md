# Change impact validation

`codbeing.impact_validation` reads a JSON graph of acceptance criteria. Each node
declares its direct dependencies, workspace-relative input files, produced
artifacts, and a validation command as an argument list. The graph is checked
for missing dependencies and cycles.

```json
{
  "nodes": [
    {
      "id": "ac1",
      "depends_on": [],
      "inputs": ["src/decision.py"],
      "artifacts": ["ac1-result.xml"],
      "command": ["python3", "-m", "pytest", "-q", "tests/test_decision.py", "--junitxml=ac1-result.xml"]
    },
    {
      "id": "ac4",
      "depends_on": ["ac1"],
      "inputs": ["src/impact.py"],
      "artifacts": ["ac4-result.xml"],
      "command": ["python3", "-m", "pytest", "-q", "tests/test_impact.py", "--junitxml=ac4-result.xml"]
    }
  ]
}
```

Save the graph in the workspace, then run:

```bash
python3 -m codbeing.impact_validation graph.json status
python3 -m codbeing.impact_validation graph.json run
```

`run` validates stale nodes in dependency order. A changed input, artifact,
command, or upstream receipt makes that node stale. A rerun gives its downstream
nodes a new dependency receipt, so only affected descendants rerun. Failed
commands and missing artifacts do not count as complete. `status` is read-only:
it calculates completion from successful command receipts, current file hashes,
and dependency receipts, regardless of any agent's completion claim. Receipts
are local files under `.codbeing-validation`; preserve them for incremental
runs. The hash-linked evidence ledger can separately record a release's
immutable evidence chain.

The executable public graph is `examples/synthetic-cycle/validation-graph.json`.
Run it with `python3 -m codbeing.impact_validation
examples/synthetic-cycle/validation-graph.json run --receipt-dir
.codbeing-validation/public-cycle`. Its four nodes build the model, produce
the prediction, compare the later choice, and verify the files. The receipts
contain exact argv, exit code, output, and artifact hashes. Changing a direct
decision invalidates the model and descendants; changing only the actual
choice invalidates comparison and verification.
