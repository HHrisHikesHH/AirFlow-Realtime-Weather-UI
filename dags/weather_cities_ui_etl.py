"""
Weather UI ETL DAG for Multiple Cities

This DAG keeps a "latest snapshot" of weather for multiple cities around
the world, suitable for driving an animated UI (e.g. a plane whose rotation
and altitude depend on wind, with backgrounds for day/night/dawn, etc.).

It uses the Open-Meteo forecast API:
https://api.open-meteo.com/v1/forecast

Pipeline (runs every minute):
- Define a fixed list of cities with latitude, longitude, and timezone.
- Extract: For each city, call Open-Meteo hourly forecast including:
  temperature_2m, wind_speed_10m, wind_direction_10m, weather_code, is_day.
- Transform: For each city, pick the time step closest to "now" in the
  city's local time and derive:
  - heat_level (freezing, cold, cool, mild, warm, hot, very_hot, extreme)
  - plane_angle_deg (from wind_direction_10m)
  - plane_altitude (0-1 scale from wind_speed_10m)
  - weather_state (clear, cloudy, rain, snow, storm, fog, windy, unknown)
  - time_of_day (8 buckets based on local hour:
      deep_night, pre_dawn, dawn, morning, afternoon,
      late_afternoon, evening, late_night)
- Load: Upsert one row per city into Postgres table `city_weather_latest`,
  and maintain a small `cities` lookup table for convenience.

This DAG expects an Airflow connection with conn_id `postgres_default`
pointing to your Postgres instance.
"""

from __future__ import annotations

from typing import Dict, List

import json
from dataclasses import dataclass

import pendulum
import requests
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import dag, task


@dataclass
class City:
    id: int
    name: str
    latitude: float
    longitude: float
    timezone: str


# Diverse cities for variety, including extreme heat/cold and windy places
CITIES: List[City] = [
    City(id=1, name="Pune", latitude=18.52, longitude=73.86, timezone="Asia/Kolkata"),
    City(id=2, name="Sydney", latitude=-33.87, longitude=151.21, timezone="Australia/Sydney"),
    City(id=3, name="Tokyo", latitude=35.68, longitude=139.69, timezone="Asia/Tokyo"),
    City(id=4, name="McMurdo Station", latitude=-77.85, longitude=166.67, timezone="Antarctica/McMurdo"),  # Antarctica
    City(id=5, name="Nairobi", latitude=-1.29, longitude=36.82, timezone="Africa/Nairobi"),
    City(id=6, name="New York", latitude=40.71, longitude=-74.01, timezone="America/New_York"),
    City(id=7, name="London", latitude=51.51, longitude=-0.13, timezone="Europe/London"),
    City(id=8, name="São Paulo", latitude=-23.55, longitude=-46.63, timezone="America/Sao_Paulo"),
    City(id=9, name="Cairo", latitude=30.04, longitude=31.24, timezone="Africa/Cairo"),  # hot & dry
    City(id=10, name="Moscow", latitude=55.76, longitude=37.62, timezone="Europe/Moscow"),  # cold winters
    City(id=11, name="Dubai", latitude=25.20, longitude=55.27, timezone="Asia/Dubai"),  # extreme heat
    City(id=12, name="Reykjavik", latitude=64.13, longitude=-21.90, timezone="Atlantic/Reykjavik"),  # very cold, windy
    City(id=13, name="Chicago", latitude=41.88, longitude=-87.63, timezone="America/Chicago"),  # windy city
    City(id=14, name="Singapore", latitude=1.35, longitude=103.82, timezone="Asia/Singapore"),  # hot & humid
    City(id=15, name="Buenos Aires", latitude=-34.60, longitude=-58.38, timezone="America/Argentina/Buenos_Aires"),
]


def _classify_heat(temperature_c: float) -> str:
    if temperature_c <= -5:
        return "freezing"
    if temperature_c <= 5:
        return "cold"
    if temperature_c <= 12:
        return "cool"
    if temperature_c <= 20:
        return "mild"
    if temperature_c <= 28:
        return "warm"
    if temperature_c <= 35:
        return "hot"
    if temperature_c <= 42:
        return "very_hot"
    return "extreme"


