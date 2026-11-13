import asyncio

import pytest
from fastmcp import Client

from mcp_il_health import server

FAKE = {"total": 1, "records": [{"dummy": "value"}]}


async def _fake_search(resource_id, **kwargs):
    return FAKE


def _call(tool, args):
    async def run():
        async with Client(server.mcp) as client:
            return await client.call_tool(tool, args)

    return asyncio.run(run())


def test_tools_registered():
    async def run():
        async with Client(server.mcp) as client:
            return {t.name for t in await client.list_tools()}

    names = asyncio.run(run())
    assert {'medical_cannabis', 'food_nutrition', 'verify_doctor', 'health', 'health_organizations', 'compare_foods', 'verify_pharmacist'} <= names


def test_offline_call_has_provenance(monkeypatch):
    monkeypatch.setattr(server, "datastore_search", _fake_search)
    result = _call('food_nutrition', {'food': 'חומוס'})
    data = result.data if hasattr(result, "data") else result
    assert "source" in data and "data.gov.il" in data["source"]


def test_clean_value():
    from mcp_il_health.ckan import clean_value

    assert clean_value("בע~מ") == 'בע"מ'
    assert clean_value("  ") is None


@pytest.mark.live
def test_live_smoke():
    result = _call('verify_doctor', {'name': 'כהן', 'limit': 2})
    data = result.data if hasattr(result, "data") else result
    assert "retrieved_at" in data
