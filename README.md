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

## Data Sources

- [OpenStreetMap](https://www.openstreetmap.org/) - Water points, roads, boundaries
- [Supabase](https://supabase.com/) - Managed PostgreSQL + PostGIS
- [OSRM](http://project-osrm.org/) - Walking route calculations

## Technology Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Maps | MapLibre GL JS |
| Backend | Python, FastAPI |
| Database | PostgreSQL, PostGIS, Supabase |
| Geospatial | GeoPandas, Shapely, NumPy |
| Routing | OSRM |

## GIS Analysis

[To be documented during implementation]

## Limitations

- Initial implementation uses sample data
- Routing based on road network (not actual paths)
- Single study area initially
- No offline support

## Installation

### Prerequisites
- Node.js 18+
- Python 3.10+
- Supabase account (free tier)

### Setup

1. Clone the repository
```bash
git clone https://github.com/Bilaaladenuga/Water-Access-Mapper.git
cd Water-Access-Mapper
```

2. Set up frontend
```bash
cd apps/web
npm install
cp .env.example .env.local
# Edit .env.local with your Supabase credentials
npm run dev
```

3. Set up backend
```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn main:app --reload
```

4. Set up database
- Create a Supabase project at [supabase.com](https://supabase.com)
- Run migrations from `database/migrations/`

## Deployment

### Frontend (Vercel)
[To be documented]

### Backend (Render/Railway)
[To be documented]

### Database (Supabase)
[To be documented]

## Environment Variables

See `.env.example` for required environment variables.

## Future Work

- Mobile-responsive PWA
- Multi-country support
- Real-time WebSocket updates
- Satellite imagery integration
- Machine learning for water point detection
- IoT integration for monitoring

## License

[Choose appropriate license]

---

*Developed as part of a Geoinformatics portfolio to demonstrate proficiency in GIS, spatial databases, Python, and full-stack web development.*
