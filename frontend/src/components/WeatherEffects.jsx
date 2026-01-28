import React from "react";

// Layered weather effects: clouds, rain, snow, storm flashes, wind streaks
export default function WeatherEffects({ snapshot }) {
  if (!snapshot) return null;

  const { weather_state: state, wind_speed_kmh: wind } = snapshot;

  const windTier =
    wind > 45 ? "high" : wind > 25 ? "med" : wind > 10 ? "low" : "calm";

  return (
    <>
      <div className={`cloud-layer cloud-layer--back cloud-layer--${state}`} />
      <div className={`cloud-layer cloud-layer--front cloud-layer--${state}`} />

      {(state === "rain" || state === "storm") && (
        <div className={`rain rain--${windTier}`} />
      )}

      {state === "snow" && <div className={`snow snow--${windTier}`} />}

      {state === "storm" && <div className="storm-flash" />}

      {windTier !== "calm" && (
        <div className={`wind-streaks wind-streaks--${windTier}`} />
      )}
    </>
  );
}