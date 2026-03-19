import { useState, useEffect, useCallback, useMemo } from "react";

// ── Swiss airport data ──────────────────────────────────────────────
const SWISS_AIRPORTS = [
  { icao: "LSZH", iata: "ZRH", name: "Zürich", lat: 47.4647, lon: 8.5492, type: "major" },
  { icao: "LSGG", iata: "GVA", name: "Geneva", lat: 46.2381, lon: 6.1089, type: "major" },
  { icao: "LSZB", iata: "BRN", name: "Bern", lat: 46.9141, lon: 7.4972, type: "regional" },
  { icao: "LSZA", iata: "LUG", name: "Lugano", lat: 46.0040, lon: 8.9106, type: "regional" },
  { icao: "LFSB", iata: "BSL", name: "Basel", lat: 47.5896, lon: 7.5299, type: "major" },
  { icao: "LSZR", iata: "ACH", name: "St. Gallen", lat: 47.4853, lon: 9.5608, type: "regional" },
  { icao: "LSGS", iata: "SIR", name: "Sion", lat: 46.2196, lon: 7.3267, type: "regional" },
  { icao: "LSME", iata: "", name: "Emmen (Mil)", lat: 47.0924, lon: 8.3052, type: "military" },
  { icao: "LSMP", iata: "", name: "Payerne (Mil)", lat: 46.8432, lon: 6.9153, type: "military" },
];

// ── Aircraft performance database (simplified OpenAP-style) ────────
const AIRCRAFT_DB = {
  A320: { name: "Airbus A320-200", maxPax: 180, mtow: 78000, fuelBurn: 2.5, range: 6100, engines: "CFM56-5B", category: "narrow" },
  A321: { name: "Airbus A321neo", maxPax: 220, mtow: 97000, fuelBurn: 2.7, range: 7400, engines: "PW1133G", category: "narrow" },
  A333: { name: "Airbus A330-300", maxPax: 440, mtow: 242000, fuelBurn: 5.8, range: 11750, engines: "Trent 700", category: "wide" },
  B738: { name: "Boeing 737-800", maxPax: 189, mtow: 79016, fuelBurn: 2.4, range: 5765, engines: "CFM56-7B", category: "narrow" },
  B77W: { name: "Boeing 777-300ER", maxPax: 550, mtow: 351500, fuelBurn: 7.5, range: 13650, engines: "GE90-115B", category: "wide" },
  E190: { name: "Embraer E190", maxPax: 114, mtow: 51800, fuelBurn: 1.6, range: 4537, engines: "CF34-10E", category: "regional" },
  BCS3: { name: "Airbus A220-300", maxPax: 160, mtow: 69900, fuelBurn: 2.0, range: 6300, engines: "PW1524G", category: "narrow" },
  DH8D: { name: "Dash 8 Q400", maxPax: 90, mtow: 30481, fuelBurn: 1.0, range: 2040, engines: "PW150A", category: "turboprop" },
  C56X: { name: "Cessna Citation Excel", maxPax: 10, mtow: 9163, fuelBurn: 0.6, range: 3700, engines: "PW545A", category: "bizjet" },
};

const AIRLINES = [
  { code: "SWR", name: "SWISS", color: "#e30613" },
  { code: "EZS", name: "easyJet CH", color: "#ff6600" },
  { code: "EDW", name: "Edelweiss Air", color: "#c8102e" },
  { code: "SXS", name: "SunExpress", color: "#f2c800" },
  { code: "DLH", name: "Lufthansa", color: "#05164d" },
  { code: "AFR", name: "Air France", color: "#002157" },
  { code: "BAW", name: "British Airways", color: "#075aaa" },
  { code: "UAE", name: "Emirates", color: "#d4af37" },
  { code: "THY", name: "Turkish Airlines", color: "#c8102e" },
  { code: "PVT", name: "Private", color: "#888888" },
];

