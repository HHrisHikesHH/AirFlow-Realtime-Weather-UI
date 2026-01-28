import React, { useMemo } from "react";
import PilotSprite from "./PilotSprite.jsx";
import WeatherEffects from "./WeatherEffects.jsx";

const timeOfDayClassMap = {
  deep_night: "bg-deep-night",
  pre_dawn: "bg-pre-dawn",
  dawn: "bg-dawn",
  morning: "bg-morning",
  afternoon: "bg-afternoon",
  late_afternoon: "bg-late-afternoon",
  evening: "bg-evening",
  late_night: "bg-late-night",
};

export default function PlaneScene({ snapshot }) {
  const backgroundClass = useMemo(() => {
    if (!snapshot) return "bg-deep-night";
    return timeOfDayClassMap[snapshot.time_of_day] || "bg-afternoon";
  }, [snapshot]);

  const rotation = snapshot ? snapshot.plane_angle_deg : 0;
  const altitude = snapshot ? snapshot.plane_altitude : 0;

  const translateY = useMemo(() => {
    // Map altitude [0,1] to CSS translateY from +40px (low) to -80px (high)
    const min = -80;
    const max = 40;
    const y = max - (max - min) * altitude;
    return y;
  }, [altitude]);

  return (
    <div className={`plane-scene ${backgroundClass}`}>
      <div className="sky-overlay" />
      <WeatherEffects snapshot={snapshot} />

      <div
        className="plane"
        style={{
          transform: `translateY(${translateY}px) rotate(${rotation}deg)`,
        }}
      >
        <PilotSprite snapshot={snapshot} />
      </div>

      <div className="ground" />
    </div>
  );
}

