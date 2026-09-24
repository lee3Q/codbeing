"""Local, hash-linked evidence events for an auditable work cycle."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import selectors
import signal
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KINDS = {"seed", "acceptance_criterion", "command", "test_receipt", "artifact", "invalidation", "handoff"}
FILE_KINDS = {"seed", "test_receipt", "artifact", "handoff"}
GENESIS = "0" * 64
MAX_CAPTURE_BYTES = 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


class LedgerError(ValueError):
    """An event or its referenced evidence failed verification."""


def _execute_bounded(argv: list[str], root: Path, timeout: float) -> tuple[int, str, str, str]:
    """Capture a subprocess without allowing either stream to exceed its memory bound."""
    try:
        process = subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
    except OSError as error:
        return 127, "", str(error), "launch_error"
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    outcome = "exited"
    deadline = time.monotonic() + timeout

    def stop() -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()

    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    outcome = "timeout"
                    stop()
                    break
                for key, _ in selector.select(timeout=min(remaining, 0.25)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffer = buffers[key.data]
                    buffer.extend(chunk[:MAX_CAPTURE_BYTES + 1 - len(buffer)])
                    if len(buffer) > MAX_CAPTURE_BYTES:
                        outcome = "output_limit"
                        stop()
                        break
                if outcome != "exited":
                    break
        if outcome == "exited":
            try:
                process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                outcome = "timeout"
                stop()
    except KeyboardInterrupt:
        outcome = "interrupted"
        stop()
    finally:
        process.stdout.close()
        process.stderr.close()
    exit_code = {"timeout": 124, "output_limit": 125, "interrupted": 130}.get(outcome, process.returncode)
    stdout = buffers["stdout"][:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")
    stderr = buffers["stderr"][:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")
    if outcome == "interrupted" and not stderr:
        stderr = "interrupted"
    return exit_code, stdout, stderr, outcome


class EvidenceLedger:
    def __init__(self, root: Path, ledger: Path):
        self.root = root.resolve()
        self.ledger = (self.root / ledger).resolve()
        if not self.ledger.is_relative_to(self.root):
            raise LedgerError("ledger must stay within the workspace")

    def _file_ref(self, path: str) -> dict[str, str]:
        if not isinstance(path, str) or not path or Path(path).is_absolute():
            raise LedgerError("evidence path must be a workspace-relative file")
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root) or target == self.ledger or not target.is_file():
            raise LedgerError(f"invalid workspace evidence file: {path}")
        if target.stat().st_size > MAX_EVIDENCE_BYTES:
            raise LedgerError(f"evidence file exceeds size limit: {path}")
        return {"path": target.relative_to(self.root).as_posix(), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}

    def _snapshot(self, paths: list[str]) -> dict[str, str | None]:
        snapshot: dict[str, str | None] = {}
        for path in paths:
            if not isinstance(path, str) or not path or Path(path).is_absolute():
                raise LedgerError("artifact paths must be workspace-relative")
            target = (self.root / path).resolve()
            if not target.is_relative_to(self.root) or target == self.ledger:
                raise LedgerError("artifact path escapes workspace or names ledger")
            name = target.relative_to(self.root).as_posix()
            if name in snapshot:
                raise LedgerError("duplicate artifact path")
            if target.is_file() and target.stat().st_size > MAX_EVIDENCE_BYTES:
                raise LedgerError(f"artifact exceeds size limit: {path}")
            snapshot[name] = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
        return snapshot

    def _replay(self, lines: list[str], expected_head: str | None = None) -> dict[str, Any]:
        state: dict[str, Any] = {"head": GENESIS, "seed": None, "criteria": {}}
        events: list[dict[str, Any]] = []
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
            if not isinstance(kind, str) or kind not in KINDS:
                raise LedgerError(f"unknown event kind at event {number}")
            if kind in FILE_KINDS and kind != "artifact":
                file_ref = event.get("file")
                if not isinstance(file_ref, dict) or file_ref != self._file_ref(file_ref.get("path", "")):
                    raise LedgerError(f"evidence file changed at event {number}")
            ac_id = event.get("ac_id")
            if kind != "seed" and (not isinstance(ac_id, str) or not ac_id):
                raise LedgerError(f"invalid criterion link at event {number}")
            if kind == "seed":
                if state["seed"] is not None:
                    raise LedgerError("only one seed may be recorded")
                state["seed"] = digest
            elif kind == "acceptance_criterion":
                if state["seed"] is None or not isinstance(ac_id, str) or not ac_id or ac_id in state["criteria"]:
                    raise LedgerError(f"invalid criterion at event {number}")
                if not isinstance(event.get("text"), str) or not event["text"].strip() or event.get("source_hash") != state["seed"]:
                    raise LedgerError(f"invalid criterion source at event {number}")
                dependencies = event.get("depends_on", [])
                if (not isinstance(dependencies, list)
                        or any(not isinstance(item, str) or item not in state["criteria"] for item in dependencies)
                        or len(dependencies) != len(set(dependencies))):
                    raise LedgerError(f"invalid criterion dependencies at event {number}")
                state["criteria"][ac_id] = {"status": "registered", "depends_on": dependencies,
                                            "criterion_hash": digest, "last_command": None, "last_argv": None,
                                            "last_receipt": None, "artifacts": [], "artifact_files": [],
                                            "handoff": None, "attempts": [], "last_output_hashes": {}}
            else:
                criterion = state["criteria"].get(ac_id)
                if criterion is None or event.get("criterion_hash") != criterion["criterion_hash"]:
                    raise LedgerError(f"missing criterion link at event {number}")
                if kind == "command":
                    if not isinstance(event.get("text"), str) or not event["text"].strip():
                        raise LedgerError(f"empty command at event {number}")
                    criterion["last_command"] = digest
                    criterion["artifacts"] = []
                    criterion["artifact_files"] = []
                    criterion["handoff"] = None
                    if "attempt_id" in event:
                        if (not isinstance(event["attempt_id"], str) or not event["attempt_id"]
                                or not isinstance(event.get("inputs"), dict) or not isinstance(event.get("outputs"), list)):
                            raise LedgerError(f"invalid command provenance at event {number}")
                        if any(value is None for value in event["inputs"].values()):
                            raise LedgerError(f"missing command input at event {number}")
                    try:
                        criterion["last_argv"] = json.loads(event["text"])
                    except json.JSONDecodeError:
                        criterion["last_argv"] = None
                    criterion["status"] = "command_recorded"
                elif kind == "test_receipt":
                    if criterion["last_command"] is None or event.get("command_hash") != criterion["last_command"]:
                        raise LedgerError(f"missing command link at event {number}")
                    if event.get("passed") is True and "attempt_id" not in event:
                        raise LedgerError(f"passing receipt lacks observed attempt at event {number}")
                    try:
                        evidence = json.loads((self.root / event["file"]["path"]).read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as error:
                        raise LedgerError(f"invalid process receipt at event {number}") from error
                    if (not isinstance(evidence, dict) or evidence.get("command_hash") != criterion["last_command"]
                            or evidence.get("argv") != criterion["last_argv"]
                            or not isinstance(evidence.get("inputs"), dict)
                            or not isinstance(evidence.get("output_paths"), list)
                            or any(not isinstance(path, str) for path in evidence["output_paths"])
                            or not isinstance(evidence.get("outputs"), dict)
                            or set(evidence["outputs"]) != set(evidence["output_paths"])
                            or any(value is not None and (not isinstance(value, str) or len(value) != 64)
                                   for value in evidence["outputs"].values())
                            or not isinstance(evidence.get("exit_code"), int)
                            or not isinstance(evidence.get("stdout"), str)
                            or not isinstance(evidence.get("stderr"), str)
                            or event.get("passed") is not (evidence["exit_code"] == 0 and
                                evidence.get("outcome", "exited") == "exited" and
                                all(evidence["outputs"].values()))):
                        raise LedgerError(f"invalid process receipt at event {number}")
                    if "attempt_id" in event:
                        command = next((item for item in reversed(events) if item["event_hash"] == criterion["last_command"]), None)
                        if (command is None or evidence.get("attempt_id") != command.get("attempt_id")
                                or event["attempt_id"] != command.get("attempt_id")
                                or evidence.get("inputs") != command.get("inputs")
                                or evidence.get("output_paths") != command.get("outputs")
                                or event.get("exit_code") != evidence["exit_code"]
                                or event.get("stdout") != evidence["stdout"]
                                or event.get("stderr") != evidence["stderr"]
                                or event.get("inputs") != evidence["inputs"]
                                or event.get("outputs") != evidence.get("outputs")
                                or evidence.get("outcome") not in {"exited", "timeout", "interrupted", "launch_error", "output_limit"}
                                or (evidence["outcome"] != "exited" and event["passed"])):
                            raise LedgerError(f"mismatched attempt receipt at event {number}")
                        criterion["attempts"].append({"attempt_id": event["attempt_id"], "receipt_hash": digest,
                                                       "exit_code": evidence["exit_code"], "outcome": evidence["outcome"]})
                    criterion["last_receipt"] = digest
                    criterion["status"] = "verified" if event["passed"] else "failed"
                    criterion["last_evidence"] = evidence
                    criterion["last_output_hashes"] = evidence.get("outputs", {})
                elif kind == "artifact":
                    if criterion["status"] != "verified" or event.get("receipt_hash") != criterion["last_receipt"]:
                        raise LedgerError(f"missing passing receipt link at event {number}")
                    if not isinstance(event.get("file"), dict) or not isinstance(event["file"].get("path"), str):
                        raise LedgerError(f"invalid artifact file at event {number}")
                    observed_outputs = criterion.get("last_evidence", {}).get("outputs", {})
                    if observed_outputs.get(event["file"]["path"]) != event["file"].get("sha256"):
                        raise LedgerError(f"artifact is not a matching declared output at event {number}")
                    criterion["artifacts"].append(digest)
                    criterion["artifact_files"].append(event["file"])
                elif kind == "handoff":
                    if (criterion["status"] != "verified" or not criterion["artifacts"]
                            or event.get("artifact_hashes") != criterion["artifacts"]):
                        raise LedgerError(f"missing artifact links at event {number}")
                    criterion["handoff"] = digest
                    criterion["status"] = "handed_off"
                elif kind == "invalidation":
                    if not isinstance(event.get("text"), str) or not event["text"].strip():
                        raise LedgerError(f"invalidation requires a reason at event {number}")
                    criterion["status"] = "invalid"
            state["head"] = digest
            events.append(event)
        if expected_head is not None and state["head"] != expected_head:
            raise LedgerError("head differs from external anchor")
        for criterion in state["criteria"].values():
            evidence = criterion.get("last_evidence")
            if criterion["status"] in {"verified", "handed_off"}:
                for file_ref in criterion["artifact_files"]:
                    try:
                        matches = file_ref == self._file_ref(file_ref["path"])
                    except LedgerError:
                        matches = False
                    if not matches:
                        criterion["status"] = "invalid"
                        break
            if criterion["status"] in {"verified", "handed_off"} and evidence and "inputs" in evidence:
                if (self._snapshot(list(evidence["inputs"])) != evidence["inputs"]
                        or self._snapshot(evidence["output_paths"]) != evidence["outputs"]
                        or any(value is None for value in evidence["outputs"].values())):
                    criterion["status"] = "invalid"
            criterion.pop("last_evidence", None)
        public_status = {"verified": "PASS", "handed_off": "PASS", "failed": "FAIL",
                         "invalid": "INVALID", "registered": "PENDING", "command_recorded": "PENDING"}
        state["current_status"] = {ac_id: public_status[criterion["status"]]
                                   for ac_id, criterion in state["criteria"].items()}
        for ac_id, criterion in state["criteria"].items():
            upstream = [state["current_status"][item] for item in criterion["depends_on"]]
            if any(status in {"FAIL", "BLOCKED"} for status in upstream):
                state["current_status"][ac_id] = "BLOCKED"
            elif upstream and any(status != "PASS" for status in upstream):
                state["current_status"][ac_id] = "INVALID"
        return state

    def verify(self, *, expected_head: str | None = None) -> dict[str, Any]:
        if not self.ledger.exists():
            raise LedgerError("ledger does not exist")
        with self.ledger.open("r", encoding="utf-8") as stream:
            return self._replay(stream.readlines(), expected_head)

    def append(self, kind: str, *, ac_id: str | None = None, text: str | None = None,
               path: str | None = None, passed: bool | None = None,
               details: dict[str, Any] | None = None) -> dict[str, Any]:
        """Append a descriptive event; only run/recovery may append process provenance."""
        return self._append_event(kind, ac_id=ac_id, text=text, path=path, passed=passed,
                                  details=details, internal=False)

    def _append_event(self, kind: str, *, ac_id: str | None = None, text: str | None = None,
                      path: str | None = None, passed: bool | None = None,
                      details: dict[str, Any] | None = None, internal: bool = False) -> dict[str, Any]:
        if kind not in KINDS:
            raise LedgerError(f"unknown event kind: {kind}")
        if (kind in FILE_KINDS) != (path is not None):
            raise LedgerError("file required only for file-backed event kinds")
        if kind in {"acceptance_criterion", "command"} and (not isinstance(text, str) or not text.strip()):
            raise LedgerError("criterion and command require text")
        if kind == "test_receipt" and not isinstance(passed, bool):
            raise LedgerError("test receipt requires a pass/fail result")
        if kind == "test_receipt" and not internal:
            raise LedgerError("test receipts must come from ledger.run, which executes the command")
        if kind == "command" and not internal and details and set(details) & {"attempt_id", "inputs", "outputs"}:
            raise LedgerError("observed command provenance must come from ledger.run")
        if kind == "invalidation" and (not isinstance(text, str) or not text.strip()):
            raise LedgerError("invalidation requires a reason")
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
                if kind == "command" and criterion["status"] == "command_recorded":
                    raise LedgerError("incomplete command has unknown execution outcome; reconcile before retry")
                event["criterion_hash"] = criterion["criterion_hash"]
                if kind == "test_receipt":
                    event["command_hash"] = criterion["last_command"]
                    event["passed"] = passed
                elif kind == "artifact":
                    event["receipt_hash"] = criterion["last_receipt"]
                elif kind == "handoff":
                    event["artifact_hashes"] = criterion["artifacts"][:]
            if details:
                if set(details) & set(event):
                    raise LedgerError("event details duplicate reserved fields")
                event.update(details)
            event["event_hash"] = _hash(event)
            self._replay(lines + [_canonical(event).decode("utf-8") + "\n"])
            stream.seek(0, os.SEEK_END)
            stream.write(_canonical(event).decode("utf-8") + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            return event

    def run(self, ac_id: str, argv: list[str], receipt_path: str, *,
            inputs: list[str] | None = None, outputs: list[str] | None = None,
            timeout: float | None = 300.0) -> tuple[dict[str, Any], dict[str, Any]]:
        """Execute an argv vector and append its observed result, never caller-supplied success."""
        if not isinstance(argv, list) or not argv or not all(isinstance(arg, str) and arg for arg in argv):
            raise LedgerError("run requires a non-empty argv vector")
        if (inputs is not None and not isinstance(inputs, list)) or (outputs is not None and not isinstance(outputs, list)):
            raise LedgerError("inputs and outputs must be lists")
        if timeout is None:
            timeout = 300.0
        if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
                or not math.isfinite(timeout) or not 0 < timeout <= 3600):
            raise LedgerError("timeout must be finite and between 0 and 3600 seconds")
        if not isinstance(receipt_path, str) or not receipt_path or Path(receipt_path).is_absolute():
            raise LedgerError("receipt path must be a new workspace-relative file")
        target = (self.root / receipt_path).resolve()
        if not target.is_relative_to(self.root) or target == self.ledger:
            raise LedgerError("receipt path must be a new workspace-relative file")
        if target.exists():
            return self.recover_receipt(ac_id, argv, receipt_path, inputs=inputs, outputs=outputs)
        input_hashes = self._snapshot(inputs or [])
        if any(value is None for value in input_hashes.values()):
            raise LedgerError("command input is missing")
        output_paths = list(self._snapshot(outputs or []))
        if target.relative_to(self.root).as_posix() in output_paths:
            raise LedgerError("receipt cannot be a command output")
        if set(input_hashes) & set(output_paths):
            raise LedgerError("a command output cannot also be an input")
        state = self.verify()
        criterion = state["criteria"].get(ac_id)
        if criterion is None:
            raise LedgerError("record the criterion before its evidence")
        if criterion["status"] == "command_recorded":
            raise LedgerError("incomplete command has unknown execution outcome; reconcile before retry")
        known_outputs = criterion["last_output_hashes"]
        for path in output_paths:
            output = self.root / path
            if output.exists() and not output.is_file():
                raise LedgerError(f"command output is not a file: {path}")
            if output.exists() and hashlib.sha256(output.read_bytes()).hexdigest() != known_outputs.get(path):
                raise LedgerError(f"refusing to overwrite unrecorded or modified output: {path}")
        before_stats = {path: (self.root / path).stat() if (self.root / path).exists() else None
                        for path in output_paths}
        attempt_id = uuid.uuid4().hex
        command = self._append_event("command", ac_id=ac_id, text=json.dumps(argv, ensure_ascii=False),
                                     details={"attempt_id": attempt_id, "inputs": input_hashes, "outputs": output_paths},
                                     internal=True)
        exit_code, stdout, stderr, outcome = _execute_bounded(argv, self.root, timeout)
        try:
            output_hashes = self._snapshot(output_paths)
        except LedgerError as error:
            if "exceeds size limit" not in str(error):
                raise
            output_hashes = {path: None for path in output_paths}
            exit_code, outcome = 125, "output_limit"
            stderr = (stderr + "\n" + str(error)).strip()
        for path in output_paths:
            output = self.root / path
            if before_stats[path] is not None and output.exists():
                previous, current = before_stats[path], output.stat()
                if ((previous.st_dev, previous.st_ino, previous.st_mtime_ns, previous.st_ctime_ns, previous.st_size)
                        == (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_ctime_ns, current.st_size)):
                    output_hashes[path] = None
        receipt = {"command_hash": command["event_hash"], "argv": argv,
                   "attempt_id": attempt_id, "inputs": input_hashes, "output_paths": output_paths,
                   "outputs": output_hashes, "outcome": outcome,
                   "exit_code": exit_code, "stdout": stdout, "stderr": stderr}
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                             prefix=".receipt-", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(receipt, stream, ensure_ascii=False, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        passed = exit_code == 0 and outcome == "exited" and all(output_hashes.values())
        return command, self._append_event("test_receipt", ac_id=ac_id, path=receipt_path,
                                           passed=passed, internal=True,
                                           details={"attempt_id": attempt_id, "exit_code": exit_code,
                                                    "stdout": stdout, "stderr": stderr,
                                                    "inputs": input_hashes, "outputs": output_hashes})

    def recover_receipt(self, ac_id: str, argv: list[str], receipt_path: str, *,
                        inputs: list[str] | None = None, outputs: list[str] | None = None
                        ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Finish a receipt event left after an interrupted append, without rerunning the process."""
        state = self.verify()
        criterion = state["criteria"].get(ac_id)
        if criterion is None or criterion["status"] != "command_recorded":
            raise LedgerError("no incomplete command to recover")
        file_ref = self._file_ref(receipt_path)
        try:
            receipt = json.loads((self.root / file_ref["path"]).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise LedgerError("invalid incomplete receipt JSON") from error
        command = next((json.loads(line) for line in reversed(self.ledger.read_text(encoding="utf-8").splitlines())
                        if json.loads(line).get("event_hash") == criterion["last_command"]), None)
        if (not isinstance(receipt, dict) or command is None
                or command.get("ac_id") != ac_id or receipt.get("command_hash") != command["event_hash"]
                or receipt.get("attempt_id") != command.get("attempt_id")
                or receipt.get("argv") != argv or receipt.get("inputs") != self._snapshot(inputs or [])
                or receipt.get("output_paths") != list(self._snapshot(outputs or []))
                or not isinstance(receipt.get("outputs"), dict)
                or receipt.get("outputs") != self._snapshot(outputs or [])
                or receipt.get("outcome") not in {"exited", "timeout", "interrupted", "launch_error", "output_limit"}
                or type(receipt.get("exit_code")) is not int
                or not isinstance(receipt.get("stdout"), str)
                or not isinstance(receipt.get("stderr"), str)):
            raise LedgerError("incomplete receipt does not match the recorded command or current files")
        passed = (receipt["exit_code"] == 0 and receipt["outcome"] == "exited"
                  and all(receipt["outputs"].values()))
        event = self._append_event("test_receipt", ac_id=ac_id, path=receipt_path,
                                   passed=passed, internal=True,
                                   details={"attempt_id": receipt["attempt_id"], "exit_code": receipt["exit_code"],
                                            "stdout": receipt["stdout"], "stderr": receipt["stderr"],
                                            "inputs": receipt["inputs"], "outputs": receipt["outputs"]})
        return command, event


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
    run.add_argument("--input", action="append", default=[])
    run.add_argument("--output", action="append", default=[])
    run.add_argument("--timeout", type=float)
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
            command, receipt = ledger.run(args.ac_id, argv, args.receipt,
                                          inputs=args.input, outputs=args.output, timeout=args.timeout)
            result = {"command": command, "receipt": receipt}
        else:
            result = ledger.verify(expected_head=args.expected_head)
    except (LedgerError, OSError) as error:
        parser.exit(2, f"evidence ledger error: {error}\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.action == "run" and not result["receipt"]["passed"]:
        return result["receipt"]["exit_code"] or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
