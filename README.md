# 🗺️ Streamlit GeoSpatial Transport Analyzer

Streamlit-based web application for analyzing transportation data with geospatial capabilities (Shapefile integration, spatial/temporal aggregation, OD matrix)

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
streamlit run web_ui.py
```

---

## 🛠️ Tech Stack

- **Streamlit** - Web UI
- **GeoPandas** - GIS operations & Shapefile handling
- **Pandas** - Data processing
- **Shapely** - Spatial geometry

---

## ✨ Features

### 🔍 Filters
- Boundary Filter (Shapefile-based)
- Time & Hour Filters
- Combined Time-Space Filter

### 🔄 Transforms
- Spatial Aggregation (Grid-based: 50m-1km)
- Spatiotemporal Aggregation
- Time Slicing

### 🔗 Joins
- **Shapefile Join** with temporal separation (hourly/total)
- OD Matrix generation

### 🛠️ Utilities
- File Preview

---

## 📂 Structure

```
├── web_ui.py              # Main app
├── config.py              # Path configs
├── analysis_engine.py     # Core engine
├── operations/            # Modular operations
│   ├── config.py         # Global settings
│   ├── filters/
│   ├── transforms/
│   └── joins/
└── ui_helpers/           # UI utilities
```

---

## ⚙️ Configuration

All global settings centralized in `operations/config.py`:
- Boundary sources (neighborhoods, districts, zones)
- Grid sizes (50m, 100m, 250m, 500m, 1km)
- Time bins (15min, 30min, 60min, 2h, 3h)
- Aggregation levels

---

## 📝 License

MIT
