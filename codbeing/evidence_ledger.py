"""Local, hash-linked evidence events for an auditable work cycle."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KINDS = {"seed", "acceptance_criterion", "command", "test_receipt", "artifact", "handoff"}
FILE_KINDS = {"seed", "test_receipt", "artifact", "handoff"}
GENESIS = "0" * 64


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class LedgerError(ValueError):
    """An event or its referenced evidence failed verification."""


class EvidenceLedger:
    def __init__(self, root: Path, ledger: Path):
        self.root = root.resolve()
        self.ledger = (self.root / ledger).resolve()
        if not self.ledger.is_relative_to(self.root):
            raise LedgerError("ledger must stay within the workspace")

    def _file_ref(self, path: str) -> dict[str, str]:
        if not isinstance(path, str) or not path:
            raise LedgerError("evidence path must be a workspace-relative file")
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root) or target == self.ledger or not target.is_file():
            raise LedgerError(f"invalid workspace evidence file: {path}")
        return {"path": target.relative_to(self.root).as_posix(), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    def _replay(self, lines: list[str], expected_head: str | None = None) -> dict[str, Any]:
        state: dict[str, Any] = {"head": GENESIS, "seed": None, "criteria": {}}
        if lines and not lines[-1].endswith("\n"):
            raise LedgerError("incomplete final event")
        for number, line in enumerate(lines, 1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise LedgerError(f"invalid JSON at event {number}") from error
            if not isinstance(event, dict) or event.get("sequence") != number or event.get("previous_hash") != state["head"]:
                raise LedgerError(f"broken event chain at event {number}")
            digest = event.get("event_hash")
            if digest != _hash({key: value for key, value in event.items() if key != "event_hash"}):
                raise LedgerError(f"event hash mismatch at event {number}")
            kind = event.get("kind")
            if kind not in KINDS:
                raise LedgerError(f"unknown event kind at event {number}")
            if kind in FILE_KINDS:
                file_ref = event.get("file")
                if not isinstance(file_ref, dict) or file_ref != self._file_ref(file_ref.get("path", "")):
                    raise LedgerError(f"evidence file changed at event {number}")
            ac_id = event.get("ac_id")
            if kind == "seed":
                if state["seed"] is not None:
                    raise LedgerError("only one seed may be recorded")
                state["seed"] = digest
            elif kind == "acceptance_criterion":
                if state["seed"] is None or not isinstance(ac_id, str) or not ac_id or ac_id in state["criteria"]:
                    raise LedgerError(f"invalid criterion at event {number}")
                if not isinstance(event.get("text"), str) or not event["text"].strip() or event.get("source_hash") != state["seed"]:
                    raise LedgerError(f"invalid criterion source at event {number}")
                state["criteria"][ac_id] = {"status": "registered", "criterion_hash": digest, "last_command": None, "last_argv": None, "last_receipt": None, "artifacts": [], "handoff": None}
            else:
                criterion = state["criteria"].get(ac_id)
                if criterion is None or event.get("criterion_hash") != criterion["criterion_hash"]:
                    raise LedgerError(f"missing criterion link at event {number}")
                if kind == "command":
                    if not isinstance(event.get("text"), str) or not event["text"].strip():
                        raise LedgerError(f"empty command at event {number}")
                    criterion["last_command"] = digest
                    try:
                        criterion["last_argv"] = json.loads(event["text"])
                    except json.JSONDecodeError:
                        criterion["last_argv"] = None
                    criterion["status"] = "command_recorded"
                elif kind == "test_receipt":
                    if criterion["last_command"] is None or event.get("command_hash") != criterion["last_command"]:
                        raise LedgerError(f"missing command link at event {number}")
                    evidence = json.loads((self.root / event["file"]["path"]).read_text(encoding="utf-8"))
                    if (not isinstance(evidence, dict) or evidence.get("command_hash") != criterion["last_command"]
                            or evidence.get("argv") != criterion["last_argv"]
                            or not isinstance(evidence.get("exit_code"), int)
                            or not isinstance(evidence.get("stdout"), str)
                            or not isinstance(evidence.get("stderr"), str)
                            or event.get("passed") is not (evidence["exit_code"] == 0)):
                        raise LedgerError(f"invalid process receipt at event {number}")
                    criterion["last_receipt"] = digest
                    criterion["status"] = "verified" if event["passed"] else "failed"
                elif kind == "artifact":
                    if criterion["status"] != "verified" or event.get("receipt_hash") != criterion["last_receipt"]:
                        raise LedgerError(f"missing passing receipt link at event {number}")
                    criterion["artifacts"].append(digest)
                elif kind == "handoff":
                    if not criterion["artifacts"] or event.get("artifact_hashes") != criterion["artifacts"]:
                        raise LedgerError(f"missing artifact links at event {number}")
                    criterion["handoff"] = digest
                    criterion["status"] = "handed_off"
            state["head"] = digest
        if expected_head is not None and state["head"] != expected_head:
            raise LedgerError("head differs from external anchor")
        return state

    def verify(self, *, expected_head: str | None = None) -> dict[str, Any]:
        if not self.ledger.exists():
            raise LedgerError("ledger does not exist")
        with self.ledger.open("r", encoding="utf-8") as stream:
            return self._replay(stream.readlines(), expected_head)

    def append(self, kind: str, *, ac_id: str | None = None, text: str | None = None,
               path: str | None = None, passed: bool | None = None,
               _observed: bool = False) -> dict[str, Any]:
        if kind not in KINDS:
            raise LedgerError(f"unknown event kind: {kind}")
        if (kind in FILE_KINDS) != (path is not None):
            raise LedgerError("file required only for file-backed event kinds")
        if kind in {"acceptance_criterion", "command"} and (not isinstance(text, str) or not text.strip()):
            raise LedgerError("criterion and command require text")
        if kind == "test_receipt" and not isinstance(passed, bool):
            raise LedgerError("test receipt requires a pass/fail result")
        if kind == "test_receipt" and not _observed:
            raise LedgerError("test receipts must come from ledger.run, which executes the command")
        if kind != "seed" and (not isinstance(ac_id, str) or not ac_id):
            raise LedgerError("event requires an AC id")
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a+", encoding="utf-8") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            lines = stream.readlines()
            state = self._replay(lines)
            event: dict[str, Any] = {
                "sequence": len(lines) + 1, "previous_hash": state["head"],
                "kind": kind, "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            if path is not None:
                event["file"] = self._file_ref(path)
            if text is not None:
                event["text"] = text
            if ac_id is not None:
                event["ac_id"] = ac_id
            if kind == "acceptance_criterion":
                event["source_hash"] = state["seed"]
            elif kind != "seed":
                criterion = state["criteria"].get(ac_id)
                if criterion is None:
                    raise LedgerError("record the criterion before its evidence")
                event["criterion_hash"] = criterion["criterion_hash"]
                if kind == "test_receipt":
                    event["command_hash"] = criterion["last_command"]
                    event["passed"] = passed
                elif kind == "artifact":
                    event["receipt_hash"] = criterion["last_receipt"]
                elif kind == "handoff":
                    event["artifact_hashes"] = criterion["artifacts"][:]
            event["event_hash"] = _hash(event)
            self._replay(lines + [_canonical(event).decode("utf-8") + "\n"])
            stream.seek(0, os.SEEK_END)
            stream.write(_canonical(event).decode("utf-8") + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            return event

    def run(self, ac_id: str, argv: list[str], receipt_path: str) -> tuple[dict[str, Any], dict[str, Any]]:
        """Execute an argv vector and append its observed result, never caller-supplied success."""
        if not argv or not all(isinstance(arg, str) and arg for arg in argv):
            raise LedgerError("run requires a non-empty argv vector")
        target = (self.root / receipt_path).resolve()
        if not target.is_relative_to(self.root) or target.exists() or target == self.ledger:
            raise LedgerError("receipt path must be a new workspace-relative file")
        command = self.append("command", ac_id=ac_id, text=json.dumps(argv, ensure_ascii=False))
        try:
            process = subprocess.run(argv, cwd=self.root, capture_output=True, text=True, check=False)
            exit_code, stdout, stderr = process.returncode, process.stdout, process.stderr
        except OSError as error:
            exit_code, stdout, stderr = 127, "", str(error)
        receipt = {"command_hash": command["event_hash"], "argv": argv,
                   "exit_code": exit_code, "stdout": stdout, "stderr": stderr}
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
        return command, self.append("test_receipt", ac_id=ac_id, path=receipt_path,
                                    passed=exit_code == 0, _observed=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="action", required=True)
    record = sub.add_parser("record")
    record.add_argument("kind", choices=sorted(KINDS))
    record.add_argument("--ac-id")
    record.add_argument("--text")
    record.add_argument("--file")
    record.add_argument("--passed", choices=("true", "false"))
    run = sub.add_parser("run")
    run.add_argument("--ac-id", required=True)
    run.add_argument("--receipt", required=True)
    run.add_argument("argv", nargs=argparse.REMAINDER)
    check = sub.add_parser("verify")
    check.add_argument("--expected-head")
    args = parser.parse_args(argv)
    ledger = EvidenceLedger(args.root, args.ledger)
    try:
        if args.action == "record":
            result = ledger.append(args.kind, ac_id=args.ac_id, text=args.text, path=args.file,
                                   passed=None if args.passed is None else args.passed == "true")
        elif args.action == "run":
            argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
            command, receipt = ledger.run(args.ac_id, argv, args.receipt)
            result = {"command": command, "receipt": receipt}
        else:
            result = ledger.verify(expected_head=args.expected_head)
    except (LedgerError, OSError) as error:
        parser.exit(2, f"evidence ledger error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
