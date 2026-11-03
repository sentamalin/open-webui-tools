<!--
  SPDX-FileCopyrightText: 2026 Don Geronimo <https://sentamal.in>
  SPDX-License-Identifier: CC0-1.0
-->

# Semantic Fetch URL

Fetches a web page via URL. Prioritizes substantive JSON-LD (Schema.org) data and semantic HTML tags like `<main>` or `<article>` before falling back to full-body text extraction.

## Why use this?

The default web fetcher `fetch_url` takes the contents of a page's `<body>`, strips out HTML tags, and dumps it into the LLM's context window. This can introduce a lot of noise. `semantic_fetch_url` solves this by:

* **Prioritizing native JSON-LD (Schema.org):** Extracts structured data (`url`, `name`, `text`) directly when authored by the site
* **Semantic fallback:** Cascading `text` extraction from (in order):
    * JSON-LD `mainContentOfPage` property
    * HTML `<main>` tag
    * HTML `<article>` tag
    * HTML `<body>` tag
* **Pristine normalization:** Cleans whitespace chaos while respecting configurable size ceilings

## Installation

1. In Open WebUI, navigate to **Workspace > Tools > Create New Tool**
2. Copy the contents of `semantic-fetch-url.py` and paste it into the editor
3. Click **Save**

## Recommended agent configuration

To prevent the model from defaulting to the default `fetch_url` tool, add the following directive to your model's **System Prompt**:

> **Web Fetch Policy:** You **must** use Semantic Fetch URL (`semantic_fetch_url`) when retrieving a URL or reading from search results (`search_web`). **Do not use** `fetch_url`.

## Configuration valves

You can tune the behavior of `semantic_fetch_url` directly from the Open WebUI interface via its Pydantic valves:

* `max_chars`: Maximum character ceiling for the text payload (`0` for unlimited content); default: `0`
* `include_semantic_metadata`: Include @context and @type JSON-LD keys in the output; default `false`

## License

Code licensed under the [MIT License][mit]. Documentation licensed under [CC0-1.0 Universal][cc0].

[mit]: ../LICENSES/MIT.txt
[cc0]: ../LICENSES/CC0-1.0.txt

