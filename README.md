# mcp-il-health

<!-- mcp-name: io.github.olegsher-ds-2025/mcp-il-health -->

Israeli Ministry of Health registries for AI agents: doctor licence verification, national nutrition database, health NGOs, medical-cannabis pharmacies — live from data.gov.il.

**מאגרי משרד הבריאות: אימות רישיון רופא, מאגר התזונה הלאומי, ארגוני בריאות, קנביס רפואי**

An [MCP](https://modelcontextprotocol.io) server that lets Claude and other AI assistants query official Israeli
government open data in plain language. No API key, no scraping — every call goes to the public
[data.gov.il](https://data.gov.il) CKAN API and returns the source with each answer.

## Tools

| Tool | What it does |
|---|---|
| `verify_doctor` | Physician licence number, date and recognised specialties |
| `food_nutrition` | Nutrients per 100 g from the Israeli National Nutrition Database |
| `compare_foods` | Side-by-side nutrient comparison of up to 8 foods |
| `health_organizations` | Health NGOs and patient organizations directory |
| `medical_cannabis` | Licensed cannabis pharmacies or certified physicians |
| `verify_pharmacist` | Pharmacists with personal permit |
| `health` | Connectivity check |

## Try asking

- “Is Dr. Oded Shalev a licensed specialist in internal medicine?”
- “How much protein is in 100 g of hummus vs. tahini?”
- “Which patient organizations work on diabetes?”

## Install

No install needed with [uv](https://docs.astral.sh/uv/):

```bash
uvx mcp-il-health
```

Claude Desktop / Claude Code (`.mcp.json`):

```json
{ "mcpServers": { "il-health": { "command": "uvx", "args": ["mcp-il-health"] } } }
```

Or `pip install mcp-il-health`, or from source: `pip install git+https://github.com/olegsher-ds-2025/mcp-il-health`.

Also listed in the official MCP Registry as `io.github.olegsher-ds-2025/mcp-il-health`.

Run over HTTP (for remote hosting):

```bash
MCP_TRANSPORT=http PORT=8000 mcp-il-health   # → http://localhost:8000/mcp
```

Docker: `docker build -t mcp-il-health . && docker run -p 8000:8000 mcp-il-health`.

Prefect Horizon entrypoint: `server.py:mcp`.

## Verify the package

Releases are built and published by GitHub Actions with PyPI Trusted Publishing — no stored tokens.
Each release carries PyPI (PEP 740) attestations and a GitHub build-provenance attestation:

```bash
pip download mcp-il-health --no-deps -d dl && gh attestation verify dl/*.whl -R olegsher-ds-2025/mcp-il-health
```

## Data sources

- Physician licences
- Israeli National Nutrition Database
- Health organizations directory
- Medical-cannabis pharmacies & certified physicians
- Pharmacists with personal permit

All data © the publishing Israeli government authority, via data.gov.il. This project is independent and not
affiliated with the Government of Israel. Registry data can lag; verify critical facts with the authority.

## Development

```bash
pip install -e ".[dev]"
pytest            # offline tests
pytest -m live    # hits data.gov.il
```

## Roadmap

- [ ] Drug registry (israeldrugs.health.gov.il) — API blocks cloud POSTs; needs testing from a local IP
- [ ] Health basket (סל הבריאות) decisions
- [ ] Hospital & clinic directory with geolocation
- [ ] Link nutrition to PubMed evidence (Life Science News channel)

## Related

Part of a family of Israeli public-data MCP servers by [Oleg Sher](https://linkedin.com/in/sheroleg):
mcp-il-companies · mcp-il-vehicles · mcp-il-health · mcp-il-professionals · mcp-cbs-places · mcp-mavat.

## License

MIT
