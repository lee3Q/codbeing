"""Readonly original-decision inspection, independent of model providers."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io
import argparse
import codbeing.__main__ as cli

from codbeing.schema import REQUIRED_FIELDS

ROOT = Path(__file__).parents[1]
TRACE = dict(context='원래 상황 ' + 'long reason ' * 25, options=['A', 'B'], chosen_action='A', rejected_options=['B'], judgment_basis='원래 이유', observed_behavior='관찰', outcome='아직 모름', aftertaste='느낌', memory_confidence='low', source='synthetic fixture', extension={'untouched': True})

class ShowRecordTests(unittest.TestCase):
    def run_show(self, payload, index='0', raw=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'store.json'
            if payload is not None or raw is not None:
                path.write_bytes(raw if raw is not None else json.dumps(payload, ensure_ascii=False).encode())
            before = path.read_bytes() if path.exists() else None
            env = os.environ.copy()
            env['PYTHONPATH'] = str(ROOT)
            result = subprocess.run([sys.executable, '-m', 'codbeing', 'show', index, '--store', str(path)], cwd=directory, env=env, capture_output=True, text=True)
            self.assertEqual(path.read_bytes() if path.exists() else None, before)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ['store.json'] if before is not None else [])
            return result

    def test_full_original_fields_and_no_mutation(self):
        result = self.run_show([TRACE, dict(TRACE, context='other')])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(TRACE['context'].strip(), result.stdout)
        for field in REQUIRED_FIELDS:
            self.assertIn(field + ':', result.stdout)
        self.assertIn('원래 이유', result.stdout)
        self.assertIn('  - A', result.stdout)
        self.assertNotIn('other', result.stdout)
        self.assertNotIn('extension:', result.stdout)

    def test_single_object_and_second_index(self):
        self.assertEqual(self.run_show(TRACE).returncode, 0)
        result = self.run_show([TRACE, dict(TRACE, judgment_basis='second reason')], '1')
        self.assertEqual(result.returncode, 0)
        self.assertIn('second reason', result.stdout)

    def test_missing_empty_and_out_of_range(self):
        for payload, index in [(None,'0'),([], '0'),([TRACE],'-1'),([TRACE],'1'),([TRACE],'no')]:
            with self.subTest(payload=payload,index=index):
                result = self.run_show(payload,index)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('Traceback', result.stderr)
                if index != 'no': self.assertIn('record index not found', result.stdout)
                self.assertNotIn('원래 이유', result.stdout)

    def test_invalid_store(self):
        for raw in [b'{partial',b'\xff',b'[{}]', b'null']:
            with self.subTest(raw=raw):
                result = self.run_show(None, raw=raw)
                self.assertEqual(result.returncode,2)
                self.assertNotIn('Traceback', result.stderr)
                self.assertIn('validation error:', result.stdout)

    def test_terminal_safe_full_display(self):
        trace = dict(TRACE, judgment_basis='safe\x1b[2J\x07\u202eend', options=['A\x1b[H','B\u2066'], source='한글\u200d', outcome={'legacy':'value'})
        result = self.run_show(trace)
        self.assertEqual(result.returncode,0)
        for control in ['\x1b','\x07','\u202e','\u2066']:
            self.assertNotIn(control,result.stdout)
        self.assertIn('한글\u200d',result.stdout)
        self.assertIn('legacy',result.stdout)

    def test_read_failure_is_actionable_and_does_not_call_models(self):
        output = io.StringIO()
        with patch("codbeing.__main__._load_trace_store", side_effect=PermissionError), patch("codbeing.__main__._append_model_assist") as model, redirect_stdout(output):
            self.assertEqual(cli._show(argparse.Namespace(store=Path("private.json"), index=0)), 2)
        self.assertIn("could not read trace store", output.getvalue())
        model.assert_not_called()

    def test_success_never_uses_model_assist(self):
        with patch("codbeing.__main__._load_trace_store", return_value=[TRACE]), patch("codbeing.__main__._append_model_assist") as model, redirect_stdout(io.StringIO()):
            self.assertEqual(cli._show(argparse.Namespace(store=Path("private.json"), index=0)), 0)
        model.assert_not_called()
