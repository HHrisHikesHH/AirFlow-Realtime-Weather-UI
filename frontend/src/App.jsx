import React, { useEffect, useState } from "react";
import CitySelector from "./components/CitySelector.jsx";
import PlaneScene from "./components/PlaneScene.jsx";
import PilotComment from "./components/PilotComment.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [cities, setCities] = useState([]);
  const [selectedCityId, setSelectedCityId] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);

  // Load cities on mount
  useEffect(() => {
    async function loadCities() {
      try {
        const res = await fetch(`${API_BASE}/cities`);
        const data = await res.json();
        setCities(data);
        if (data.length > 0) {
          setSelectedCityId(data[0].id);
        }
      } catch (e) {
        console.error(e);
        setError("Unable to load cities from API.");
      }
    }
    loadCities();
  }, []);

  // Poll latest snapshot for selected city
  useEffect(() => {
    if (!selectedCityId) return;

    let cancelled = false;

    async function fetchSnapshot() {
      try {
        const res = await fetch(
          `${API_BASE}/weather/latest?city_id=${selectedCityId}`
        );
        if (!res.ok) {
          throw new Error(`Status ${res.status}`);
        }
        const data = await res.json();
        if (!cancelled) {
          setSnapshot(data);
          setError(null);
        }
      } catch (e) {
        console.error(e);
        if (!cancelled) {
          setError("Unable to load weather snapshot.");
        }
      }
    }

    fetchSnapshot();
    const id = setInterval(fetchSnapshot, 5000); // poll every 5 seconds

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [selectedCityId]);

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>AirFlow Weather Plane</h1>
        <p className="subtitle">
          Animated airplane and sky driven by Airflow + FastAPI + Open-Meteo
        </p>
      </header>

      <main className="app-main">
        <section className="controls">
          <CitySelector
            cities={cities}
            selectedCityId={selectedCityId}
            onChange={setSelectedCityId}
          />
          {snapshot && (
            <>
              <div className="info-panel">
                <div>
                  <strong>City:</strong> {snapshot.city_name}
                </div>
                <div>
                  <strong>Local time:</strong> {snapshot.timestamp_local}
                </div>
                <div>
                  <strong>Temperature:</strong>{" "}
                  {snapshot.temperature_c.toFixed(1)}°C ({snapshot.heat_level})
                </div>
                <div>
                  <strong>Wind:</strong>{" "}
                  {snapshot.wind_speed_kmh.toFixed(1)} km/h at{" "}
                  {snapshot.wind_direction_deg.toFixed(0)}°
                </div>
                <div>
                  <strong>Time of day:</strong> {snapshot.time_of_day}
                </div>
                <div>
                  <strong>Weather:</strong> {snapshot.weather_state}
                </div>
              </div>
              <PilotComment snapshot={snapshot} />
            </>
          )}
          {error && <div className="error">{error}</div>}
        </section>

        <section className="scene-container">
          <PlaneScene snapshot={snapshot} />
        </section>
      </main>
    </div>
  );
}


