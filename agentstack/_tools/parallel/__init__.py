"""Free anonymous search and page excerpts through Parallel Search MCP."""

import json
from datetime import timedelta
from urllib.parse import urlsplit

from agentstack.search import get_search_session_id
from agentstack.utils import get_version


MCP_URL = 'https://search.parallel.ai/mcp'
REQUEST_TIMEOUT = timedelta(seconds=30)


async def _call_tool(name: str, arguments: dict) -> str:
    # Imported only when called, so listing tools does not require the MCP extra.
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    headers = {'User-Agent': f'AgentStack/{get_version()}'}
    result = None
    async with streamablehttp_client(
        MCP_URL,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        sse_read_timeout=REQUEST_TIMEOUT,
    ) as (read, write, _):
        async with ClientSession(read, write, read_timeout_seconds=REQUEST_TIMEOUT) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments, read_timeout_seconds=REQUEST_TIMEOUT)

    if result is None:
        # A transport task can be cancelled while its task group unwinds.
        # Preserve cancellation even if an SDK context manager suppresses it.
        from anyio import get_cancelled_exc_class

        raise get_cancelled_exc_class()
    text = '\n'.join(block.text for block in result.content if block.type == 'text')
    if result.isError:
        raise RuntimeError(f'Parallel {name} failed: {text}')
    if text:
        return text
    if result.structuredContent is not None:
        return json.dumps(result.structuredContent)
    raise RuntimeError(f'Parallel {name} returned no text or structured content')


def _run_tool(name: str, arguments: dict) -> str:
    from anyio.from_thread import start_blocking_portal

    arguments['session_id'] = get_search_session_id()
    # Framework tools are synchronous. A portal also works when their caller
    # already runs an event loop, without nesting asyncio.run in that loop.
    with start_blocking_portal() as portal:
        return portal.call(_call_tool, name, arguments)


def web_search(objective: str, search_queries: list[str]) -> str:
    """Search the web for current information, returning source URLs and excerpts.

    Args:
        objective: A focused description of the information to find.
        search_queries: At least one related keyword query; prefer 3–6 words each.

    Returns:
        Search results with URLs and excerpts to cite or read with web_fetch.
    """
    if not objective.strip() or not search_queries or any(not query.strip() for query in search_queries):
        raise ValueError('Provide an objective and at least one nonempty search query')
    return _run_tool('web_search', {'objective': objective, 'search_queries': search_queries})


def web_fetch(urls: list[str], objective: str) -> str:
    """Read excerpts from up to 20 HTTP(S) pages, preserving source URLs.

    Args:
        urls: The web page URLs to read, such as sources returned by web_search.
        objective: Description of relevant information, up to 200 characters; use an empty string for general excerpts.

    Returns:
        Page excerpts and their source URLs for the agent to analyze and cite.
    """
    if not 1 <= len(urls) <= 20:
        raise ValueError('Provide between 1 and 20 URLs')
    if any(urlsplit(url).scheme not in ('http', 'https') or not urlsplit(url).netloc for url in urls):
        raise ValueError('Only absolute HTTP or HTTPS URLs are supported')
    if len(objective) > 200:
        raise ValueError('The fetch objective must be at most 200 characters')
    return _run_tool('web_fetch', {'urls': urls, 'objective': objective or None})
