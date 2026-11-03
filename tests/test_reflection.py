"""A later observation never rewrites the original decision."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).parents[1]
TRACE=dict(context='합성 원래 상황',options=['A','B'],chosen_action='A',rejected_options=['B'],judgment_basis='원래 이유',observed_behavior='',outcome='',aftertaste='',memory_confidence='low',source='synthetic')

class ReflectionTests(unittest.TestCase):
    def run_cli(self, directory, args, input=None):
        env=os.environ.copy();env['PYTHONPATH']=str(ROOT)
        return subprocess.run([sys.executable,'-m','codbeing',*args],input=input,cwd=directory,env=env,text=True,capture_output=True)

    def test_capture_reflection_and_read_without_original_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            store=Path(td)/'store.json';store.write_text(json.dumps([TRACE],ensure_ascii=False));before=store.read_bytes()
            result=self.run_cli(td,['reflect','0','--store','store.json','--output','reflection.json'],'나중에 관찰한 일\n달라진 점\ny\n')
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(store.read_bytes(),before)
            if os.name == 'posix':
                self.assertEqual(Path(td,'reflection.json').stat().st_mode & 0o777, 0o600)
            data=json.loads(Path(td,'reflection.json').read_text())
            self.assertEqual(data['original_decision'],TRACE)
            self.assertEqual(data['observation'],'나중에 관찰한 일')
            self.assertEqual(data['reflection'],'달라진 점')
            self.assertIn('recorded_at',data)
            original=json.dumps(TRACE,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
            self.assertEqual(data['original_sha256'],hashlib.sha256(original).hexdigest())
            shown=self.run_cli(td,['reflection','reflection.json'])
            self.assertEqual(shown.returncode,0)
            for text in ['원래 이유','나중에 관찰한 일','달라진 점']:
                self.assertIn(text,shown.stdout)

    def test_cancel_eof_and_blank_do_not_create_file(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td,'store.json').write_text(json.dumps([TRACE]))
            for answers in ['', '\n\n', 'observation\nreflection\nn\n']:
                result=self.run_cli(td,['reflect','0','--store','store.json','--output','new.json'],answers)
                self.assertNotIn('Traceback',result.stderr)
                self.assertFalse(Path(td,'new.json').exists())

    def test_existing_output_and_missing_record_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td,'store.json').write_text(json.dumps([TRACE]));target=Path(td,'out.json');target.write_bytes(b'old')
            result=self.run_cli(td,['reflect','0','--store','store.json','--output','out.json'],'observation\nreflection\ny\n')
            self.assertEqual(result.returncode,2)
            self.assertEqual(target.read_bytes(),b'old')
            result=self.run_cli(td,['reflect','-1','--store','store.json','--output','new.json'],'observation\nreflection\ny\n')
            self.assertEqual(result.returncode,2);self.assertFalse(Path(td,'new.json').exists())

    def test_tampered_reflection_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td,'store.json').write_text(json.dumps([TRACE]))
            result=self.run_cli(td,['reflect','0','--store','store.json','--output','reflection.json'],'observation\nreflection\ny\n')
            self.assertEqual(result.returncode,0)
            p=Path(td,'reflection.json');data=json.loads(p.read_text());data['original_decision']['judgment_basis']='changed';p.write_text(json.dumps(data))
            result=self.run_cli(td,['reflection','reflection.json'])
            self.assertEqual(result.returncode,2);self.assertNotIn('Traceback',result.stderr)

    def test_missing_parent_and_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            Path(td,'store.json').write_text(json.dumps([TRACE]))
            for name in ['missing/out.json', 'link.json']:
                if name == 'link.json':
                    Path(td,'link.json').symlink_to('target.json')
                result=self.run_cli(td,['reflect','0','--store','store.json','--output',name],'observation\nreflection\ny\n')
                self.assertEqual(result.returncode,2)
                self.assertNotIn('Traceback',result.stderr)
            self.assertFalse(Path(td,'target.json').exists())

    def test_malformed_store_and_reflection_do_not_crash(self):
        with tempfile.TemporaryDirectory() as td:
            for payload in ['{', 'null', '[]', '{"format":"codbeing-reflection-v1"}', '\ud800']:
                Path(td,'bad.json').write_bytes(payload.encode('utf-8',errors='surrogatepass'))
                result=self.run_cli(td,['reflection','bad.json'])
                self.assertEqual(result.returncode,2);self.assertNotIn('Traceback',result.stderr)
            Path(td,'store.json').write_text('{')
            result=self.run_cli(td,['reflect','0','--store','store.json','--output','new.json'],'o\nr\ny\n')
            self.assertEqual(result.returncode,2);self.assertFalse(Path(td,'new.json').exists())

    def test_external_provider_not_called_and_control_text_safe(self):
        from argparse import Namespace
        import contextlib
        import io
        from unittest.mock import patch
        from codbeing import reflection
        from codbeing.__main__ import _terminal_safe
        with tempfile.TemporaryDirectory() as td:
            trace=dict(TRACE, extra_private_field='extra stays in snapshot')
            out=Path(td,'reflection.json')
            with patch('builtins.input',side_effect=['note\x1b[31m\x07','changed','y']), patch('urllib.request.urlopen',side_effect=AssertionError('no provider')), contextlib.redirect_stdout(io.StringIO()) as screen:
                result=reflection.capture(Namespace(store=Path(td,'store.json'),index=0,output=out),lambda _: [trace],_terminal_safe)
            self.assertEqual(result,0)
            self.assertNotIn('\x1b',screen.getvalue());self.assertNotIn('\x07',screen.getvalue())
            self.assertEqual(json.loads(out.read_text())['original_decision'],trace)
            with contextlib.redirect_stdout(io.StringIO()) as screen:
                self.assertEqual(reflection.show(out,_terminal_safe),0)
            self.assertNotIn('\x1b',screen.getvalue())

    def test_write_failure_has_no_original_mutation(self):
        from argparse import Namespace
        import contextlib
        import io
        from unittest.mock import patch
        from codbeing import reflection
        with tempfile.TemporaryDirectory() as td:
            with patch('builtins.input',side_effect=['observation','reflection','y']), patch('codbeing.reflection.os.open',side_effect=OSError('disk error')), contextlib.redirect_stdout(io.StringIO()) as screen:
                result=reflection.capture(Namespace(store=Path(td,'store.json'),index=0,output=Path(td,'out.json')),lambda _:[TRACE],str)
            self.assertEqual(result,2);self.assertIn('may be incomplete',screen.getvalue())
            self.assertFalse(Path(td,'out.json').exists())
