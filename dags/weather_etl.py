"""
Simple Weather ETL DAG

This DAG calls the Open-Meteo API to retrieve an hourly temperature forecast
for Berlin, performs a small transformation, and loads the data into Postgres.

Pipeline steps:
- Extract: Call `https://api.open-meteo.com/v1/forecast?...` and get the hourly
  timestamps and temperatures.
- Transform: Keep only rows for the logical run date and add a boolean flag
  `is_freezing` (True when temperature <= 0°C).
- Load: Upsert the rows into a Postgres table `weather_hourly` using a
  connection called `postgres_default`.

To use this DAG:
- Ensure you have a Postgres connection in Airflow named `postgres_default`
  pointing to your target database.
- The DAG will create the `weather_hourly` table if it does not exist.
"""

from __future__ import annotations

from typing import List, Dict

import json

import pendulum
import requests
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task


API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=52.52&longitude=13.41&hourly=temperature_2m"
)


@dag(
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule="@daily",
    catchup=False,
    default_args={"owner": "Astro", "retries": 1},
    tags=["example", "weather", "etl"],
    doc_md=__doc__,
)
def weather_etl():
    @task
    def extract_weather() -> dict:
        """
        Extract step: call the Open-Meteo API and return the JSON payload.
        """
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        return response.json()

    @task
    def transform_weather(payload: dict, logical_date: str) -> List[Dict]:
        """
        Transform step: keep only records for the logical_date (YYYY-MM-DD)
        and add a simple `is_freezing` flag based on temperature.
        """
        hourly = payload.get("hourly", {})
        times: List[str] = hourly.get("time", [])
        temps: List[float] = hourly.get("temperature_2m", [])

        rows: List[Dict] = []
        for ts, temp in zip(times, temps):
            # ts is an ISO-like string, e.g. "2026-01-28T00:00"
            if not ts.startswith(logical_date):
                continue

            rows.append(
                {
                    "timestamp": ts,
                    "temperature_c": float(temp),
                    "is_freezing": temp <= 0,
                }
            )

        return rows

    @task
    def load_weather(rows: List[Dict]) -> None:
        """
        Load step: create table if not exists and insert transformed rows.

        Table schema:
            weather_hourly (
                timestamp      TIMESTAMP PRIMARY KEY,
                temperature_c  DOUBLE PRECISION NOT NULL,
                is_freezing    BOOLEAN NOT NULL,
                raw_payload    JSONB
            )
        """
        if not rows:
            # Nothing to load for this logical date
            return

        hook = PostgresHook(postgres_conn_id="postgres_default")

        # Create table if it does not exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS weather_hourly (
            timestamp      TIMESTAMP PRIMARY KEY,
            temperature_c  DOUBLE PRECISION NOT NULL,
            is_freezing    BOOLEAN NOT NULL,
            raw_payload    JSONB
        );
        """
        hook.run(create_table_sql)

        # Prepare rows as tuples for insert
        records = [
            (
                r["timestamp"],
                r["temperature_c"],
                r["is_freezing"],
                json.dumps(r),
            )
            for r in rows
        ]

        # Simple upsert on timestamp primary key
        insert_sql = """
        INSERT INTO weather_hourly (timestamp, temperature_c, is_freezing, raw_payload)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (timestamp) DO UPDATE
        SET
            temperature_c = EXCLUDED.temperature_c,
            is_freezing   = EXCLUDED.is_freezing,
            raw_payload   = EXCLUDED.raw_payload;
        """

        # Run the upsert once per record to avoid DB-API formatting issues
        for record in records:
            hook.run(insert_sql, parameters=record)

    extract_result = extract_weather()

    # Use the DAG's logical_date so the DAG is deterministic for backfills
    logical_date_str = "{{ ds }}"  # e.g. "2026-01-28"

    transformed_rows = transform_weather(
        payload=extract_result,
        logical_date=logical_date_str,
    )

    load_weather(transformed_rows)


weather_etl()


