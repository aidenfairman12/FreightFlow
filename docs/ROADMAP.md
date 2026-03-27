# FreightFlow Roadmap

## Completed

- **Data Pipeline** — FAF5 CSV ingestion (bulk COPY loader), EIA/FRED economic ETL, zone ID mapping for FAF5.7.x
- **FAF5 Zone Centroids** — complete 132-zone JSON with verified coordinates for all FAF5.7.x zones
- **Cost Model** — cost per ton-mile by mode with diesel sensitivity, grounded in ATRI/AAR/BTS rates
- **Supply Chain Explorer** — pick a finished product, select assembly location, visualize precursor material flows on interactive map with Sankey-like weighted lines, cost breakdown charts, mode analysis
- **Commodity Dependencies** — curated mapping of 6 finished goods to precursor materials with BOM ratios
- **Landing Page** — clean hero with single CTA into the Supply Chain Explorer

## Future Enhancements

### High Impact
- **Particle Effects** — animated flow particles along supply chain lines for visual impact
- **Sankey Diagram View** — traditional Sankey showing material → intermediate → finished good flow
- **Time Comparison** — compare supply chains across years (2017-2022) to show shifts

### Medium Impact
- **Disruption Simulation** — model impact of removing a source zone (port closure, factory shutdown)
- **More Finished Goods** — expand beyond 6 products to cover more industries
- **Zone-Level Drill-Down** — click source zones for granular flow detail

### Polish
- **Mobile Responsiveness** — current design is desktop-first
- **Loading Animations** — skeleton states while analysis runs
- **Expanded Test Coverage** — supply chain endpoint integration tests
