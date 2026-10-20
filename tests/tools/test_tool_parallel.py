"""Scripted runtime dispatch with real MCP protocol handling and mocked HTTP."""

import asyncio
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

import agentstack
from agentstack import conf
from agentstack.cli.run import run_project
from agentstack.search import search_session
from agentstack.utils import get_version


pytest.importorskip('mcp')
AIMessage = pytest.importorskip('langchain_core.messages').AIMessage
graph_module = pytest.importorskip('langgraph.graph')
StateGraph, MessagesState = graph_module.StateGraph, graph_module.MessagesState
START, END = graph_module.START, graph_module.END
ToolNode = pytest.importorskip('langgraph.prebuilt').ToolNode


@pytest.fixture
def project(tmp_path, monkeypatch):
    old_path = conf.PATH
    monkeypatch.setenv('AGENTSTACK_TELEMETRY_OPT_OUT', '1')
    monkeypatch.delenv('PERPLEXITY_API_KEY', raising=False)
    monkeypatch.delenv('PARALLEL_API_KEY', raising=False)
    monkeypatch.setattr(Path, 'home', lambda: tmp_path / 'home')
    (tmp_path / 'agentstack.json').write_text(json.dumps({'framework': 'langgraph', 'tools': ['parallel']}))
    (tmp_path / 'src').mkdir()
    shutil.copy(
        Path(__file__).parent.parent / 'fixtures/frameworks/langgraph/entrypoint_max.py',
        tmp_path / 'src/graph.py',
    )
    conf.set_path(tmp_path)
    yield tmp_path
    conf.set_path(old_path)


@pytest.fixture
def server(monkeypatch):
    requests = []
    behavior = {'error': None, 'tool_error': False, 'structured': False}
    original_client = httpx.AsyncClient

    def handler(request):
        assert str(request.url) == 'https://search.parallel.ai/mcp'
        assert request.headers['user-agent'] == f'AgentStack/{get_version()}'
        assert 'authorization' not in request.headers
        assert request.extensions['timeout']['read'] == 30
        if request.method != 'POST':
            return httpx.Response(405)
        body = json.loads(request.content)
        requests.append(body)
        method = body['method']
        if method == 'notifications/initialized':
            return httpx.Response(202)
        if method == 'initialize':
            result = {
                'protocolVersion': body['params']['protocolVersion'],
                'capabilities': {'tools': {}},
                'serverInfo': {'name': 'parallel-fixture', 'version': '1'},
            }
        elif method == 'tools/list':
            result = {
                'tools': [
                    {'name': name, 'inputSchema': {'type': 'object', 'properties': {}}}
                    for name in ['web_search', 'web_fetch']
                ]
            }
        else:
            assert method == 'tools/call'
            if behavior['error']:
                raise behavior['error']
            text = (
                'Quota exceeded'
                if behavior['tool_error']
                else 'Source: https://example.com/research\nPage excerpt'
            )
            result = {'content': [{'type': 'text', 'text': text}], 'isError': behavior['tool_error']}
            if behavior['structured']:
                result = {'content': [], 'structuredContent': {'url': 'https://example.com/research'}}
        return httpx.Response(200, json={'jsonrpc': '2.0', 'id': body['id'], 'result': result})

    def client(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, 'AsyncClient', client)
    yield requests, behavior


def dispatcher():
    graph = StateGraph(MessagesState)
    graph.add_node('tools', ToolNode(agentstack.tools['parallel'], handle_tool_errors=False))
    # Scripted consumer stands in for the next model turn, retaining source URLs.
    graph.add_node('consume', lambda state: {'messages': [AIMessage(content=state['messages'][-1].content)]})
    graph.add_edge(START, 'tools')
    graph.add_edge('tools', 'consume')
    graph.add_edge('consume', END)
    return graph.compile()


def invoke(app, name='web_search', arguments=None):
    arguments = (
        arguments
        if arguments is not None
        else {'objective': 'Find research', 'search_queries': ['research sources']}
    )
    message = AIMessage(
        content='', tool_calls=[{'name': name, 'args': arguments, 'id': 'call-1', 'type': 'tool_call'}]
    )
    return app.invoke({'messages': [message]})['messages'][-1].content


def calls(server):
    return [request['params'] for request in server[0] if request['method'] == 'tools/call']


def test_search_fetch_and_followup_reach_consumer(project, server):
    app = dispatcher()
    with search_session():
        assert 'https://example.com/research' in invoke(app)
        assert 'Page excerpt' in invoke(
            app, 'web_fetch', {'urls': ['https://example.com/research'], 'objective': ''}
        )
        invoke(app)
    assert [call['name'] for call in calls(server)] == ['web_search', 'web_fetch', 'web_search']
    assert len({call['arguments']['session_id'] for call in calls(server)}) == 1
    assert calls(server)[1]['arguments']['urls'] == ['https://example.com/research']
    assert calls(server)[0]['arguments']['search_queries'] == ['research sources']