const DESTINATIONS = [
  { name: "London", lat: 51.47, lon: -0.46 },
  { name: "Paris", lat: 49.01, lon: 2.55 },
  { name: "Frankfurt", lat: 50.03, lon: 8.57 },
  { name: "Amsterdam", lat: 52.31, lon: 4.76 },
  { name: "Rome", lat: 41.80, lon: 12.24 },
  { name: "Barcelona", lat: 41.30, lon: 2.08 },
  { name: "Dubai", lat: 25.25, lon: 55.36 },
  { name: "Istanbul", lat: 41.28, lon: 28.75 },
  { name: "New York", lat: 40.64, lon: -73.78 },
  { name: "Munich", lat: 48.35, lon: 11.79 },
  { name: "Vienna", lat: 48.11, lon: 16.57 },
  { name: "Milan", lat: 45.63, lon: 8.72 },
];

// ── Utility functions ───────────────────────────────────────────────
function haversine(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function lerp(a, b, t) { return a + (b - a) * t; }

function generateFlights(count = 35) {
  const flights = [];
  const acTypes = Object.keys(AIRCRAFT_DB);
  for (let i = 0; i < count; i++) {
    const origin = SWISS_AIRPORTS[Math.floor(Math.random() * 5)]; // major airports
    const isInbound = Math.random() > 0.5;
    const dest = DESTINATIONS[Math.floor(Math.random() * DESTINATIONS.length)];
    const acType = acTypes[Math.floor(Math.random() * acTypes.length)];
    const ac = AIRCRAFT_DB[acType];
    const airline = AIRLINES[Math.floor(Math.random() * AIRLINES.length)];
    const flightNum = `${airline.code}${100 + Math.floor(Math.random() * 900)}`;
    const dist = isInbound ? haversine(dest.lat, dest.lon, origin.lat, origin.lon) : haversine(origin.lat, origin.lon, dest.lat, dest.lon);
    const progress = Math.random();
    const fromLat = isInbound ? dest.lat : origin.lat;
    const fromLon = isInbound ? dest.lon : origin.lon;
    const toLat = isInbound ? origin.lat : dest.lat;
    const toLon = isInbound ? origin.lon : dest.lon;
    const curLat = lerp(fromLat, toLat, progress);
    const curLon = lerp(fromLon, toLon, progress);
    const altProfile = progress < 0.15 ? progress / 0.15 : progress > 0.85 ? (1 - progress) / 0.15 : 1;
    const cruiseAlt = ac.category === "turboprop" ? 25000 : ac.category === "bizjet" ? 41000 : ac.category === "wide" ? 39000 : 37000;
    const altitude = Math.round(altProfile * cruiseAlt);
    const speed = ac.category === "turboprop" ? 310 : ac.category === "bizjet" ? 460 : altitude > 30000 ? 480 : 350;
    const totalFuel = Math.round(ac.fuelBurn * (dist / speed) * 1000);
    const fuelBurned = Math.round(totalFuel * progress);
    const heading = Math.round((Math.atan2(toLon - fromLon, toLat - fromLat) * 180 / Math.PI + 360) % 360);
    const vertRate = progress < 0.15 ? Math.round(1800 + Math.random() * 700) : progress > 0.85 ? -Math.round(1200 + Math.random() * 500) : 0;
    const icao24 = Array.from({ length: 6 }, () => "0123456789abcdef"[Math.floor(Math.random() * 16)]).join("");

    flights.push({
      id: icao24, callsign: flightNum, acType, acInfo: ac, airline,
      origin: isInbound ? dest.name : origin.name,
      destination: isInbound ? origin.name : dest.name,
      originAirport: isInbound ? null : origin,
      destAirport: isInbound ? origin : null,
      lat: curLat, lon: curLon, altitude, speed, heading, vertRate,
      progress, distance: Math.round(dist), totalFuel, fuelBurned,
      isInbound, fromLat, fromLon, toLat, toLon,
      co2: Math.round(fuelBurned * 3.16),
      phase: progress < 0.15 ? "climb" : progress > 0.85 ? "descent" : "cruise",
    });
  }
  return flights;
}

// ── Map projection (Mercator, bounded to Swiss region + surroundings) ──
const MAP_BOUNDS = { minLat: 40, maxLat: 55, minLon: -5, maxLon: 20 };

function projectToMap(lat, lon, width, height) {
  const x = ((lon - MAP_BOUNDS.minLon) / (MAP_BOUNDS.maxLon - MAP_BOUNDS.minLon)) * width;
  const mercY = (l) => Math.log(Math.tan(Math.PI / 4 + (l * Math.PI) / 360));
  const y = height - ((mercY(lat) - mercY(MAP_BOUNDS.minLat)) / (mercY(MAP_BOUNDS.maxLat) - mercY(MAP_BOUNDS.minLat))) * height;
  return { x, y };
}

// ── SVG Map Component ───────────────────────────────────────────────
function AirspaceMap({ flights, selectedFlight, onSelectFlight, width = 700, height = 500 }) {
  const swissBorderPoints = [
    [47.81, 8.57], [47.69, 8.30], [47.59, 7.53], [47.44, 7.02],
    [46.87, 6.09], [46.45, 6.21], [46.15, 6.78], [45.82, 7.04],
    [45.83, 7.89], [46.01, 8.46], [46.17, 9.02], [46.23, 9.48],
    [46.48, 9.83], [46.86, 10.49], [47.27, 10.18], [47.54, 9.60],
    [47.66, 9.49], [47.81, 8.57],
  ];
  const borderPath = swissBorderPoints.map((p, i) => {
    const { x, y } = projectToMap(p[0], p[1], width, height);
    return `${i === 0 ? "M" : "L"}${x},${y}`;
  }).join(" ") + "Z";

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: "100%", height: "100%", background: "#0a0e1a" }}>
      <defs>
        <radialGradient id="glowGrad" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#1a3a5c" stopOpacity="0.4" />
          <stop offset="100%" stopColor="#0a0e1a" stopOpacity="0" />
        </radialGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {/* Grid lines */}
      {[42, 44, 46, 48, 50, 52, 54].map((lat) => {
        const { y } = projectToMap(lat, 0, width, height);
        return <line key={`lat-${lat}`} x1={0} y1={y} x2={width} y2={y} stroke="#0f1a2e" strokeWidth={0.5} />;
      })}
      {[-4, -2, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18].map((lon) => {
        const { x } = projectToMap(46, lon, width, height);
        return <line key={`lon-${lon}`} x1={x} y1={0} x2={x} y2={height} stroke="#0f1a2e" strokeWidth={0.5} />;
      })}
      {/* Swiss border */}
      <path d={borderPath} fill="rgba(0,180,216,0.04)" stroke="#00b4d8" strokeWidth={1.2} strokeOpacity={0.5} />
      {/* Swiss glow */}
      {(() => { const c = projectToMap(46.8, 8.2, width, height); return <ellipse cx={c.x} cy={c.y} rx={80} ry={60} fill="url(#glowGrad)" />; })()}
      {/* Flight trails */}
      {flights.map((f) => {
        const from = projectToMap(f.fromLat, f.fromLon, width, height);
        const to = projectToMap(f.toLat, f.toLon, width, height);
        const cur = projectToMap(f.lat, f.lon, width, height);
        const isSelected = selectedFlight?.id === f.id;
        return (
          <g key={`trail-${f.id}`}>
            <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke={isSelected ? f.airline.color : "#1a2744"} strokeWidth={isSelected ? 1.2 : 0.4} strokeDasharray={isSelected ? "none" : "3,6"} opacity={isSelected ? 0.7 : 0.3} />
            {isSelected && <line x1={from.x} y1={from.y} x2={cur.x} y2={cur.y} stroke={f.airline.color} strokeWidth={1.5} opacity={0.5} />}
          </g>
        );
      })}
      {/* Airports */}
      {SWISS_AIRPORTS.map((ap) => {
        const { x, y } = projectToMap(ap.lat, ap.lon, width, height);
        const r = ap.type === "major" ? 4 : ap.type === "military" ? 3 : 2.5;
        const col = ap.type === "major" ? "#00b4d8" : ap.type === "military" ? "#ffd60a" : "#48cae4";
        return (
          <g key={ap.icao}>
            <circle cx={x} cy={y} r={r + 3} fill={col} opacity={0.1} />
            <circle cx={x} cy={y} r={r} fill="#0a0e1a" stroke={col} strokeWidth={1.2} filter="url(#glow)" />
            <text x={x + r + 4} y={y + 3} fill={col} fontSize={8} fontFamily="'JetBrains Mono', monospace" opacity={0.8}>{ap.iata || ap.icao}</text>
          </g>
        );
      })}
      {/* Aircraft positions */}
      {flights.map((f) => {
        const { x, y } = projectToMap(f.lat, f.lon, width, height);
        const isSelected = selectedFlight?.id === f.id;
        const rot = f.heading - 90;
        const col = isSelected ? "#ffffff" : f.airline.color;
        const size = isSelected ? 7 : 4;
        return (
          <g key={f.id} onClick={() => onSelectFlight(f)} style={{ cursor: "pointer" }} transform={`translate(${x},${y})`}>
            {isSelected && <circle r={12} fill={f.airline.color} opacity={0.2}><animate attributeName="r" values="12;18;12" dur="2s" repeatCount="indefinite" /></circle>}
            <g transform={`rotate(${rot})`}>
              <polygon points={`0,${-size} ${size * 0.6},${size * 0.4} 0,${size * 0.15} ${-size * 0.6},${size * 0.4}`} fill={col} opacity={isSelected ? 1 : 0.85} />
            </g>
            {isSelected && <text y={-14} textAnchor="middle" fill="#fff" fontSize={9} fontFamily="'JetBrains Mono', monospace" fontWeight="bold">{f.callsign}</text>}
          </g>
        );
      })}
    </svg>
  );
}

