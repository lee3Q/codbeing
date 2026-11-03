"""Separate, local retrospective notes. Never prediction evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable

from .schema import REQUIRED_FIELDS, validate_decision_trace


def original_digest(trace: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        trace, ensure_ascii=False, sort_keys=True, separators=(',', ':')
    ).encode('utf-8')).hexdigest()


def capture(args: Any, load_store: Callable, safe: Callable) -> int:
    """Confirm the snapshot and create a separate file exclusively."""
    saving = False
    try:
        traces = load_store(args.store)
        if args.index < 0 or args.index >= len(traces):
            raise ValueError('record index not found. Run cb list with the same --store.')
        trace = traces[args.index]
        print('Original decision snapshot (private content follows):')
        render_original(trace, safe)
        print('Later observation, not a forecast or independent proof. Original store is not changed.')
        observation = input('나중에 관찰한 일: ').strip()
        reflection = input('그때의 판단과 비교해 달라진 점: ').strip()
        if not observation or not reflection:
            print('Reflection cancelled: both notes are required; no file created.')
            return 0
        print(f'observation: {safe(observation)}')
        print(f'reflection: {safe(reflection)}')
        print(f'New local file: {safe(args.output)} (contains original private notes too)')
        if input('이 별도 기록을 저장할까요? [y/N]: ').strip().lower() != 'y':
            print('Reflection cancelled; no file created.')
            return 0
        payload = dict(
            format='codbeing-reflection-v1',
            recorded_at=datetime.now(timezone.utc).isoformat(),
            original_decision=trace, original_sha256=original_digest(trace),
            observation=observation, reflection=reflection,
        )
        # Exclusive create refuses all existing paths, including symlinks.
        # No original store rewrite or parent-directory creation.
        saving = True
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write('\n')
        print(f'Reflection saved: {safe(args.output)}')
        print(f'Read it with: cb reflection {safe(args.output)}')
        return 0
    except FileExistsError:
        print('reflection error: output already exists; existing bytes were not changed. Choose a new filename.')
        return 2
    except EOFError:
        print('Reflection cancelled: input ended; no file created.')
        return 0
    except KeyboardInterrupt:
        print('Reflection interrupted during save; inspect output before retrying.' if saving else 'Reflection cancelled; no file created.')
        return 130
    except (OSError, ValueError, UnicodeError) as error:
        print(f'reflection error: {safe(error)}')
        if saving:
            print('Output may be incomplete; inspect it before retrying. Original store was not changed.')
        return 2


def render_original(trace: dict[str, Any], safe: Callable) -> None:
    for field in REQUIRED_FIELDS:
        value = trace[field]
        print(f'{field}:')
        for item in value if isinstance(value, list) else [value]:
            print(f'  {safe(item)}')


def show(path: Path, safe: Callable) -> int:
    try:
        with path.open(encoding='utf-8') as file:
            data = json.load(file)
        if not isinstance(data, dict) or data.get('format') != 'codbeing-reflection-v1':
            raise ValueError('not a codbeing reflection file')
        trace = data.get('original_decision')
        validate_decision_trace(trace, require_core=True)
        if data.get('original_sha256') != original_digest(trace):
            raise ValueError('original snapshot digest mismatch')
        for field in ('observation', 'reflection', 'recorded_at'):
            if not isinstance(data.get(field), str) or not data[field].strip():
                raise ValueError(f'missing or invalid {field}')
        datetime.fromisoformat(data['recorded_at'])
        print('Local retrospective reflection (private content follows).')
        print('Not prediction evidence. Local time and digest are editable, not independent proof.')
        print(f"recorded_at: {safe(data['recorded_at'])}")
        render_original(trace, safe)
        print(f"observation: {safe(data['observation'])}")
        print(f"reflection: {safe(data['reflection'])}")
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f'reflection error: {safe(error)}')
        return 2
