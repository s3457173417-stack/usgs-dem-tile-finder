# -*- coding: utf-8 -*-
"""Pure-Python helpers for US USGS 3DEP DEM tile naming (1m, 10m, 30m) and version selection."""

import math
import re
from collections import defaultdict

TILE_SIZE = 10000.0

MODE_AUTO = "auto"
MODE_USGS_1M = "usgs_1m"
MODE_USGS_10M = "usgs_10m"
MODE_USGS_30M = "usgs_30m"

TILE_RE = re.compile(r"(?<![A-Za-z0-9])x\s*0*(\d{1,3})\s*y\s*0*(\d{2,4})(?!\d)", re.IGNORECASE)
NED_TILE_RE = re.compile(r"(?<![A-Za-z0-9])([ns])(\d{2})([ew])(\d{3})(?![A-Za-z0-9])", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")


def tile_index(easting, northing):
    """
    Return USGS legacy 1 m DEM 10 km tile name index (x, y).

    The x index is based on the western/left 10 km easting boundary.
    The y index identifies the northern/top 10 km northing boundary.

    Example:
        E = 425000, N = 3745000  -> x42y375
        x42y375 spans approximately:
        E 420000..430000, N 3740000..3750000
    """
    x = int(math.floor(float(easting) / TILE_SIZE))
    y = int(math.floor(float(northing) / TILE_SIZE)) + 1
    return x, y


def deg_tile_index(lon, lat):
    """
    Return 1x1 degree tile index (ix, iy) where:
        ix = floor(lon)  (west boundary in degrees, -180..179)
        iy = floor(lat)  (south boundary in degrees, -90..89)
    """
    ix = max(-180, min(179, int(math.floor(float(lon)))))
    iy = max(-90, min(89, int(math.floor(float(lat)))))
    return ix, iy


def tile_name(ix, iy, mode=MODE_USGS_1M):
    ix = int(ix)
    iy = int(iy)
    if mode in (MODE_USGS_10M, MODE_USGS_30M):
        # USGS 1/3 arc-sec (10m) and 1 arc-sec (30m) 1x1 degree tiles (e.g. n34w112)
        # use the NORTH-WEST corner: north_lat = iy + 1, west_lon = ix
        north_lat = iy + 1
        ns = "n" if north_lat >= 0 else "s"
        ew = "e" if ix >= 0 else "w"
        return f"{ns}{abs(north_lat):02d}{ew}{abs(ix):03d}"
    return f"x{ix}y{iy}"


def tile_bounds(ix, iy, mode=MODE_USGS_1M):
    """
    Bounds for a tile in its native grid CRS:
    - MODE_USGS_1M: UTM meters (xmin, ymin, xmax, ymax)
    - MODE_USGS_10M / MODE_USGS_30M: WGS84 degrees (xmin, ymin, xmax, ymax)
    """
    if mode in (MODE_USGS_10M, MODE_USGS_30M):
        xmin = float(int(ix))
        ymin = float(int(iy))
        return xmin, ymin, xmin + 1.0, ymin + 1.0

    xmin = int(ix) * TILE_SIZE
    xmax = xmin + TILE_SIZE
    ymax = int(iy) * TILE_SIZE
    ymin = ymax - TILE_SIZE
    return xmin, ymin, xmax, ymax


def parse_tile_from_title(title, mode=MODE_USGS_1M):
    if not title:
        return None
    s = str(title)
    if mode in (MODE_USGS_10M, MODE_USGS_30M):
        m = NED_TILE_RE.search(s)
        if not m:
            return None
        ns = 1 if m.group(1).lower() == "n" else -1
        north_lat = ns * int(m.group(2))
        iy = north_lat - 1
        ew = 1 if m.group(3).lower() == "e" else -1
        ix = ew * int(m.group(4))
        return ix, iy

    m = TILE_RE.search(s)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_tile_identifier(text):
    """Parse any USGS tile identifier ('x42y375' or 'n34w112') to (ix, iy)."""
    if not text:
        return None
    s = str(text).strip()
    for mode in (MODE_USGS_10M, MODE_USGS_1M):
        res = parse_tile_from_title(s, mode=mode)
        if res is not None:
            return res
    return None


def project_tail(title, mode=MODE_USGS_1M):
    """Return the part after tile identifier; normally the collection/project/date name."""
    if not title:
        return ""
    s = str(title).strip()
    regex = NED_TILE_RE if mode in (MODE_USGS_10M, MODE_USGS_30M) else TILE_RE
    m = regex.search(s)
    if m:
        tail = s[m.end():].strip(" _-")
        if tail:
            return tail
    return regex.sub("", s).strip(" _-")


def project_key(title, mode=MODE_USGS_1M):
    tail = project_tail(title, mode=mode)
    return re.sub(r"[\s_-]+", "_", tail.lower()).strip("_")


def extract_year(text):
    s = str(text or "")
    years = [int(x) for x in YEAR_RE.findall(s)]
    if years:
        return max(years)
    m = re.search(r"\b(20\d{2})\d{4}\b", s)
    return int(m.group(1)) if m else 0


def _date_score(value):
    """Turn common ISO-ish or YYYYMMDD timestamps into a sortable integer."""
    if not value:
        return 0
    s = str(value).strip()
    m = re.search(r"(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?", s)
    if m:
        y = int(m.group(1))
        mo = int(m.group(2))
        d = int(m.group(3) or 1)
        return y * 10000 + mo * 100 + d
    m = re.search(r"\b(20\d{2})(\d{2})(\d{2})\b", s)
    if m:
        return int(m.group(1)) * 10000 + int(m.group(2)) * 100 + int(m.group(3))
    m = re.search(r"\b(20\d{2})\b", s)
    return int(m.group(1)) * 10000 + 101 if m else 0


def normalize_product(raw, mode=MODE_USGS_1M):
    title = (
        raw.get("title")
        or raw.get("name")
        or raw.get("productTitle")
        or ""
    )
    tile = parse_tile_from_title(title, mode=mode)
    download = (
        raw.get("downloadURL")
        or raw.get("downloadUrl")
        or raw.get("download_url")
        or raw.get("url")
        or ""
    )
    info = (
        raw.get("moreInfo")
        or raw.get("metaUrl")
        or raw.get("metadataURL")
        or raw.get("metadataUrl")
        or ""
    )
    updated = raw.get("lastUpdated") or raw.get("modified") or raw.get("updated") or ""
    published = raw.get("publicationDate") or raw.get("published") or raw.get("date") or ""
    return {
        "raw": raw,
        "title": str(title),
        "tile": tile,
        "project_tail": project_tail(title, mode=mode),
        "project_key": project_key(title, mode=mode),
        "year": extract_year(title) or extract_year(published) or extract_year(updated),
        "updated": str(updated),
        "published": str(published),
        "date_score": max(_date_score(updated), _date_score(published), _date_score(title)),
        "download_url": str(download),
        "info_url": str(info),
        "format": str(raw.get("format") or raw.get("productFormat") or "GeoTIFF"),
        "size": raw.get("sizeInBytes") or raw.get("size") or 0,
    }


def choose_recommendations(products_by_tile, required_tiles):
    """
    Pick a consistent collection/project where possible.

    1) maximize coverage of required tiles by same project key
    2) prefer newer project year
    3) prefer newer publication/update date
    4) for tiles missing from winning project, fall back to best local product
    """
    required_tiles = set(required_tiles)
    coverage = defaultdict(set)
    project_best_year = defaultdict(int)
    project_best_date = defaultdict(int)

    for tile, products in products_by_tile.items():
        for p in products:
            key = p.get("project_key") or ""
            if not key:
                continue
            if tile in required_tiles:
                coverage[key].add(tile)
            project_best_year[key] = max(project_best_year[key], int(p.get("year") or 0))
            project_best_date[key] = max(project_best_date[key], int(p.get("date_score") or 0))

    winning_key = ""
    if coverage:
        winning_key = max(
            coverage.keys(),
            key=lambda k: (
                len(coverage[k]),
                project_best_year[k],
                project_best_date[k],
                k,
            ),
        )

    recommendations = {}
    for tile, products in products_by_tile.items():
        if not products:
            recommendations[tile] = None
            continue
        matching = [p for p in products if winning_key and p.get("project_key") == winning_key]
        pool = matching if matching else products
        recommendations[tile] = max(
            pool,
            key=lambda p: (
                int(p.get("year") or 0),
                int(p.get("date_score") or 0),
                bool(p.get("download_url")),
                p.get("title") or "",
            ),
        )

    return winning_key, recommendations, coverage


def relation_name(ix, iy, anchor_ix, anchor_iy):
    dx = int(ix) - int(anchor_ix)
    dy = int(iy) - int(anchor_iy)
    if dx == 0 and dy == 0:
        return "中心"
    if dx > 0 and dy > 0:
        name = "东北"
    elif dx < 0 and dy > 0:
        name = "西北"
    elif dx > 0 and dy < 0:
        name = "东南"
    elif dx < 0 and dy < 0:
        name = "西南"
    elif dx > 0:
        name = "东"
    elif dx < 0:
        name = "西"
    elif dy > 0:
        name = "北"
    else:
        name = "南"
    if abs(dx) > 1 or abs(dy) > 1:
        name += f" ({dx:+d},{dy:+d})"
    return name
