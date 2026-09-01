# Water Access Mapper

A geospatial web application for mapping, analyzing, and improving water point accessibility in Lagos State, Nigeria.

![MapLibre GL JS](https://img.shields.io/badge/Map-MapLibre%20GL%20JS-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)
![PostGIS](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20PostGIS-blue)
![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black)

---

## Problem Statement

Access to clean water remains a critical challenge in Lagos State, Nigeria — a megacity of over 20 million people. Communities often lack comprehensive, up-to-date information about available water points, their operational status, and accessibility. Existing data is fragmented across multiple sources and rarely integrated into a single, actionable platform.

**This project addresses that gap** by creating an interactive, data-driven platform that:

- Combines real OpenStreetMap data with crowdsourced submissions
- Provides spatial analysis to identify underserved areas
- Offers walking route navigation to the nearest water point
- Enables community reporting of broken or incorrect water points

---

## Study Area

**Lagos State, Nigeria** — the most populous state in Nigeria and one of the largest metropolitan areas in Africa.

| Property | Value |
|----------|-------|
| **Area** | 3,671.5 km² |
| **Boundary source** | OCHA HDX COD-AB (CC BY-IGO) |
| **Coordinates** | 6.37–6.70°N, 2.70–4.35°E |
| **LGAs covered** | All 20 Local Government Areas |
| **Water points** | 147 (69 OSM + 77 sample + 1 crowdsourced) |

The study area boundary was downloaded from the [OCHA Humanitarian Data Exchange](https://data.humdata.org/dataset/cod-ab-nga) using the official Nigerian Administrative Boundaries (COD-AB) dataset.

---

## Methodology

### Data Collection

1. **OpenStreetMap (OSM)** — 69 real water points downloaded via the Overpass API, queried across 5 tag types: `drinking_water`, `water_well`, `water_tap`, `water_point`, `spring`
2. **Sample Data** — 77 clearly labeled sample points for demonstration, spread across Lagos neighborhoods
3. **Crowdsourcing** — User-submitted points through the web interface (stored as unverified until approved)

### Spatial Analysis

| Technique | PostGIS Function | Purpose |
|-----------|-----------------|---------|
| **Nearest Neighbor** | `ST_Distance` + KNN `<->` operator | Find closest water point to any location |
| **Radius Search** | `ST_DWithin` (geography) | All water points within X meters |
| **Density Grid** | `ST_X`/`ST_Y` + `GROUP BY` | Identify high/low density areas |
| **Accessibility Model** | Haversine formula + grid overlay | Classify areas by water access (0–500m to >5km) |
| **Walking Routes** | OSRM foot profile | Network-based walking routes |

### Data Quality

- Coordinate validation (range checks within Lagos bounds)
- Duplicate detection (50m threshold using Shapely)
- Geometry validation (`ST_IsValid`, `shapely.validation.make_valid()`)
- Data provenance tracking (source: osm/sample/crowdsourced)

---

## Architecture

```
┌──────────────────────────────────────────────┐
│           Frontend (Next.js 14)               │
│     MapLibre GL JS · React · TypeScript       │
│     OpenFreeMap vector tiles (no API key)     │
└──────────────────┬───────────────────────────┘
                   │ REST API (JSON)
                   ▼
┌──────────────────────────────────────────────┐
│           Backend (FastAPI)                    │
│     25+ endpoints · Spatial queries           │
│     OSRM routing · Crowdsourcing              │
└──────────────────┬───────────────────────────┘
                   │ asyncpg + SQLAlchemy
                   ▼
┌──────────────────────────────────────────────┐
│     Database (Neon PostgreSQL + PostGIS)       │
│     water_points · study_areas                 │
│     water_point_submissions · reports          │
│     Spatial indexes (GIST)                     │
└──────────────────────────────────────────────┘
```

### Key Design Decisions

- **No Docker** — runs locally with Node.js, Python venv, and Neon PostgreSQL
- **OpenFreeMap** — free vector tiles with no API key or rate limits
- **Neon** — serverless PostgreSQL with PostGIS (migrated from Supabase free tier)
- **OSRM** — OpenStreetMap-based walking route calculations
- **Unverified data workflow** — crowdsourced submissions require admin approval

---

## Technology Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| **Frontend** | Next.js 14, React 18, TypeScript | SSR/SSG, type safety, React ecosystem |
| **Maps** | MapLibre GL JS | Open-source, vector/raster tile support |
| **Tile Provider** | OpenFreeMap | Free, no API key, no rate limits |
| **Backend** | Python 3.11, FastAPI | Async support, automatic API docs, Pydantic validation |
| **Database** | PostgreSQL 15 + PostGIS 3.3 | Spatial indexing, KNN queries, geodesic distance |
| **Hosting** | Neon (serverless PostgreSQL) | Free tier, auto-scaling, connection pooling |
| **Routing** | OSRM (Open Source Routing Machine) | OSM road network, walking profile |
| **Geospatial** | GeoPandas, Shapely, NumPy | Geometry validation, spatial operations |

---

## API Endpoints

### Core

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service status and version |
| GET | `/database` | PostgreSQL + PostGIS version |
| GET | `/` | API info and endpoint listing |
| GET | `/docs` | Swagger UI interactive documentation |

### Water Points

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/water-points/geojson` | All water points as GeoJSON |
| GET | `/api/water-points/geojson?status=operational` | Filter by status |
| GET | `/api/water-points/geojson?water_type=tap` | Filter by type |
| GET | `/api/water-points/stats` | Counts by status, type, source |
| GET | `/api/study-areas/geojson` | Lagos State boundary polygon |

### Spatial Queries

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/spatial/nearest?lat=&lon=` | Nearest water point (KNN) |
| GET | `/api/spatial/within-radius?lat=&lon=&radius_meters=` | Points within radius |
| GET | `/api/spatial/analysis?lat=&lon=&radius_meters=` | Combined analysis |
| GET | `/api/spatial/density` | Grid-based density |

### Routing

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/routing/to-nearest?lat=&lon=` | Walking route to nearest |
| GET | `/api/routing/to-point?lat=&lon=&target_id=` | Route to specific point |

### Accessibility

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/accessibility/analysis` | Coverage by distance categories |
| GET | `/api/accessibility/underserved` | Identify underserved areas |
| GET | `/api/accessibility/point-analysis?lat=&lon=` | Point-specific analysis |

### Crowdsourcing

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/crowd/submit` | Submit new water point |
| POST | `/api/crowd/report` | Report broken/incorrect point |
| GET | `/api/crowd/submissions` | List submissions |
| GET | `/api/crowd/reports` | List reports |
| POST | `/api/crowd/approve/{id}` | Approve submission (admin) |
| POST | `/api/crowd/reject/{id}` | Reject submission (admin) |
| POST | `/api/crowd/resolve/{id}` | Resolve report (admin) |

### Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/summary` | Dashboard summary stats |
| GET | `/api/analytics/breakdown` | Chart data |
| GET | `/api/analytics/coverage` | Coverage and density analysis |
| GET | `/api/analytics/data-quality` | Quality metrics |

---

## Project Structure

```
water-access-mapper/
├── apps/
│   ├── web/                        # Next.js frontend
│   │   └── src/
│   │       ├── app/
│   │       │   ├── page.tsx        # Map page
│   │       │   └── analytics/      # Analytics dashboard
│   │       └── components/
│   │           └── MapView.tsx     # Main map component
│   └── api/                        # FastAPI backend
│       ├── main.py                 # App entry point
│       ├── database.py             # DB connection (asyncpg)
│       ├── config.py               # Settings
│       └── routes/
│           ├── water_points.py     # GeoJSON endpoints
│           ├── spatial_queries.py  # PostGIS analysis
│           ├── routing.py          # OSRM routing
│           ├── accessibility.py    # Coverage model
│           ├── crowdsourcing.py    # Submissions & reports
│           └── analytics.py        # Dashboard stats
├── geospatial/
│   └── ingestion/
│       ├── geojson_loader.py       # GeoJSON ingestion pipeline
│       └── osm_loader.py           # Overpass API loader
├── data/
│   ├── raw/                        # Downloaded data
│   ├── processed/boundaries/       # Lagos boundary GeoJSON
│   └── sample/                     # Sample datasets
├── scripts/
│   ├── fetch_lagos_boundary.py     # OCHA HDX boundary download
│   ├── import_geojson.py           # PostGIS import script
│   └── osm_water_points.py         # Expanded OSM loader
├── tests/                          # 30 pytest tests
├── PROJECT_SPEC.md                 # Full project specification
├── PROGRESS.md                     # Task progress tracker
└── README.md                       # This file
```

---

## Installation

### Prerequisites

- **Node.js 18+** (with pnpm recommended)
- **Python 3.10+**
- **Neon account** (free tier for PostgreSQL + PostGIS)

### 1. Clone the repository

```bash
git clone https://github.com/Bilaaladenuga/Water-Access-Mapper.git
cd Water-Access-Mapper
```

### 2. Backend setup

```bash
cd apps/api

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Neon DATABASE_URL
```

### 3. Load data

```bash
# Download Lagos State boundary from OCHA HDX
python scripts/fetch_lagos_boundary.py

# Import boundary into PostGIS
python scripts/import_geojson.py area data/processed/boundaries/lagos_state.geojson

# Import water points
python scripts/import_geojson.py water data/sample/water_points.geojson

# Download real OSM water points
python scripts/osm_water_points.py
python scripts/import_geojson.py water data/raw/osm_water_points.geojson
```

### 4. Frontend setup

```bash
cd apps/web

# Install dependencies
pnpm install    # or npm install

# Start dev server
pnpm dev    # or npm run dev
```

### 5. Start the backend

```bash
cd apps/api
uvicorn main:app --reload --port 8000
```

### 6. Open the application

- **Map**: http://localhost:3000
- **Analytics**: http://localhost:3000/analytics
- **API Docs**: http://localhost:8000/docs

### 7. Run tests

```bash
cd apps/api
python -m pytest tests/ -v
```

---

## Deployment

### Frontend → Vercel

```bash
cd apps/web
vercel deploy
```

Set `NEXT_PUBLIC_API_URL` to your backend URL.

### Backend → Render

1. Create a new Web Service on [render.com](https://render.com)
2. Connect the GitHub repository
3. Set build command: `cd apps/api && pip install -r requirements.txt`
4. Set start command: `cd apps/api && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variable: `DATABASE_URL` (your Neon connection string)

### Database → Neon

1. Create a project at [neon.tech](https://neon.tech)
2. Copy the connection string to your backend `.env`
3. Enable PostGIS: `CREATE EXTENSION IF NOT EXISTS postgis;`
4. Run the data loading scripts (see Installation step 3)

---

## GIS Analysis Performed

### 1. Accessibility Classification

Water points are classified into 5 distance categories:

| Category | Distance | Description |
|----------|----------|-------------|
| Excellent | 0–500m | Walking distance |
| Good | 500m–1km | Easy access |
| Moderate | 1–2km | Requires planning |
| Poor | 2–5km | Difficult access |
| Critical | >5km | Severely underserved |

### 2. Nearest Neighbor Analysis

Uses PostGIS KNN operator (`<->`) for efficient spatial indexing:

```sql
SELECT name, ST_Distance(geometry::geography, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) AS distance
FROM water_points
ORDER BY geometry <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
LIMIT 1;
```

### 3. Walking Route Calculation

OSRM foot profile provides network-based walking routes with:
- Turn-by-turn navigation instructions
- Actual walking distance (vs straight-line)
- Estimated walking time (at 5 km/h average speed)

### 4. Density Analysis

Grid-based density calculation identifies underserved areas:

```sql
SELECT ROUND(ST_X(geometry), 2) AS grid_x,
       ROUND(ST_Y(geometry), 2) AS grid_y,
       COUNT(*) AS point_count
FROM water_points
GROUP BY grid_x, grid_y
ORDER BY point_count DESC;
```

---

## Data Quality

| Metric | Score |
|--------|-------|
| **Named points** | 147/147 (100%) |
| **Valid coordinates** | 147/147 (100%) |
| **Quality score** | 70.2/100 |

The quality score accounts for naming (30%), coordinate validity (40%), and verification status (30%).

---

## Test Results

**30 tests passing** across 5 test files:

```
tests/test_health.py          — 2 tests ✅
tests/test_water_points.py    — 10 tests ✅
tests/test_spatial.py         — 6 tests ✅
tests/test_crowdsourcing.py   — 7 tests ✅
tests/test_analytics.py       — 7 tests ✅
```

Tests run against the live API with real PostGIS queries.

---

## Limitations

1. **Sample data** — 77 of 147 points are fabricated for demonstration (clearly labeled)
2. **OSM coverage** — OpenStreetMap data varies by region; rural areas may have fewer mapped points
3. **Routing** — OSRM routing is based on the OSM road network; informal paths may not be included
4. **Single study area** — Currently limited to Lagos State
5. **No offline support** — Requires internet connection for map tiles and API calls

---

## Future Improvements

- **Multi-country support** — Expand beyond Lagos State
- **Real-time monitoring** — IoT integration for water point status
- **Mobile PWA** — Offline-first progressive web app
- **Satellite imagery** — ML-based water point detection
- **Water quality data** — Integrate testing results
- **Community maps** — Neighborhood-level boundary mapping
- **Analytics export** — PDF/CSV report generation
- **Multi-language** — Yoruba and Pidgin translations

---

## License

This project is for educational and portfolio purposes.

- OSM data: [ODbL](https://opendatacommons.org/licenses/odbl/) (attribution required)
- OCHA boundary: CC BY-IGO (attribution required)

---

## Author

**Bilaal Adenuga** — Surveying & Geoinformatics Student

Demonstrating proficiency in:
- GIS and spatial analysis
- PostGIS spatial databases
- Python geospatial processing
- Web GIS with MapLibre GL JS
- Full-stack development (Next.js + FastAPI)
- Data quality and validation
- Open-source geospatial tools
