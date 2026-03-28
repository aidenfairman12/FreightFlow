# FreightFlow

Interactive US supply chain risk intelligence — built on FAF5 freight flow data from the Bureau of Transportation Statistics.

**[Live Demo →](https://freight-flow-jk57.vercel.app)**

---

## What It Does

The federal government publishes detailed records of every major freight flow across the US — hundreds of millions of tons of goods, mapped by origin, destination, and commodity. It all lives in a 500,000-row spreadsheet. FreightFlow makes it explorable.

Pick a finished product and see where its raw materials come from, how concentrated those sources are, and what happens if a key region goes offline.

### Pages

**Risk Overview** — Ranks four critical US supply chains (Automobiles, Beef, Pharmaceuticals, Steel) by geographic concentration risk. Concentration is measured as the share of primary precursor tonnage entering the headline assembly zone from just the top three source zones.

**Supply Chain Explorer** — Interactive flow map showing weighted precursor lines fanning into an assembly hub. Click any source zone to simulate a disruption; the app calculates tonnage gap and estimated cost impact instantly, client-side.

**Critical Nodes** — Cross-supply-chain systemic risk view. Source zones are ranked by their share of total precursor tonnage across all four supply chains simultaneously, identifying the regions whose disruption would ripple across multiple industries at once.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React 18, TypeScript |
| Maps | Leaflet 1.9 |
| Styling | Tailwind CSS |
| Data | Pre-computed JSON from FAF5 v5.7.1 |
| Hosting | Vercel (free tier, no backend) |

The app is fully static — all supply chain analysis is pre-computed into JSON files at build time. There is no server, no database, and no API at runtime.

---

## Data & Methodology

**Source:** [FAF5 v5.7.1](https://www.bts.gov/faf) (Freight Analysis Framework), Bureau of Transportation Statistics / Federal Highway Administration. 522,000 domestic freight flow records for 2022, covering 132 geographic zones.

**Automobile precursor weights** derived from material composition data in the American Chemistry Council's *Chemistry and Automobiles: Driving the Future* (May 2024), Table 5.

**Concentration risk** = % of primary precursor tonnage into the headline assembly zone supplied by the top 3 source zones.

**Critical Nodes score** = a zone's share of total modelled precursor tonnage across all four supply chains. Intra-zone flows excluded.

See [`docs/ESTIMATION_CONSTANTS.md`](docs/ESTIMATION_CONSTANTS.md) for all hardcoded rate constants and their sources.

---

## Run Locally

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
```

All data is pre-computed and lives in `frontend/public/data/`. No environment variables or external services required.

To regenerate the data from FAF5 source files:

```bash
# Requires FAF5 CSV files in backend/data/faf5/
pip install -r backend/requirements.txt
python3 precompute.py
```

---

## Project Structure

```
FreightFlow/
├── frontend/                   Next.js app (the deployed product)
│   ├── public/data/            Pre-computed JSON (products, zones, supply chains, risk scores)
│   └── src/
│       ├── app/                Pages: Risk Overview, Explorer, Critical Nodes
│       ├── components/Map/     Leaflet map components (flow lines, critical nodes)
│       └── lib/api.ts          JSON data loaders
├── backend/                    Python data pipeline (offline, not deployed)
│   └── services/
│       ├── commodity_dependencies.py   Finished goods → precursor commodity mappings
│       └── freight_cost_model.py       Cost per ton-mile by mode (ATRI/AAR/BTS rates)
├── precompute.py               Generates all frontend/public/data/ JSON from FAF5 CSVs
└── docs/
    ├── ARCHITECTURE.md         System architecture
    └── ESTIMATION_CONSTANTS.md All hardcoded rate constants with sources
```