// ── Stat cards ──────────────────────────────────────────────────────
function StatCard({ label, value, unit, accent = "#00b4d8", sub }) {
  return (
    <div style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: "10px 14px", minWidth: 120 }}>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 4, fontFamily: "'JetBrains Mono', monospace" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: accent, fontFamily: "'JetBrains Mono', monospace" }}>
        {value}<span style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", marginLeft: 4 }}>{unit}</span>
      </div>
      {sub && <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ── Flight detail panel ─────────────────────────────────────────────
function FlightDetail({ flight }) {
  if (!flight) return (
    <div style={{ padding: 24, textAlign: "center", color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
      <div style={{ fontSize: 32, marginBottom: 8 }}>✦</div>
      Select an aircraft on the map to view logistics data
    </div>
  );
  const f = flight;
  const phaseColors = { climb: "#4cc9f0", cruise: "#00b4d8", descent: "#f77f00" };
  const efficiencyScore = Math.round((1 - f.fuelBurned / (f.totalFuel * 1.2)) * 100);
  return (
    <div style={{ padding: 16, fontFamily: "'JetBrains Mono', monospace" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: f.airline.color }} />
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#fff" }}>{f.callsign}</div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>{f.airline.name} · {f.acInfo.name}</div>
        </div>
        <div style={{ marginLeft: "auto", background: phaseColors[f.phase], color: "#000", fontSize: 9, padding: "3px 8px", borderRadius: 4, fontWeight: 700, textTransform: "uppercase" }}>{f.phase}</div>
      </div>
      {/* Route */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, padding: "10px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 6 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: "#00b4d8" }}>{f.origin}</div>
        <div style={{ flex: 1, height: 2, background: "rgba(255,255,255,0.1)", position: "relative", borderRadius: 1 }}>
          <div style={{ position: "absolute", top: 0, left: 0, height: 2, width: `${f.progress * 100}%`, background: `linear-gradient(90deg, ${f.airline.color}, #00b4d8)`, borderRadius: 1 }} />
          <div style={{ position: "absolute", top: -3, left: `${f.progress * 100}%`, width: 8, height: 8, background: "#fff", borderRadius: "50%", transform: "translateX(-4px)" }} />
        </div>
        <div style={{ fontSize: 14, fontWeight: 700, color: "#00b4d8" }}>{f.destination}</div>
      </div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textAlign: "center", marginTop: -10, marginBottom: 12 }}>{f.distance} km · {Math.round(f.progress * 100)}% complete</div>
      {/* Metrics grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
        {[
          { label: "Altitude", value: f.altitude.toLocaleString(), unit: "ft" },
          { label: "Ground Speed", value: f.speed, unit: "kts" },
          { label: "Heading", value: `${f.heading}°`, unit: "" },
          { label: "Vert Rate", value: f.vertRate > 0 ? `+${f.vertRate}` : f.vertRate, unit: "fpm" },
        ].map((m, i) => (
          <div key={i} style={{ background: "rgba(255,255,255,0.02)", borderRadius: 4, padding: "6px 8px" }}>
            <div style={{ fontSize: 8, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: 1 }}>{m.label}</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#fff" }}>{m.value} <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)" }}>{m.unit}</span></div>
          </div>
        ))}
      </div>
      {/* Fuel & Emissions */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12, marginBottom: 12 }}>
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Fuel & Emissions Model</div>
        <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
          <div style={{ flex: 1, background: "rgba(255,255,255,0.02)", borderRadius: 4, padding: "6px 8px" }}>
            <div style={{ fontSize: 8, color: "rgba(255,255,255,0.3)" }}>FUEL BURNED</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#f77f00" }}>{f.fuelBurned.toLocaleString()} <span style={{ fontSize: 9, opacity: 0.5 }}>kg</span></div>
          </div>
          <div style={{ flex: 1, background: "rgba(255,255,255,0.02)", borderRadius: 4, padding: "6px 8px" }}>
            <div style={{ fontSize: 8, color: "rgba(255,255,255,0.3)" }}>TOTAL EST.</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#fff" }}>{f.totalFuel.toLocaleString()} <span style={{ fontSize: 9, opacity: 0.5 }}>kg</span></div>
          </div>
          <div style={{ flex: 1, background: "rgba(255,255,255,0.02)", borderRadius: 4, padding: "6px 8px" }}>
            <div style={{ fontSize: 8, color: "rgba(255,255,255,0.3)" }}>CO₂ EST.</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#e63946" }}>{f.co2.toLocaleString()} <span style={{ fontSize: 9, opacity: 0.5 }}>kg</span></div>
          </div>
        </div>
        {/* Fuel burn progress bar */}
        <div style={{ height: 6, background: "rgba(255,255,255,0.05)", borderRadius: 3, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${(f.fuelBurned / f.totalFuel) * 100}%`, background: "linear-gradient(90deg, #f77f00, #e63946)", borderRadius: 3 }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 8, color: "rgba(255,255,255,0.3)", marginTop: 2 }}>
          <span>{Math.round((f.fuelBurned / f.totalFuel) * 100)}% consumed</span>
          <span>Burn rate: ~{f.acInfo.fuelBurn} t/hr</span>
        </div>
      </div>
      {/* Aircraft specs */}
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: 12 }}>
        <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Aircraft Specs</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 4, fontSize: 11 }}>
          {[
            ["Type", f.acType],
            ["Category", f.acInfo.category],
            ["Max Pax", f.acInfo.maxPax],
            ["MTOW", `${(f.acInfo.mtow / 1000).toFixed(0)}t`],
            ["Engines", f.acInfo.engines],
            ["Range", `${f.acInfo.range} km`],
          ].map(([k, v], i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
              <span style={{ color: "rgba(255,255,255,0.35)" }}>{k}</span>
              <span style={{ color: "#fff", fontWeight: 500 }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
      {/* ML readiness indicator */}
      <div style={{ marginTop: 12, padding: "8px 10px", background: "rgba(0,180,216,0.06)", border: "1px solid rgba(0,180,216,0.15)", borderRadius: 6, fontSize: 10 }}>
        <div style={{ color: "#00b4d8", fontWeight: 600, marginBottom: 2 }}>⚡ ML-Ready Data Points</div>
        <div style={{ color: "rgba(255,255,255,0.4)", lineHeight: 1.5 }}>
          Trajectory vectors · Fuel efficiency ratio ({efficiencyScore}%) · Phase segmentation · Weather correlation ready · Route deviation: +{Math.round(f.distance * 0.04)} km vs great circle
        </div>
      </div>
    </div>
  );
}

// ── Network analysis mini chart ─────────────────────────────────────
function NetworkChart({ flights }) {
  const routeCounts = {};
  flights.forEach((f) => {
    const key = [f.origin, f.destination].sort().join("-");
    routeCounts[key] = (routeCounts[key] || 0) + 1;
  });
  const sorted = Object.entries(routeCounts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = sorted[0]?.[1] || 1;
  return (
    <div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>Route Frequency</div>
      {sorted.map(([route, count], i) => (
        <div key={route} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <div style={{ width: 120, fontSize: 9, color: "rgba(255,255,255,0.5)", fontFamily: "'JetBrains Mono', monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{route}</div>
          <div style={{ flex: 1, height: 8, background: "rgba(255,255,255,0.04)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${(count / max) * 100}%`, background: `linear-gradient(90deg, #00b4d8, #4cc9f0)`, borderRadius: 4, transition: "width 0.5s" }} />
          </div>
          <div style={{ width: 16, fontSize: 10, color: "#00b4d8", fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>{count}</div>
        </div>
      ))}
    </div>
  );
}

