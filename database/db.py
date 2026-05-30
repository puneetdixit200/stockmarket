from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from common import json_dumps, now_iso


def initialise_database(db_path: str | Path = "database/stocks.db") -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def upsert_json_cache(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    key: str,
    data_column: str,
    data: dict[str, Any],
    fetched_column: str = "fetched_at",
) -> None:
    columns = [key_column, data_column, fetched_column]
    bind_markers = ", ".join("?" for _ in columns)
    updates = ", ".join(f"{column}=excluded.{column}" for column in columns[1:])
    sql = (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({bind_markers}) "
        f"ON CONFLICT({key_column}) DO UPDATE SET {updates}"
    )
    conn.execute(sql, (key, json_dumps(data), now_iso()))
    conn.commit()


def load_json_cache(
    conn: sqlite3.Connection,
    table: str,
    key_column: str,
    key: str,
    data_column: str = "data",
) -> dict[str, Any] | None:
    row = conn.execute(
        f"SELECT {data_column} FROM {table} WHERE {key_column} = ?",
        (key,),
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[data_column])
    except json.JSONDecodeError:
        return None
