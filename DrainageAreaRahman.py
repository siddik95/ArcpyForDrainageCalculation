#!/usr/bin/env python
# coding: utf-8

# In[6]:


"""
DEM to Drainage Area — ArcPy Script
Produces a raster of upstream contributing area (map units²) per cell.
Intermediate rasters are held in memory only.
"""

import arcpy
from arcpy import env
from arcpy.sa import *
import sys
import traceback

# ── Configuration ─────────────────────────────────────────────────────────────
DEM_PATH  = r"F:\onedrive\OneDrive - University of Central Florida\ESRI_GIS\DEM_Huntsville30m.tif" # input dem file path
OUT_PATH  = r"F:\onedrive\OneDrive - University of Central Florida\ESRI_GIS\huntsville_drainage.tif" # output drainge file path
PROJ_DEM  = r"F:\onedrive\OneDrive - University of Central Florida\ESRI_GIS\DEM_Huntsville30m_utm16n.tif" # projected dem file path
WORKSPACE = r"F:\onedrive\OneDrive - University of Central Florida\ESRI_GIS" # working path
TARGET_SR = arcpy.SpatialReference(32616)  # WGS 1984 UTM Zone 16N
# ─────────────────────────────────────────────────────────────────────────────

def log(msg):
    """Print to both ArcGIS message pane and stdout."""
    print(msg)
    arcpy.AddMessage(msg)

def verify_raster(raster, name):
    """Check a raster object is valid and has data. Raises if not."""
    if raster is None:
        raise ValueError(f"{name} is None — step did not produce output.")
    try:
        mn   = float(arcpy.GetRasterProperties_management(raster, "MINIMUM").getOutput(0))
        mx   = float(arcpy.GetRasterProperties_management(raster, "MAXIMUM").getOutput(0))
        mean = float(arcpy.GetRasterProperties_management(raster, "MEAN").getOutput(0))
        log(f" Verified: min={mn:.3f}  max={mx:.3f}  mean={mean:.3f}")
        if mn == mx:
            log(f" WARNING {name} has no variation (flat raster). Check input data.")
    except Exception as e:
        raise RuntimeError(f"Could not verify {name}: {e}")

def main():
    log("=" * 55)
    log("  DEM to Drainage Area Process Starting...")
    log("=" * 55)

    # ── Preflight checks ──────────────────────────────────────
    log("\n[0/6] File Path Verification...")

    if not arcpy.Exists(DEM_PATH):
        raise FileNotFoundError(f"DEM not found: {DEM_PATH}")
    log(f"  DEM found:  {DEM_PATH}")

    if arcpy.CheckExtension("Spatial") != "Available":
        raise RuntimeError("Spatial Analyst licence is not available.")
    arcpy.CheckOutExtension("Spatial")
    log(" Spatial Analyst: Available")

    env.workspace = WORKSPACE
    env.overwriteOutput = True
    log(f" Workspace:  {WORKSPACE}")

    src_sr = arcpy.Describe(DEM_PATH).spatialReference
    log(f"Source CRS: {src_sr.name}")
    log(f"Target CRS: {TARGET_SR.name} (EPSG {TARGET_SR.factoryCode})")
    log("Preflight OK.\n")

    # ── Step 1: Project to UTM Zone 16N ──────────────────────
    log("[1/6] Projecting DEM to UTM Zone 16N...")
    arcpy.management.ProjectRaster(
        in_raster       = DEM_PATH,
        out_raster      = PROJ_DEM,
        out_coor_system = TARGET_SR,
        resampling_type = "BILINEAR",
        cell_size       = ""
    )
    if not arcpy.Exists(PROJ_DEM):
        raise RuntimeError(f"Projection failed — output not found: {PROJ_DEM}")
    proj_desc = arcpy.Describe(PROJ_DEM)
    x_size    = proj_desc.meanCellWidth
    y_size    = proj_desc.meanCellHeight
    log(f"      Output CRS:      {proj_desc.spatialReference.name}")
    log(f"      Projected cell size: {x_size:.4f} × {y_size:.4f} m")
    log("      Projection complete.\n")

    # ── Step 2: Fill sinks ────────────────────────────────────
    log("[2/6] Filling sinks...")
    filled = Fill(PROJ_DEM)
    if filled is None:
        raise RuntimeError("Fill() returned an empty raster.")
    verify_raster(filled, "Filled DEM")
    log("      Fill complete.\n")

    # ── Step 3: Flow direction ────────────────────────────────
    log("[3/6] Computing flow direction (D8)...")
    flowdir = FlowDirection(filled)
    verify_raster(flowdir, "Flow direction")
    valid_codes = {1, 2, 4, 8, 16, 32, 64, 128}
    fd_min = int(arcpy.GetRasterProperties_management(flowdir, "MINIMUM").getOutput(0))
    fd_max = int(arcpy.GetRasterProperties_management(flowdir, "MAXIMUM").getOutput(0))
    if fd_min not in valid_codes or fd_max not in valid_codes:
        log(f"WARNING — unexpected direction codes: min={fd_min}, max={fd_max}. "
             "Check for flat areas or no-data edges.")
    else:
        log(f"Direction codes look valid (range {fd_min}–{fd_max}).")
    log("Flow direction complete.\n")

    # ── Step 4: Flow accumulation ─────────────────────────────
    log("[4/6] Computing flow accumulation...")
    flowacc = FlowAccumulation(flowdir)
    verify_raster(flowacc, "Flow accumulation")
    acc_max = float(arcpy.GetRasterProperties_management(flowacc, "MAXIMUM").getOutput(0))
    if acc_max < 1:
        log(" WARNING — max accumulation < 1. Flow direction may be incorrect.")
    else:
        log(f" Max upstream cells: {acc_max:,.0f}")
    log("Flow accumulation complete.\n")

    # ── Step 5: Compute drainage area ─────────────────────────
    log("[5/6] Computing drainage area...")
    cell_area = x_size * y_size
    log(f"Cell area:  {cell_area:.4f} m²")
    drainage = Times(flowacc, cell_area)
    verify_raster(drainage, "Drainage area")
    log("Drainage area complete.\n")

    # ── Step 6: Save output ───────────────────────────────────
    log("[6/6] Saving output raster...")
    drainage.save(OUT_PATH)

    if not arcpy.Exists(OUT_PATH):
        raise RuntimeError(f"Save appeared to succeed but file not found: {OUT_PATH}")

    result = arcpy.Describe(OUT_PATH)
    out_mn = float(arcpy.GetRasterProperties_management(OUT_PATH, "MINIMUM").getOutput(0))
    out_mx = float(arcpy.GetRasterProperties_management(OUT_PATH, "MAXIMUM").getOutput(0))
    log(f"File:        {result.file}")
    log(f"Directory:   {WORKSPACE}")
    log(f"Value range: {out_mn:,.2f} – {out_mx:,.2f} m²")
    log("Output saved and verified.\n")

    # ── Summary ───────────────────────────────────────────────
    log("=" * 55)
    log("  All 6 steps completed successfully.")
    log("  No steps were skipped.")
    log("=" * 55)

    arcpy.CheckInExtension("Spatial")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("\n*** ERROR — processing stopped. Details below: ***")
        log(traceback.format_exc())
        arcpy.CheckInExtension("Spatial")
        sys.exit(1)

