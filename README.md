## AirFlow + Anime Weather Cockpit

An educational mini-project that combines **Apache Airflow (via Astro)**, **FastAPI**, **React**, and **Postgres** to build a fun, anime‑style weather cockpit:

- Airflow DAGs pull data from the **Open‑Meteo API** and store transformed weather snapshots in Postgres.
- A FastAPI backend exposes those snapshots as a simple JSON API.
- A React + Vite frontend visualizes a **pilot in a cockpit** whose outfit, mood, and the sky animation react to live weather (temperature, wind, conditions, time of day) across multiple cities.

Use this project to revise:
- How to build ETL pipelines with **Astro + Airflow**.
- How to connect Airflow to **Postgres**.
- How to serve ETL results via **FastAPI** and consume them in a **React** app.

---

## High‑Level Architecture

- **Airflow / Astro**
  - Runs in Docker using the Astro Runtime image.
  - DAGs live in the `dags/` folder.
  - Writes processed weather data into a Postgres database.

- **Postgres**
  - Used by Airflow as its metadata database (Astro default).
  - Also stores **project tables**:
    - `weather_hourly` – simple ETL from the weather API.
    - `cities` – static city metadata (name, coordinates, timezone).
    - `city_weather_latest` – one latest weather snapshot per city for the UI.

- **FastAPI backend**
  - `backend/main.py`.
  - Reads from `cities` and `city_weather_latest`.
  - Exposes:
    - `GET /cities`
    - `GET /weather/latest?city_id=...`

- **React frontend**
  - Located in `frontend/` (Vite + React).
  - Polls FastAPI every few seconds.
  - Renders:
    - A dropdown of cities.
    - Anime‑like cockpit with a pilot sprite.
    - Weather‑driven sky (day/night/dawn/evening), clouds, rain, snow, storms, wind streaks.
    - A “Pilot log” text box with funny comments based on conditions.

---

## Airflow DAGs (Astro)

### `example_astronauts`

- Original Astro example DAG.
- Demonstrates:
  - Airflow **TaskFlow API**.
  - Dynamic task mapping.
  - External API call (Open Notify “astronauts in space” API).

Use this DAG when you want to quickly recall:
- How to define a simple DAG in Astro.
- How XCom / task returns work.

### `weather_etl`

- Simple ETL that calls the **Open‑Meteo** forecast API for Berlin:
  - Endpoint similar to  
    `https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m`
    (see [Open‑Meteo docs](https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m)).
- Steps:
  - **Extract**: call the API and fetch hourly temperatures.
  - **Transform**:
    - Filter to the DAG’s logical date.
    - Compute a simple `is_freezing` flag (\(\le 0^\circ C\)).
  - **Load**: upsert into Postgres table `weather_hourly` using `PostgresHook`.

Key concepts to revise:
- How to use `PostgresHook` from `apache-airflow-providers-postgres`.
- How to create tables and run **upserts** from a task.

### `weather_cities_ui_etl`

- Main DAG powering the anime cockpit UI.
- Runs **every 1 minute**.
- Uses a fixed list of **~15 cities** around the world (Pune, Sydney, Tokyo, McMurdo Station, Nairobi, New York, London, São Paulo, Cairo, Moscow, Dubai, Reykjavik, Chicago, Singapore, Buenos Aires, etc.).

**Extract**
- For each city:
  - Calls Open‑Meteo with:
    - `hourly=temperature_2m,wind_speed_10m,wind_direction_10m,weather_code,is_day`
    - `timezone=<city timezone>` so times are local.

**Transform**
- For each city:
  - Picks the forecast time step closest to “now” (in the city’s local tz).
  - Derives UI‑friendly fields:
    - `heat_level`: `freezing`, `cold`, `cool`, `mild`, `warm`, `hot`, `very_hot`, `extreme`.
    - `time_of_day`: 8 buckets (`deep_night`, `pre_dawn`, `dawn`, `morning`, `afternoon`, `late_afternoon`, `evening`, `late_night`).
    - `weather_state`: `clear`, `cloudy`, `rain`, `snow`, `storm`, `fog`, `windy`, `unknown`.
    - `plane_angle_deg`: from wind direction.
    - `plane_altitude`: normalized 0–1 from wind speed.

**Load**
- Ensures tables:
  - `cities (id, name, latitude, longitude, timezone)`.
  - `city_weather_latest` with weather + UI fields.
- Upserts:
  - All cities into `cities`.
  - One **latest snapshot per city** into `city_weather_latest`.

Use this DAG to revise:
- Working with multiple external API calls in a single DAG.
- Timezone handling with **Pendulum**.
- How to model ETL results specifically for a **frontend use case**.

---

## FastAPI Backend

File: `backend/main.py`

- Reads DB configuration from env vars (with local defaults):
  - `DB_HOST` (default `localhost`)
  - `DB_PORT` (default `5432`)
  - `DB_USER` (default `postgres`)
  - `DB_PASSWORD` (default `postgres`)
  - `DB_NAME` (default `postgres`)
- Uses `psycopg2` to connect to Postgres.
- Endpoints:
  - `GET /health`  
    Simple health check: `{"status": "ok"}`.
  - `GET /cities`  
    Returns list of cities (id + name).
  - `GET /weather/latest?city_id=...`  
    Returns:
    - City info (`city_name`, `timezone`, `timestamp_local`).
    - Numeric fields (`temperature_c`, `wind_speed_kmh`, `wind_direction_deg`, `weather_code`).
    - Derived UI fields (`heat_level`, `time_of_day`, `weather_state`, `plane_angle_deg`, `plane_altitude`, `is_day`).

