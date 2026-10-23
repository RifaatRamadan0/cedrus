"""Shared settings. Changing BOX or CELL changes the test — see docs/TEST_PLAN.md."""
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

# Mainland Portugal: lon_min, lat_min, lon_max, lat_max (drops Azores and Madeira)
BOX = (-9.6, 36.9, -6.1, 42.2)
CELL = 0.25  # degrees
NX = int(round((BOX[2] - BOX[0]) / CELL))


def cell_of(lon, lat):
    ix = np.floor((np.asarray(lon) - BOX[0]) / CELL).astype(int)
    iy = np.floor((np.asarray(lat) - BOX[1]) / CELL).astype(int)
    return iy * NX + ix


def cell_bounds(cell):
    iy, ix = divmod(int(cell), NX)
    lon = BOX[0] + ix * CELL
    lat = BOX[1] + iy * CELL
    return lon, lat, lon + CELL, lat + CELL