def test_new_and_concurrent_conversations_use_distinct_ids(project, server):
    app = dispatcher()

    def conversation():
        with search_session():
            invoke(app)
            invoke(app, 'web_fetch', {'urls': ['https://example.com/research'], 'objective': ''})

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: conversation(), range(2)))
    counts = {}
    for call in calls(server):
        identifier = call['arguments']['session_id']
        counts[identifier] = counts.get(identifier, 0) + 1
    assert sorted(counts.values()) == [2, 2]
    conversation()
    assert calls(server)[-1]['arguments']['session_id'] not in counts


def test_cli_starts_new_session_and_reuses_it_within_run(project, server):
    # Import the same real dispatcher used above from an actual project entrypoint.
    module = __name__
    (project / 'src/main.py').write_text(
        f'from {module} import dispatcher, invoke\n'
        'def run():\n'
        '    app = dispatcher()\n'
        '    invoke(app)\n'
        '    invoke(app, "web_fetch", {"urls": ["https://example.com/research"], "objective": ""})\n'
    )
    run_project()
    run_project()
    ids = [call['arguments']['session_id'] for call in calls(server)]
    assert ids[0] == ids[1]
    assert ids[2] == ids[3]
    assert ids[0] != ids[2]


def test_async_cli_entrypoint_can_call_sync_tools(project, server):
    (project / 'src/main.py').write_text(
        f'from {__name__} import dispatcher, invoke\n'
        'async def run():\n'
        '    invoke(dispatcher())\n'
        '    invoke(dispatcher())\n'
    )
    run_project()
    assert len(calls(server)) == 2
    assert calls(server)[0]['arguments']['session_id'] == calls(server)[1]['arguments']['session_id']


def test_explicit_perplexity_error_does_not_fall_back(project, server, monkeypatch):
    import requests

    (project / 'agentstack.json').write_text(json.dumps({'framework': 'langgraph', 'tools': ['perplexity']}))
    destinations = []

    def fail(method, url, **kwargs):
        destinations.append(url)
        return type('Response', (), {'status_code': 503, 'text': 'Service unavailable'})()

    monkeypatch.setattr(requests, 'request', fail)
    query = agentstack.tools['perplexity'][0]
    assert query('research sources') == 'Failed to query perplexity'
    assert destinations == ['https://api.perplexity.ai/chat/completions']
    assert conf.ConfigFile().tools == ['perplexity']
    assert server[0] == []


def test_quota_error_and_retry_keep_conversation(project, server):
    app = dispatcher()
    with search_session():
        server[1]['tool_error'] = True
        with pytest.raises(RuntimeError, match='Quota exceeded'):
            invoke(app)
        server[1]['tool_error'] = False
        assert 'Page excerpt' in invoke(app)
    assert calls(server)[0]['arguments']['session_id'] == calls(server)[1]['arguments']['session_id']


@pytest.mark.parametrize('error', [httpx.ReadTimeout('timed out'), asyncio.CancelledError()])
def test_timeout_and_cancellation_do_not_return_success(project, server, error):
    server[1]['error'] = error
    with pytest.raises(BaseException) as caught:
        invoke(dispatcher())

    def leaves(exception):
        if hasattr(exception, 'exceptions'):
            return [leaf for nested in exception.exceptions for leaf in leaves(nested)]
        return [exception]

    # The synchronous portal represents async cancellation as Future cancellation.
    from concurrent.futures import CancelledError

    expected = httpx.ReadTimeout if isinstance(error, httpx.ReadTimeout) else CancelledError
    assert any(isinstance(leaf, expected) for leaf in leaves(caught.value)), repr(caught.value)
    assert len(calls(server)) == 1  # No hidden retry, provider fallback or new identity.


def test_structured_content_is_consumed(project, server):
    server[1]['structured'] = True
    assert json.loads(invoke(dispatcher())) == {'url': 'https://example.com/research'}


@pytest.mark.parametrize(
    'name,arguments',
    [
        ('web_search', {'objective': '', 'search_queries': ['research']}),
        ('web_search', {'objective': 'research', 'search_queries': []}),
        ('web_fetch', {'urls': ['file:///etc/passwd'], 'objective': ''}),
        ('web_fetch', {'urls': [], 'objective': ''}),
        ('web_fetch', {'urls': ['https://example.com'], 'objective': 'x' * 201}),
    ],
)
def test_invalid_input_never_contacts_server(project, server, name, arguments):
    with pytest.raises(ValueError):
        invoke(dispatcher(), name, arguments)
    assert server[0] == []


def test_missing_fetch_objective_fails_native_schema(project, server):
    with pytest.raises(Exception, match='objective'):
        invoke(dispatcher(), 'web_fetch', {'urls': ['https://example.com']})
    assert server[0] == []


def test_removed_tool_is_not_available_to_dispatcher(project, server):
    graph = StateGraph(MessagesState)
    graph.add_node('tools', ToolNode([]))
    graph.add_edge(START, 'tools')
    graph.add_edge('tools', END)
    result = invoke(graph.compile())
    assert 'not a valid tool' in result
    assert server[0] == []
