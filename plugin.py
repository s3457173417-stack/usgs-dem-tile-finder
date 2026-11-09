# -*- coding: utf-8 -*-

import json
import math
import os
import re
from pathlib import Path

from qgis.PyQt.QtCore import Qt, QUrl, QUrlQuery, QVariant, QSettings
from qgis.PyQt.QtGui import QColor, QDesktopServices, QIcon
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.PyQt.QtWidgets import QAction, QApplication, QFileDialog, QTableWidgetItem

from qgis.core import (
    Qgis,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFileDownloader,
    QgsFillSymbol,
    QgsGeometry,
    QgsHillshadeRenderer,
    QgsNetworkAccessManager,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsRendererCategory,
    QgsRasterLayer,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.gui import QgsMapToolEmitPoint

from .core_logic import (
    MODE_AUTO,
    MODE_USGS_10M,
    MODE_USGS_1M,
    MODE_USGS_30M,
    TILE_SIZE,
    choose_recommendations,
    deg_tile_index,
    normalize_product,
    parse_tile_from_title,
    parse_tile_identifier,
    tile_bounds,
    tile_index,
    tile_name,
)
from .dock import FinderDock


API_URL = "https://tnmaccess.nationalmap.gov/api/v1/products"
DATASET_1M = "Digital Elevation Model (DEM) 1 meter"
DATASET_10M = "National Elevation Dataset (NED) 1/3 arc-second Current"
DATASET_30M = "National Elevation Dataset (NED) 1 arc-second Current"
LAYER_NAME = "USGS 3DEP DEM Tiles"


class USGSDEMTileFinderPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.action = None
        self.dock = None
        self.map_tool = None
        self.previous_map_tool = None

        self.active_mode = MODE_USGS_1M
        self._auto_fallback_stage = 0
        self._last_input_kind = None
        self._last_wgs84_lonlat = None
        self._last_geom = None
        self._last_geom_crs = None

        self.utm_crs = None
        self.utm_zone = None
        self.anchor_tile = None
        self.required_tiles = set()
        self.display_tiles = set()
        self.products_by_tile = {}
        self.recommendations = {}
        self.winning_project = ""
        self.tile_layer_id = None
        self.downloaders = []
        self.download_targets = {}
        self.download_progress = {}
        self.download_completed_paths = set()
        self.download_folder = ""
        self.download_total_files = 0
        self._zoom_to_result = True

        self.settings = QSettings()
        self.lang = self.settings.value("USGSDEMTileFinder/ui_lang", "en", type=str)
        if self.lang not in ("en", "zh", "es", "fr"):
            self.lang = "en"
        default_cache = str(Path.home() / "Documents" / "USGS_DEM")
        self.cache_dir = self.settings.value(
            "USGSDEMTileFinder/cache_dir",
            default_cache,
            type=str,
        )
        self.local_product_paths = {}
        self.local_files_by_tile = {}
        self._valid_raster_cache = {}
        self.last_source_layer_id = None

    # ---------------- QGIS plugin lifecycle ----------------

    def initGui(self):
        self.action = QAction(
            QIcon(":/images/themes/default/mActionAddRasterLayer.svg"),
            "USGS 3DEP DEM Tile Finder",
            self.iface.mainWindow(),
        )
        self.action.triggered.connect(self.show_dock)
        self.iface.addPluginToRasterMenu("&USGS DEM Tile Finder", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginRasterMenu("&USGS DEM Tile Finder", self.action)
            self.iface.removeToolBarIcon(self.action)
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None
        self._remove_tile_layer()

    def show_dock(self):
        if self.dock is None:
            self.dock = FinderDock(self.iface.mainWindow())
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

            self.dock.pick_btn.clicked.connect(self.activate_pick_point)
            self.dock.extent_btn.clicked.connect(self.use_canvas_extent)
            self.dock.layer_btn.clicked.connect(self.use_active_layer_extent)
            self.dock.basemap_btn.clicked.connect(self.add_us_basemap)
            self.dock.source_combo.currentIndexChanged.connect(self._on_source_mode_changed)
            self.dock.query_btn.clicked.connect(self.query_usgs)
            self.dock.zoom_btn.clicked.connect(self.zoom_to_tiles)
            self.dock.open_btn.clicked.connect(self.open_selected_product)
            self.dock.download_btn.clicked.connect(self.download_checked)
            self.dock.clear_btn.clicked.connect(self.clear_results)
            self.dock.table.itemSelectionChanged.connect(self.update_details)
            self.dock.lang_combo.currentIndexChanged.connect(self._on_language_changed)
            self.dock.cancel_download_btn.clicked.connect(self.cancel_all_downloads)
            self.dock.change_cache_btn.clicked.connect(self.choose_cache_directory)
            self.dock.clean_partial_btn.clicked.connect(self.clean_incomplete_files)
            self.dock.refresh_local_btn.clicked.connect(self.refresh_local_status)
            self.dock.import_required_btn.clicked.connect(self.import_required_local_dems)
            self.dock.import_checked_btn.clicked.connect(self.import_checked_local_dems)
            self.dock.set_language(self.lang)
            self._ensure_cache_dir()
            self.dock.cache_path_edit.setText(self.cache_dir)
            self.clean_incomplete_files(silent=True)

            self.dock.setFloating(False)
            self.dock.apply_best_size()

        self.dock.show()
        self.dock.raise_()

    # ---------------- Language ----------------

    def _on_language_changed(self, _idx=0):
        if not self.dock:
            return
        lang = self.dock.lang_combo.currentData() or "en"
        self.lang = lang
        self.settings.setValue("USGSDEMTileFinder/ui_lang", self.lang)
        self.dock.set_language(self.lang)
        if self.display_tiles:
            self._update_tile_layer_attributes()
            state = self._tr("queried") if self.recommendations else self._tr("not_queried")
            self._populate_table(query_state=state)
            self._refresh_summary_status()
            self.update_details()

    def toggle_language(self):
        order = ["en", "zh", "es", "fr"]
        nxt = order[(order.index(self.lang) + 1) % len(order)] if self.lang in order else "en"
        self.lang = nxt
        self.settings.setValue("USGSDEMTileFinder/ui_lang", self.lang)
        if self.dock:
            self.dock.set_language(self.lang)
        if self.display_tiles:
            self._update_tile_layer_attributes()
            state = self._tr("queried") if self.recommendations else self._tr("not_queried")
            self._populate_table(query_state=state)
            self._refresh_summary_status()
            self.update_details()

    def _tr(self, key):
        packs = {
            "en": {
                "center": "Center",
                "north": "North",
                "south": "South",
                "east": "East",
                "west": "West",
                "northeast": "Northeast",
                "northwest": "Northwest",
                "southeast": "Southeast",
                "southwest": "Southwest",
                "required": "Required",
                "neighbor": "Neighbor",
                "available": "Downloadable",
                "products_no_url": "Version found, no URL",
                "not_queried": "Not queried",
                "queried": "Queried",
                "api_failed": "API failed",
                "versions": "Available versions",
                "recommended": "★ Recommended",
                "full_name": "Full name",
                "published": "Published",
                "updated": "Updated",
                "size_label": "File size",
                "direct_download": "Direct download",
                "metadata": "Metadata / Info",
                "no_product": "No matching USGS DEM product was found for this tile, or the API has not been queried yet.",
                "utm_zone": "UTM Zone",
                "tile_detail": "Selected tile details",
            },
            "zh": {
                "center": "中心",
                "north": "北",
                "south": "南",
                "east": "东",
                "west": "西",
                "northeast": "东北",
                "northwest": "西北",
                "southeast": "东南",
                "southwest": "西南",
                "required": "必须下载",
                "neighbor": "周边参考",
                "available": "可下载",
                "products_no_url": "有版本但无下载URL",
                "not_queried": "未查询",
                "queried": "已查询",
                "api_failed": "API查询失败",
                "versions": "可用版本",
                "recommended": "★ 推荐",
                "full_name": "完整名称",
                "published": "发布",
                "updated": "更新",
                "size_label": "文件大小",
                "direct_download": "直接下载",
                "metadata": "元数据/信息",
                "no_product": "当前瓦片没有匹配到 USGS DEM 产品，或尚未执行 API 查询。",
                "utm_zone": "UTM Zone",
                "tile_detail": "选中瓦片详情",
            },
            "es": {
                "center": "Centro",
                "north": "Norte",
                "south": "Sur",
                "east": "Este",
                "west": "Oeste",
                "northeast": "Noreste",
                "northwest": "Noroeste",
                "southeast": "Sureste",
                "southwest": "Suroeste",
                "required": "Requerido",
                "neighbor": "Vecino",
                "available": "Descargable",
                "products_no_url": "Sin URL",
                "not_queried": "No consultado",
                "queried": "Consultado",
                "api_failed": "Fallo API",
                "versions": "Versiones disponibles",
                "recommended": "★ Recomendado",
                "full_name": "Nombre completo",
                "published": "Publicado",
                "updated": "Actualizado",
                "size_label": "Tamaño",
                "direct_download": "Descarga directa",
                "metadata": "Metadatos / Info",
                "no_product": "No se encontró ningún producto USGS DEM para esta celda o aún no se ha consultado la API.",
                "utm_zone": "Zona UTM",
                "tile_detail": "Detalles de celda",
            },
            "fr": {
                "center": "Centre",
                "north": "Nord",
                "south": "Sud",
                "east": "Est",
                "west": "Ouest",
                "northeast": "Nord-Est",
                "northwest": "Nord-Ouest",
                "southeast": "Sud-Est",
                "southwest": "Sud-Ouest",
                "required": "Requis",
                "neighbor": "Voisin",
                "available": "Téléchargeable",
                "products_no_url": "Sans URL",
                "not_queried": "Non interrogé",
                "queried": "Interrogé",
                "api_failed": "Échec API",
                "versions": "Versions disponibles",
                "recommended": "★ Recommandé",
                "full_name": "Nom complet",
                "published": "Publié",
                "updated": "Mis à jour",
                "size_label": "Taille",
                "direct_download": "Téléchargement direct",
                "metadata": "Métadonnées / Info",
                "no_product": "Aucun produit USGS DEM trouvé pour cette dalle, ou l'API n'a pas encore été interrogée.",
                "utm_zone": "Zone UTM",
                "tile_detail": "Détails de la dalle",
            },
        }
        pack = packs.get(self.lang, packs["en"])
        return pack.get(key, packs["en"].get(key, key))

    def _mode_label(self, mode=None):
        m = mode or self.active_mode
        if self.lang == "en":
            return {
                MODE_USGS_1M: "USGS 1m DEM (10km UTM)",
                MODE_USGS_10M: "USGS 10m DEM (1/3 arc-sec, 1°×1°)",
                MODE_USGS_30M: "USGS 30m DEM (1 arc-sec, 1°×1°)",
            }.get(m, m)
        return {
            MODE_USGS_1M: "USGS 1m DEM (10km UTM)",
            MODE_USGS_10M: "USGS 10m DEM (1/3 arc-sec, 1°×1°)",
            MODE_USGS_30M: "USGS 30m DEM (1 arc-sec, 1°×1°)",
        }.get(m, m)

    def _dataset_for_mode(self, mode=None):
        m = mode or self.active_mode
        if m == MODE_USGS_10M:
            return DATASET_10M
        if m == MODE_USGS_30M:
            return DATASET_30M
        return DATASET_1M

    def _layer_title_for_mode(self):
        return {
            MODE_USGS_1M: "USGS 1m DEM Tiles",
            MODE_USGS_10M: "USGS 10m DEM Tiles (1°×1°)",
            MODE_USGS_30M: "USGS 30m DEM Tiles (1°×1°)",
        }.get(self.active_mode, LAYER_NAME)

    def _relation_localized(self, ix, iy):
        ax, ay = self.anchor_tile
        dx = int(ix) - int(ax)
        dy = int(iy) - int(ay)
        if dx == 0 and dy == 0:
            name = self._tr("center")
        elif dx > 0 and dy > 0:
            name = self._tr("northeast")
        elif dx < 0 and dy > 0:
            name = self._tr("northwest")
        elif dx > 0 and dy < 0:
            name = self._tr("southeast")
        elif dx < 0 and dy < 0:
            name = self._tr("southwest")
        elif dx > 0:
            name = self._tr("east")
        elif dx < 0:
            name = self._tr("west")
        elif dy > 0:
            name = self._tr("north")
        else:
            name = self._tr("south")
        if abs(dx) > 1 or abs(dy) > 1:
            name += f" ({dx:+d},{dy:+d})"
        return name

    def _refresh_summary_status(self):
        if not self.dock or not self.display_tiles:
            return
        mode_desc = self._mode_label()
        if self.recommendations:
            available = sum(1 for t in self.display_tiles if self.products_by_tile.get(t))
            req_available = sum(1 for t in self.required_tiles if self.products_by_tile.get(t))
            project_label = self._winning_project_label()
            if self.lang == "en":
                text = (
                    f"[{mode_desc}] UTM Zone {self.utm_zone}: {len(self.required_tiles)} required tile(s), "
                    f"{len(self.display_tiles)} shown. USGS matched {available}/{len(self.display_tiles)} tiles; "
                    f"required tiles with data: {req_available}/{len(self.required_tiles)}."
                )
                if project_label:
                    text += f" Recommended collection: {project_label}."
            else:
                text = (
                    f"【{mode_desc}】UTM Zone {self.utm_zone}：所需 {len(self.required_tiles)} 块，"
                    f"当前显示 {len(self.display_tiles)} 块。USGS 匹配 {available}/{len(self.display_tiles)} 块；"
                    f"所需瓦片有数据 {req_available}/{len(self.required_tiles)}。"
                )
                if project_label:
                    text += f" 推荐项目组合：{project_label}。"
        else:
            req = ", ".join(tile_name(t[0], t[1], self.active_mode) for t in sorted(self.required_tiles))
            if self.lang == "en":
                text = (
                    f"[{mode_desc}] UTM Zone {self.utm_zone}: {len(self.required_tiles)} required tile(s), "
                    f"{len(self.display_tiles)} shown. Required: {req}"
                )
            else:
                text = (
                    f"【{mode_desc}】UTM Zone {self.utm_zone}：所需 {len(self.required_tiles)} 块，"
                    f"当前显示 {len(self.display_tiles)} 块。所需：{req}"
                )
        self.dock.set_status(text)

    # ---------------- Source mode & input selection ----------------

    def _resolve_mode(self, forced_mode=None):
        if forced_mode:
            return forced_mode
        selected = self.dock.current_source_mode() if self.dock else MODE_AUTO
        if selected != MODE_AUTO:
            return selected
        return MODE_USGS_1M

    def _on_source_mode_changed(self, _idx=0):
        if not self.display_tiles or not self._last_input_kind:
            return
        self._auto_fallback_stage = 0
        if self._last_input_kind == "point" and self._last_wgs84_lonlat:
            lon, lat = self._last_wgs84_lonlat
            self._build_tiles_from_wgs84_point(lon, lat)
        elif self._last_input_kind == "geom" and self._last_geom and self._last_geom_crs:
            self._build_tiles_from_geometry(self._last_geom, self._last_geom_crs)

    def activate_pick_point(self):
        self._zoom_to_result = False
        self.previous_map_tool = self.canvas.mapTool()
        self.map_tool = QgsMapToolEmitPoint(self.canvas)
        self.map_tool.canvasClicked.connect(self._point_clicked)
        self.canvas.setMapTool(self.map_tool)
        msg = (
            "Click a location on the map. Its DEM tile will be used as the center."
            if self.lang == "en"
            else "请在地图上单击一个位置。该位置所在 Tile 将作为中心。"
        )
        self.dock.set_status(msg)
        self.iface.messageBar().pushMessage(
            "USGS DEM Tile Finder",
            msg,
            level=Qgis.Info,
            duration=4,
        )

    def _point_clicked(self, point, button):
        if button != Qt.LeftButton:
            return
        try:
            wgs84_point = self._transform_point(
                point,
                self.canvas.mapSettings().destinationCrs(),
                QgsCoordinateReferenceSystem("EPSG:4326"),
            )
            lon, lat = wgs84_point.x(), wgs84_point.y()
            self._last_input_kind = "point"
            self._last_wgs84_lonlat = (lon, lat)
            self._auto_fallback_stage = 0
            self._build_tiles_from_wgs84_point(lon, lat)
        except Exception as exc:
            self._error(str(exc))
        finally:
            if self.previous_map_tool:
                self.canvas.setMapTool(self.previous_map_tool)

    def _build_tiles_from_wgs84_point(self, lon, lat, forced_mode=None):
        self.active_mode = self._resolve_mode(forced_mode=forced_mode)
        r = self.dock.radius_spin.value() if self.dock else 1

        if self.active_mode == MODE_USGS_1M:
            self._setup_utm_from_lonlat(lon, lat)
            utm_point = self._transform_point(
                QgsPointXY(lon, lat),
                QgsCoordinateReferenceSystem("EPSG:4326"),
                self.utm_crs,
            )
            ix, iy = tile_index(utm_point.x(), utm_point.y())
            self.anchor_tile = (ix, iy)
            self.required_tiles = {(ix, iy)}
            self.display_tiles = {
                (x, y)
                for x in range(ix - r, ix + r + 1)
                for y in range(iy - r, iy + r + 1)
            }
        else:
            if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                raise ValueError("无法从当前坐标确定有效经纬度。")
            self.utm_zone = self._utm_zone_for_lon(lon)
            self.utm_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            ix, iy = deg_tile_index(lon, lat)
            self.anchor_tile = (ix, iy)
            self.required_tiles = {(ix, iy)}
            self.display_tiles = {
                (x, y)
                for x in range(max(-180, ix - r), min(179, ix + r) + 1)
                for y in range(max(-90, iy - r), min(89, iy + r) + 1)
            }

        self._after_tiles_built()

    def add_us_basemap(self):
        basemap_name = "Esri World Imagery (Satellite)"
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == basemap_name:
                return
        uri = (
            "type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/%7Bz%7D/%7By%7D/%7Bx%7D&zmax=19&zmin=0"
        )
        layer = QgsRasterLayer(uri, basemap_name, "wms")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer, False)
            QgsProject.instance().layerTreeRoot().insertLayer(-1, layer)
            self.canvas.refresh()
            if self.dock:
                self.dock.set_status(
                    "Added Esri World Imagery satellite basemap."
                    if self.lang == "en"
                    else "已在底层加载 Esri World Imagery 高清卫星底图。"
                )

    def use_active_layer_extent(self):
        self._zoom_to_result = True
        target = self.iface.activeLayer()
        tile_layer = QgsProject.instance().mapLayer(self.tile_layer_id) if self.tile_layer_id else None
        if target is None or target == tile_layer or not isinstance(target, QgsVectorLayer):
            # Look for the most recently added Parcel or polygon vector layer in the project
            target = None
            for lyr in reversed(list(QgsProject.instance().mapLayers().values())):
                if lyr == tile_layer or not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
                    continue
                target = lyr
                break

        if target is None or not target.isValid():
            self._warn(
                "Please load or select a Parcel / vector layer first."
                if self.lang == "en"
                else "请先加载或选择一个 Parcel 地块/矢量图层。"
            )
            return

        rect = target.boundingBoxOfSelected() if target.selectedFeatureCount() > 0 else target.extent()
        if rect.isEmpty():
            self._warn(
                "The selected layer has an empty extent."
                if self.lang == "en"
                else "所选图层范围为空。"
            )
            return

        geom = QgsGeometry.fromRect(rect)
        src_crs = target.crs()
        self._last_input_kind = "geom"
        self._last_geom = QgsGeometry(geom)
        self._last_geom_crs = src_crs
        self._auto_fallback_stage = 0
        self._build_tiles_from_geometry(geom, src_crs)

    def use_canvas_extent(self):
        self._zoom_to_result = False
        rect = self.canvas.extent()
        geom = QgsGeometry.fromRect(rect)
        src_crs = self.canvas.mapSettings().destinationCrs()
        self._last_input_kind = "geom"
        self._last_geom = QgsGeometry(geom)
        self._last_geom_crs = src_crs
        self._auto_fallback_stage = 0
        self._build_tiles_from_geometry(geom, src_crs)

    def _build_tiles_from_geometry(self, geom, src_crs, forced_mode=None):
        try:
            wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
            geom_wgs = QgsGeometry(geom)
            if src_crs != wgs84:
                geom_wgs.transform(QgsCoordinateTransform(src_crs, wgs84, QgsProject.instance()))
            c = geom_wgs.centroid().asPoint()
            self.active_mode = self._resolve_mode(forced_mode=forced_mode)

            if self.active_mode == MODE_USGS_1M:
                self._setup_utm_from_lonlat(c.x(), c.y())

                bb_wgs = geom_wgs.boundingBox()
                zones = {
                    self._utm_zone_for_lon(bb_wgs.xMinimum()),
                    self._utm_zone_for_lon(bb_wgs.xMaximum()),
                    self._utm_zone_for_lon(c.x()),
                }
                if len(zones) > 1:
                    self.iface.messageBar().pushMessage(
                        "USGS DEM Tile Finder",
                        "提示：区域跨越多个 UTM Zone（如亚利桑那州 Zone 11 / Zone 12 交界）。当前 1m 模式按中心所在分带计算；大范围分析可切换为 10m / 30m (1°×1°) 模式。",
                        level=Qgis.Warning,
                        duration=10,
                    )

                geom_utm = QgsGeometry(geom)
                geom_utm.transform(QgsCoordinateTransform(src_crs, self.utm_crs, QgsProject.instance()))
                bb = geom_utm.boundingBox()
                eps = 1e-7
                minx = int(math.floor(bb.xMinimum() / TILE_SIZE))
                maxx = int(math.floor((bb.xMaximum() - eps) / TILE_SIZE))
                miny = int(math.floor(bb.yMinimum() / TILE_SIZE)) + 1
                maxy = int(math.floor((bb.yMaximum() - eps) / TILE_SIZE)) + 1

                candidate_count = max(0, maxx - minx + 1) * max(0, maxy - miny + 1)
                if candidate_count > 400:
                    self._warn(
                        f"当前范围涉及约 {candidate_count} 个 10 km 候选瓦片，范围过大。"
                        "请缩小地图范围，或在数据精度中切换为 USGS 10m / 30m (1°×1°) 模式。"
                    )
                    return

                required = set()
                for ix in range(minx, maxx + 1):
                    for iy in range(miny, maxy + 1):
                        xmin, ymin, xmax, ymax = tile_bounds(ix, iy, mode=MODE_USGS_1M)
                        tile_geom = QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax))
                        if geom_utm.intersects(tile_geom):
                            required.add((ix, iy))

                if not required:
                    self._warn("没有计算出相交的 DEM Tile。")
                    return

                center_utm = geom_utm.centroid().asPoint()
                self.anchor_tile = tile_index(center_utm.x(), center_utm.y())
                self.required_tiles = required

                r = self.dock.radius_spin.value()
                rx = [x for x, _ in required]
                ry = [y for _, y in required]
                self.display_tiles = {
                    (x, y)
                    for x in range(min(rx) - r, max(rx) + r + 1)
                    for y in range(min(ry) - r, max(ry) + r + 1)
                }
                if len(self.display_tiles) > 400:
                    self._warn("加上周边范围后超过 400 个瓦片，请减小“额外显示周边 DEM”圈数。")
                    return
            else:
                self.utm_zone = self._utm_zone_for_lon(c.x())
                self.utm_crs = wgs84
                bb = geom_wgs.boundingBox()
                eps = 1e-9
                minx = max(-180, min(179, int(math.floor(bb.xMinimum()))))
                maxx = max(-180, min(179, int(math.floor(bb.xMaximum() - eps))))
                miny = max(-90, min(89, int(math.floor(bb.yMinimum()))))
                maxy = max(-90, min(89, int(math.floor(bb.yMaximum() - eps))))

                candidate_count = max(0, maxx - minx + 1) * max(0, maxy - miny + 1)
                if candidate_count > 144:
                    self._warn(
                        f"当前范围涉及约 {candidate_count} 个 1°×1° 候选瓦片（范围过大）。"
                        "请适当放大地图后再查询。"
                    )
                    return

                required = set()
                for ix in range(minx, maxx + 1):
                    for iy in range(miny, maxy + 1):
                        xmin, ymin, xmax, ymax = tile_bounds(ix, iy, mode=self.active_mode)
                        tile_geom = QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax))
                        if geom_wgs.intersects(tile_geom):
                            required.add((ix, iy))

                if not required:
                    self._warn("没有计算出相交的 1°×1° DEM Tile。")
                    return

                self.anchor_tile = deg_tile_index(c.x(), c.y())
                self.required_tiles = required

                r = self.dock.radius_spin.value()
                rx = [x for x, _ in required]
                ry = [y for _, y in required]
                self.display_tiles = {
                    (x, y)
                    for x in range(max(-180, min(rx) - r), min(179, max(rx) + r) + 1)
                    for y in range(max(-90, min(ry) - r), min(89, max(ry) + r) + 1)
                }
                if len(self.display_tiles) > 196:
                    self._warn("加上周边范围后超过 196 个 1°×1° 瓦片，请减小周边圈数或放大地图。")
                    return

            self._after_tiles_built()
        except Exception as exc:
            self._error(str(exc))

    # ---------------- Tile and CRS helpers ----------------

    def _utm_zone_for_lon(self, lon):
        return max(1, min(60, int(math.floor((float(lon) + 180.0) / 6.0)) + 1))

    def _setup_utm_from_lonlat(self, lon, lat):
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError("无法从当前坐标确定经纬度。")
        zone = self._utm_zone_for_lon(lon)
        epsg = 32600 + zone if lat >= 0 else 32700 + zone
        self.utm_zone = zone
        self.utm_crs = QgsCoordinateReferenceSystem(f"EPSG:{epsg}")
        if not self.utm_crs.isValid():
            raise ValueError(f"无法建立 UTM Zone {zone} 坐标系。")

    def _transform_point(self, point, src, dst):
        if src == dst:
            return QgsPointXY(point)
        tr = QgsCoordinateTransform(src, dst, QgsProject.instance())
        return tr.transform(point)

    def _after_tiles_built(self):
        self.products_by_tile = {t: [] for t in self.display_tiles}
        self.recommendations = {}
        self.winning_project = ""
        self.scan_local_cache(auto_import=False)
        self._create_tile_layer()
        self._update_tile_layer_attributes()
        self._populate_table(query_state=self._tr("not_queried"))
        self._refresh_summary_status()
        if self.dock.query_check.isChecked():
            self.query_usgs()

    # ---------------- USGS API ----------------

    def query_usgs(self):
        if not self.display_tiles or not self.utm_crs:
            self._warn("请先选择区域并生成 DEM Tile。")
            return

        dataset = self._dataset_for_mode()
        try:
            bbox = self._display_bbox_wgs84()
            url = QUrl(API_URL)
            q = QUrlQuery()
            q.addQueryItem("datasets", dataset)
            q.addQueryItem(
                "bbox",
                f"{bbox[0]:.8f},{bbox[1]:.8f},{bbox[2]:.8f},{bbox[3]:.8f}",
            )
            q.addQueryItem("prodFormats", "GeoTIFF")
            q.addQueryItem("outputFormat", "JSON")
            q.addQueryItem("max", "1000")
            url.setQuery(q)

            self.dock.set_status(
                f"Querying {self._mode_label()}…"
                if self.lang == "en"
                else f"正在查询 {self._mode_label()}…"
            )
            request = QNetworkRequest(url)
            request.setRawHeader(b"User-Agent", b"QGIS-USGS-DEM-Tile-Finder/0.4.0")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                reply = QgsNetworkAccessManager.blockingGet(request, "", True)
            finally:
                QApplication.restoreOverrideCursor()

            if reply.error() != QNetworkReply.NoError:
                msg = reply.errorString() or "未知网络错误"
                self.scan_local_cache(auto_import=False)
                self._update_tile_layer_attributes()
                self._populate_table(query_state=self._tr("api_failed"))
                self.dock.set_status(
                    "瓦片网格已生成，但 USGS API 查询失败。可稍后点击“重新查询 USGS”。"
                )
                self._warn(f"USGS TNMAccess 查询失败：{msg}")
                return

            content = bytes(reply.content()).decode("utf-8", errors="replace")
            data = json.loads(content)
            raw_items = data.get("items") or data.get("results") or data.get("products") or []

            by_tile = {t: [] for t in self.display_tiles}
            for raw in raw_items:
                p = normalize_product(raw, mode=self.active_mode)
                tile = p.get("tile")
                if tile in by_tile:
                    by_tile[tile].append(p)

            self.products_by_tile = by_tile
            self.winning_project, self.recommendations, _coverage = choose_recommendations(
                self.products_by_tile, self.required_tiles
            )

            # In Auto mode, if the area has 0 required tiles covered by 1m DEM,
            # automatically fall back to 10m (1/3 arc-sec), and if still 0, to 30m (1 arc-sec).
            req_matched = sum(1 for t in self.required_tiles if self.products_by_tile.get(t))
            if (
                self.dock
                and self.dock.current_source_mode() == MODE_AUTO
                and req_matched == 0
            ):
                next_mode = None
                if self.active_mode == MODE_USGS_1M and self._auto_fallback_stage < 1:
                    self._auto_fallback_stage = 1
                    next_mode = MODE_USGS_10M
                    fallback_msg = (
                        "No USGS 1m DEM covers this area; automatically switched to USGS 10m (1/3 arc-sec) DEM."
                        if self.lang == "en"
                        else "当前区域暂无 USGS 1m DEM 覆盖，已自动切换为全美无缝覆盖的 USGS 10m (1/3 arc-sec) DEM。"
                    )
                elif self.active_mode == MODE_USGS_10M and self._auto_fallback_stage < 2:
                    self._auto_fallback_stage = 2
                    next_mode = MODE_USGS_30M
                    fallback_msg = (
                        "No USGS 10m DEM covers this area; automatically switched to USGS 30m (1 arc-sec) DEM."
                        if self.lang == "en"
                        else "当前区域暂无 USGS 10m DEM 覆盖，已自动切换为 USGS 30m (1 arc-sec) DEM。"
                    )

                if next_mode:
                    self.iface.messageBar().pushMessage(
                        "USGS DEM Tile Finder",
                        fallback_msg,
                        level=Qgis.Info,
                        duration=8,
                    )
                    if self._last_input_kind == "point" and self._last_wgs84_lonlat:
                        self._build_tiles_from_wgs84_point(
                            self._last_wgs84_lonlat[0],
                            self._last_wgs84_lonlat[1],
                            forced_mode=next_mode,
                        )
                        return
                    if self._last_input_kind == "geom" and self._last_geom and self._last_geom_crs:
                        self._build_tiles_from_geometry(
                            self._last_geom,
                            self._last_geom_crs,
                            forced_mode=next_mode,
                        )
                        return

            self.scan_local_cache(auto_import=False)
            self._update_tile_layer_attributes()
            self._populate_table(query_state=self._tr("queried"))
            self._refresh_summary_status()
        except Exception as exc:
            self._populate_table(query_state=self._tr("api_failed"))
            self._error(f"USGS 查询或解析失败：{exc}")

    def _display_bbox_wgs84(self):
        xs = [x for x, _ in self.display_tiles]
        ys = [y for _, y in self.display_tiles]
        if self.active_mode in (MODE_USGS_10M, MODE_USGS_30M):
            return float(min(xs)), float(min(ys)), float(max(xs) + 1), float(max(ys) + 1)

        xmin = min(xs) * TILE_SIZE
        xmax = (max(xs) + 1) * TILE_SIZE
        ymin = (min(ys) - 1) * TILE_SIZE
        ymax = max(ys) * TILE_SIZE

        tr = QgsCoordinateTransform(
            self.utm_crs,
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsProject.instance(),
        )
        corners = [
            tr.transform(xmin, ymin),
            tr.transform(xmin, ymax),
            tr.transform(xmax, ymin),
            tr.transform(xmax, ymax),
        ]
        lons = [p.x() for p in corners]
        lats = [p.y() for p in corners]
        return min(lons), min(lats), max(lons), max(lats)

    # ---------------- Map layer ----------------

    def _create_tile_layer(self):
        self._remove_tile_layer()

        layer = QgsVectorLayer(
            f"Polygon?crs={self.utm_crs.authid()}",
            self._layer_title_for_mode(),
            "memory",
        )
        pr = layer.dataProvider()
        pr.addAttributes([
            QgsField("tile", QVariant.String),
            QgsField("relation", QVariant.String),
            QgsField("kind", QVariant.String),
            QgsField("display", QVariant.String),
            QgsField("versions", QVariant.Int),
            QgsField("recommended", QVariant.String),
            QgsField("project", QVariant.String),
            QgsField("status", QVariant.String),
            QgsField("label", QVariant.String),
        ])
        layer.updateFields()

        feats = []
        for ix, iy in sorted(self.display_tiles, key=lambda t: (-t[1], t[0])):
            xmin, ymin, xmax, ymax = tile_bounds(ix, iy, mode=self.active_mode)
            f = QgsFeature(layer.fields())
            f.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin, ymin, xmax, ymax)))
            kind = "required" if (ix, iy) in self.required_tiles else "neighbor"
            display = f"{kind}_missing"
            tn = tile_name(ix, iy, mode=self.active_mode)
            rel_local = self._relation_localized(ix, iy)
            kind_local = self._tr("required") if kind == "required" else self._tr("neighbor")
            f.setAttributes([
                tn, rel_local, kind, display, 0, "", "",
                self._tr("not_queried"),
                f"{tn}\n{rel_local}\n{kind_local}"
            ])
            feats.append(f)

        pr.addFeatures(feats)
        layer.updateExtents()

        required_missing_symbol = QgsFillSymbol.createSimple({
            "color": "255,196,0,65",
            "outline_color": "255,120,0,255",
            "outline_width": "0.8",
        })
        neighbor_missing_symbol = QgsFillSymbol.createSimple({
            "color": "80,150,255,28",
            "outline_color": "65,105,160,210",
            "outline_width": "0.45",
        })
        required_local_symbol = QgsFillSymbol.createSimple({
            "color": "50,190,90,95",
            "outline_color": "20,130,55,255",
            "outline_width": "1.0",
        })
        neighbor_local_symbol = QgsFillSymbol.createSimple({
            "color": "70,200,110,55",
            "outline_color": "30,150,70,230",
            "outline_width": "0.7",
        })

        renderer = QgsCategorizedSymbolRenderer(
            "display",
            [
                QgsRendererCategory(
                    "required_local",
                    required_local_symbol,
                    "必须下载 · 已下载" if self.lang != "en" else "Required · Local",
                ),
                QgsRendererCategory(
                    "neighbor_local",
                    neighbor_local_symbol,
                    "周边参考 · 已下载" if self.lang != "en" else "Neighbor · Local",
                ),
                QgsRendererCategory(
                    "required_missing",
                    required_missing_symbol,
                    self._tr("required"),
                ),
                QgsRendererCategory(
                    "neighbor_missing",
                    neighbor_missing_symbol,
                    self._tr("neighbor"),
                ),
            ],
        )
        layer.setRenderer(renderer)

        pal = QgsPalLayerSettings()
        pal.enabled = True
        pal.fieldName = "label"
        pal.placement = Qgis.LabelPlacement.OverPoint
        fmt = QgsTextFormat()
        fmt.setSize(9)
        fmt.setColor(QColor(255, 255, 255))
        buffer = QgsTextBufferSettings()
        buffer.setEnabled(True)
        buffer.setSize(1.1)
        buffer.setColor(QColor(0, 0, 0))
        fmt.setBuffer(buffer)
        pal.setFormat(fmt)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(pal))
        layer.setLabelsEnabled(True)

        previous_active = self.iface.activeLayer()
        QgsProject.instance().addMapLayer(layer)
        self.tile_layer_id = layer.id()

        if previous_active and QgsProject.instance().mapLayer(previous_active.id()):
            try:
                self.iface.setActiveLayer(previous_active)
            except Exception:
                pass

        if self._zoom_to_result:
            self.zoom_to_tiles()

        self.canvas.refresh()

    def zoom_to_tiles(self):
        layer = QgsProject.instance().mapLayer(self.tile_layer_id) if self.tile_layer_id else None
        if not layer:
            self._warn("当前还没有 DEM 网格。请先进行点定位或当前范围查询。")
            return

        try:
            canvas_crs = self.canvas.mapSettings().destinationCrs()
            rect = layer.extent()

            if layer.crs() != canvas_crs:
                ct = QgsCoordinateTransform(
                    layer.crs(),
                    canvas_crs,
                    QgsProject.instance(),
                )
                rect = ct.transformBoundingBox(rect)

            rect.scale(1.08)
            self.canvas.setExtent(rect)
            self.canvas.refresh()
        except Exception as exc:
            self._error(f"缩放到 DEM 网格失败：{exc}")

    def _update_tile_layer_attributes(self):
        layer = QgsProject.instance().mapLayer(self.tile_layer_id) if self.tile_layer_id else None
        if not layer:
            return
        idx_versions = layer.fields().indexOf("versions")
        idx_rec = layer.fields().indexOf("recommended")
        idx_proj = layer.fields().indexOf("project")
        idx_status = layer.fields().indexOf("status")
        idx_label = layer.fields().indexOf("label")
        idx_rel = layer.fields().indexOf("relation")
        idx_display = layer.fields().indexOf("display")

        renderer = layer.renderer()
        if isinstance(renderer, QgsCategorizedSymbolRenderer):
            cats = renderer.categories()
            for cat in cats:
                if cat.value() == "required_local":
                    cat.setLabel("Required · Local" if self.lang == "en" else "必须下载 · 已下载")
                elif cat.value() == "neighbor_local":
                    cat.setLabel("Neighbor · Local" if self.lang == "en" else "周边参考 · 已下载")
                elif cat.value() == "required_missing":
                    cat.setLabel(self._tr("required"))
                elif cat.value() == "neighbor_missing":
                    cat.setLabel(self._tr("neighbor"))

        changes = {}
        for f in layer.getFeatures():
            tn = f["tile"]
            tile = parse_tile_identifier(tn)
            if not tile:
                continue
            products = self.products_by_tile.get(tile, [])
            rec = self.recommendations.get(tile)
            version_count = len(products)
            rec_tail = rec.get("project_tail", "") if rec else ""
            local_path = self.local_product_paths.get(tile)
            is_local = bool(local_path and os.path.exists(local_path))
            status = (
                "Local / Ready" if self.lang == "en" else "本地已有 / 可用"
            ) if is_local else (
                self._tr("available") if rec and rec.get("download_url") else (
                    self._tr("queried") if products else self._tr("not_queried")
                )
            )

            rel_local = self._relation_localized(tile[0], tile[1])
            kind_code = str(f["kind"])
            kind_local = self._tr("required") if kind_code == "required" else self._tr("neighbor")
            display_code = f"{kind_code}_{'local' if is_local else 'missing'}"

            label_lines = [tn, rel_local, kind_local]
            if is_local:
                label_lines.append("✓ Downloaded" if self.lang == "en" else "✓ 已下载")
            if rec_tail:
                label_lines.append(self._short(rec_tail, 30))

            changes[f.id()] = {
                idx_versions: version_count,
                idx_rel: rel_local,
                idx_display: display_code,
                idx_rec: rec.get("title", "") if rec else "",
                idx_proj: rec_tail,
                idx_status: status,
                idx_label: "\n".join(label_lines),
            }
        layer.dataProvider().changeAttributeValues(changes)
        layer.triggerRepaint()
        self.canvas.refresh()

    def _remove_tile_layer(self):
        if self.tile_layer_id:
            QgsProject.instance().removeMapLayer(self.tile_layer_id)
            self.tile_layer_id = None

    # ---------------- Table and details ----------------

    def _populate_table(self, query_state="未查询"):
        if not self.dock:
            return
        table = self.dock.table
        table.setRowCount(0)

        ordered = sorted(
            self.display_tiles,
            key=lambda t: (0 if t in self.required_tiles else 1, -t[1], t[0]),
        )
        for tile in ordered:
            row = table.rowCount()
            table.insertRow(row)
            ix, iy = tile
            products = self.products_by_tile.get(tile, [])
            rec = self.recommendations.get(tile)
            downloadable = bool(rec and rec.get("download_url"))

            check = QTableWidgetItem("")
            check.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            check.setCheckState(Qt.Checked if (tile in self.required_tiles and downloadable) else Qt.Unchecked)
            check.setData(Qt.UserRole, tile)
            table.setItem(row, 0, check)

            local_path = self.local_product_paths.get(tile)
            if local_path:
                status_text = "Local / Added" if self.lang == "en" else "本地已有 / 可用"
            else:
                status_text = (
                    self._tr("available") if downloadable
                    else (self._tr("products_no_url") if products else query_state)
                )

            values = [
                tile_name(ix, iy, mode=self.active_mode),
                self._relation_localized(ix, iy),
                self._tr("required") if tile in self.required_tiles else self._tr("neighbor"),
                str(len(products)),
                self._short(rec.get("project_tail", ""), 48) if rec else "",
                status_text,
            ]
            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setData(Qt.UserRole, tile)
                table.setItem(row, col, item)

        if table.rowCount():
            table.selectRow(0)
        else:
            self.dock.details.clear()

    def update_details(self):
        row = self.dock.table.currentRow() if self.dock else -1
        if row < 0:
            return
        item = self.dock.table.item(row, 1)
        tile = item.data(Qt.UserRole) if item else None
        if not tile:
            return

        tile = tuple(tile)
        products = self.products_by_tile.get(tile, [])
        rec = self.recommendations.get(tile)
        required = tile in self.required_tiles
        rel = self._relation_localized(tile[0], tile[1])
        grid_desc = "10,000 × 10,000 m" if self.active_mode == MODE_USGS_1M else "1° × 1° (WGS84)"
        html = [
            f"<b>{tile_name(tile[0], tile[1], mode=self.active_mode)}</b> &nbsp; | &nbsp; {rel} &nbsp; | &nbsp; "
            f"{self._tr('required') if required else self._tr('neighbor')}",
            f"<br>{self._mode_label()} &nbsp; | &nbsp; {self._tr('utm_zone')}: {self.utm_zone} &nbsp; | &nbsp; {grid_desc}",
        ]
        local_path = self.local_product_paths.get(tile)
        local_versions = self.local_files_by_tile.get(tile, [])
        if local_path:
            local_label = "Local file" if self.lang == "en" else "本地文件"
            local_count_label = "Local versions" if self.lang == "en" else "本地版本数"
            html.append(
                f"<p><b>{local_label}：</b>{self._html(local_path)}"
                f"<br><b>{local_count_label}：</b>{len(local_versions)}</p>"
            )

        if not products:
            html.append(f"<p>{self._tr('no_product')}</p>")
        else:
            html.append(f"<p>{self._tr('versions')}：<b>{len(products)}</b></p>")
            for i, p in enumerate(
                sorted(products, key=lambda x: (x.get("year", 0), x.get("date_score", 0)), reverse=True),
                start=1,
            ):
                star = self._tr("recommended") if rec is p or (rec and rec.get("title") == p.get("title")) else ""
                size_bytes = self._expected_size_bytes(p)
                size_line = (
                    f"{self._tr('size_label')}：{self._format_bytes(size_bytes)}<br>"
                    if size_bytes > 0
                    else ""
                )
                html.append(
                    "<hr>"
                    f"<b>{i}. {self._html(p.get('project_tail') or p.get('title'))}</b> {star}<br>"
                    f"{self._tr('full_name')}：{self._html(p.get('title'))}<br>"
                    f"{size_line}"
                    f"{self._tr('published')}：{self._html(p.get('published')) or '-'}<br>"
                    f"{self._tr('updated')}：{self._html(p.get('updated')) or '-'}<br>"
                )
                if p.get("download_url"):
                    html.append(
                        f'<a href="{self._html_attr(p["download_url"])}">{self._tr("direct_download")}</a> '
                    )
                if p.get("info_url"):
                    html.append(
                        f' | <a href="{self._html_attr(p["info_url"])}">{self._tr("metadata")}</a>'
                    )
        self.dock.details.setHtml("".join(html))

    # ---------------- Open / download ----------------

    def open_selected_product(self):
        tile = self._current_tile()
        if not tile:
            self._warn("请先在表格中选择一个瓦片。")
            return
        rec = self.recommendations.get(tile)
        if not rec:
            self._warn("该瓦片当前没有推荐产品。")
            return
        url = rec.get("info_url") or rec.get("download_url")
        if not url:
            self._warn("该产品没有可打开的 URL。")
            return
        QDesktopServices.openUrl(QUrl(url))

    def download_checked(self):
        if not self.dock:
            return

        selected = []
        skipped_local = []
        for row in range(self.dock.table.rowCount()):
            item = self.dock.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                tile = tuple(item.data(Qt.UserRole))
                local_path = self.local_product_paths.get(tile)
                if local_path and os.path.exists(local_path):
                    skipped_local.append((tile, local_path))
                    continue

                rec = self.recommendations.get(tile)
                if rec and rec.get("download_url"):
                    selected.append((tile, rec))

        for tile, path in skipped_local:
            if self.dock.add_after_download.isChecked():
                self._add_raster_if_needed(path)
            self._set_tile_download_status(tile, 100, "local")

        if not selected:
            if skipped_local:
                msg = (
                    f"{len(skipped_local)} checked DEM(s) already exist locally and are ready to use."
                    if self.lang == "en"
                    else f"勾选的 {len(skipped_local)} 个 DEM 本地已经完整存在，可直接使用。"
                )
                self.dock.set_status(msg)
                return
            self._warn("请先勾选至少一个具有下载 URL 的 DEM。")
            return

        self._ensure_cache_dir()
        self.clean_incomplete_files(silent=True)
        folder = self.cache_dir

        self.download_targets.clear()
        self.download_progress.clear()
        self.download_completed_paths.clear()
        self.download_folder = folder
        self.download_total_files = len(selected)

        self.dock.progress_bar.setRange(0, 100)
        self.dock.progress_bar.setValue(0)
        self.dock.cancel_download_btn.setEnabled(True)
        self.dock.cache_path_edit.setText(folder)

        if self.lang == "en":
            self.dock.progress_label.setText(
                f"Preparing {len(selected)} download(s)…\nFixed folder: {folder}"
            )
        else:
            self.dock.progress_label.setText(
                f"准备下载 {len(selected)} 个 DEM…\n固定目录：{folder}"
            )

        started = 0
        for tile, rec in selected:
            url = QUrl(rec["download_url"])
            filename = url.fileName()
            if not filename:
                filename = self._safe_filename(rec.get("title") or tile_name(tile[0], tile[1], self.active_mode)) + ".tif"

            final_path = os.path.join(folder, filename)
            part_path = final_path + ".part"

            if os.path.exists(part_path):
                try:
                    os.remove(part_path)
                except Exception:
                    pass

            downloader = QgsFileDownloader(url, part_path, "", True)
            downloader.downloadCompleted.connect(
                lambda *_args, p=part_path, final=final_path, t=tile, rec=rec:
                    self._download_completed_atomic(p, final, t, rec)
            )
            downloader.downloadProgress.connect(
                lambda received, total, p=part_path:
                    self._download_progress(p, received, total)
            )
            downloader.downloadError.connect(
                lambda messages, p=part_path: self._download_error(p, messages)
            )
            downloader.downloadExited.connect(
                lambda *_args, d=downloader: self._download_exited(d)
            )

            self.downloaders.append(downloader)
            self.download_targets[part_path] = tile
            self.download_progress[part_path] = {
                "received": 0,
                "total": self._expected_size_bytes(rec),
                "finished": False,
            }
            self._set_tile_download_status(tile, 0, "downloading")
            downloader.startDownload()
            started += 1

        if self.lang == "en":
            self.dock.set_status(
                f"Started {started} DEM download(s) to fixed folder: {folder}"
            )
        else:
            self.dock.set_status(
                f"已开始下载 {started} 个 DEM 到固定目录：{folder}"
            )
        self._update_overall_download_progress()

    def _download_completed_atomic(self, part_path, final_path, tile, rec):
        state = self.download_progress.setdefault(
            part_path, {"received": 0, "total": 0, "finished": False}
        )
        state["finished"] = True
        if state.get("total", 0) > 0:
            state["received"] = state["total"]

        try:
            expected = self._expected_size_bytes(rec)
            actual = os.path.getsize(part_path) if os.path.exists(part_path) else 0

            if expected and actual:
                if actual < expected * 0.98:
                    raise IOError(
                        f"Incomplete file: {actual} bytes < expected {expected} bytes"
                    )

            if not self._raster_file_looks_valid(part_path):
                raise IOError("Downloaded GeoTIFF cannot be opened as a valid raster.")

            if os.path.exists(final_path):
                os.remove(final_path)
            os.replace(part_path, final_path)

            self.local_product_paths[tile] = final_path
            self.local_files_by_tile.setdefault(tile, [])
            if final_path not in self.local_files_by_tile[tile]:
                self.local_files_by_tile[tile].append(final_path)
            self.download_completed_paths.add(final_path)
            self._set_tile_download_status(tile, 100, "completed")
            self._update_tile_layer_attributes()

            if self.dock and self.dock.add_after_download.isChecked():
                self._add_raster_if_needed(final_path)

            self._update_overall_download_progress()

            msg = (
                f"Download complete: {os.path.basename(final_path)}"
                if self.lang == "en"
                else f"下载完成：{os.path.basename(final_path)}"
            )
            self.iface.messageBar().pushMessage(
                "USGS DEM Tile Finder",
                msg,
                level=Qgis.Success,
                duration=5,
            )
        except Exception as exc:
            try:
                if os.path.exists(part_path):
                    os.remove(part_path)
            except Exception:
                pass
            self._set_tile_download_status(tile, 0, "failed")
            self._update_overall_download_progress()
            self._warn(
                f"Downloaded file failed validation: {exc}"
                if self.lang == "en"
                else f"下载文件校验失败，已删除未完成文件：{exc}"
            )

    def _download_error(self, path, messages):
        state = self.download_progress.setdefault(path, {"received": 0, "total": 0, "finished": False})
        state["finished"] = True
        tile = self.download_targets.get(path)
        if tile:
            self._set_tile_download_status(tile, 0, "failed")
        self._update_overall_download_progress()
        if self.lang == "en":
            self._warn(f"Download failed {os.path.basename(path)}: {'; '.join(messages)}")
        else:
            self._warn(f"下载失败 {os.path.basename(path)}：{'；'.join(messages)}")

    def _download_exited(self, downloader):
        try:
            self.downloaders.remove(downloader)
        except ValueError:
            pass
        if not self.downloaders and self.dock:
            self.dock.cancel_download_btn.setEnabled(False)
            self._update_overall_download_progress()
            self.clean_incomplete_files(silent=True)

    # ---------------- Local DEM cache ----------------

    def _ensure_cache_dir(self):
        if not self.cache_dir:
            self.cache_dir = str(Path.home() / "Documents" / "USGS_DEM")
        os.makedirs(self.cache_dir, exist_ok=True)
        if self.dock:
            self.dock.cache_path_edit.setText(self.cache_dir)

    def choose_cache_directory(self):
        self._ensure_cache_dir()
        folder = QFileDialog.getExistingDirectory(
            self.iface.mainWindow(),
            "Choose USGS DEM Cache Folder" if self.lang == "en" else "选择 USGS DEM 固定目录",
            self.cache_dir,
        )
        if not folder:
            return
        self.cache_dir = folder
        self.settings.setValue("USGSDEMTileFinder/cache_dir", folder)
        if self.dock:
            self.dock.cache_path_edit.setText(folder)

        removed = self.clean_incomplete_files(silent=True)
        self.scan_local_cache(auto_import=False)
        self._update_tile_layer_attributes()
        self._populate_table(query_state=self._tr("queried") if self.recommendations else self._tr("not_queried"))
        self.update_details()

        msg = (
            f"Fixed DEM folder changed to: {folder}"
            if self.lang == "en"
            else f"固定 DEM 目录已改为：{folder}"
        )
        if removed:
            msg += (
                f" ({removed} incomplete file(s) removed)"
                if self.lang == "en"
                else f"（同时清理 {removed} 个未完成文件）"
            )
        self.dock.set_status(msg)

    def clean_incomplete_files(self, silent=False):
        self._ensure_cache_dir()
        removed = 0

        for path in Path(self.cache_dir).glob("*.part"):
            if str(path) in self.download_targets and any(
                not s.get("finished")
                for p, s in self.download_progress.items()
                if p == str(path)
            ):
                continue
            try:
                path.unlink()
                removed += 1
            except Exception:
                pass

        for ext in ("*.tif", "*.tiff", "*.TIF", "*.TIFF"):
            for path in Path(self.cache_dir).glob(ext):
                if not path.is_file():
                    continue
                if not self._raster_file_looks_valid(str(path)):
                    try:
                        path.unlink()
                        removed += 1
                    except Exception:
                        pass

        if not silent and self.dock:
            if self.lang == "en":
                self.dock.set_status(
                    f"Incomplete-file cleanup finished: {removed} file(s) removed."
                )
            else:
                self.dock.set_status(
                    f"未完成文件清理完成：删除 {removed} 个文件。"
                )
            if self.display_tiles:
                try:
                    self.scan_local_cache(auto_import=False)
                    self._update_tile_layer_attributes()
                    self._populate_table(
                        query_state=self._tr("queried") if self.recommendations else self._tr("not_queried")
                    )
                except Exception:
                    pass
        return removed

    def scan_local_cache(self, auto_import=True):
        """
        Scan every GeoTIFF in the fixed cache and index it by the active mode's tile key:
        - MODE_USGS_1M: xNNyNNN (10km UTM)
        - MODE_USGS_10M: USGS_13_nNNwNNN (1x1 deg 1/3 arc-sec)
        - MODE_USGS_30M: USGS_1_nNNwNNN (1x1 deg 1 arc-sec)
        """
        self._ensure_cache_dir()
        self.local_product_paths = {}
        self.local_files_by_tile = {}

        cache_root = Path(self.cache_dir)
        valid_files = []

        for path in cache_root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in (".tif", ".tiff"):
                continue

            name = path.name
            tile = self._parse_tile_from_filename(name, mode=self.active_mode)
            if tile is None:
                continue

            if self.active_mode == MODE_USGS_1M:
                zone = self._parse_zone_from_filename(name)
                if self.utm_zone and zone and zone != self.utm_zone:
                    continue

            if not self._raster_file_looks_valid(str(path)):
                continue

            self.local_files_by_tile.setdefault(tile, []).append(str(path))
            valid_files.append(str(path))

        for tile, paths in self.local_files_by_tile.items():
            rec = self.recommendations.get(tile)
            preferred = None

            if rec:
                url_name = QUrl(rec.get("download_url", "")).fileName()
                if url_name:
                    for p in paths:
                        if os.path.basename(p).lower() == url_name.lower():
                            preferred = p
                            break

                if preferred is None:
                    title_name = self._safe_filename(rec.get("title") or "")
                    for p in paths:
                        if title_name and title_name.lower() in os.path.basename(p).lower():
                            preferred = p
                            break

            if preferred is None:
                preferred = max(
                    paths,
                    key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
                )

            self.local_product_paths[tile] = preferred

        imported = 0
        return len(valid_files), imported

    def _parse_tile_from_filename(self, filename, mode=None):
        m_mode = mode or self.active_mode
        if m_mode == MODE_USGS_10M:
            # Distinguish 1/3 arc-sec (USGS_13_...) from 1 arc-sec (USGS_1_...) when prefixes are present
            low = filename.lower()
            if "usgs_1_" in low and "usgs_13_" not in low:
                return None
            return parse_tile_from_title(filename, mode=MODE_USGS_10M)
        if m_mode == MODE_USGS_30M:
            low = filename.lower()
            if "usgs_13_" in low:
                return None
            return parse_tile_from_title(filename, mode=MODE_USGS_30M)

        m = re.search(r"(?<![A-Za-z0-9])x\s*0*(\d{1,3})\s*y\s*0*(\d{2,4})(?!\d)", filename, re.IGNORECASE)
        if not m:
            m = re.search(r"(?:^|[_\s-])x0*(\d{1,3})y0*(\d{2,4})(?:[_\s.-]|$)", filename, re.IGNORECASE)
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def _parse_zone_from_filename(self, filename):
        patterns = [
            r"USGS[_\s-]*1M[_\s-]*(\d{1,2})[_\s-]*x",
            r"USGS[_\s-]*1[_\s-]*Meter[_\s-]*(\d{1,2})[_\s-]*x",
        ]
        for pat in patterns:
            m = re.search(pat, filename, re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
        return None

    def refresh_local_status(self):
        found, _imported = self.scan_local_cache(auto_import=False)
        self._update_tile_layer_attributes()
        self._populate_table(
            query_state=self._tr("queried") if self.recommendations else self._tr("not_queried")
        )
        self.update_details()

        shown_local = sum(
            1 for t in self.display_tiles if t in self.local_product_paths
        )

        if self.dock:
            if self.lang == "en":
                self.dock.set_status(
                    f"Local cache refreshed ({self._mode_label()}): {found} valid DEM file(s) indexed; "
                    f"{shown_local} downloaded tile(s) in the current map grid."
                )
            else:
                self.dock.set_status(
                    f"本地缓存已刷新（{self._mode_label()}）：共识别 {found} 个当前精度有效 DEM；"
                    f"当前地图网格中有 {shown_local} 个区块已下载。"
                )

    def _add_hillshade_for_layer(self, dem_path, base_name):
        hs_name = f"{base_name} [Hillshade]"
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == hs_name:
                return False
        hs_layer = QgsRasterLayer(dem_path, hs_name)
        if not hs_layer.isValid():
            return False
        try:
            renderer = QgsHillshadeRenderer(hs_layer.dataProvider(), 1, 315.0, 45.0)
            hs_layer.setRenderer(renderer)
            hs_layer.setOpacity(0.45)
        except Exception:
            pass
        QgsProject.instance().addMapLayer(hs_layer)
        return True

    def _import_tile_set(self, tiles):
        self.scan_local_cache(auto_import=False)
        imported = 0
        already = 0
        missing = []
        valid_paths = []
        tile_codes = []

        for tile in sorted(tiles):
            code = tile_name(tile[0], tile[1], self.active_mode)
            path = self.local_product_paths.get(tile)
            if not path:
                missing.append(code)
                continue
            valid_paths.append(path)
            tile_codes.append(code)

        use_vrt = bool(self.dock and self.dock.build_vrt_check.isChecked() and len(valid_paths) >= 2)
        use_hs = bool(self.dock and self.dock.hillshade_check.isChecked())

        if use_vrt:
            try:
                from osgeo import gdal
                tag = "_".join(tile_codes[:4])
                if len(tile_codes) > 4:
                    tag += f"_plus{len(tile_codes) - 4}"
                vrt_name = f"USGS_DEM_Mosaic_{tag}.vrt"
                vrt_path = os.path.join(self.cache_dir, vrt_name)
                ds = gdal.BuildVRT(vrt_path, valid_paths)
                if ds is not None:
                    ds.FlushCache()
                    ds = None
                if os.path.exists(vrt_path):
                    if self._add_raster_if_needed(vrt_path):
                        imported = 1
                    else:
                        already = 1
                    if use_hs:
                        self._add_hillshade_for_layer(vrt_path, os.path.splitext(vrt_name)[0])
                    return imported, already, missing
            except Exception:
                pass

        for path in valid_paths:
            if self._add_raster_if_needed(path):
                imported += 1
            else:
                already += 1
            if use_hs:
                self._add_hillshade_for_layer(path, os.path.splitext(os.path.basename(path))[0])

        return imported, already, missing

    def import_required_local_dems(self):
        imported, already, missing = self._import_tile_set(self.required_tiles)

        self._update_tile_layer_attributes()
        self._populate_table(
            query_state=self._tr("queried") if self.recommendations else self._tr("not_queried")
        )

        if self.dock:
            if self.lang == "en":
                msg = (
                    f"Required DEM import: {imported} added, {already} already in QGIS, "
                    f"{len(missing)} missing locally."
                )
            else:
                msg = (
                    f"所需 DEM 一键导入完成：新加入 {imported} 个，"
                    f"已在 QGIS 中 {already} 个，本地缺少 {len(missing)} 个。"
                )
            if missing:
                msg += (
                    " Missing: " + ", ".join(missing)
                    if self.lang == "en"
                    else " 缺少：" + "、".join(missing)
                )
            self.dock.set_status(msg)

    def import_checked_local_dems(self):
        if not self.dock:
            return

        checked_tiles = []
        for row in range(self.dock.table.rowCount()):
            item = self.dock.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                value = item.data(Qt.UserRole)
                if value:
                    checked_tiles.append(tuple(value))

        if not checked_tiles:
            self._warn(
                "请先勾选至少一个 Tile。"
                if self.lang != "en"
                else "Check at least one Tile first."
            )
            return

        imported, already, missing = self._import_tile_set(checked_tiles)
        self._update_tile_layer_attributes()

        if self.lang == "en":
            msg = (
                f"Checked local DEM import: {imported} added, {already} already loaded, "
                f"{len(missing)} not found locally."
            )
        else:
            msg = (
                f"勾选区块导入完成：新加入 {imported} 个，"
                f"已加载 {already} 个，本地未找到 {len(missing)} 个。"
            )
        if missing:
            msg += (
                " Missing: " + ", ".join(missing)
                if self.lang == "en"
                else " 未找到：" + "、".join(missing)
            )
        self.dock.set_status(msg)

    def _expected_size_bytes(self, rec):
        if not rec:
            return 0
        raw = rec.get("raw") or {}
        value = (
            raw.get("sizeInBytes")
            or raw.get("size")
            or rec.get("size")
            or 0
        )
        try:
            if isinstance(value, str):
                m = re.search(r"\d+", value.replace(",", ""))
                return int(m.group(0)) if m else 0
            return int(value)
        except Exception:
            return 0

    def _raster_file_looks_valid(self, path):
        try:
            if not os.path.exists(path):
                return False
            st = os.stat(path)
            if st.st_size < 4096:
                return False
            key = os.path.normcase(os.path.abspath(path))
            sig = (getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)), st.st_size)
            if self._valid_raster_cache.get(key) == sig:
                return True
            layer = QgsRasterLayer(path, "__usgs_dem_validation__")
            if not layer.isValid():
                return False
            provider = layer.dataProvider()
            valid = (
                layer.width() > 0
                and layer.height() > 0
                and provider is not None
            )
            if valid:
                self._valid_raster_cache[key] = sig
            return valid
        except Exception:
            return False

    def _add_raster_if_needed(self, path):
        path_norm = os.path.normcase(os.path.abspath(path))
        for layer in QgsProject.instance().mapLayers().values():
            try:
                if isinstance(layer, QgsRasterLayer):
                    source = layer.source().split("|", 1)[0]
                    if os.path.normcase(os.path.abspath(source)) == path_norm:
                        return False
            except Exception:
                pass

        layer = self.iface.addRasterLayer(path, os.path.basename(path))
        return bool(layer and layer.isValid())

    # ---------------- Download progress ----------------

    def _download_progress(self, path, received, total):
        state = self.download_progress.setdefault(
            path, {"received": 0, "total": 0, "finished": False}
        )
        state["received"] = max(0, int(received))
        if int(total) > 0:
            state["total"] = int(total)

        eff_total = state.get("total", 0)
        tile = self.download_targets.get(path)
        if tile and eff_total > 0:
            percent = max(0, min(100, int(round(received * 100.0 / eff_total))))
            self._set_tile_download_status(tile, percent, "downloading")
        elif tile:
            self._set_tile_download_status(tile, None, "downloading")

        self._update_overall_download_progress()

    def _set_tile_download_status(self, tile, percent=None, state="downloading"):
        if not self.dock:
            return
        table = self.dock.table
        for row in range(table.rowCount()):
            item = table.item(row, 1)
            if not item:
                continue
            item_tile = item.data(Qt.UserRole)
            if not item_tile or tuple(item_tile) != tuple(tile):
                continue

            status_item = table.item(row, 6)
            if not status_item:
                return

            if state == "completed":
                text = "Downloaded" if self.lang == "en" else "下载完成"
            elif state == "failed":
                text = "Failed" if self.lang == "en" else "下载失败"
            elif state == "canceled":
                text = "Canceled" if self.lang == "en" else "已取消"
            elif state == "local":
                text = "Local / Ready" if self.lang == "en" else "本地已有 / 可用"
            else:
                if percent is None:
                    text = "Downloading…" if self.lang == "en" else "下载中…"
                else:
                    text = (
                        f"Downloading {percent}%"
                        if self.lang == "en"
                        else f"下载中 {percent}%"
                    )
            status_item.setText(text)
            break

    def _update_overall_download_progress(self):
        if not self.dock:
            return

        states = list(self.download_progress.values())
        if not states:
            self.dock.progress_bar.setRange(0, 100)
            self.dock.progress_bar.setValue(0)
            self.dock.progress_label.setText(
                "No download started."
                if self.lang == "en"
                else "尚未开始下载。"
            )
            return

        known_total = sum(s.get("total", 0) for s in states if s.get("total", 0) > 0)
        known_received = sum(
            min(s.get("received", 0), s.get("total", 0))
            for s in states
            if s.get("total", 0) > 0
        )
        finished = sum(1 for s in states if s.get("finished"))

        if known_total > 0:
            percent = max(0, min(100, int(round(known_received * 100.0 / known_total))))
            self.dock.progress_bar.setRange(0, 100)
            self.dock.progress_bar.setValue(percent)
        else:
            self.dock.progress_bar.setRange(0, 0)

        rec_text = self._format_bytes(known_received)
        total_text = self._format_bytes(known_total) if known_total > 0 else "—"
        folder = self.download_folder

        if self.lang == "en":
            label = (
                f"Files: {finished}/{self.download_total_files} complete  |  "
                f"Data: {rec_text} / {total_text}"
            )
            if folder:
                label += f"\nFixed folder: {folder}"
        else:
            label = (
                f"文件：{finished}/{self.download_total_files} 完成  |  "
                f"数据：{rec_text} / {total_text}"
            )
            if folder:
                label += f"\n固定目录：{folder}"

        self.dock.progress_label.setText(label)

        if finished >= self.download_total_files and self.download_total_files > 0:
            self.dock.progress_bar.setRange(0, 100)
            self.dock.progress_bar.setValue(100)
            self.dock.cancel_download_btn.setEnabled(False)

    def cancel_all_downloads(self):
        active = list(self.downloaders)
        if not active:
            return
        for downloader in active:
            try:
                downloader.cancelDownload()
            except Exception:
                pass

        for path, tile in self.download_targets.items():
            state = self.download_progress.get(path, {})
            if not state.get("finished"):
                state["finished"] = True
                self._set_tile_download_status(tile, None, "canceled")

        self._update_overall_download_progress()
        if self.dock:
            self.dock.cancel_download_btn.setEnabled(False)
            self.dock.set_status(
                "Download cancellation requested."
                if self.lang == "en"
                else "已请求取消全部下载。"
            )

    def _format_bytes(self, value):
        try:
            value = float(value)
        except Exception:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while value >= 1024.0 and i < len(units) - 1:
            value /= 1024.0
            i += 1
        if i == 0:
            return f"{int(value)} {units[i]}"
        return f"{value:.1f} {units[i]}"

    # ---------------- Clear / utility ----------------

    def clear_results(self):
        self._remove_tile_layer()
        self.required_tiles = set()
        self.display_tiles = set()
        self.products_by_tile = {}
        self.recommendations = {}
        self.winning_project = ""
        self.anchor_tile = None
        self.utm_crs = None
        self.utm_zone = None
        self._last_input_kind = None
        self._last_wgs84_lonlat = None
        self._last_geom = None
        self._last_geom_crs = None
        self._auto_fallback_stage = 0
        self.download_progress.clear()
        self.download_completed_paths.clear()
        self.download_folder = ""
        self.download_total_files = 0
        if self.dock:
            self.dock.table.setRowCount(0)
            self.dock.details.clear()
            self.dock.progress_bar.setRange(0, 100)
            self.dock.progress_bar.setValue(0)
            self.dock.progress_label.setText(
                "No download started." if self.lang == "en" else "尚未开始下载。"
            )
            self.dock.cancel_download_btn.setEnabled(False)
            self.dock.set_status("Results cleared." if self.lang == "en" else "结果已清除。")

    def _current_tile(self):
        if not self.dock:
            return None
        row = self.dock.table.currentRow()
        if row < 0:
            return None
        item = self.dock.table.item(row, 1)
        value = item.data(Qt.UserRole) if item else None
        return tuple(value) if value else None

    def _winning_project_label(self):
        if not self.winning_project:
            return ""
        for products in self.products_by_tile.values():
            for p in products:
                if p.get("project_key") == self.winning_project:
                    return p.get("project_tail") or p.get("title") or ""
        return self.winning_project

    def _short(self, s, n):
        s = str(s or "")
        return s if len(s) <= n else s[: n - 1] + "…"

    def _safe_filename(self, s):
        s = re.sub(r'[\\/:*?"<>|]+', "_", str(s))
        return s.strip(" ._") or "USGS_DEM"

    def _html(self, s):
        return (
            str(s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _html_attr(self, s):
        return self._html(s).replace('"', "&quot;")

    def _warn(self, text):
        if self.dock:
            self.dock.set_status(text)
        self.iface.messageBar().pushMessage(
            "USGS DEM Tile Finder", text, level=Qgis.Warning, duration=8
        )

    def _error(self, text):
        if self.dock:
            self.dock.set_status(text)
        self.iface.messageBar().pushMessage(
            "USGS DEM Tile Finder", text, level=Qgis.Critical, duration=10
        )
