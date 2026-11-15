"""mcp-il-health — Israeli health registries: doctor licence verification, national nutrition database,
health NGOs directory, medical-cannabis pharmacies & certified physicians, licensed pharmacists.
Live data from data.gov.il (Ministry of Health)."""
from __future__ import annotations

import asyncio
import os

from fastmcp import FastMCP

from . import __version__
from .ckan import datastore_search, meta

R_DOCTORS = "9c64c522-bbc2-48fe-96fb-3b2a8626f59e"  # מאגר רישיונות רופאים
R_NUTRITION = "c3cb0630-0650-46c1-a068-82d575c094b2"  # מאגר התזונה הלאומי — רכיבים ל-100 גרם
R_HEALTH_ORGS = "422972e3-f68f-4d26-bed2-e6b4fb0282a2"  # אוגדן ארגונים ועמותות בתחום הבריאות
R_CANNABIS_PHARM = "f635f611-5b6d-4b21-9cd3-ce7b14da6c11"  # בתי מרקחת המורשים לקנביס רפואי
R_CANNABIS_DOCS = "37f14c29-47af-4b6c-b38e-e08a15e15b5b"  # רופאים מוסמכים לקנביס רפואי
R_PHARMACISTS = "73df1b93-9735-4bc0-b84d-aa5f6bcbfb92"  # רוקחים בעלי הרשאה אישית

DS = {
    "doctors": "Ministry of Health — physician licences",
    "nutrition": "Ministry of Health — Israeli National Nutrition Database",
    "orgs": "Ministry of Health — health organizations & NGOs directory",
    "cannabis_pharm": "Ministry of Health — pharmacies licensed for medical cannabis",
    "cannabis_docs": "Ministry of Health — physicians certified for medical cannabis",
    "pharmacists": "Ministry of Health — pharmacists with personal permit",
}

NUTRIENTS = {
    "energy_kcal": "food_energy", "protein_g": "protein", "fat_g": "total_fat", "saturated_fat_g": "saturated_fat",
    "carbohydrates_g": "carbohydrates", "sugars_g": "total_sugars", "fiber_g": "total_dietary_fiber",
    "sodium_mg": "sodium", "potassium_mg": "potassium", "calcium_mg": "calcium", "iron_mg": "iron",
    "magnesium_mg": "magnesium", "zinc_mg": "zinc", "vitamin_c_mg": "vitamin_c", "vitamin_d_mcg": "vitamin_d",
    "vitamin_b12_mcg": "vitamin_b12", "folate_mcg": "folate", "cholesterol_mg": "cholesterol",
}

mcp = FastMCP(
    "mcp-il-health",
    version=__version__,
    instructions=(
        "Israeli Ministry of Health open registries. verify_doctor checks a physician's licence and specialty; "
        "food_nutrition returns nutrients per 100 g from the national database (search in Hebrew). "
        "Informational only — not medical advice."
    ),
)


def _doctor(r: dict) -> dict:
    def d(v):  # stored as DDMMYYYY integers
        s = str(v) if v else ""
        s = s.zfill(8) if s.isdigit() else s
        return f"{s[4:]}-{s[2:4]}-{s[:2]}" if len(s) == 8 and s.isdigit() else (v or None)

    return {
        "first_name": r.get("שם פרטי"), "last_name": r.get("שם משפחה"),
        "license_number": r.get("מספר רישיון רופא"), "license_date": d(r.get("תאריך רישום רישיון")),
        "specialty": r.get("שם התמחות"), "specialty_certificate": r.get("מספר תעודת התמחות"),
        "specialty_date": d(r.get("תאריך רישום התמחות")),
    }


@mcp.tool
async def verify_doctor(name: str = "", license_number: str = "", specialty: str = "", limit: int = 20) -> dict:
    """Verify an Israeli physician: licence number, licence date and recognised specialties.

    Give a licence number, or a name (Hebrew, e.g. "עודד שלו"), optionally with a specialty keyword.
    A doctor with several specialties appears once per specialty.
    """
    if license_number:
        digits = "".join(ch for ch in license_number if ch.isdigit())
        res = await datastore_search(R_DOCTORS, filters={"מספר רישיון רופא": int(digits)}, limit=20)
    elif name or specialty:
        q = " ".join(x for x in (name, specialty) if x)
        res = await datastore_search(R_DOCTORS, q=q, limit=max(1, min(limit, 100)))
    else:
        raise ValueError("Provide name or license_number")
    return {"total": res["total"], "doctors": [_doctor(r) for r in res["records"]], **meta(DS["doctors"])}


def _food(r: dict, nutrients: list[str] | None = None) -> dict:
    keys = nutrients or list(NUTRIENTS)
    return {
        "code": r.get("smlmitzrach"), "name_he": r.get("shmmitzrach"), "name_en": r.get("english_name"),
        "per_100g": {k: r.get(NUTRIENTS[k]) for k in keys if k in NUTRIENTS and r.get(NUTRIENTS[k]) is not None},
    }


