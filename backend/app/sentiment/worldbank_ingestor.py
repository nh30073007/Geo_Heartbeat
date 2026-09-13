# backend/app/sentiment/worldbank_ingestor.py
"""
World Bank Open Data Ingestor - Real economic indicators.
Free, no API key. Docs: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

import httpx

logger = logging.getLogger(__name__)

WB_BASE = "https://api.worldbank.org/v2"

INDICATORS = {
    "gdp_usd": "NY.GDP.MKTP.CD",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "inflation": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "population": "SP.POP.TOTL",
    "debt_to_gdp": "GC.DOD.TOTL.GD.ZS",
    "exports_pct_gdp": "NE.EXP.GNFS.ZS",
    "imports_pct_gdp": "NE.IMP.GNFS.ZS",
}


class WorldBankIngestor:
    def __init__(self, timeout: float = 20.0):
        self.client = httpx.AsyncClient(timeout=timeout)

    async def fetch_indicator(
        self,
        country_iso2: str,
        indicator_key: str,
    ) -> Optional[Dict]:
        """Fetch most recent non-null value for one indicator."""
        code = INDICATORS.get(indicator_key)
        if not code:
            return None

        url = f"{WB_BASE}/country/{country_iso2}/indicator/{code}"
        params = {"format": "json", "per_page": 10, "date": "2018:2024"}

        try:
            r = await self.client.get(url, params=params)
            r.raise_for_status()
            data = r.json()

            if not isinstance(data, list) or len(data) < 2 or not data[1]:
                return None

            for entry in data[1]:
                if entry.get("value") is not None:
                    return {
                        "country": country_iso2,
                        "indicator": indicator_key,
                        "value": float(entry["value"]),
                        "year": entry.get("date", ""),
                    }
            return None
        except Exception as e:
            logger.debug(f"WorldBank {indicator_key} / {country_iso2}: {e}")
            return None

    async def fetch_all_for_country(self, country_iso2: str) -> Dict[str, float]:
        """Fetch all indicators for one country."""
        import asyncio
        tasks = {
            key: self.fetch_indicator(country_iso2, key)
            for key in INDICATORS
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        output = {}
        for key, res in zip(tasks.keys(), results):
            if isinstance(res, dict) and res:
                output[key] = res["value"]
        return output

    async def close(self):
        await self.client.aclose()