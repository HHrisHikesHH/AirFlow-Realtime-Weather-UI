from __future__ import annotations

"""
FastAPI backend to serve weather data prepared by Airflow for the animated UI.

Exposes:
- GET /cities
- GET /weather/latest?city_id=...

The API reads from Postgres tables populated by the `weather_cities_ui_etl` DAG:
    - cities
    - city_weather_latest

Database connection configuration (env vars with sensible defaults for local use):
- DB_HOST (default: "localhost")
- DB_PORT (default: "5432")
- DB_USER (default: "postgres")
- DB_PASSWORD (default: "postgres")
- DB_NAME (default: "postgres")

Run locally (from project root, after installing requirements):
    uvicorn backend.main:app --reload --port 8000
"""

import os
from typing import List, Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "postgres")


def _get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME,
    )


class City(BaseModel):
    id: int
    name: str


class WeatherSnapshot(BaseModel):
    city_id: int
    city_name: str
    timezone: str
    timestamp_local: str
    temperature_c: float
    heat_level: str
    wind_speed_kmh: float
    wind_direction_deg: float
    weather_code: int
    weather_state: str
    is_day: bool
    time_of_day: str
    plane_angle_deg: float
    plane_altitude: float


app = FastAPI(title="Weather Plane UI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/cities", response_model=List[City])
def list_cities() -> List[City]:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM cities ORDER BY id;")
            rows = cur.fetchall()
    return [City(id=row[0], name=row[1]) for row in rows]


@app.get("/weather/latest", response_model=WeatherSnapshot)
def get_latest_weather(city_id: int = Query(..., description="City id from /cities")) -> WeatherSnapshot:
    sql = """
    SELECT
        c.id,
        c.name,
        c.timezone,
        w.timestamp_local,
        w.temperature_c,
        w.heat_level,
        w.wind_speed_kmh,
        w.wind_direction_deg,
        w.weather_code,
        w.weather_state,
        w.is_day,
        w.time_of_day,
        w.plane_angle_deg,
        w.plane_altitude
    FROM city_weather_latest w
    JOIN cities c ON c.id = w.city_id
    WHERE c.id = %s;
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (city_id,))
            row: Optional[tuple] = cur.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Weather snapshot not found for this city.")

    return WeatherSnapshot(
        city_id=row[0],
        city_name=row[1],
        timezone=row[2],
        timestamp_local=row[3].isoformat(),
        temperature_c=row[4],
        heat_level=row[5],
        wind_speed_kmh=row[6],
        wind_direction_deg=row[7],
        weather_code=row[8],
        weather_state=row[9],
        is_day=row[10],
        time_of_day=row[11],
        plane_angle_deg=row[12],
        plane_altitude=row[13],
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


