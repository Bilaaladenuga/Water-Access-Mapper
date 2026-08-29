# Water Access Mapper

A geospatial web application for mapping, analyzing, and improving water point accessibility in underserved communities.

## Problem

Access to clean water remains a critical challenge globally. Communities often lack comprehensive, up-to-date information about available water points, their operational status, and accessibility. This project addresses this gap by creating an interactive, data-driven platform for water resource management.

## Motivation

This project demonstrates proficiency in:
- **GIS**: Spatial data analysis and visualization
- **PostGIS**: Spatial database queries and indexing
- **Python**: Geospatial processing with GeoPandas and Shapely
- **Web GIS**: Interactive mapping with MapLibre GL JS
- **Full-stack Development**: Next.js frontend with FastAPI backend
- **Spatial Analysis**: Buffer analysis, network routing, proximity queries

## Study Area

[To be defined during implementation]

## Methodology

### Data Sources
- OpenStreetMap water point data
- GeoJSON/CSV public datasets
- Crowdsourced user submissions

### Spatial Analysis
- Buffer analysis for accessibility zones
- Network routing for walking distances
- Point density analysis
- Proximity queries

## Architecture

```
┌─────────────────────────────────────┐
│        Frontend (Next.js)           │
│    MapLibre GL JS + React           │
└──────────────┬──────────────────────┘
               │ REST API
               ▼
┌─────────────────────────────────────┐
│        Backend (FastAPI)            │
│    Spatial queries + Routing        │
└──────────────┬──────────────────────┘
               │ PostGIS
               ▼
┌─────────────────────────────────────┐
│   Database (Supabase/PostgreSQL)    │
│         + PostGIS extension         │
└─────────────────────────────────────┘
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Maps | MapLibre GL JS |
| Backend | Python 3.10+, FastAPI |
| Database | PostgreSQL, PostGIS, Supabase |
| Geospatial | GeoPandas, Shapely, NumPy |
| Routing | OSRM |

## Data Sources

- [OpenStreetMap](https://www.openstreetmap.org/) - Water points, roads, boundaries
- [Supabase](https://supabase.com/) - Managed PostgreSQL + PostGIS
- [OSRM](http://project-osrm.org/) - Walking route calculations

## Installation

### Prerequisites
- Node.js 18+
- Python 3.10+
- Supabase account (free tier)

### Quick Setup

Run the setup script:
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Manual Setup

#### 1. Clone the repository
```bash
git clone https://github.com/Bilaaladenuga/Water-Access-Mapper.git
cd Water-Access-Mapper
```

#### 2. Frontend (Next.js)
```bash
cd apps/web
npm install
cp .env.local.example .env.local
# Edit .env.local with your settings
npm run dev
```
Frontend runs at: http://localhost:3000

#### 3. Backend (FastAPI)
```bash
cd apps/api
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase credentials
uvicorn main:app --reload
```
Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

#### 4. Database (Supabase)
1. Create a project at [supabase.com](https://supabase.com)
2. Copy your `SUPABASE_URL` and `SUPABASE_ANON_KEY` to `.env`
3. Run migrations from `database/migrations/` (Phase 2)

## Project Structure

```
water-access-mapper/
├── apps/
│   ├── web/           # Next.js frontend
│   └── api/           # FastAPI backend
├── geospatial/        # Python geospatial processing
│   ├── ingestion/
│   ├── cleaning/
│   ├── analysis/
│   └── routing/
├── data/
│   ├── raw/           # Original data files
│   ├── processed/     # Cleaned data
│   └── sample/        # Sample datasets
├── database/
│   └── migrations/    # SQL migration scripts
├── scripts/           # Setup and utility scripts
├── docs/              # Documentation
├── tests/             # Test files
├── PROJECT_SPEC.md    # Full project specification
├── PROGRESS.md        # Task progress tracker
└── README.md
```

## GIS Analysis

[To be documented as features are implemented]

## Limitations

- Initial implementation uses sample data
- Routing based on road network (not actual paths)
- Single study area initially
- No offline support

## Deployment

[To be configured in Phase 11]

- Frontend → Vercel
- Backend → Render/Railway
- Database → Supabase

## Future Work

- Mobile-responsive PWA for offline access
- Multi-country support
- Real-time WebSocket updates
- Satellite imagery integration
- Machine learning for water point detection
- IoT integration for monitoring

---

*Developed as part of a Geoinformatics portfolio to demonstrate proficiency in GIS, spatial databases, Python, and full-stack web development.*
