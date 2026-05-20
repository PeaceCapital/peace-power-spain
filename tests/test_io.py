from __future__ import annotations

from io import BytesIO
import unittest
import zipfile

import pandas as pd
import requests

from peace_power.io import (
    fetch_esios_indicator,
    fetch_omie_history,
    fetch_omie_marginal_prices,
    fetch_omie_year_archive,
    parse_omie_marginalpdbc_text,
    search_esios_indicators,
)


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b"",
        json_data: dict[str, object] | None = None,
        url: str = "https://example.test/resource",
    ) -> None:
        self.status_code = status_code
        self.content = content
        self._json_data = json_data or {}
        self.url = url

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self) -> dict[str, object]:
        return self._json_data


class OmieSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def get(self, url: str, params: dict[str, object] | None = None, timeout: int = 60) -> DummyResponse:
        filename = str((params or {}).get("filename", ""))
        self.calls.append(filename)
        if filename.endswith(".zip"):
            archive_bytes = BytesIO()
            with zipfile.ZipFile(archive_bytes, mode="w") as archive:
                archive.writestr(
                    "marginalpdbc_20260101.1",
                    "\n".join(
                        [
                            "MARGINALPDBC;",
                            "2026;1;1;1;50.00;49.00;",
                            "2026;1;1;2;52.00;51.00;",
                            "*",
                        ]
                    ).encode("latin-1"),
                )
                archive.writestr(
                    "marginalpdbc_20260102.1",
                    "\n".join(
                        [
                            "MARGINALPDBC;",
                            "2026;1;2;1;54.00;53.00;",
                            "2026;1;2;2;56.00;55.00;",
                            "*",
                        ]
                    ).encode("latin-1"),
                )
            return DummyResponse(content=archive_bytes.getvalue(), url=f"{url}?filename={filename}")
        if filename.endswith(".9") or filename.endswith(".8") or filename.endswith(".7") or filename.endswith(".6") or filename.endswith(".5") or filename.endswith(".4"):
            return DummyResponse(status_code=404, url=f"{url}?filename={filename}")
        sample = "\n".join(
            [
                "MARGINALPDBC;",
                "2026;3;24;1;85.50;84.10;",
                "2026;3;24;2;80,00;79,50;",
                "*",
            ]
        ).encode("latin-1")
        return DummyResponse(content=sample, url=f"{url}?filename={filename}")


class EsiosSession:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def get(
        self,
        url: str,
        headers: dict[str, object] | None = None,
        params: dict[str, object] | None = None,
        timeout: int = 60,
    ) -> DummyResponse:
        self.calls.append((url, params))
        return DummyResponse(json_data=self.payload, url=url)


class IoTests(unittest.TestCase):
    def test_parse_omie_text_returns_prices(self) -> None:
        text = "\n".join(
            [
                "MARGINALPDBC;",
                "2026;3;24;1;85.50;84.10;",
                "2026;3;24;2;80,00;79,50;",
                "*",
            ]
        )
        frame = parse_omie_marginalpdbc_text(text, source_name="marginalpdbc_20260324.3")
        self.assertEqual(list(frame["period"]), [1, 2])
        self.assertAlmostEqual(frame.loc[1, "price_omie"], 79.5)
        self.assertEqual(int(frame.loc[0, "omie_revision"]), 3)

    def test_fetch_omie_tries_latest_revision(self) -> None:
        session = OmieSession()
        frame = fetch_omie_marginal_prices(
            "2026-03-24",
            revision=None,
            session=session,
        )
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.loc[0, "source_file"], "marginalpdbc_20260324.3")
        self.assertEqual(int(frame.loc[0, "omie_revision"]), 3)
        self.assertIn("marginalpdbc_20260324.3", session.calls)

    def test_fetch_omie_year_archive_returns_combined_rows(self) -> None:
        session = OmieSession()
        frame = fetch_omie_year_archive(
            2026,
            session=session,
        )
        self.assertEqual(len(frame), 4)
        self.assertEqual(frame["delivery_date"].min(), pd.Timestamp("2026-01-01"))
        self.assertEqual(frame["delivery_date"].max(), pd.Timestamp("2026-01-02"))
        self.assertEqual(session.calls[0], "marginalpdbc_2026.zip")

    def test_fetch_omie_history_uses_archives_for_full_years(self) -> None:
        session = OmieSession()
        frame = fetch_omie_history(
            "2026-01-01",
            "2026-12-31",
            session=session,
        )
        self.assertEqual(len(frame), 4)
        self.assertEqual(list(frame["price_omie"]), [49.0, 51.0, 53.0, 55.0])
        self.assertEqual(session.calls[0], "marginalpdbc_2026.zip")

    def test_search_esios_indicators_filters_indicator_results(self) -> None:
        payload = {
            "indicators": [
                {
                    "id": 88001,
                    "name": "Bateria instalada",
                    "short_name": "BESS",
                    "description": "Potencia instalada de baterias",
                }
            ],
        }
        session = EsiosSession(payload)
        frame = search_esios_indicators(
            "bateria",
            token="demo-token",
            session=session,
        )
        self.assertEqual(len(frame), 1)
        self.assertEqual(int(frame.loc[0, "id"]), 88001)
        self.assertEqual(frame.loc[0, "result_bucket"], "indicators")
        self.assertTrue(session.calls[0][0].endswith("/indicators"))
        self.assertEqual(session.calls[0][1], {"text": "bateria"})

    def test_search_esios_indicators_can_include_contents(self) -> None:
        payload = {
            "indicators": [
                {
                    "id": 88001,
                    "name": "Bateria instalada",
                    "short_name": "BESS",
                }
            ],
            "contents": [
                {
                    "id": "content-3",
                    "name": "Mapa demanda",
                    "description": "Mapa REE",
                }
            ],
        }
        session = EsiosSession(payload)
        frame = search_esios_indicators(
            "bateria",
            token="demo-token",
            include_contents=True,
            session=session,
        )
        self.assertEqual(len(frame), 2)
        self.assertTrue(session.calls[0][0].endswith("/search"))
        self.assertEqual(session.calls[0][1], {"query": "bateria"})

    def test_fetch_esios_indicator_flattens_values(self) -> None:
        payload = {
            "indicator": {
                "id": 91001,
                "name": "BESS online",
                "short_name": "BESS_ONLINE",
                "values": [
                    {
                        "datetime": "2026-03-01T00:00:00+01:00",
                        "value": "250.5",
                        "geo_name": "Spain",
                    },
                    {
                        "datetime": "2026-03-01T01:00:00+01:00",
                        "value": "255.0",
                        "geo_name": "Spain",
                    },
                ],
            }
        }
        frame = fetch_esios_indicator(
            91001,
            token="demo-token",
            start_date="2026-03-01T00:00:00+01:00",
            end_date="2026-03-01T23:00:00+01:00",
            session=EsiosSession(payload),
        )
        self.assertEqual(list(frame["indicator_id"]), [91001, 91001])
        self.assertIsInstance(frame["datetime"].dtype, pd.DatetimeTZDtype)
        self.assertAlmostEqual(frame.loc[0, "value"], 250.5)


if __name__ == "__main__":
    unittest.main()
