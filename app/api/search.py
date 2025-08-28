from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
import urllib.parse
import asyncio
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/duckduckgo")
async def duckduckgo_search(q: str = Query(..., min_length=1)) -> List[Dict[str, str]]:
    """Perform a basic DuckDuckGo search and return top result links and titles.

    This uses DuckDuckGo HTML search results scraping, which is simple and
    doesn't require an API key. It returns up to 10 results with title and url.
    """
    # Use the HTML endpoint host directly to avoid a redirect response
    search_url = "https://html.duckduckgo.com/html/"
    params = {"q": q}

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(search_url, params=params, headers={"User-Agent": "CalmGuide/1.0"})
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        # Bubble up a friendly error to the client instead of a 500
        raise HTTPException(status_code=502, detail=f"Search provider error: {str(e)}")

    soup = BeautifulSoup(html, "html.parser")
    results = []

    def _unwrap_duckduckgo_link(href: str) -> str:
        """Convert DuckDuckGo redirect links (/l/?uddg=...) to the actual target URL when possible.

        If the link is already an absolute URL that's not a DDG redirect, return as-is. If parsing fails,
        return the original href so the frontend can still try to open it.
        """
        try:
            if not href:
                return href
            # Absolute DDG redirect
            parsed = urllib.parse.urlparse(href)
            if (parsed.netloc and 'duckduckgo.com' in parsed.netloc and parsed.path.startswith('/l/')) or href.startswith('/l/'):
                # Extract uddg parameter
                qs = urllib.parse.parse_qs(parsed.query)
                uddg_vals = qs.get('uddg') or qs.get('u') or []
                if uddg_vals:
                    return urllib.parse.unquote(uddg_vals[0])
                # If no uddg, return absolute DDG link
                if not parsed.netloc:
                    return urllib.parse.urljoin('https://duckduckgo.com', href)
            # If href is relative path, try to make it absolute to duckduckgo
            if href.startswith('/'):
                return urllib.parse.urljoin('https://duckduckgo.com', href)
            return href
        except Exception:
            return href

    # Try a few selectors to be resilient against markup changes
    try:
        anchors = soup.select(".result__a") or soup.select("a.result__a") or soup.select("a[href].result__a")
        if not anchors:
            # Fallback: try any result links in common containers
            anchors = soup.select(".result a") or soup.select(".results a") or soup.find_all("a")

        seen = set()
        for r in anchors:
            title = r.get_text(strip=True)
            href = r.get("href")
            if href:
                href = _unwrap_duckduckgo_link(href)
            if href and title and href not in seen:
                results.append({"title": title, "url": href})
                seen.add(href)
            if len(results) >= 10:
                break
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed parsing search results: {e}")

    return results


@router.get("/duckduckgo_summary")
async def duckduckgo_summary(q: str = Query(..., min_length=1), n: int = Query(3, ge=1, le=10)) -> Dict[str, str]:
    """Search DuckDuckGo for q, take top `n` results and ask the LLM to summarize them.

    Returns JSON: {"summary": "..."}
    """
    # Fetch raw results
    # Use DuckDuckGo's html host which avoids an initial redirect
    search_url = "https://html.duckduckgo.com/html/"
    params = {"q": q}

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(search_url, params=params, headers={"User-Agent": "CalmGuide/1.0"})
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search provider error: {str(e)}")

    soup = BeautifulSoup(html, "html.parser")
    results = []

    def _unwrap_duckduckgo_link(href: str) -> str:
        try:
            if not href:
                return href
            parsed = urllib.parse.urlparse(href)
            if (parsed.netloc and 'duckduckgo.com' in parsed.netloc and parsed.path.startswith('/l/')) or href.startswith('/l/'):
                qs = urllib.parse.parse_qs(parsed.query)
                uddg_vals = qs.get('uddg') or qs.get('u') or []
                if uddg_vals:
                    return urllib.parse.unquote(uddg_vals[0])
                if not parsed.netloc:
                    return urllib.parse.urljoin('https://duckduckgo.com', href)
            if href.startswith('/'):
                return urllib.parse.urljoin('https://duckduckgo.com', href)
            return href
        except Exception:
            return href

    for r in soup.select(".result__a")[:n]:
        title = r.get_text(strip=True)
        href = r.get("href")
        if href:
            href = _unwrap_duckduckgo_link(href)
        if href and title:
            results.append({"title": title, "url": href})

    if not results:
        return {"summary": "No search results found."}

    # Build prompt for LLM
    prompt_lines = [f"Summarize the top {len(results)} web search results for the query: '{q}'. Be concise. For each result, provide a one-sentence summary and the URL. Use bullet points."]
    for i, r in enumerate(results, start=1):
        prompt_lines.append(f"Result {i}: {r['title']} - {r['url']}")

    prompt = "\n".join(prompt_lines)

    # Check LLM availability
    if not llm_service.is_available():
        return {"summary": "LLM service is not available to summarize results."}

    try:
        summary = await llm_service.generate_response(prompt, session_id="search_summary")

        # For TTS, replace URLs with 'link to domain', but keep real URLs in summary for frontend
        import re
        def url_replacer(match):
            url = match.group(0)
            url_clean = url.strip('`').strip()
            domain = re.sub(r'^https?://', '', url_clean).split('/')[0]
            if domain:
                return f'link to {domain}'
            return 'link'

        url_pattern = r'`?(https?://[^\s`]+)`?'
        tts_text = re.sub(url_pattern, url_replacer, summary)

        async def _run_tts_and_log(text: str):
            try:
                audio = await tts_service(text)
                if audio:
                    logger.info(f"Background TTS produced audio (length={len(audio)}) for search summary")
                else:
                    logger.info("Background TTS produced no audio for search summary")
            except Exception as exc:
                logger.error(f"Background TTS error: {exc}")

        # Fire-and-forget: use TTS-friendly text for audio, but send real summary to frontend
        try:
            asyncio.create_task(_run_tts_and_log(tts_text))
        except Exception:
            logger.warning("Unable to schedule background TTS task")

        return {"summary": summary, "audio": ""}
    except Exception as e:
        return {"summary": f"Error summarizing results: {str(e)}"}
