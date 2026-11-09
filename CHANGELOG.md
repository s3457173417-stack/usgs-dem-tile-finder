# Changelog

## 0.4.0

- Added `③ Parcel / Layer` button (`use_active_layer_extent`) to detect required DEM tiles directly from the active Parcel/vector layer extent;
- Added `Build seamless VRT mosaic when importing multiple tiles` (`gdal.BuildVRT`) and `Auto-generate Hillshade layer` (`QgsHillshadeRenderer`);
- Added one-click `Basemap` (`Esri World Imagery`) button at the top bar;
- Added 4-language UI selector (`English` default, `简体中文`, `Español`, `Français`) and `WaitCursor` feedback.


## 0.3.1

- Dedicated to all official US USGS 3DEP resolutions (`1m`, `10m 1/3 arc-sec`, and `30m 1 arc-sec`);
- `Auto` mode queries USGS 1m DEM (10km UTM) first and automatically falls back to USGS 10m (`1/3 arc-sec`) or 30m (`1 arc-sec`) `1°×1°` tiles (`nNNwNNN`) when 1m coverage is unavailable;
- Separate local cache file matching for `USGS_1M_`, `USGS_13_`, and `USGS_1_` GeoTIFFs.


## 0.2.4

- Fixed `AttributeError: 'FinderDock' object has no attribute 'auto_import_cache'` when downloading checked DEMs that already exist locally;
- Immediately scan and display local DEM cache status when building tiles, even when USGS auto-query is off or the API request fails;
- Made `scan_local_cache` strictly read-only (never deletes `.tif` files during a scan) and cached raster validity checks by `(mtime, size)` to avoid UI freezes;
- Made `QgsFileDownloader` signal lambdas accept arbitrary arguments and removed dead `_download_completed` code;
- Cleaned up duplicate imports in `dock.py`.


## 0.2.3

- Default window is docked on the QGIS right side again;
- Added a vertical scroll area for the whole plugin;
- Removed horizontal/vertical layout switch;
- Removed draggable sizing for sections 1, 3, and 4;
- Only section 2 (DEM Tiles) has adjustable height;
- Text/controls now preserve their natural height and scroll when necessary.


## 0.2.2

- Removed Selected Parcel / Polygon detection;
- Kept only Point and Current Map Extent detection;
- Arranged the two detection buttons in a 1:1 symmetric horizontal row.


## 0.2.1

- Plugin opens floating by default;
- Added recommended default geometry: 1180 × 860;
- Added Best Size button;
- Best Size restores the 4 functional-section proportions;
- Floating mode gives free left/right/up/down resizing;
- Dock mode remains available.


## 0.2.0

- Added horizontal/vertical four-section layout switch;
- All four sections can now be resized left/right or up/down;

- Rebuilt UI into four functional sections;
- All four sections are vertically resizable through draggable splitter handles;
- Kept float/dock mode for free window movement and resizing;
- Detection never auto-imports local DEMs;
- Manual import is required through Import Required / Import Checked;
- Auto-add after download now defaults to off.


## 0.1.9

- Indexed all valid cached GeoTIFFs by x/y Tile;
- Added green map styling for locally downloaded Tiles;
- Added `✓ Downloaded` label state;
- Added Refresh Local Status;
- Added one-click Import Required DEM;
- Added Import Checked Local DEM;
- Local old versions are recognized even when they are not the current USGS recommendation;
- Download completion updates the map status immediately.


## 0.1.8

- Fixed selected-polygon mode by scanning all selected polygon layers;
- Restores the user's active Parcel/Subbasin layer after creating DEM tiles;
- Point/polygon/current-extent modes no longer auto-pan or auto-zoom;
- Added CRS-safe “Zoom to DEM Tiles” action;
- Added obvious draggable splitter;
- Added Float/Dock Window button for free movement and resizing;
- Stacked the three area-selection buttons vertically.


## 0.1.7

- Added persistent fixed DEM cache directory;
- Detects and reuses valid local DEMs;
- Auto-imports required local DEMs into QGIS;
- New downloads use `.part` files and atomic rename on success;
- Cleans orphaned `.part` and invalid old raster files;
- Avoids re-downloading complete local DEM products.


## 0.1.6

- Enlarged the Tile results area by default;
- Added adjustable Results Height (220–750 px);
- Added Maximize Results / Restore Details;
- Lower progress/details pane can collapse;
- Results receive priority in the default vertical layout.


## 0.1.5

- Author changed to `sus/oa`;
- Added draggable vertical splitter for results vs. progress/details;
- Table columns can be resized manually;
- Improved dock resizing and floating behavior.


## 0.1.4

- 新增总体下载进度条；
- 新增实时 bytes received / total；
- 表格按 Tile 显示下载百分比；
- 显示保存目录和完成文件数量；
- 新增取消全部下载。


## 0.1.3

- 修复 USGS 传统 1 m DEM 的 Y 瓦片编号偏 1；
- yNNN 按瓦片北侧/上边界的 10 km Northing 编号；
- 修复点、面、地图范围、周边网格及 API bbox 的相应计算。


## 0.1.2

- Tile 标签改为白色并增加黑色描边；
- 新增中文 / English 一键切换；
- 地图标签、方向、类型、表格和详情同步切换语言。


## 0.1.1

- 修复 QGIS 新版本 LabelPlacement / LabelPredefinedPointPosition 枚举冲突；
- 使用 `Qgis.LabelPlacement.OverPoint`；
- 优化三个区域选择按钮的中文名称；
- 当前屏幕范围查询后保持原地图视图，不再强制缩放。

## 0.1.0

- 首个可安装测试版；
- 支持点、选中面、当前地图范围；
- 10 km UTM Tile 网格和 `x/y` 名称；
- 周边方位显示；
- TNMAccess 1 m DEM 查询；
- 多版本分组与一致项目优先推荐；
- 推荐 DEM 下载和下载后自动加载。
