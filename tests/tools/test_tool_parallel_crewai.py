"""Keep the native CrewAI tool schema consistent with the advertised inputs."""

import json

import pytest

import agentstack
from agentstack import conf
from agentstack._tools import parallel


pytest.importorskip('crewai')


def test_fetch_objective_is_explicit_and_accepts_empty_string(tmp_path, monkeypatch):
    original_path = conf.PATH
    (tmp_path / 'agentstack.json').write_text(json.dumps({'framework': 'crewai', 'tools': ['parallel']}))
    conf.set_path(tmp_path)
    seen = []

    def result(name, arguments):
        seen.append((name, arguments))
        return 'Source https://example.com: excerpt'

    monkeypatch.setattr(parallel, '_run_tool', result)
    try:
        _, fetch = agentstack.tools['parallel']
        with pytest.raises(ValueError, match='objective'):
            fetch.args_schema.model_validate({'urls': ['https://example.com']})
        assert seen == []
        assert 'https://example.com' in fetch.run(urls=['https://example.com'], objective='')
        assert seen == [('web_fetch', {'urls': ['https://example.com'], 'objective': None})]
    finally:
        conf.set_path(original_path)
