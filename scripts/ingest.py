from pathlib import Path
import hashlib

import boto3
import duckdb


# ============================================================
# Configuration
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

BUCKET = "datathon-migration-dev-045740834598-us-east-1-an"

S3_KEY = "raw/batch_001/sales_dirty.csv"

AWS_REGION = "us-east-1"

LOCAL_CSV = BASE_DIR / "data" / "raw" / "sales_dirty.csv"

DATABASE_PATH = BASE_DIR / "db" / "datathon.duckdb"


# ============================================================
# Download the source file
# ============================================================

def download_from_s3():

    LOCAL_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
    )

    print(f"Downloading s3://{BUCKET}/{S3_KEY}")

    s3.download_file(
        BUCKET,
        S3_KEY,
        str(LOCAL_CSV),
    )

    print(f"Saved to: {LOCAL_CSV}")


# ============================================================
# Generate a file checksum
# ============================================================

def calculate_sha256(file_path):

    digest = hashlib.sha256()

    with open(file_path, "rb") as file:

        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


# ============================================================
# Load CSV into DuckDB
# ============================================================

def load_raw_data():

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(
        str(DATABASE_PATH)
    )

    try:

        connection.execute("""
            CREATE SCHEMA IF NOT EXISTS raw;
        """)

        # Recreate only the development RAW table.
        # The source CSV stored in S3 is never modified.

        connection.execute("""
            CREATE OR REPLACE TABLE raw.sales_raw (
                raw_col_1 VARCHAR,
                raw_col_2 VARCHAR,
                raw_col_3 VARCHAR,
                raw_col_4 VARCHAR,
                raw_col_5 VARCHAR,
                raw_col_6 VARCHAR,
                raw_col_7 VARCHAR,
                source_row_id VARCHAR,
                ingest_row_id VARCHAR
            );
        """)

        connection.execute(
            """
            COPY raw.sales_raw
            FROM ?
            (
                FORMAT CSV,
                HEADER TRUE,
                DELIMITER ',',
                QUOTE '"'
            );
            """,
            [str(LOCAL_CSV)],
        )

        row_count = connection.execute("""
            SELECT COUNT(*)
            FROM raw.sales_raw;
        """).fetchone()[0]

        print(f"RAW rows loaded: {row_count}")

        print("\nFirst five records:")

        results = connection.execute("""
            SELECT *
            FROM raw.sales_raw
            LIMIT 5;
        """).fetchall()

        for row in results:
            print(row)

    finally:

        connection.close()


# ============================================================
# Main
# ============================================================

def main():

    download_from_s3()

    checksum = calculate_sha256(
        LOCAL_CSV
    )

    print(f"Source SHA256: {checksum}")

    load_raw_data()

    print("S3 → DuckDB ingestion completed.")


if __name__ == "__main__":
    main()