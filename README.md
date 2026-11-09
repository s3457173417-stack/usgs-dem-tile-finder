# USGS 3DEP DEM Tile Finder for QGIS (`v0.4.2`)

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Buy%20Me%20a%20Coffee%20☕-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/susnzhe)

Nationwide US **USGS 3DEP Digital Elevation Model (DEM)** finder, local cache manager, and downloader for QGIS (`1m`, `10m 1/3 arc-sec`, and `30m 1 arc-sec`) with automatic resolution fallback, active Parcel/vector layer detection, seamless VRT mosaic & Hillshade generation, one-click satellite basemap, and a 4-language UI (`English` default, `简体中文`, `Español`, `Français`).

> ☕ **Support / 赞赏支持**: If this plugin saved you time on your GIS, surveying, or civil/hydrology projects, feel free to [Buy Me a Coffee on Ko-fi (https://ko-fi.com/susnzhe)](https://ko-fi.com/susnzhe)!

---

## Key Features (`v0.4.0`)

- **Nationwide US Multi-Resolution 3DEP (`Auto` / `1m` / `10m` / `30m`)**:
  - **Auto Mode (Default)**: Queries **USGS 1m DEM (`10km × 10km` UTM grid, `xNNyNNN`)** first; if 1m LiDAR coverage is unavailable in rural/desert areas, automatically falls back to **USGS 10m (`1/3 arc-second`, `1° × 1°` grid, `nNNwNNN`)** or **30m (`1 arc-second`)** with 100% US coverage.
- **3 Detection Modes**:
  - `① Pick Point` — Click any point on the QGIS map canvas.
  - `② Map Extent` — Detect tiles covering the current map view.
  - `③ Parcel / Layer` — Detect required DEM tiles directly from the active Parcel or vector layer extent.
- **Seamless VRT Mosaic + Auto Hillshade**:
  - Automatically builds a seamless GDAL `.vrt` virtual mosaic when importing multiple adjacent DEM tiles (eliminating black/white contrast seams across tiles).
  - Automatically adds a semi-transparent `QgsHillshadeRenderer` terrain layer for instant topographic visualization.
- **One-Click Satellite Basemap (`Basemap`)**:
  - Loads `Esri World Imagery (Satellite)` at the very bottom of the QGIS layer tree (`insertLayer(-1, layer)`).
- **4-Language Interface**:
  - `English` (default), `简体中文`, `Español`, `Français`.

---

## Installation

1. Download the plugin `.zip` from Releases (or clone this repository into your QGIS `python/plugins/usgs_dem_tile_finder` folder).
2. In QGIS, open **Plugins → Manage and Install Plugins → Install from ZIP**, or enable **USGS DEM Tile Finder** in the Installed tab.

---

## 0.4.0 更新说明（中文）

- **新增 `③ 按地块/图层`（`③ Parcel / Layer`）联动检测**：直接读取当前激活的 Parcel 地块或矢量图层范围计算所需 DEM 分幅。
- **跨块无缝 VRT 虚拟镶嵌 + 自动生成 Hillshade 山体阴影**：多块 DEM 导入时自动拼接为无缝 VRT 并叠加半透明山体阴影图层。
- **顶部一键 `卫星底图`（`Basemap`）**：在图层树最底层加载 Esri 全球高清卫星影像。
- **支持 4 种语言切换**：`English`（默认）、`简体中文`、`Español`、`Français`。

## 0.3.1 专注全美 USGS 3DEP 全分辨率（1m + 10m + 30m）

- 专注美国本土及全境 **USGS 3DEP 官方高程数据**，提供 4 档数据精度模式：
  1. `自动（优先 1m → 无覆盖自动回退 10m / 30m）`（默认）：
     - 优先生成 **10km × 10km UTM 网格 (`x42y375`)** 并查询 **USGS 1m DEM**；
     - 若项目位于偏远地区暂无 1m LiDAR 覆盖，自动无缝切换为全美 100% 覆盖的 **USGS 10m DEM (`1/3 arc-second`, 1°×1° 网格 `n34w112`)**（若仍无则回退至 **USGS 30m `1 arc-second`**）。
  2. `USGS 1m DEM（10km UTM 网格，xNNyNNN）`
  3. `USGS 10m DEM（1/3 arc-sec，1°×1° 网格，全美无缝）`
  4. `USGS 30m DEM（1 arc-sec，1°×1° 网格，大范围分析）`
- 本地缓存按 `USGS_1M_`（1m）、`USGS_13_`（10m）、`USGS_1_`（30m）自动区分索引，互不干扰。


## 0.2.4 稳定性与本地缓存修复

- 修复勾选含本地已存在瓦片时点击“下载勾选 DEM”触发 `auto_import_cache` 属性报错的问题（改用 `add_after_download`）；
- 生成瓦片网格时立即扫描并高亮显示本地已下载 DEM，即使未勾选“自动查询 USGS 版本”或 API 超时也能正常显示本地状态；
- `scan_local_cache` 改为纯只读扫描并增加栅格校验签名缓存，避免只读扫描时误删文件或重复校验造成卡顿；
- 兼容 `QgsFileDownloader` 完成/退出信号参数并清理冗余代码。


## 0.2.3 右侧滚动与单一区域高度调整

- 插件恢复为**默认停靠在 QGIS 右侧**；
- 移除“左右布局”按钮；
- 取消 1/3/4 区域的拖动分隔线；
- 整个插件内容放入纵向滚动区域：
  - 当窗口高度不足时，最右侧自动出现纵向滚动条；
  - 文字和按钮不会再因为强制压缩而错位；
- **只有第 2 区“DEM 区块 / 地图状态”允许调整高度**：
  - 使用“结果区高度”控制；
  - 范围 180–700 px；
  - “最大化区块列表”仅影响第 2 区；
- 第 1、3、4 区保持自然内容高度，不再手工缩放；
- “最佳尺寸”恢复右侧停靠推荐尺寸和第 2 区默认高度；
- 浮动窗口功能仍保留，但不再默认浮动。


## 0.2.2 区域入口精简与对称布局

- 移除“按已选 Parcel / 面查询”；
- 区域检测仅保留两个入口：
  - `① 地图点击定位`
  - `② 当前屏幕范围查询`
- 两个按钮改为同一行左右对称布局：
  - 宽度 1:1；
  - 高度一致；
  - 中间固定间距；
- 中英文界面同步采用两按钮对称布局；
- 其余地图 Tile、本地缓存、下载、手动导入功能保持不变。


## 0.2.1 默认最佳尺寸与自由左右缩放

- 插件首次打开默认采用**浮动窗口**，不再被 QGIS 右侧 Dock 宽度限制；
- 默认推荐尺寸约为 `1180 × 860`：
  - Tile 表格可以完整显示更多列；
  - 本地 DEM 管理按钮不会被挤压；
  - 4 个功能区保持适合实际工作的比例；
- 浮动窗口可以从：
  - 左边缘；
  - 右边缘；
  - 上边缘；
  - 下边缘；
  自由拖动改变大小，也可以直接拖动标题栏移动到其他位置；
- 新增“最佳尺寸”按钮：
  - 窗口被拉乱后可一键恢复推荐大小；
  - 同时恢复四个功能区的默认比例；
- “停靠窗口”仍然保留，需要时可以重新放回 QGIS 右侧；
- 停靠状态下 QGIS 自身会限制横向宽度，因此需要自由左右调整时推荐保持浮动窗口。


## 0.2.0 界面重构与手动导入

- 新增“左右布局 / 上下布局”切换：
  - 上下布局：拖动横向灰色分隔条调整 4 个功能区高度；
  - 左右布局：自动浮动为宽窗口，拖动竖向灰色分隔条调整 4 个功能区宽度；
  - 因此每个功能区既可以上下调整，也可以左右调整；

- 界面重构为 4 个功能分区：
  1. 区域定位 / 检测
  2. DEM 区块 / 地图状态
  3. 本地 DEM 管理 / 下载
  4. 选中瓦片详情
- 4 个分区全部放在同一个垂直 `QSplitter` 中：
  - 每两个分区之间都有明显灰色拖动条；
  - 可以上下自由调整每个功能区的高度；
  - “最大化区块列表”可临时收起其他功能区；
- 整个插件仍支持“浮动窗口”：
  - 浮动后可自由移动；
  - 可从左、右、上、下四边拉伸窗口；
- 取消“检测到本地 DEM 自动导入”：
  - 点定位、Parcel 查询、当前地图范围查询只负责检测；
  - 已下载 Tile 只会在地图上标绿并显示“✓ 已下载”；
  - 不会自动加入 QGIS；
  - 必须手动点击“一键导入所需 DEM”或“导入勾选本地 DEM”；
- “下载完成后自动加入 QGIS”默认改为关闭，可由用户自行勾选。


## 0.1.9 本地已下载区块地图状态 + 一键导入

- 固定缓存目录会扫描所有 `.tif/.tiff`，按 USGS 文件名中的 `xNNyNNN` 自动建立本地 Tile 索引；
- 不再要求本地文件必须等于当前 API 推荐版本：
  - 只要是同一个 Tile 的有效 DEM，就会显示为“本地已下载”；
  - 当前推荐版本若本地存在，优先使用推荐版本；
  - 否则优先使用该 Tile 中修改时间较新的本地文件；
- 地图 DEM 网格实时显示本地下载状态：
  - 绿色：本地已经下载；
  - 橙色：必须使用但本地还没有；
  - 蓝色：周边参考且本地没有；
- 地图标签增加 `✓ 已下载`；
- 新增“刷新本地状态”：
  - 固定目录中新复制/下载的 DEM 可以立即重新识别；
- 新增“一键导入所需 DEM”：
  - 当前 Parcel / 点 / 屏幕范围对应的所有“必须下载”区块，只要本地已有就一次性加入 QGIS；
  - 已经在 QGIS 中的不会重复导入；
  - 缺失 Tile 会明确列出来；
- 新增“导入勾选本地 DEM”：
  - 表格里勾哪几个 Tile，就把本地对应 DEM 一次性导入；
- Tile 详情中显示当前采用的本地文件路径以及同一 Tile 的本地版本数量；
- 下载完成后地图中的该 Tile 会立即从未下载样式变为绿色已下载样式。


## 0.1.8 交互与定位修复

- 修复按钮②“按已选 Parcel / 面查询”失效：
  - 不再只检查当前活动图层；
  - 自动扫描整个 QGIS 项目中具有已选择面要素的图层；
  - 排除插件自己生成的 `USGS 1m DEM Tiles`；
  - 优先 Parcel / Subbasin 等常见图层；
  - 插件生成 DEM 网格后会恢复原来的活动图层，避免抢走 Parcel 图层焦点。
- 修复按钮①点定位后地图跳到错误位置：
  - 点定位、面查询、当前屏幕范围查询默认都不再移动当前地图；
  - 新增“缩放到 DEM 网格”按钮；
  - 手动缩放时先把 DEM UTM 网格范围转换为当前地图 CRS，再设置画布范围。
- 改进界面尺寸调整：
  - 上下区域之间改为明显的灰色粗分隔条；
  - 可直接拖动分隔条；
  - 降低下方详情区最小尺寸限制；
  - 新增“浮动窗口 / 停靠窗口”按钮；
  - 浮动后窗口可以自由移动、拉宽和拉高。
- 选择区域三个按钮改为纵向排列，窄 Dock 中也不会被截断。


## 0.1.7 本地 DEM 缓存与安全下载

- 下载目录改为固定缓存目录，默认：
  - Windows 用户文档目录下 `USGS_DEM`
- 路径会写入 QGIS 设置，关闭 QGIS 后仍会记住；
- 插件每次查询 USGS 后会扫描固定目录：
  - 找到完整、可读取、与推荐产品匹配的 DEM → 标记“本地已有 / 可用”；
  - 对“必须下载”的本地 DEM 可自动加入 QGIS；
  - 已经加入 QGIS 的文件不会重复加载；
- 下载采用安全的 `.part` 临时文件机制：
  - 下载中：`xxx.tif.part`
  - 完成并校验成功：原子改名为 `xxx.tif`
  - 中断时不会把半个 GeoTIFF 当成完整数据；
- 新增“清理未完成文件”：
  - 删除遗留 `.part`；
  - 检测并删除无法正常打开的旧版残缺 `.tif`；
- 下载完成后会进行基础 GeoTIFF 可用性检查；
- 如果 USGS API 提供文件大小，还会对实际文件大小进行校验；
- 勾选一个已经完整存在于本地的 DEM 时不会重新下载，而是直接使用/导入。


## 0.1.6 结果区尺寸控制

- Tile 结果表格默认显示区域明显增大；
- 新增“结果区高度”数值控制，可在 220–750 px 之间调整；
- 新增“最大化结果区 / 恢复详情”按钮：
  - 最大化时临时收起下载进度和 Tile 详情；
  - 可以一次看到更多 DEM 区块；
- 仍然支持直接拖动表格下方分隔线自由调整；
- 默认布局改为优先给结果列表更多垂直空间。


## 0.1.5 界面调整

- 作者改为 `sus/oa`；
- Tile 结果列表与下载进度/详情之间加入可拖动分隔条；
- 可以直接上下拖动分隔条，调整结果列表显示高度；
- Dock 本身支持拖动边缘改变宽度，也可从 QGIS 中浮动为独立窗口后自由改变大小；
- 表格列宽改为可手动拖动调整。


## 0.1.4 下载进度

- 新增真实下载进度条；
- 使用 QGIS `QgsFileDownloader.downloadProgress(bytesReceived, bytesTotal)`；
- 显示：
  - 总体百分比；
  - 已下载 / 总大小（MB / GB）；
  - 已完成文件数 / 总文件数；
  - 当前保存目录；
- 表格中每个 Tile 的状态会实时显示：
  - `下载中 37%`
  - `下载完成`
  - `下载失败`
  - `已取消`
- 新增“取消全部下载”按钮；
- 如果 USGS 服务器暂时没有返回文件总大小，进度条会先显示为不确定状态，拿到总大小后自动切换为百分比。


## 0.1.3 重要定位修复

- 修正 USGS 传统 1 m DEM 的 Y Tile 命名规则；
- `x42y375` 现在对应约：
  - E 420,000–430,000 m
  - N 3,740,000–3,750,000 m
- 修复此前会把 `x42y375` 区域错误显示为 `x42y374` 的问题；
- 同步修正：
  - 点定位；
  - Parcel / 面范围相交；
  - 当前地图范围；
  - 周边网格；
  - USGS API 查询 bbox。


## 0.1.2 新增

- 地图 Tile 标签改为白色；
- 标签增加轻微黑色描边，提高卫星图 / DEM 上的可读性；
- 增加 `English / 中文` 一键切换按钮；
- 切换语言后同步更新：
  - 按钮与分组标题；
  - 表格标题；
  - 中心/东南西北方向；
  - 必须下载/周边参考；
  - Tile 详情和状态文字；
  - 地图 Tile 标签。


版本：0.3.1

这是一个面向 QGIS 3.x 的实验版插件，用于把 USGS 1 Meter DEM 的 10 km × 10 km 瓦片直接显示在地图中，并辅助判断应该下载哪些区块。

## 0.1.1 修复

- 修复新版 QGIS 中 `LabelPlacement` 强类型枚举导致的报错：
  `a member of enum 'LabelPlacement' is expected not 'LabelPredefinedPointPosition'`；
- 将标签位置显式改为 `Qgis.LabelPlacement.OverPoint`；
- “当前地图范围”现在不会强制把地图缩放到生成的瓦片范围；
- 三个区域按钮改名，明确区分 Parcel 查询和当前屏幕查询。

## 功能

- 地图点击一个位置，显示其所在 DEM Tile 和周边 3×3 / 5×5 / 7×7 网格；
- 使用当前已选择的 Parcel、Subbasin 等面要素，自动计算所有相交的 10 km Tile；
- 使用当前地图范围计算 Tile；
- 地图标签显示：
  - `x42y375` 之类的 Tile 名；
  - 北 / 南 / 东 / 西 / 东北 / 西北等相对方位；
  - “必须下载”或“周边参考”；
  - 查询成功后显示推荐项目名称；
- 调用 USGS TNMAccess API 查询 `Digital Elevation Model (DEM) 1 meter`；
- 同一个 Tile 有多个版本时全部保留在详情中；
- 推荐算法优先：
  1. 同一 collection/project 覆盖更多“必须下载”瓦片；
  2. 项目年份较新；
  3. 发布/更新时间较新；
- 可勾选推荐 DEM 并直接下载；
- 可选择“下载完成后自动加入 QGIS”。

## 安装

1. 不要解压 ZIP。
2. 打开 QGIS。
3. `插件` → `管理并安装插件`。
4. 选择 `从 ZIP 安装`。
5. 选择 `usgs_dem_tile_finder_0.1.0.zip`。
6. 安装后可从：
   - `栅格`菜单；
   - QGIS 工具栏图标；
   打开 `USGS 1m DEM Tile Finder`。

## 最推荐的使用方式

### 方法 A：Parcel / 项目边界

1. 在图层中选中一个或多个面要素；
2. 打开插件；
3. 选择“使用已选择面要素”；
4. 默认周边圈数 = 1；
5. 插件会显示真正相交的“必须下载”瓦片，以及外围一圈“周边参考”瓦片；
6. 如果开启“自动查询 USGS 版本”，插件会进一步查询真实可下载产品。

### 方法 B：地图点

1. 点击“地图拾取一个点”；
2. 在地图上单击；
3. 中心 Tile 会作为当前区块，外围自动显示周边瓦片。

## 关于 x/y 编号

当前版本按 10 km UTM 网格计算：

- `x = floor(Easting / 10000)`
- `y = floor(Northing / 10000) + 1`（USGS 文件名中的 y 表示瓦片北侧 10 km 边界）

例如 UTM 坐标约为：

- Easting = 425,000 m
- Northing = 3,745,000 m

对应：

- `x42`
- `y375`
- Tile = `x42y375`

其中 `x42y375` 的标准 10 km 主体范围约为：

- Easting：420,000–430,000 m
- Northing：3,740,000–3,750,000 m

## 关于多个 DEM 版本

插件不会简单地“每一块都选最新日期”。

如果：

- `x42y375` 同时存在 `MaricopaPinal 2020` 和 `NorthCentral 2023`
- `x42y376` 只有 `NorthCentral 2023`

那么插件会优先推荐：

- `x42y375 → NorthCentral 2023`
- `x42y376 → NorthCentral 2023`

因为这样更容易保持同一项目的数据连续性。

## 当前限制

- 第一版主要针对 USGS 传统 `Digital Elevation Model (DEM) 1 meter` 瓦片产品；
- 对跨多个 UTM Zone 的大型研究区，当前版本以区域中心所在 UTM Zone 计算并给出警告，建议分区运行；
- TNMAccess 偶尔可能超时。即使 API 暂时不可用，瓦片网格、编号和方位仍可正常显示，稍后可点击“重新查询 USGS”；
- API 返回记录若标题中没有 `xNNyNNN`，第一版不会自动归入 Tile；
- 尚未包含自动 Mosaic、Clip、0→NoData。建议作为 0.2 版功能继续开发。

## 数据源

USGS The National Map / TNMAccess API  
Dataset: `Digital Elevation Model (DEM) 1 meter`
