"""Input loaders and live-data helpers for the Peace Power Spain stack."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Iterable
import zipfile

import pandas as pd
import requests


OMIE_DOWNLOAD_URL = "https://www.omie.es/en/file-download"
OMIE_MARGINAL_PRICES_PARENT = "marginalpdbc"
ESIOS_BASE_URL = "https://api.esios.ree.es"


def _coerce_date_string(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y%m%d")


def _coerce_iso_datetime(value: object) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.isoformat()
    return ts.tz_convert("UTC").isoformat()


def _decode_text_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _raise_for_status(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        detail = f"HTTP {status}" if status else "HTTP error"
        wrapped = requests.HTTPError(f"{detail} for {response.url}")
        wrapped.response = response
        raise wrapped from exc


def _to_float(value: object) -> float:
    text = str(value).strip().replace(",", ".")
    if not text:
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def build_omie_daily_filename(trade_date: object, revision: int = 1) -> str:
    """Build the OMIE daily day-ahead price filename for Spain."""
    if revision < 1:
        raise ValueError("revision must be >= 1")
    return f"{OMIE_MARGINAL_PRICES_PARENT}_{_coerce_date_string(trade_date)}.{revision}"


def build_omie_year_archive_filename(year: int) -> str:
    """Build the OMIE yearly archive filename for Spain day-ahead prices."""
    if year < 2000:
        raise ValueError("year looks invalid")
    return f"{OMIE_MARGINAL_PRICES_PARENT}_{year}.zip"


def download_omie_raw_file(
    filename: str,
    *,
    output_path: str | Path | None = None,
    parents: str = OMIE_MARGINAL_PRICES_PARENT,
    session: requests.Session | None = None,
    timeout: int = 60,
) -> bytes | Path:
    """Download a raw OMIE file and optionally persist it locally."""
    http = session or requests.Session()
    response = http.get(
        OMIE_DOWNLOAD_URL,
        params={"filename": filename, "parents": parents},
        timeout=timeout,
    )
    _raise_for_status(response)
    content = response.content
    if output_path is None:
        return content
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def parse_omie_marginalpdbc_text(
    text: str,
    *,
    source_name: str | None = None,
) -> pd.DataFrame:
    """Parse an OMIE `marginalpdbc` daily file into a tidy DataFrame."""
    rows: list[dict[str, object]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "*" or line.startswith("MARGINALPDBC"):
            continue
        parts = [part.strip() for part in line.split(";")]
        if parts and parts[-1] == "":
            parts = parts[:-1]
        if len(parts) < 6:
            continue
        year, month, day, period = parts[:4]
        if not all(field.isdigit() for field in (year, month, day, period)):
            continue
        rows.append(
            {
                "year": int(year),
                "month": int(month),
                "day": int(day),
                "period": int(period),
                "price_portugal": _to_float(parts[4]),
                "price_spain": _to_float(parts[5]),
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return pd.DataFrame(
            columns=[
                "datetime",
                "delivery_date",
                "period",
                "period_minutes",
                "price_portugal",
                "price_spain",
                "price_omie",
                "source_file",
                "omie_revision",
            ]
        )

    max_period = int(frame["period"].max())
    period_minutes = 15 if max_period > 25 else 60
    delivery_date = pd.to_datetime(frame[["year", "month", "day"]])
    frame["delivery_date"] = delivery_date.dt.normalize()
    frame["datetime"] = frame["delivery_date"] + pd.to_timedelta(
        (frame["period"] - 1) * period_minutes,
        unit="m",
    )
    frame["period_minutes"] = period_minutes
    frame["price_omie"] = frame["price_spain"]
    frame["source_file"] = source_name

    revision = None
    if source_name and "." in source_name:
        tail = source_name.rsplit(".", 1)[-1]
        revision = int(tail) if tail.isdigit() else None
    frame["omie_revision"] = revision

    ordered = [
        "datetime",
        "delivery_date",
        "period",
        "period_minutes",
        "price_portugal",
        "price_spain",
        "price_omie",
        "source_file",
        "omie_revision",
    ]
    return frame[ordered].sort_values(["datetime", "period"]).reset_index(drop=True)


def load_omie_marginalpdbc_file(path: str | Path) -> pd.DataFrame:
    """Load a raw OMIE daily file or yearly archive into a DataFrame."""
    file_path = Path(path)
    if file_path.suffix.lower() == ".zip":
        return load_omie_year_archive(file_path)
    return parse_omie_marginalpdbc_text(
        _decode_text_bytes(file_path.read_bytes()),
        source_name=file_path.name,
    )


def load_omie_year_archive(
    path: str | Path,
    *,
    members: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load all OMIE daily files from a yearly archive into one DataFrame."""
    archive_path = Path(path)
    wanted = set(members or [])
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if not name.endswith("/")
            and name.startswith(f"{OMIE_MARGINAL_PRICES_PARENT}_")
            and (not wanted or name in wanted)
        )
        for name in names:
            frames.append(
                parse_omie_marginalpdbc_text(
                    _decode_text_bytes(archive.read(name)),
                    source_name=name,
                )
            )
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def fetch_omie_year_archive(
    year: int,
    *,
    output_dir: str | Path | None = None,
    session: requests.Session | None = None,
    timeout: int = 120,
) -> pd.DataFrame:
    """Download and parse one OMIE yearly archive."""
    filename = build_omie_year_archive_filename(year)
    output_path = Path(output_dir) / filename if output_dir else None
    result = download_omie_raw_file(
        filename,
        output_path=output_path,
        session=session,
        timeout=timeout,
    )
    if isinstance(result, Path):
        return load_omie_year_archive(result)
    with zipfile.ZipFile(BytesIO(result)) as archive:
        frames: list[pd.DataFrame] = []
        for name in sorted(
            entry
            for entry in archive.namelist()
            if not entry.endswith("/") and entry.startswith(f"{OMIE_MARGINAL_PRICES_PARENT}_")
        ):
            frames.append(
                parse_omie_marginalpdbc_text(
                    _decode_text_bytes(archive.read(name)),
                    source_name=name,
                )
            )
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def fetch_omie_marginal_prices(
    start_date: object,
    end_date: object | None = None,
    *,
    revision: int | None = None,
    output_dir: str | Path | None = None,
    session: requests.Session | None = None,
    timeout: int = 60,
) -> pd.DataFrame:
    """Download and parse OMIE day-ahead Spain prices over a date range."""
    http = session or requests.Session()
    dates = pd.date_range(start=pd.Timestamp(start_date), end=pd.Timestamp(end_date or start_date), freq="D")
    frames: list[pd.DataFrame] = []
    revisions = [revision] if revision is not None else list(range(9, 0, -1))

    for trade_date in dates:
        last_error: Exception | None = None
        raw_content: bytes | None = None
        found_filename: str | None = None
        for candidate in revisions:
            filename = build_omie_daily_filename(trade_date, candidate)
            output_path = Path(output_dir) / filename if output_dir else None
            try:
                result = download_omie_raw_file(
                    filename,
                    output_path=output_path,
                    session=http,
                    timeout=timeout,
                )
            except requests.HTTPError as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if revision is None and status == 404:
                    last_error = exc
                    continue
                raise
            found_filename = filename
            if isinstance(result, Path):
                raw_content = result.read_bytes()
            else:
                raw_content = result
            break
        if raw_content is None or found_filename is None:
            if last_error is not None:
                raise last_error
            raise FileNotFoundError(f"Could not download OMIE data for {trade_date:%Y-%m-%d}")
        frames.append(
            parse_omie_marginalpdbc_text(
                _decode_text_bytes(raw_content),
                source_name=found_filename,
            )
        )

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False)