def _classify_time_of_day(local_hour: int) -> str:
    """
    8 buckets that can be mapped to distinct backgrounds on the UI.
    """
    if 0 <= local_hour < 3:
        return "deep_night"
    if 3 <= local_hour < 5:
        return "pre_dawn"
    if 5 <= local_hour < 7:
        return "dawn"
    if 7 <= local_hour < 11:
        return "morning"
    if 11 <= local_hour < 15:
        return "afternoon"
    if 15 <= local_hour < 18:
        return "late_afternoon"
    if 18 <= local_hour < 21:
        return "evening"
    return "late_night"  # 21-23


def _classify_weather_state(weather_code: int) -> str:
    # Simplified mapping based on WMO codes used by Open-Meteo
    if weather_code in (0,):
        return "clear"
    if weather_code in (1, 2, 3):
        return "cloudy"
    if weather_code in (45, 48):
        return "fog"
    if weather_code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if weather_code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if weather_code in (95, 96, 99):
        return "storm"
    return "windy" if weather_code == 73 else "unknown"


def _normalize_plane_altitude(wind_speed_kmh: float) -> float:
    """
    Map wind speed (km/h) to a 0-1 range for plane altitude in UI.
    Clip extremes to keep visuals stable.
    """
    if wind_speed_kmh <= 0:
        return 0.0
    # Assume 0-100 km/h as typical range
    normalized = min(wind_speed_kmh / 100.0, 1.0)
    return round(normalized, 3)