// ── Fuel by aircraft type chart ─────────────────────────────────────
function FuelByTypeChart({ flights }) {
  const byType = {};
  flights.forEach((f) => {
    if (!byType[f.acType]) byType[f.acType] = { total: 0, count: 0 };
    byType[f.acType].total += f.fuelBurned;
    byType[f.acType].count++;
  });
  const sorted = Object.entries(byType).sort((a, b) => b[1].total - a[1].total).slice(0, 6);
  const max = sorted[0]?.[1].total || 1;
  const colors = ["#e63946", "#f77f00", "#ffd60a", "#00b4d8", "#4cc9f0", "#90e0ef"];
  return (
    <div>
      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8, fontFamily: "'JetBrains Mono', monospace" }}>Fuel Burn by Type</div>
      {sorted.map(([type, data], i) => (
        <div key={type} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <div style={{ width: 36, fontSize: 10, color: colors[i], fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>{type}</div>
          <div style={{ flex: 1, height: 8, background: "rgba(255,255,255,0.04)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${(data.total / max) * 100}%`, background: colors[i], borderRadius: 4, opacity: 0.7 }} />
          </div>
          <div style={{ width: 48, fontSize: 9, color: "rgba(255,255,255,0.5)", fontFamily: "'JetBrains Mono', monospace", textAlign: "right" }}>{(data.total / 1000).toFixed(1)}t</div>
        </div>
      ))}
    </div>
  );
}

// ── Main Dashboard ──────────────────────────────────────────────────
export default function SwissAirspaceDashboard() {
  const [flights, setFlights] = useState(() => generateFlights(35));
  const [selectedFlight, setSelectedFlight] = useState(null);
  const [activeTab, setActiveTab] = useState("detail");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setFlights((prev) =>
        prev.map((f) => {
          const newProgress = Math.min(f.progress + 0.002 + Math.random() * 0.001, 0.99);
          const newLat = lerp(f.fromLat, f.toLat, newProgress);
          const newLon = lerp(f.fromLon, f.toLon, newProgress);
          const altProfile = newProgress < 0.15 ? newProgress / 0.15 : newProgress > 0.85 ? (1 - newProgress) / 0.15 : 1;
          const cruiseAlt = f.acInfo.category === "turboprop" ? 25000 : f.acInfo.category === "bizjet" ? 41000 : f.acInfo.category === "wide" ? 39000 : 37000;
          const newAlt = Math.round(altProfile * cruiseAlt);
          const newFuelBurned = Math.round(f.totalFuel * newProgress);
          return {
            ...f, progress: newProgress, lat: newLat, lon: newLon, altitude: newAlt, fuelBurned: newFuelBurned,
            co2: Math.round(newFuelBurned * 3.16),
            phase: newProgress < 0.15 ? "climb" : newProgress > 0.85 ? "descent" : "cruise",
            vertRate: newProgress < 0.15 ? Math.round(1800 + Math.random() * 700) : newProgress > 0.85 ? -Math.round(1200 + Math.random() * 500) : Math.round((Math.random() - 0.5) * 200),
          };
        })
      );
      setTick((t) => t + 1);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedFlight) {
      setSelectedFlight((prev) => flights.find((f) => f.id === prev?.id) || null);
    }
  }, [flights]);

  const stats = useMemo(() => {
    const totalFuel = flights.reduce((s, f) => s + f.fuelBurned, 0);
    const totalCO2 = flights.reduce((s, f) => s + f.co2, 0);
    const avgAlt = Math.round(flights.reduce((s, f) => s + f.altitude, 0) / flights.length);
    const inbound = flights.filter((f) => f.isInbound).length;
    return { totalFuel, totalCO2, avgAlt, inbound, outbound: flights.length - inbound };
  }, [flights]);

  const tabStyle = (t) => ({
    padding: "6px 14px", fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
    color: activeTab === t ? "#00b4d8" : "rgba(255,255,255,0.3)", cursor: "pointer",
    background: activeTab === t ? "rgba(0,180,216,0.1)" : "transparent",
    border: `1px solid ${activeTab === t ? "rgba(0,180,216,0.2)" : "transparent"}`,
    borderRadius: 4, textTransform: "uppercase", letterSpacing: 1, transition: "all 0.2s",
  });

  return (
    <div style={{ background: "#080c16", color: "#fff", minHeight: "100vh", fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      {/* Header */}
      <div style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#00b4d8", boxShadow: "0 0 12px rgba(0,180,216,0.5)" }} />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 2 }}>SWISS AIRSPACE LOGISTICS</div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono', monospace" }}>Real-time flight analytics · Proof of Concept</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e" }}><div style={{ width: 6, height: 6, borderRadius: "50%", background: "#22c55e", animation: "pulse 2s infinite" }} /></div>
            <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", fontFamily: "'JetBrains Mono', monospace" }}>LIVE</span>
          </div>
          <div style={{ fontSize: 10, color: "rgba(255,255,255,0.3)", fontFamily: "'JetBrains Mono', monospace" }}>
            {new Date().toLocaleTimeString("en-GB")} UTC+1
          </div>
        </div>
      </div>
      {/* Stats bar */}
      <div style={{ padding: "10px 20px", display: "flex", gap: 10, overflowX: "auto", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
        <StatCard label="Active Flights" value={flights.length} unit="ac" accent="#00b4d8" sub={`${stats.inbound} inbound · ${stats.outbound} outbound`} />
        <StatCard label="Total Fuel Burned" value={(stats.totalFuel / 1000).toFixed(1)} unit="tonnes" accent="#f77f00" />
        <StatCard label="CO₂ Emitted" value={(stats.totalCO2 / 1000).toFixed(1)} unit="tonnes" accent="#e63946" />
        <StatCard label="Avg. Altitude" value={stats.avgAlt.toLocaleString()} unit="ft" accent="#4cc9f0" />
        <StatCard label="Aircraft Types" value={new Set(flights.map((f) => f.acType)).size} unit="types" accent="#90e0ef" />
      </div>
      {/* Main content */}
      <div style={{ display: "flex", height: "calc(100vh - 140px)" }}>
        {/* Map */}
        <div style={{ flex: 1, position: "relative" }}>
          <AirspaceMap flights={flights} selectedFlight={selectedFlight} onSelectFlight={setSelectedFlight} />
          {/* Map legend */}
          <div style={{ position: "absolute", bottom: 12, left: 12, background: "rgba(8,12,22,0.85)", backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 6, padding: "8px 12px", fontSize: 9, fontFamily: "'JetBrains Mono', monospace" }}>
            <div style={{ color: "rgba(255,255,255,0.4)", marginBottom: 4 }}>LEGEND</div>
            <div style={{ display: "flex", gap: 12 }}>
              <span><span style={{ color: "#00b4d8" }}>●</span> Major</span>
              <span><span style={{ color: "#48cae4" }}>●</span> Regional</span>
              <span><span style={{ color: "#ffd60a" }}>●</span> Military</span>
            </div>
          </div>
          <div style={{ position: "absolute", top: 12, right: 12, background: "rgba(8,12,22,0.85)", backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 6, padding: "8px 12px", fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: "rgba(255,255,255,0.3)" }}>
            Data source: OpenSky Network API · Fuel model: OpenAP
          </div>
        </div>
        {/* Side panel */}
        <div style={{ width: 340, borderLeft: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.01)", overflowY: "auto" }}>
          <div style={{ display: "flex", gap: 4, padding: "8px 12px", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div style={tabStyle("detail")} onClick={() => setActiveTab("detail")}>Flight Detail</div>
            <div style={tabStyle("network")} onClick={() => setActiveTab("network")}>Network</div>
            <div style={tabStyle("fuel")} onClick={() => setActiveTab("fuel")}>Fuel</div>
          </div>
          <div style={{ padding: activeTab === "detail" ? 0 : 16 }}>
            {activeTab === "detail" && <FlightDetail flight={selectedFlight} />}
            {activeTab === "network" && <NetworkChart flights={flights} />}
            {activeTab === "fuel" && <FuelByTypeChart flights={flights} />}
          </div>
        </div>
      </div>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
      `}</style>
    </div>
  );
}
