"""
title: Semantic Fetch URL
author: Don Geronimo
author_url: https://sentamal.in
git_url: https://github.com/sentamalin/open-webui-tools.git
description: >
  Fetches a web page via URL. Prioritizes substantive JSON-LD
  (Schema.org) data and semantic HTML tags like <main> or <article>
  before falling back to full <body> text extraction.
requirements: httpx, beautifulsoup4, lxml, markdownify
version: 0.1.2
license: MIT
SPDX-FileCopyrightText: 2026 Don Geronimo <https://sentamal.in>
SPDX-License-Identifier: MIT
"""

import json
from bs4 import BeautifulSoup
from typing import Any
import httpx
import lxml.html
from markdownify import markdownify
try: # A bypass stub to allow testing the function using the command line
    from pydantic import BaseModel, Field
except ImportError:
    class Field:
        def __init__(self, default=None, **kwargs):
            self.default = default
    class BaseModel:
        def __init__(self):
            for key, value in self.__class__.__dict__.items():
                if isinstance(value, Field):
                    setattr(self, key, value.default)

class Tools:

    class Valves(BaseModel):
        max_chars: int = Field(
            default=0,
            description=(
                "Maximum character ceiling for the 'text' content "
                "payload (0 for no limit)."
            ),
        )
        include_semantic_metadata: bool = Field(
            default=False,
            description=(
                "Include @context and @type JSON-LD metadata in the "
                "output."
            ),
        )

    def __init__(self):
        self.valves = self.Valves()

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="125"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Linux"',
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    async def _fetch_html(
        self, client: httpx.AsyncClient, url: str
    ) -> str | dict[str, Any]:
        """Fetches raw HTML content from the given URL."""
        try:
            response = await client.get(url, headers=self._HEADERS)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as e:
            error = {}
            if self.valves.include_semantic_metadata:
                error["@context"] = "https://schema.org/"
                error["@type"] = "Error"
            error["url"] = url
            if isinstance(e, httpx.HTTPStatusError):
                error["errorCode"] = e.response.status_code
            error["description"] = str(e)
            return error

    def _extract_json_ld(self, soup: BeautifulSoup) -> dict[str, Any] | None:
        """Extracts the first valid Schema.org JSON-LD data block."""
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                parsed = json.loads(script.string or script.text)
                if isinstance(parsed, dict):
                    return parsed
                elif isinstance(parsed, list) and len(parsed) > 0:
                    return parsed[0]
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _extract_via_css(
        self, elem: dict, soup: BeautifulSoup
    ) -> str | None:
        """Extracts and markdownifies content matching a CSS selector."""
        css_selector = elem.get("cssSelector")
        if css_selector and soup:
            target_el = soup.select_one(css_selector)
            if target_el:
                return markdownify(
                    str(target_el), heading_style="ATX"
                ).strip()
        return None

    def _extract_via_xpath(
        self, elem: dict, soup: BeautifulSoup
    ) -> str | None:
        """Extracts and markdownifies content matching an XPath."""
        xpath = elem.get("xpath")
        if xpath and soup:
            try:
                dom = lxml.html.fromstring(str(soup))
                matches = dom.xpath(xpath)
                if matches and hasattr(matches[0], "text_content"):
                    html_snippet = lxml.html.tostring(
                        matches[0], encoding="unicode"
                    )
                    return markdownify(
                        html_snippet, heading_style="ATX"
                    ).strip()
            except Exception:
                pass
        return None

    def _resolve_main_content_hint(
        self, main_content: Any, soup: BeautifulSoup
    ) -> str | None:
        """Resolves `mainContentOfPage` hints via CSS selectors or XPaths."""
        elements = (
            main_content
            if isinstance(main_content, list)
            else [main_content]
        )
        for elem in elements:
            if not isinstance(elem, dict):
                continue
            text = self._extract_via_css(elem, soup)
            if text:
                return text
            text = self._extract_via_xpath(elem, soup)
            if text:
                return text
        return None

    def _apply_json_ld_data(
        self, source_json: dict, soup: BeautifulSoup, payload: dict
    ) -> None:
        """Populates the payload using extracted JSON-LD data."""
        for field in ("name", "headline", "description", "abstract"):
            if source_json.get(field):
                payload[field] = source_json[field]

        if not source_json.get("articleBody") and source_json.get("text"):
            payload["text"] = source_json["text"]
        elif source_json.get("articleBody"):
            payload["text"] = source_json["articleBody"]
        elif source_json.get("mainContentOfPage"):
            hint_text = self._resolve_main_content_hint(
                source_json["mainContentOfPage"], soup
            )
            if hint_text:
                payload["text"] = hint_text

    def _apply_semantic_fallback(
        self, soup: BeautifulSoup, payload: dict
    ) -> None:
        """If `text` is missing, apply full-body semantic HTML scraping."""
        if not payload.get("text"):
            content_container = (
                soup.find("main")
                or soup.find("article")
                or soup.body
                or soup
            )
            payload["text"] = markdownify(
                str(content_container), heading_style="ATX"
            ).strip()

    async def semantic_fetch_url(self, url: str) -> str:
        """Fetches a web page, prioritizes substantive JSON-LD
        (Schema.org) data, and falls back to normalized full-body text
        extraction if text content is missing.

        :param url: The full HTTP or HTTPS URL to retrieve.
        :return: A structured JSON string using Schema.org naming
          conventions (i.e. url, name, text), optionally including
          JSON-LD metadata of type WebPage if enabled via valves.
        """
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True
        ) as client:
            html_content = await self._fetch_html(client, url)

        if isinstance(html_content, dict):
            return json.dumps(html_content, ensure_ascii=False, indent=2)

        soup = BeautifulSoup(html_content, "html.parser")
        payload = {}
        payload["url"] = url
        payload["name"] = soup.title.string.strip() if soup.title else ""

        json_ld_data = self._extract_json_ld(soup)
        if json_ld_data:
            self._apply_json_ld_data(dict(json_ld_data), soup, payload)
        self._apply_semantic_fallback(soup, payload)

        # Truncate `text` to fit in the maximum characters if
        # `max_chars` is greater than 0
        if self.valves.max_chars > 0:
            payload["text"] = payload["text"][: self.valves.max_chars]

        # 3. Add metadata to make the payload JSON-LD if
        # `include_semantic_metadata` is true
        if self.valves.include_semantic_metadata:
            payload["@context"] = "https://schema.org/"
            payload["@type"] = "WebPage"

        # Serialize safely without breaking JSON syntax
        return json.dumps(payload, ensure_ascii=False, indent=2)

# Simple function to test the tool on the command line
if __name__ == "__main__":
    import asyncio
    import sys

    async def test():
        url = "https://openwebui.com"
        if len(sys.argv) >= 2:
            url = sys.argv[1]
        tool = Tools()
        # Test with a sample URL
        print(f"Fetching: {url}...\n")
        result = await tool.semantic_fetch_url(url)
        print(result)

    asyncio.run(test())