def _best_match(query: str, records: list[dict]) -> dict | None:
    """Prefer a food whose name starts with the query (the plain food), then the shortest name."""
    if not records:
        return None
    q = query.strip()
    starts = [r for r in records if (r.get("shmmitzrach") or "").startswith(q)]
    pool = starts or records
    return min(pool, key=lambda r: len(r.get("shmmitzrach") or ""))


@mcp.tool
async def food_nutrition(food: str, limit: int = 10) -> dict:
    """Nutrients per 100 g for foods and Israeli dishes from the national nutrition database
    (search in Hebrew, e.g. "חומוס", "שקשוקה", "פיתה")."""
    lim = max(1, min(limit, 50))
    res = await datastore_search(R_NUTRITION, q=food, limit=max(lim, 30))
    q = food.strip()
    ranked = sorted(res["records"], key=lambda r: (not (r.get("shmmitzrach") or "").startswith(q),
                                                   len(r.get("shmmitzrach") or "")))
    return {"total": res["total"], "foods": [_food(r) for r in ranked[:lim]], **meta(DS["nutrition"])}


@mcp.tool
async def compare_foods(foods: list[str], nutrients: list[str] | None = None) -> dict:
    """Compare the best match for 2-8 foods side by side. nutrients: subset of
    energy_kcal, protein_g, fat_g, carbohydrates_g, sugars_g, fiber_g, sodium_mg, ... (default: all)."""
    foods = foods[:8]
    res = await asyncio.gather(*(datastore_search(R_NUTRITION, q=f, limit=15) for f in foods))
    rows = []
    for f, r in zip(foods, res, strict=True):
        best = _best_match(f, r["records"])
        rows.append({"query": f, **(_food(best, nutrients) if best else {"match": None})})
    return {"comparison": rows, "available_nutrients": list(NUTRIENTS), **meta(DS["nutrition"])}


@mcp.tool
async def health_organizations(query: str = "", limit: int = 20) -> dict:
    """Directory of health NGOs and patient organizations in Israel (keyword, e.g. "סוכרת", "סרטן")."""
    res = await datastore_search(R_HEALTH_ORGS, q=query or None, limit=max(1, min(limit, 100)))
    rows = [
        {"name": r.get("health_organization_title"), "registration_number": r.get("health_organization_num"),
         "focus": r.get("health_organization_sub_exp"), "audience": r.get("health_organization_colleague"),
         "description": r.get("health_organization_desc"), "website": r.get("health_organization_url"),
         "contact": r.get("health_organization_contact_name")}
        for r in res["records"]
    ]
    return {"total": res["total"], "organizations": rows, **meta(DS["orgs"])}


@mcp.tool
async def medical_cannabis(kind: str = "pharmacies", city: str = "", query: str = "", limit: int = 30) -> dict:
    """Licensed medical-cannabis pharmacies (kind="pharmacies", optional city) or physicians certified
    to issue licences (kind="physicians")."""
    if kind == "physicians":
        res = await datastore_search(R_CANNABIS_DOCS, q=query or None, limit=max(1, min(limit, 100)))
        rows = [{"name": r.get("dr_name"), "specialty": r.get("specialty"), "institution": r.get("institution"),
                 "city": r.get("city")} for r in res["records"]]
        return {"total": res["total"], "physicians": rows, **meta(DS["cannabis_docs"])}
    filters = {"pharmacy_city": city} if city else None
    res = await datastore_search(R_CANNABIS_PHARM, filters=filters, q=query or None, limit=max(1, min(limit, 100)))
    rows = [{"name": r.get("pharmacy_name"), "street": r.get("pharmacy_street"), "city": r.get("pharmacy_city"),
             "delivery": r.get("pharmacy_delivery"), "notes": r.get("pharmacy_notes")} for r in res["records"]]
    return {"total": res["total"], "pharmacies": rows, **meta(DS["cannabis_pharm"])}


@mcp.tool
async def verify_pharmacist(name: str = "", license_number: str = "") -> dict:
    """Pharmacists holding a personal permit (רוקחים בעלי הרשאה אישית), by name or licence number."""
    if license_number:
        res = await datastore_search(R_PHARMACISTS, filters={"License": int("".join(c for c in license_number
                                                                                       if c.isdigit()))})
    elif name:
        res = await datastore_search(R_PHARMACISTS, q=name, limit=20)
    else:
        raise ValueError("Provide name or license_number")
    rows = [{"name": r.get("Name"), "license_number": r.get("License"), "serial": r.get("Serial_num")}
            for r in res["records"]]
    return {"total": res["total"], "pharmacists": rows, **meta(DS["pharmacists"])}


@mcp.tool
async def health() -> dict:
    """Check that the server can reach data.gov.il."""
    try:
        res = await datastore_search(R_DOCTORS, limit=1)
        return {"status": "ok", "physician_records": res["total"], **meta(DS["doctors"])}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


def main() -> None:
    if os.environ.get("MCP_TRANSPORT", "stdio") == "stdio":
        mcp.run()
    else:
        mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
