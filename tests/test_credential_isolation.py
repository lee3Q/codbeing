"""Offline regression tests. All tokens here are fictional fixture strings."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from codbeing.config import _glm_api_key, glm_runtime_env


class CredentialIsolationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.old_cwd = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, self.old_cwd)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_generic_anthropic_environment_token_is_not_a_glm_key(self):
        os.environ['ANTHROPIC_AUTH_TOKEN'] = 'fictional-other-provider'
        self.assertIsNone(_glm_api_key())
        self.assertNotIn('ANTHROPIC_AUTH_TOKEN', glm_runtime_env())

    def test_generic_dotenv_token_is_not_a_glm_key(self):
        Path('.env').write_text('ANTHROPIC_AUTH_TOKEN=fictional-other-provider\n')
        self.assertIsNone(_glm_api_key())

    def test_shell_configuration_is_never_read_for_keys_or_endpoints(self):
        Path('.zshrc').write_text('export ANTHROPIC_AUTH_TOKEN=fictional-shell-token\nexport ANTHROPIC_BASE_URL=https://unrelated.invalid\n')
        with patch('pathlib.Path.home', return_value=Path.cwd()):
            self.assertIsNone(_glm_api_key())
            self.assertNotIn('ANTHROPIC_BASE_URL', glm_runtime_env())

    def test_each_dedicated_environment_key_is_supported(self):
        for name in ('CODBEING_GLM_API_KEY', 'GLM_API_KEY', 'ZHIPUAI_API_KEY'):
            with self.subTest(name=name), patch.dict(os.environ, {name: ' fictional-glm '}, clear=True):
                self.assertEqual(_glm_api_key(), 'fictional-glm')

    def test_explicit_key_precedence_and_whitespace(self):
        os.environ.update(CODBEING_GLM_API_KEY=' ', GLM_API_KEY='fictional-glm')
        self.assertEqual(_glm_api_key(), 'fictional-glm')
        os.environ['CODBEING_GLM_API_KEY'] = 'fictional-project-key'
        self.assertEqual(_glm_api_key(), 'fictional-project-key')

    def test_project_dotenv_and_private_dotenv_are_supported(self):
        for location in (Path('.env'), Path('private/.env')):
            with self.subTest(location=location):
                location.parent.mkdir(exist_ok=True)
                location.write_text('GLM_API_KEY=fictional-local-key\n')
                self.assertEqual(_glm_api_key(), 'fictional-local-key')
                location.unlink()
