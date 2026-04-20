Build with ArcGIS pro version 3.3.1\
Python 3.5 or later\

# DEM to Drainage Area

Derives an upstream contributing area raster from a bare-earth Digital Elevation Model using ArcPy.  
**Study area:** Huntsville, AL · **Resolution:** 30 m · **Output CRS:** WGS 1984 UTM Zone 16N (EPSG 32616)

---

## Processing Pipeline

```
Raw DEM (GCS)
    │
    ▼  ProjectRaster — BILINEAR resampling
Projected DEM (UTM 16N)          ← saved to disk
    │
    ▼  Fill
Hydrologically conditioned DEM   ← memory only
    │
    ▼  FlowDirection (D8)
Flow direction raster             ← memory only
    │
    ▼  FlowAccumulation
Flow accumulation raster          ← memory only
    │
    ▼  × cell area (m²)
Drainage area raster              ← saved to disk
```

---

## Steps

| # | Operation | Key detail |
|---|-----------|------------|
| 0 | **Preflight** | Confirms DEM exists, Spatial Analyst licence available |
| 1 | **Project to UTM 16N** | Converts degrees → metres so cell area is meaningful |
| 2 | **Fill sinks** | Removes pits that would interrupt flow routing |
| 3 | **Flow direction** | D8 algorithm — each cell drains to its steepest neighbour |
| 4 | **Flow accumulation** | Counts upstream cells draining into each cell |
| 5 | **Drainage area** | `flow accumulation × cell area (900 m²)` |
| 6 | **Save & verify** | Checks output exists and logs min / max values |

---

## Output

Each pixel in `huntsville_drainage.tif` stores the **total upstream contributing area in m²**.  
High values trace the drainage network; low values mark ridges and divides.

```
drainage_area (m²) = flow_accumulation × (30 m × 30 m)
```

---

## Requirements

- ArcGIS Pro with **Spatial Analyst** extension
- Python 3.x via ArcGIS `arcpy` environment

---

## Files

| File | Description |
|------|-------------|
| `DEM_Huntsville30m.tif` | Input raw DEM (source) |
| `DEM_Huntsville30m_utm16n.tif` | Projected DEM — intermediate, kept on disk |
| `huntsville_drainage.tif` | Final drainage area output |
| `dem_to_drainage.py` | Processing script |
