import os
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_FILE = Path(
    os.getenv(
        "DATA_FILE",
        BASE_DIR / "data" / "legacy_dirty" / "sales_dirty.csv",
    )
).resolve()

app = FastAPI(
    title="Datathon API",
    version="0.1.0",
)


def require_data_file() -> Path:
    if not DATA_FILE.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Data file is unavailable: {DATA_FILE}",
        )

    return DATA_FILE


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "data_file_available": DATA_FILE.is_file(),
    }


@app.get("/data-profile")
def data_profile() -> dict:
    data_file = require_data_file()

    with duckdb.connect(":memory:") as connection:
        cursor = connection.execute(
            """
            SELECT *
            FROM read_csv_auto(
                ?,
                header = TRUE,
                all_varchar = TRUE
            )
            LIMIT 0
            """,
            [str(data_file)],
        )

        columns = [column[0] for column in cursor.description]

        row_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM read_csv_auto(
                ?,
                header = TRUE,
                all_varchar = TRUE
            )
            """,
            [str(data_file)],
        ).fetchone()[0]

    return {
        "file": data_file.name,
        "row_count": row_count,
        "columns": columns,
    }


@app.get("/sample")
def sample(
    limit: int = Query(default=5, ge=1, le=20),
) -> dict:
    data_file = require_data_file()

    with duckdb.connect(":memory:") as connection:
        cursor = connection.execute(
            """
            SELECT *
            FROM read_csv_auto(
                ?,
                header = TRUE,
                all_varchar = TRUE
            )
            LIMIT ?
            """,
            [str(data_file), limit],
        )

        columns = [column[0] for column in cursor.description]
        records = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

    return {
        "count": len(records),
        "records": records,
    }