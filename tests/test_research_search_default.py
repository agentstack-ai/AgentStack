import json
import os
from pathlib import Path
from unittest.mock import patch

from agentstack.templates import TemplateConfig


def test_unconfigured_research_uses_parallel(tmp_path):
    with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'home', return_value=tmp_path):
        template = TemplateConfig.from_template_name('research')
    assert [(tool.name, tool.agents) for tool in template.tools] == [('parallel', ['researcher'])]


def test_configured_perplexity_is_preserved(tmp_path):
    for environment, home in [
        ({'PERPLEXITY_API_KEY': 'configured'}, ''),
        ({}, 'PERPLEXITY_API_KEY=home-key'),
    ]:
        (tmp_path / '.env').write_text(home)
        with (
            patch.dict(os.environ, environment, clear=True),
            patch.object(Path, 'home', return_value=tmp_path),
        ):
            assert TemplateConfig.from_template_name('research').tools[0].name == 'perplexity'


def test_explicit_file_template_keeps_selected_provider(tmp_path):
    data = json.loads((Path(__file__).parent.parent / 'agentstack/templates/research.json').read_text())
    template_path = tmp_path / 'research.json'
    template_path.write_text(json.dumps(data))
    with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'home', return_value=tmp_path):
        assert TemplateConfig.from_user_input(str(template_path)).tools[0].name == 'perplexity'
        data['tools'] = []
        template_path.write_text(json.dumps(data))
        assert TemplateConfig.from_user_input(str(template_path)).tools == []


def test_other_starters_keep_their_tools(tmp_path):
    with patch.dict(os.environ, {}, clear=True), patch.object(Path, 'home', return_value=tmp_path):
        assert TemplateConfig.from_template_name('hello_alex').tools[0].name == 'file_read'
