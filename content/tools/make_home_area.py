#!/usr/bin/env python3
"""Writes the map's optional home-area highlight from a US county's Census boundary.
Usage: make_home_area.py GEOID [--label "Waseca County"]
GEOID is the 5-digit county FIPS code, for example 27161. The boundary comes from
the US Census Bureau's TIGERweb service, which is public domain. The result goes to
portal/src/data/home-area.geojson, which is kept out of git so it stays local."""
import argparse
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

SERVICE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query"
OUT = Path(__file__).resolve().parents[2] / "portal" / "src" / "data" / "home-area.geojson"


def centroid(ring):
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    return [round(cx / (6 * area), 5), round(cy / (6 * area), 5)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("geoid", help="5-digit county FIPS code, like 27161")
    parser.add_argument("--label", help="button and map label (default: the county's name)")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{5}", args.geoid):
        parser.error("GEOID must be 5 digits, like 27161.")
    query = urllib.parse.urlencode({"where": f"GEOID='{args.geoid}'", "outFields": "NAME,GEOID", "outSR": "4326", "f": "geojson"})
    request = urllib.request.Request(f"{SERVICE}?{query}", headers={"User-Agent": "killday-build"})
    with urllib.request.urlopen(request, timeout=60) as response:
        features = json.load(response).get("features", [])
    if not features:
        raise SystemExit(f"No county with GEOID {args.geoid}.")
    feature = features[0]
    name = args.label or feature["properties"]["NAME"]
    geometry = feature["geometry"]
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    rounded = [[[[round(x, 5), round(y, 5)] for x, y in ring] for ring in polygon] for polygon in polygons]
    points = [p for polygon in rounded for ring in polygon for p in ring]
    largest = max(rounded, key=lambda polygon: len(polygon[0]))[0]
    home = {
        "type": "FeatureCollection",
        "name": name,
        "source": f"US Census Bureau TIGERweb, county GEOID {args.geoid}. US government work, public domain.",
        "bbox": [min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)],
        "features": [
            {"type": "Feature", "properties": {"kind": "area", "name": name}, "geometry": {"type": "MultiPolygon", "coordinates": rounded}},
            {"type": "Feature", "properties": {"kind": "label", "name": name.upper()}, "geometry": {"type": "Point", "coordinates": centroid(largest)}},
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(home, separators=(",", ":")))
    print(f"Wrote {OUT} for {name}. Rebuild the library to put it on a stick.")


if __name__ == "__main__":
    main()
