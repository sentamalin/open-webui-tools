"""
title: Semantic Fetch URL
author: Don Geronimo
author_url: https://sentamal.in
git_url: https://github.com/sentamalin/open-webui-tools.git
description: >
  Fetches a web page via URL. Prioritizes substantive JSON-LD
  (Schema.org) data and semantic HTML tags like <main> or <article>
  before falling back to full <body> text extraction.
requirements: httpx, beautifulsoup4, lxml
version: 0.1.1
license: MIT
SPDX-FileCopyrightText: 2026 Don Geronimo <https://sentamal.in>
SPDX-License-Identifier: MIT
"""

import json
from bs4 import BeautifulSoup
import httpx
import lxml.html
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

    async def semantic_fetch_url(self, url: str) -> str:
        """Fetches a web page, prioritizes substantive JSON-LD
        (Schema.org) data, and falls back to normalized full-body text
        extraction if text content is missing.

        :param url: The full HTTP or HTTPS URL to retrieve.
        :return: A structured JSON string using Schema.org naming
          conventions (i.e. url, name, text), optionally including
          JSON-LD metadata of type WebPage if enabled via valves.
        """
        headers = {
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

        try:
            async with httpx.AsyncClient(
                timeout=15.0, follow_redirects=True
            ) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                html_content = response.text
        except httpx.HTTPError as e:
            return json.dumps(
                {
                    "error": f"HTTP request failed: {str(e)}",
                    "url": url,
                }
            )

        soup = BeautifulSoup(html_content, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
        payload = {}

        # Get the URL and the HTML title
        payload["url"] = url
        payload["name"] = title

        # Attempt to extract native JSON-LD (Schema.org) blocks
        json_ld_data = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                parsed = json.loads(script.string or script.text)
                if isinstance(parsed, dict):
                    json_ld_data = parsed
                    break
                elif isinstance(parsed, list) and len(parsed) > 0:
                    json_ld_data = parsed[0]
                    break
            except (json.JSONDecodeError, TypeError):
                continue

        # Use available JSON-LD data first to construct payload key-values
        if json_ld_data:
            source_json = dict(json_ld_data)

            # Use JSON-LD `name` instead of the HTML title if defined by author
            if source_json.get("name"):
                payload["name"] = source_json["name"]

            # Add `headline` key if defined by author
            if source_json.get("headline"):
                payload["headline"] = source_json["headline"]

            # Add `description` key if defined by author
            if source_json.get("description"):
                payload["description"] = source_json["description"]

            # Add `abstract` key if defined by author
            if source_json.get("abstract"):
                payload["abstract"] = source_json["abstract"]

            # Prioritize `articleBody`, then `text`, then a
            # `mainContentOfPage` element hint for the payload `text` key
            if not source_json.get("articleBody") and source_json.get("text"):
                payload["text"] = source_json["text"]
            elif source_json.get("articleBody"):
                payload["text"] = source_json["articleBody"]
            elif source_json.get("mainContentOfPage"):
                main_content = source_json["mainContentOfPage"]
                elements = (
                    main_content
                    if isinstance(main_content, list)
                    else [main_content]
                )
                for elem in elements:
                    css_selector = elem.get("cssSelector")
                    if css_selector and soup:
                        target_el = soup.select_one(css_selector)
                        if target_el:
                            payload["text"] = target_el.get_text(
                                separator=" ", strip=True
                            )
                            break
                    xpath = elem.get("xpath")
                    if xpath and soup:
                        try:
                            dom = lxml.html.fromstring(str(soup))
                            matches = dom.xpath(xpath)
                            if matches and hasattr(matches[0], "text_content"):
                                raw_xpath_text = matches[0].text_content()
                                payload["text"] = " ".join(
                                    raw_xpath_text.split()
                                )
                                break
                        except Exception:
                            pass

        # Fallback to full-body semantic HTML scraping if no `text` or
        # `articleBody` key in JSON-LD
        if not payload.get("text"):
            content_container = (
                soup.find("main")
                or soup.find("article")
                or soup.body
                or soup
            )
            raw_text = content_container.get_text(separator=" ", strip=True)
            payload["text"] = " ".join(raw_text.split())

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

