import React, { useMemo } from "react";

// Pilot sprite that changes outfit and mood based on weather data
export default function PilotSprite({ snapshot }) {
  const heatLevel = snapshot?.heat_level || "mild";
  const weatherState = snapshot?.weather_state || "clear";
  const windSpeed = snapshot?.wind_speed_kmh ?? 0;

  // Outfit buckets from heat level
  const outfit = useMemo(() => {
    if (["freezing", "cold"].includes(heatLevel)) return "cold";
    if (["cool", "mild"].includes(heatLevel)) return "normal";
    if (["warm", "hot", "very_hot"].includes(heatLevel)) return "hot";
    return "extreme"; // extreme heat, comedic outfit
  }, [heatLevel]);

  // Comfort / emotion from wind, storms, extremes
  const mood = useMemo(() => {
    if (weatherState === "storm") return "terrified";
    if (["rain", "snow", "fog"].includes(weatherState) && windSpeed > 45) {
      return "terrified";
    }
    if (heatLevel === "extreme" || heatLevel === "freezing") return "uncomfortable";
    if (windSpeed > 40) return "worried";
    if (windSpeed > 25) return "focused";
    return "happy";
  }, [weatherState, windSpeed, heatLevel]);

  const windTier =
    windSpeed > 45 ? "high" : windSpeed > 25 ? "med" : windSpeed > 10 ? "low" : "calm";

  const classes = [
    "pilot",
    `pilot--outfit-${outfit}`,
    `pilot--mood-${mood}`,
    `pilot--weather-${weatherState}`,
    `pilot--wind-${windTier}`,
  ].join(" ");

  return (
    <div className="cockpit">
      <div className={classes}>
        <div className="pilot-body">
          <div className="pilot-harness" />
          <div className="pilot-gear-belt" />
        </div>
        <div className="pilot-head">
          <div className="pilot-face" />
          <div className="pilot-eyes" />
          <div className="pilot-mouth" />
          <div className="pilot-helmet" />
          <div className="pilot-goggles" />
          <div className="pilot-scarf" />
          <div className="pilot-sweat" />
        </div>
      </div>
    </div>
  );
}