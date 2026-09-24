"""Run only stale validation nodes and derive completion from local artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any


class GraphError(ValueError):
    """The validation graph or a receipt is invalid."""


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _file_hash(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


class ImpactValidation:
    """A graph of ACs with explicit inputs, artifacts, and validation commands."""

    def __init__(self, root: Path, graph: dict[str, Any], receipt_dir: str = ".codbeing-validation"):
        self.root = root.resolve()
        self.receipt_dir = self._path(receipt_dir)
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise GraphError("graph needs a nodes list")
        self.nodes: dict[str, dict[str, Any]] = {}
        for node in graph["nodes"]:
            if not isinstance(node, dict) or not isinstance(node.get("id"), str) or not node["id"]:
                raise GraphError("each node needs an id")
            ident = node["id"]
            if ident in self.nodes or not ident.replace("_", "").replace("-", "").isalnum():
                raise GraphError(f"invalid or duplicate node id: {ident}")
            for key in ("depends_on", "inputs", "artifacts", "command"):
                if not isinstance(node.get(key), list) or not all(isinstance(item, str) and item for item in node[key]):
                    raise GraphError(f"{ident}: {key} must be a string list")
            if not node["command"] or not node["artifacts"]:
                raise GraphError(f"{ident}: command and artifacts cannot be empty")
            if len(set(node["depends_on"])) != len(node["depends_on"]):
                raise GraphError(f"{ident}: duplicate dependency")
            for name in node["inputs"] + node["artifacts"]:
                if self._path(name) == self.receipt_dir or self.receipt_dir in self._path(name).parents:
                    raise GraphError("receipts cannot be graph inputs or artifacts")
            self.nodes[ident] = node
        self.order: list[str] = []
        visiting: set[str] = set()

        def visit(ident: str) -> None:
            if ident in visiting:
                raise GraphError("dependency cycle")
            if ident in self.order:
                return
            visiting.add(ident)
            for dep in self.nodes[ident]["depends_on"]:
                if dep not in self.nodes:
                    raise GraphError(f"{ident}: unknown dependency {dep}")
                visit(dep)
            visiting.remove(ident)
            self.order.append(ident)

        for ident in self.nodes:
            visit(ident)

    def _path(self, name: str) -> Path:
        if not isinstance(name, str) or not name or Path(name).is_absolute():
            raise GraphError("paths must be workspace relative")
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root):
            raise GraphError("path escapes workspace")
        return path

    def _receipt_path(self, ident: str) -> Path:
        return self.receipt_dir / f"{ident}.json"

    def _snapshot(self, ident: str, dependency_receipts: dict[str, str]) -> dict[str, Any]:
        node = self.nodes[ident]
        return {
            "node_hash": _digest(node),
            "inputs": {name: _file_hash(self._path(name)) for name in node["inputs"]},
            "artifacts": {name: _file_hash(self._path(name)) for name in node["artifacts"]},
            "dependencies": dependency_receipts,
        }

    def _read_receipt(self, ident: str) -> dict[str, Any] | None:
        try:
            value = json.loads(self._receipt_path(ident).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        if not isinstance(value, dict) or value.get("receipt_hash") != _digest({k: v for k, v in value.items() if k != "receipt_hash"}):
            return None
        return value

    def _archive_artifacts(self, ident: str) -> list[dict[str, str]]:
        """Keep prior immutable outputs before regenerating a stale node."""
        archived = []
        archive_root = self.receipt_dir / "history" / ident / uuid.uuid4().hex
        for name in self.nodes[ident]["artifacts"]:
            source = self._path(name)
            if not source.is_file():
                continue
            destination = archive_root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            digest = _file_hash(source)
            os.replace(source, destination)
            archived.append({"original": name, "archive": destination.relative_to(self.root).as_posix(), "sha256": digest})
        return archived

    def status(self) -> dict[str, Any]:
        """Report completion only when each receipt matches current files and dependencies."""
        result: dict[str, Any] = {}
        for ident in self.order:
            node = self.nodes[ident]
            deps = node["depends_on"]
            receipt = self._read_receipt(ident)
            dependency_receipts = {dep: result[dep]["receipt_hash"] for dep in deps if result[dep]["complete"]}
            snapshot = self._snapshot(ident, dependency_receipts)
            complete = (
                len(dependency_receipts) == len(deps)
                and receipt is not None
                and receipt.get("exit_code") == 0
                and receipt.get("snapshot") == snapshot
                and all(snapshot["artifacts"].values())
                and all(snapshot["inputs"].values())
            )
            result[ident] = {
                "complete": bool(complete),
                "reason": "current" if complete else "stale_or_missing_evidence",
                "receipt_hash": receipt["receipt_hash"] if complete else None,
            }
        return result

    def run(self) -> dict[str, Any]:
        """Execute stale nodes in topological order, stopping at the first failure."""
        for ident in self.order:
            if self.status()[ident]["complete"]:
                continue
            node = self.nodes[ident]
            missing = [name for name in node["inputs"] if not self._path(name).is_file()]
            if missing:
                raise GraphError(f"{ident}: missing inputs: {', '.join(missing)}")
            archived_artifacts = self._archive_artifacts(ident)
            process = subprocess.run(node["command"], cwd=self.root, capture_output=True, text=True, check=False)
            deps = {dep: self.status()[dep]["receipt_hash"] for dep in node["depends_on"]}
            receipt = {
                "ac_id": ident,
                "run_id": uuid.uuid4().hex,
                "command": node["command"],
                "exit_code": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "archived_artifacts": archived_artifacts,
                "snapshot": self._snapshot(ident, deps),
            }
            receipt["receipt_hash"] = _digest(receipt)
            self.receipt_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.receipt_dir, delete=False) as stream:
                json.dump(receipt, stream, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
                temporary = Path(stream.name)
            os.replace(temporary, self._receipt_path(ident))
            if process.returncode:
                raise GraphError(f"{ident}: validation failed with exit code {process.returncode}: {process.stderr.strip()}")
            if not all(receipt["snapshot"]["artifacts"].values()):
                raise GraphError(f"{ident}: validation did not produce every artifact")
        return self.status()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph", type=Path)
    parser.add_argument("action", choices=("status", "run"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--receipt-dir", default=".codbeing-validation")
    args = parser.parse_args(argv)
    try:
        validation = ImpactValidation(args.root, json.loads(args.graph.read_text(encoding="utf-8")), args.receipt_dir)
        result = validation.status() if args.action == "status" else validation.run()
    except (GraphError, OSError, json.JSONDecodeError) as error:
        parser.exit(2, f"impact validation error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
