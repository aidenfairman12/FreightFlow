# FreightFlow Roadmap

## Completed

- **Data Pipeline Audit** — FAF5 CSV ingestion (bulk COPY loader), EIA/FRED economic ETL, zone ID mapping for FAF5.7.x, corridor performance auto-computation on startup
- **FAF5 Zone Centroids** — complete 132-zone JSON with verified coordinates for all FAF5.7.x zones
- **Map Rendering Fix** — resolved Leaflet async race condition so corridors render immediately on page load
- **Corridor Performance** — auto-compute and display cost/tonnage metrics per corridor

## Next Up

- **Scenario Comparison** — run 2+ scenarios side-by-side with delta comparison across parameters

## Future Enhancements

### High Impact
- **Commodity Filtering** — global commodity selector across all pages (API already supports it, no UI yet)
- **Export to CSV/PDF** — download charts, KPIs, and scenario results
- **Corridor-Specific Economics** — cost breakdowns per corridor, not just national averages

### Medium Impact
- **Zone-Level Drill-Down** — click into origin/destination zones for granular flow analysis
- **Margin Analysis** — surface margin data from `freight_unit_economics` more prominently
- **Commodity-Mode Optimization** — recommend cheapest mode per commodity-corridor pair

### Polish
- **Expanded Test Coverage** — scenario engine, KPI aggregator, endpoint integration tests
- **Mobile Responsiveness** — current design is desktop-first
- **WebSocket Real-Time Updates** — infrastructure exists in `api/websocket.py`, not yet wired to frontend
