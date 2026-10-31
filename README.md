<!--
  SPDX-FileCopyrightText: 2026 Don Geronimo <https://sentamal.in>
  SPDX-License-Identifier: CC0-1.0
-->

# Open WebUI Tools

A miscellaneous collection of functions and tools made to be used on Open WebUI.

[![REUSE status](https://api.reuse.software/badge/github.com/sentamalin/open-webui-tools)](https://api.reuse.software/info/github.com/sentamalin/open-webui-tools)

## Design philosophy

* **Standardized contracts:** Tools output predictable structures to minimize confusion.
* **Schema-compliant data:** If a schema exists for structure or naming convention (like Schema.org), use it.
* **Configurable guardrails:** Tunable Pydantic `Valves` built directly into the UI for granular runtime control.

## Available tools

| Tool | Directory | Description |
| :--- | :-------- | :---------- |
| **Semantic Fetch URL** | [`semantic-fetch-url/`][0] | Web page fetcher prioritizing Schema.org JSON-LD and clean semantic body normalization. |

## License

This adheres to the [REUSE specification][reuse].

* Source code is licensed under the [MIT License][mit].
* Documentation and READMEs are licensed under [CC0-1.0 Universal][cc0].

See the [LICENSES][licenses] directory and individual file headers for details.

[0]: ./semantic-fetch-url/
[reuse]: https://reuse.software/
[licenses]: ./LICENSES/
[cc0]: ./LICENSES/CC0-1.0.txt
[mit]: ./LICENSES/MIT.txt