This layer is intentionally thin: it’s a **read‑only API on top of Airflow’s ETL results**.

---

## React + Vite Frontend

Folder: `frontend/`

Key files:
- `package.json` – React + Vite scaffolding.
- `vite.config.mts` – Vite config.
- `index.html` – root HTML file.
- `src/main.jsx` – React entry point.
- `src/App.jsx` – main layout:
  - City selector (`CitySelector`).
  - Weather info panel.
  - **Animated cockpit** (`PlaneScene`).
  - **Pilot log** (`PilotComment`).
- `src/components/PlaneScene.jsx` – scene container, uses:
  - `PilotSprite` (pilot + cockpit visuals).
  - `WeatherEffects` (clouds, rain, snow, storms, wind).
- `src/components/PilotSprite.jsx`
  - Chooses:
    - Outfit from `heat_level` (cold gear vs hot vs extreme).
    - Mood from wind + temp + `weather_state` (happy, focused, worried, uncomfortable, terrified).
  - Animates:
    - Idle bob, shaking in strong winds/storms.
    - Scarf waving in cold, sweat drops in hot/extreme.
- `src/components/WeatherEffects.jsx`
  - Cloud layers, rain, snow, lightning flashes, wind streaks.
- `src/components/PilotComment.jsx`
  - Generates funny “pilot log” comments from a permutation of:
    - Wind speed + direction,
    - Temperature + `heat_level`,
    - `weather_state`,
    - `time_of_day`.
- `src/index.css`
  - Global layout styles.
  - Time‑of‑day gradients for the sky.
  - Anime‑style cockpit/pilot/wind/rain/snow animations.

The frontend reads `VITE_API_BASE` (default `http://localhost:8000`) to call FastAPI and **polls every 5 seconds** for the selected city.

---

## Installation & Local Development

### 1. Prerequisites

- Docker + Docker Compose (for Astro).
- Node.js (LTS) + npm (for the frontend).
- Python 3.10+ (if you want to run FastAPI outside the Astro image).
- Astronomer CLI (`astro`) installed.

---

### 2. Start Airflow (Astro)

From the project root:

```bash
astro dev start
```

This:
- Builds the Astro image.
- Starts:
  - Webserver (Airflow UI at `http://localhost:8080/`),
  - Scheduler,
  - Triggerer,
  - DAG processor,
  - Postgres metadata DB.

Then:
1. Open the Airflow UI.
2. Enable DAGs:
   - `weather_etl`
   - `weather_cities_ui_etl`
3. Let `weather_cities_ui_etl` run for a minute or two so `cities` and `city_weather_latest` are populated.

> **Note**: Ensure Airflow has a connection `postgres_default` pointing to the same Postgres DB used by FastAPI (for local Astro defaults, host is usually `postgres`, port `5432`, user/password `postgres`).

---

### 3. Install Python dependencies (FastAPI & providers)

From the project root:

```bash
pip install -r requirements.txt
```

This installs:
- `apache-airflow-providers-postgres`
- `fastapi`
- `uvicorn[standard]`
- `psycopg2-binary`

---

### 4. Run the FastAPI backend

From the project root:

```bash
export DB_HOST=localhost      # or 'postgres' if running inside Docker network
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD=postgres
export DB_NAME=postgres

uvicorn backend.main:app --reload --port 8000
```

Check it:
- `http://localhost:8000/health`
- `http://localhost:8000/cities`
- `http://localhost:8000/weather/latest?city_id=1`

---

### 5. Run the React frontend

From `frontend/`:

```bash
cd frontend
npm install

# Optionally set API base (defaults to http://localhost:8000)
export VITE_API_BASE=http://localhost:8000

npm run dev
```

Open the printed URL (typically `http://localhost:5173/`), pick a city, and watch:
- The sky/background change with **time of day**.
- Clouds/rain/snow/storms appear with changing weather.
- Wind speed affect:
  - Plane altitude,
  - Pilot sway and wind streaks.
- Temperature and conditions change the pilot’s outfit, mood, and “Pilot log” comments.

---

## Deploying / Pushing to a Repo

When pushing to a remote repo, include:
- `dags/` – all DAG definitions.
- `backend/` – FastAPI app.
- `frontend/` – React app.
- `requirements.txt` – Python deps (used both by Astro and FastAPI).
- `airflow_settings.yaml` – optional local connections/variables (do **not** commit secrets).
- `Dockerfile`, `packages.txt`, `plugins/` – Astro runtime config & plugins.

For a cloud deployment (Astronomer or other):
- Airflow DAGs + `requirements.txt` go into the Astro image.
- FastAPI + React can be deployed as separate services that point to the same Postgres (or a read replica).

---

## What to Revise Later

- **Airflow / Astro**
  - TaskFlow API (`@dag`, `@task`).
  - DAG scheduling and `logical_date`.
  - Hooks (`PostgresHook`) and DB upserts.
  - Using Astro Runtime and `astro dev start`.

- **Data modelling**
  - Designing tables for downstream consumption (`cities`, `city_weather_latest`).
  - Mapping raw weather to UX‑oriented fields (`heat_level`, `time_of_day`, `weather_state`).

- **FastAPI**
  - Pydantic models for response schemas.
  - Basic routing and DB access patterns.

- **React / Vite**
  - Polling APIs and mapping backend fields into visuals.
  - Structuring components for complex UI effects (pilot, weather layers, comments).

This README should be enough to **rebuild the project from scratch** and to refresh your memory on how all the moving parts—Airflow, Astro, Postgres, FastAPI, and React—fit together. 