@dag(
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule="* * * * *",  # every minute
    catchup=False,
    default_args={"owner": "Astro", "retries": 1},
    tags=["weather", "ui", "example"],
    doc_md=__doc__,
)
def weather_cities_ui_etl():
    @task
    def extract_weather_for_cities() -> List[Dict]:
        """
        Call Open-Meteo for each city and collect a small hourly forecast slice.
        """
        results: List[Dict] = []
        now_utc = pendulum.now("UTC")

        for city in CITIES:
            params = {
                "latitude": city.latitude,
                "longitude": city.longitude,
                "hourly": "temperature_2m,wind_speed_10m,wind_direction_10m,weather_code,is_day",
                "timezone": city.timezone,
            }
            response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            results.append(
                {
                    "city": {
                        "id": city.id,
                        "name": city.name,
                        "timezone": city.timezone,
                        "latitude": city.latitude,
                        "longitude": city.longitude,
                    },
                    "payload": data,
                    "fetched_at_utc": now_utc.isoformat(),
                }
            )

        return results

    @task
    def transform_for_ui(extracted: List[Dict]) -> List[Dict]:
        """
        For each city, pick the forecast time step closest to "now" in local time
        and derive UI-friendly fields.
        """
        transformed: List[Dict] = []

        for item in extracted:
            city_info = item["city"]
            payload = item["payload"]
            tz = city_info["timezone"]

            hourly = payload.get("hourly", {})
            times: List[str] = hourly.get("time", [])
            temps: List[float] = hourly.get("temperature_2m", [])
            winds: List[float] = hourly.get("wind_speed_10m", [])
            dirs: List[float] = hourly.get("wind_direction_10m", [])
            codes: List[int] = hourly.get("weather_code", [])
            is_day_list: List[int] = hourly.get("is_day", [])

            if not times:
                continue

            # Determine the index of the time step closest to "now" in local time
            now_local = pendulum.now(tz)
            closest_idx = 0
            smallest_diff = None
            for i, ts in enumerate(times):
                # ts is already local time due to timezone param, e.g. "2026-01-28T18:00"
                ts_dt = pendulum.parse(ts, tz=tz)
                diff = abs((ts_dt - now_local).total_seconds())
                if smallest_diff is None or diff < smallest_diff:
                    smallest_diff = diff
                    closest_idx = i

            ts = times[closest_idx]
            temp = float(temps[closest_idx])
            wind_speed = float(winds[closest_idx])
            wind_dir = float(dirs[closest_idx])
            code = int(codes[closest_idx]) if codes else 0
            is_day = bool(is_day_list[closest_idx]) if is_day_list else True

            local_hour = int(ts[11:13])  # HH from "YYYY-MM-DDTHH:MM"

            heat_level = _classify_heat(temp)
            time_of_day = _classify_time_of_day(local_hour)
            weather_state = _classify_weather_state(code)
            plane_angle_deg = wind_dir
            plane_altitude = _normalize_plane_altitude(wind_speed)

            transformed.append(
                {
                    "city_id": city_info["id"],
                    "city_name": city_info["name"],
                    "timezone": tz,
                    "timestamp_local": ts,
                    "temperature_c": temp,
                    "wind_speed_kmh": wind_speed,
                    "wind_direction_deg": wind_dir,
                    "weather_code": code,
                    "is_day": is_day,
                    "heat_level": heat_level,
                    "time_of_day": time_of_day,
                    "weather_state": weather_state,
                    "plane_angle_deg": plane_angle_deg,
                    "plane_altitude": plane_altitude,
                    "raw_payload": payload,
                }
            )

        return transformed

    @task
    def load_city_weather_latest(rows: List[Dict]) -> None:
        """
        Create tables if needed and upsert the latest weather snapshot for each city.
        """
        if not rows:
            return

        hook = PostgresHook(postgres_conn_id="postgres_default")

        # Small lookup table for cities
        create_cities_table_sql = """
        CREATE TABLE IF NOT EXISTS cities (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            latitude    DOUBLE PRECISION NOT NULL,
            longitude   DOUBLE PRECISION NOT NULL,
            timezone    TEXT NOT NULL
        );
        """

        # Latest snapshot per city for UI consumption
        create_weather_table_sql = """
        CREATE TABLE IF NOT EXISTS city_weather_latest (
            city_id             INTEGER PRIMARY KEY REFERENCES cities(id),
            timestamp_local     TIMESTAMP NOT NULL,
            temperature_c       DOUBLE PRECISION NOT NULL,
            wind_speed_kmh      DOUBLE PRECISION NOT NULL,
            wind_direction_deg  DOUBLE PRECISION NOT NULL,
            weather_code        INTEGER NOT NULL,
            is_day              BOOLEAN NOT NULL,
            heat_level          TEXT NOT NULL,
            time_of_day         TEXT NOT NULL,
            weather_state       TEXT NOT NULL,
            plane_angle_deg     DOUBLE PRECISION NOT NULL,
            plane_altitude      DOUBLE PRECISION NOT NULL,
            raw_payload         JSONB
        );
        """

        hook.run(create_cities_table_sql)
        hook.run(create_weather_table_sql)

        # Upsert cities (so FastAPI/React can query them)
        upsert_city_sql = """
        INSERT INTO cities (id, name, latitude, longitude, timezone)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
        SET
            name = EXCLUDED.name,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            timezone = EXCLUDED.timezone;
        """

        for city in CITIES:
            hook.run(
                upsert_city_sql,
                parameters=(
                    city.id,
                    city.name,
                    city.latitude,
                    city.longitude,
                    city.timezone,
                ),
            )

        # Upsert latest weather per city
        upsert_weather_sql = """
        INSERT INTO city_weather_latest (
            city_id,
            timestamp_local,
            temperature_c,
            wind_speed_kmh,
            wind_direction_deg,
            weather_code,
            is_day,
            heat_level,
            time_of_day,
            weather_state,
            plane_angle_deg,
            plane_altitude,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (city_id) DO UPDATE
        SET
            timestamp_local    = EXCLUDED.timestamp_local,
            temperature_c      = EXCLUDED.temperature_c,
            wind_speed_kmh     = EXCLUDED.wind_speed_kmh,
            wind_direction_deg = EXCLUDED.wind_direction_deg,
            weather_code       = EXCLUDED.weather_code,
            is_day             = EXCLUDED.is_day,
            heat_level         = EXCLUDED.heat_level,
            time_of_day        = EXCLUDED.time_of_day,
            weather_state      = EXCLUDED.weather_state,
            plane_angle_deg    = EXCLUDED.plane_angle_deg,
            plane_altitude     = EXCLUDED.plane_altitude,
            raw_payload        = EXCLUDED.raw_payload;
        """

        for row in rows:
            hook.run(
                upsert_weather_sql,
                parameters=(
                    row["city_id"],
                    row["timestamp_local"],
                    row["temperature_c"],
                    row["wind_speed_kmh"],
                    row["wind_direction_deg"],
                    row["weather_code"],
                    row["is_day"],
                    row["heat_level"],
                    row["time_of_day"],
                    row["weather_state"],
                    row["plane_angle_deg"],
                    row["plane_altitude"],
                    json.dumps(row["raw_payload"]),
                ),
            )

    extracted = extract_weather_for_cities()
    transformed = transform_for_ui(extracted)
    load_city_weather_latest(transformed)


weather_cities_ui_etl()


