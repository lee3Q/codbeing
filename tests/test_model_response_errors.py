"""Malformed optional-assist responses must not discard the local report."""

from unittest.mock import patch

import pytest

from codbeing.config import CodbeingConfig
from codbeing.models import model_assist_section


@pytest.mark.parametrize('error', [IndexError('empty choices'), TypeError('null response'),
                                   UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'invalid')])
def test_optional_assist_bad_response_keeps_local_result(error):
    with patch('codbeing.models._glm_api_key', return_value='synthetic-not-a-real-key'), \
         patch('codbeing.models._call_glm', side_effect=error):
        section = model_assist_section([], '# Local report', CodbeingConfig(model_provider='glm'),
                                       'glm', consent_granted=True, assist_requested=True)
    assert 'GLM call failed; local Runtime Analysis is still available.' in '\n'.join(section)


@pytest.mark.parametrize('payload', [b'{"choices": []}', b'null', b'\xff'])
def test_actual_openai_compatible_parser_failure_is_bounded(payload):
    from unittest.mock import MagicMock
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = payload
    with patch('codbeing.models._glm_api_key', return_value='synthetic-not-a-real-key'), \
         patch('codbeing.models.glm_runtime_env', return_value={}), \
         patch('urllib.request.urlopen', return_value=response) as request:
        section = model_assist_section([], '# Local report', CodbeingConfig(model_provider='glm'),
                                       'glm', consent_granted=True, assist_requested=True)
    request.assert_called_once()
    assert 'GLM call failed; local Runtime Analysis is still available.' in '\n'.join(section)