def fetch_omie_history(
    start_date: object,
    end_date: object,
    *,
    prefer_year_archives: bool = True,
    output_dir: str | Path | None = None,
    revision: int | None = None,
    session: requests.Session | None = None,
    timeout: int = 120,
) -> pd.DataFrame:
    """Backfill OMIE prices over a long range using yearly archives when possible."""
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize()
    if end < start:
        raise ValueError("end_date must be on or after start_date.")

    http = session or requests.Session()
    frames: list[pd.DataFrame] = []
    year_output_dir = Path(output_dir) / "archives" if output_dir else None
    daily_output_dir = Path(output_dir) / "daily" if output_dir else None

    for year in range(start.year, end.year + 1):
        year_start = pd.Timestamp(year=year, month=1, day=1)
        year_end = pd.Timestamp(year=year, month=12, day=31)
        segment_start = max(start, year_start)
        segment_end = min(end, year_end)
        full_year_requested = segment_start == year_start and segment_end == year_end

        if prefer_year_archives and full_year_requested:
            frame = fetch_omie_year_archive(
                year,
                output_dir=year_output_dir,
                session=http,
                timeout=timeout,
            )
        else:
            frame = fetch_omie_marginal_prices(
                segment_start,
                segment_end,
                revision=revision,
                output_dir=daily_output_dir,
                session=http,
                timeout=timeout,
            )

        if frame.empty:
            continue
        delivery = pd.to_datetime(frame["delivery_date"], errors="coerce").dt.normalize()
        mask = (delivery >= segment_start) & (delivery <= segment_end)
        frames.append(frame.loc[mask].copy())

    if not frames:
        return pd.DataFrame()

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined = combined.sort_values(["datetime", "period"]).drop_duplicates(
        subset=["datetime", "period"],
        keep="last",
    )
    return combined.reset_index(drop=True)


