import React, { useMemo } from "react";

function bearingToDirection(deg) {
  if (deg == null || Number.isNaN(deg)) return "unknown";
  const dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  const idx = Math.round(((deg % 360) / 45)) % 8;
  return dirs[idx];
}

// Generate a fun, slightly anime-style comment from the pilot
export default function PilotComment({ snapshot }) {
  const text = useMemo(() => {
    if (!snapshot) return "Systems idle. Waiting for Airflow to bring in fresh weather data.";

    const t = snapshot.temperature_c;
    const heat = snapshot.heat_level;
    const wind = snapshot.wind_speed_kmh;
    const dir = bearingToDirection(snapshot.wind_direction_deg);
    const state = snapshot.weather_state;
    const tod = snapshot.time_of_day;

    // Some base phrases
    const windPhrase =
      wind > 60
        ? `Wind ${dir} at ${wind.toFixed(0)} km/h... my hair gel did not sign up for this.`
        : wind > 35
        ? `Strong ${dir} wind at ${wind.toFixed(0)} km/h, holding the stick tight.`
        : wind > 15
        ? `Nice ${dir} breeze, feels like a free speed boost.`
        : `Barely any ${dir} wind, it's almost too quiet.`;

    const tempPhrase =
      heat === "freezing"
        ? `It's so cold (${t.toFixed(1)}°C) my coffee is trying to become an ice sculpture.`
        : heat === "hot" || heat === "very_hot"
        ? `Cockpit is at ${t.toFixed(1)}°C, feels like I'm slow‑cooking in my flight suit.`
        : heat === "extreme"
        ? `${t.toFixed(
            1
          )}°C?! If it gets any hotter, I'm flying in just my dreams instead of this cockpit.`
        : `Temperature at ${t.toFixed(1)}°C, pretty flyable.`;

    const weatherPhrase =
      state === "storm"
        ? "Lightning all around… who ordered the dramatic anime boss battle weather?"
        : state === "rain"
        ? "Rain drumming on the canopy, visibility holding… wipers wish they had overtime pay."
        : state === "snow"
        ? "Snowflakes on the windshield—beautiful, but my landing gear looks nervous."
        : state === "fog"
        ? "Foggy skies… instruments are my only friends right now."
        : state === "cloudy"
        ? "Cloud carpets below, perfect for daydreaming and dramatic openings."
        : "Skies are clear—10/10 for sightseeing.";

    const todPhrase =
      tod === "deep_night" || tod === "late_night"
        ? "Too late to be awake, too early to be sane—perfect time for night flying."
        : tod === "pre_dawn" || tod === "dawn"
        ? "Sun is stretching, so am I. Dawn flights are peak anime opening energy."
        : tod === "evening"
        ? "Golden hour glow—if I crash now at least the lighting will be perfect."
        : tod === "late_afternoon"
        ? "Late afternoon thermals giving us a little roller‑coaster treatment."
        : "Just another chapter in today's sky adventure.";

    return `${windPhrase} ${tempPhrase} ${weatherPhrase} ${todPhrase}`;
  }, [snapshot]);

  const direction =
    snapshot && snapshot.wind_direction_deg != null
      ? `${bearingToDirection(snapshot.wind_direction_deg)} (${snapshot.wind_direction_deg.toFixed(
          0
        )}°)`
      : "N/A";

  return (
    <div className="pilot-comment">
      <div className="pilot-comment-label">Pilot log</div>
      <div className="pilot-comment-text">{text}</div>
      <div className="pilot-comment-meta">
        <span>Wind from: {direction}</span>
      </div>
    </div>
  );
}


