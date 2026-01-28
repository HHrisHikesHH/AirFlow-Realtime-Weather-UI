import React from "react";

export default function CitySelector({ cities, selectedCityId, onChange }) {
  return (
    <label className="city-selector">
      <span>Select city:</span>
      <select
        value={selectedCityId ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {cities.map((city) => (
          <option key={city.id} value={city.id}>
            {city.name}
          </option>
        ))}
      </select>
    </label>
  );
}


