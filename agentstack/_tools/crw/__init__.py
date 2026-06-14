import os
from firecrawl import FirecrawlApp
from typing import List, Dict, Any, Optional

# fastCRW is a Firecrawl-compatible web data engine (single ~8MB Rust binary;
# self-host or managed cloud). Because the API is Firecrawl-compatible, we reuse
# the official Firecrawl client and just point it at the fastCRW base URL.
# Defaults to the managed cloud; override CRW_API_URL to target a self-hosted server.
app = FirecrawlApp(
    api_key=os.getenv('CRW_API_KEY'),
    api_url=os.getenv('CRW_API_URL', 'https://fastcrw.com/api'),
)


def web_scrape(url: str):
    """
    Scrape a url and return markdown. Use this to read a singular page and web_crawl only if you
    need to read all other links as well.
    """
    scrape_result = app.scrape_url(url, params={'formats': ['markdown']})
    return scrape_result


def web_crawl(url: str):
    """
    Scrape a url and crawl through other links from that page, scraping their contents.
    This tool returns a crawl_id that you will need to use after waiting for a period of time
    to retrieve the final contents. You should attempt to accomplish another task while waiting
    for the crawl to complete.

    Crawl will ignore sublinks of a page if they aren’t children of the url you provide.
    So, the website.com/other-parent/blog-1 wouldn’t be returned if you crawled website.com/blogs/.
    """

    crawl_status = app.crawl_url(
        url, params={'limit': 100, 'scrapeOptions': {'formats': ['markdown']}}, poll_interval=30
    )

    return crawl_status


def retrieve_web_crawl(crawl_id: str):
    """
    Retrieve the results of a previously started web crawl. Crawls take time to process
    so be sure to only use this tool some time after initiating a crawl. The result
    will tell you if the crawl is finished. If it is not, wait some more time then try again.
    """
    return app.check_crawl_status(crawl_id)


def batch_scrape(urls: List[str], formats: List[str] = ['markdown', 'html']):
    """
    Batch scrape multiple URLs simultaneously.

    Args:
        urls: List of URLs to scrape
        formats: List of desired output formats (e.g., ['markdown', 'html'])

    Returns:
        Dictionary containing the batch scrape results
    """
    batch_result = app.batch_scrape_urls(urls, {'formats': formats})
    return batch_result


def async_batch_scrape(urls: List[str], formats: List[str] = ['markdown', 'html']):
    """
    Asynchronously batch scrape multiple URLs.

    Args:
        urls: List of URLs to scrape
        formats: List of desired output formats (e.g., ['markdown', 'html'])

    Returns:
        Dictionary containing the job ID and status URL
    """
    batch_job = app.async_batch_scrape_urls(urls, {'formats': formats})
    return batch_job


def check_batch_status(job_id: str):
    """
    Check the status of an asynchronous batch scrape job.

    Args:
        job_id: The ID of the batch scrape job

    Returns:
        Dictionary containing the current status and results if completed
    """
    return app.check_batch_scrape_status(job_id)


def extract_data(urls: List[str], schema: Optional[Dict[str, Any]] = None, prompt: Optional[str] = None) -> Dict[
    str, Any]:
    """
    Extract structured data from URLs using LLMs.

    Args:
        urls: List of URLs to extract data from
        schema: Optional JSON schema defining the structure of data to extract
        prompt: Optional natural language prompt describing the data to extract

    Returns:
        Dictionary containing the extracted structured data
    """
    params: Dict[str, Any] = {}

    if prompt is not None:
        params['prompt'] = prompt
    elif schema is not None:
        params['schema'] = schema

    data = app.extract(urls, params)
    return data


def map_website(url: str, search: Optional[str] = None):
    """
    Map a website to get all URLs, with optional search functionality.

    Args:
        url: The base URL to map
        search: Optional search term to filter URLs

    Returns:
        Dictionary containing the list of discovered URLs
    """
    params = {'search': search} if search else {}
    map_result = app.map_url(url, params)
    return map_result


def batch_extract(urls: List[str], extract_params: Dict[str, Any]):
    """
    Batch extract structured data from multiple URLs.

    Args:
        urls: List of URLs to extract data from
        extract_params: Dictionary containing extraction parameters including prompt or schema

    Returns:
        Dictionary containing the extracted data from all URLs
    """
    params = {
        'formats': ['extract'],
        'extract': extract_params
    }

    batch_result = app.batch_scrape_urls(urls, params)
    return batch_result