def resolve_esios_token(token: str | None = None, *, env_var: str = "ESIOS_TOKEN") -> str:
    """Resolve an ESIOS API token from an argument or environment variable."""
    resolved = token or os.getenv(env_var, "").strip()
    if not resolved:
        raise ValueError(f"Provide an ESIOS token or set {env_var}.")
    return resolved


def _esios_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/json; application/vnd.esios-api-v1+json",
        "Content-Type": "application/json",
        "x-api-key": token,
    }


def _esios_get(
    path: str,
    *,
    token: str | None = None,
    params: dict[str, object] | None = None,
    session: requests.Session | None = None,
    timeout: int = 60,
) -> dict[str, object]:
    http = session or requests.Session()
    response = http.get(
        f"{ESIOS_BASE_URL}{path}",
        headers=_esios_headers(resolve_esios_token(token)),
        params=params,
        timeout=timeout,
    )
    _raise_for_status(response)
    return response.json()


def _flatten_search_payload(payload: dict[str, object]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for bucket, values in payload.items():
        if isinstance(values, list) and values and isinstance(values[0], dict):
            frame = pd.json_normalize(values, sep="_")
            frame["result_bucket"] = bucket
            frames.append(frame)
    if not frames:
        return pd.DataFrame()
    merged = pd.concat(frames, ignore_index=True, sort=False)
    merged.columns = [col.replace(".", "_") for col in merged.columns]
    if "type" in merged.columns:
        merged = merged.rename(columns={"type": "result_type"})
    if "result_type" not in merged.columns:
        merged["result_type"] = merged["result_bucket"]
    else:
        merged["result_type"] = merged["result_type"].fillna(merged["result_bucket"])
    return merged.drop_duplicates().reset_index(drop=True)


def search_esios_indicators(
    query: str,
    *,
    token: str | None = None,
    include_contents: bool = False,
    limit: int | None = 25,
    session: requests.Session | None = None,
    timeout: int = 60,
) -> pd.DataFrame:
    """Search ESIOS indicators by free text and return a notebook-friendly DataFrame."""
    if include_contents:
        payload = _esios_get(
            "/search",
            token=token,
            params={"query": query},
            session=session,
            timeout=timeout,
        )
        frame = _flatten_search_payload(payload)
    else:
        payload = _esios_get(
            "/indicators",
            token=token,
            params={"text": query},
            session=session,
            timeout=timeout,
        )
        indicators = payload.get("indicators", []) if isinstance(payload, dict) else []
        frame = pd.json_normalize(indicators, sep="_") if indicators else pd.DataFrame()
        if not frame.empty:
            frame.columns = [col.replace(".", "_") for col in frame.columns]
            frame["result_bucket"] = "indicators"
            frame["result_type"] = "indicators"
    if frame.empty:
        return frame

    indicator_mask = pd.Series(False, index=frame.index)
    for col in ("result_bucket", "result_type"):
        if col in frame.columns:
            indicator_mask = indicator_mask | frame[col].astype(str).str.contains(
                "indicator",
                case=False,
                na=False,
            )
    if not include_contents and indicator_mask.any():
        frame = frame.loc[indicator_mask].copy()

    rank = pd.Series(0, index=frame.index, dtype=float)
    lowered = query.lower()
    for col in ("name", "short_name", "description"):
        if col in frame.columns:
            text = frame[col].fillna("").astype(str).str.lower()
            rank = rank + text.str.contains(lowered, regex=False).astype(float)
    if "id" in frame.columns:
        frame["id"] = pd.to_numeric(frame["id"], errors="coerce").astype("Int64")
    frame["match_score"] = rank
    frame = frame.sort_values(["match_score", "id"], ascending=[False, True], na_position="last")
    if limit is not None:
        frame = frame.head(limit)

    preferred = [
        "id",
        "name",
        "short_name",
        "description",
        "result_type",
        "result_bucket",
        "match_score",
    ]
    cols = [col for col in preferred if col in frame.columns] + [
        col for col in frame.columns if col not in preferred
    ]
    return frame[cols].reset_index(drop=True)


def fetch_esios_indicator(
    indicator_id: int | str,
    *,
    token: str | None = None,
    start_date: object | None = None,
    end_date: object | None = None,
    datetime: object | None = None,
    time_trunc: str | None = "hour",
    time_agg: str | None = None,
    geo_ids: Iterable[int | str] | None = None,
    geo_trunc: str | None = None,
    geo_agg: str | None = None,
    locale: str = "en",
    session: requests.Session | None = None,
    timeout: int = 60,
) -> pd.DataFrame:
    """Fetch one ESIOS indicator and flatten its values into a DataFrame."""
    params: dict[str, object] = {"locale": locale}
    if datetime is not None:
        params["datetime"] = _coerce_iso_datetime(datetime)
    if start_date is not None:
        params["start_date"] = _coerce_iso_datetime(start_date)
    if end_date is not None:
        params["end_date"] = _coerce_iso_datetime(end_date)
    if time_trunc:
        params["time_trunc"] = time_trunc
    if time_agg:
        params["time_agg"] = time_agg
    if geo_ids:
        params["geo_ids[]"] = [str(value) for value in geo_ids]
    if geo_trunc:
        params["geo_trunc"] = geo_trunc
    if geo_agg:
        params["geo_agg"] = geo_agg

    payload = _esios_get(
        f"/indicators/{indicator_id}",
        token=token,
        params=params,
        session=session,
        timeout=timeout,
    )
    indicator = payload.get("indicator", payload)
    values = indicator.get("values", []) if isinstance(indicator, dict) else []
    frame = pd.json_normalize(values, sep="_") if values else pd.DataFrame()
    frame.columns = [col.replace(".", "_") for col in frame.columns]

    if "value" in frame.columns:
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    for col in ("datetime", "datetime_utc", "datetime_local"):
        if col in frame.columns:
            frame[col] = pd.to_datetime(frame[col], errors="coerce", utc=col.endswith("_utc"))
    if "datetime" not in frame.columns:
        if "datetime_local" in frame.columns:
            frame["datetime"] = frame["datetime_local"]
        elif "datetime_utc" in frame.columns:
            frame["datetime"] = frame["datetime_utc"]

    metadata = {
        "indicator_id": indicator.get("id", indicator_id) if isinstance(indicator, dict) else indicator_id,
        "indicator_name": indicator.get("name") if isinstance(indicator, dict) else None,
        "indicator_short_name": indicator.get("short_name") if isinstance(indicator, dict) else None,
    }
    for key, value in reversed(list(metadata.items())):
        frame.insert(0, key, value)

    preferred = [
        "indicator_id",
        "indicator_name",
        "indicator_short_name",
        "datetime",
        "datetime_local",
        "datetime_utc",
        "value",
    ]
    cols = [col for col in preferred if col in frame.columns] + [
        col for col in frame.columns if col not in preferred
    ]
    return frame[cols]


def load_bess_dispatch_csv(path: str | Path) -> pd.DataFrame:
    """Load hourly BESS deployment and dispatch data from a CSV."""
    df = pd.read_csv(path)
    required = {"datetime", "bess_online_mw", "bess_absorption_mw", "bess_discharge_mw"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"BESS dispatch CSV missing columns: {', '.join(sorted(missing))}")
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.dropna(subset=["datetime"]).sort_values("datetime")
    df = df.set_index("datetime")
    for col in ["bess_online_mw", "bess_absorption_mw", "bess_discharge_mw"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def load_node_capacity_csv(path: str | Path) -> pd.DataFrame:
    """Load REE node-capacity map data from a CSV."""
    df = pd.read_csv(path)
    required = {"node_id", "node_name", "region", "available_capacity_mw"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"REE node-capacity CSV missing columns: {', '.join(sorted(missing))}")
    df = df.copy()
    df["available_capacity_mw"] = pd.to_numeric(df["available_capacity_mw"], errors="coerce").fillna(0.0)
    return df


def merge_bess_dispatch(market_df: pd.DataFrame, bess_df: pd.DataFrame) -> pd.DataFrame:
    """Left-join hourly BESS dispatch onto a market feature frame."""
    if not isinstance(market_df.index, pd.DatetimeIndex):
        raise ValueError("market_df must be indexed by datetime.")
    if not isinstance(bess_df.index, pd.DatetimeIndex):
        raise ValueError("bess_df must be indexed by datetime.")
    merged = market_df.join(
        bess_df[["bess_online_mw", "bess_absorption_mw", "bess_discharge_mw"]],
        how="left",
    )
    for col in ["bess_online_mw", "bess_absorption_mw", "bess_discharge_mw"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)
    return merged
