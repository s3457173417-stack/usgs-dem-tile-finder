# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QComboBox, QTableWidget, QHeaderView,
    QTextBrowser, QAbstractItemView, QGroupBox, QProgressBar, QSizePolicy, QLineEdit, QScrollArea, QFrame
)

from .core_logic import (
    MODE_AUTO,
    MODE_USGS_10M,
    MODE_USGS_1M,
    MODE_USGS_30M,
)

LANGUAGES = [
    ("English", "en"),
    ("简体中文", "zh"),
    ("Español", "es"),
    ("Français", "fr"),
]

UI_TEXTS = {
    "en": {
        "basemap_btn": "Basemap",
        "basemap_tip": "Add Esri World Imagery satellite basemap to the bottom of the layer tree.",
        "best_size": "Best Size",
        "best_size_tip": "Restore recommended right-dock width and tile list height.",
        "float_win": "Float",
        "dock_win": "Dock",
        "float_tip": "Switch to a floating window when a larger workspace is needed.",
        "intro": (
            "Nationwide US USGS 3DEP multi-resolution support (1m 10km UTM + 10m/30m 1°×1° grids). "
            "Detection checks availability; click Import to load DEMs (with optional seamless VRT mosaic & Hillshade)."
        ),
        "sec1": "1. Area Detection & Resolution",
        "source_label": "Resolution:",
        "pick_btn": "① Pick Point",
        "extent_btn": "② Map Extent",
        "layer_btn": "③ Parcel / Layer",
        "layer_tip": "Detect DEM tiles covering the active Parcel or vector layer (or its selected features).",
        "radius_label": "Extra neighbor rings:",
        "radius_tip": "1 ring = show one ring of reference tiles around the required DEM tiles.",
        "query_check": "Auto-query USGS versions",
        "status_wait": "Waiting for area selection.",
        "sec2": "2. DEM Tiles / Map Status",
        "height_label": "List height:",
        "height_tip": "Adjust the height of the Section 2 tile list.",
        "max_list": "Maximize List",
        "restore_list": "Restore List",
        "zoom_btn": "Zoom to DEM Grid",
        "headers": ["Get", "Tile", "Direction", "Type", "Versions", "Recommended", "Status"],
        "query_btn": "Re-query USGS",
        "open_btn": "Open Product Page",
        "download_btn": "Download Checked DEM",
        "clear_btn": "Clear Results",
        "sec3": "3. Local DEM Cache / Download",
        "cache_label": "Cache folder:",
        "change_cache": "Change Folder",
        "refresh_local": "Refresh Local Status",
        "import_req": "Import Required DEMs",
        "import_chk": "Import Checked Local DEMs",
        "clean_part": "Clean Incomplete Files",
        "build_vrt": "Merge multiple tiles into seamless VRT",
        "hillshade": "Auto-generate Hillshade layer",
        "manual_hint": (
            "Note: Detection only marks local status. Click Import to load local DEMs into QGIS."
        ),
        "local_hint": "Map colors: Green = local ready; Orange = required & missing; Blue = neighbor reference.",
        "progress_idle": "No active downloads.",
        "add_after": "Auto-add to QGIS after download",
        "cancel_dl": "Cancel All Downloads",
        "sec4": "4. Selected Tile Details",
        "modes": [
            ("Auto (Prefer 1m → Fallback 10m / 30m)", MODE_AUTO),
            ("USGS 1m DEM (10km UTM Grid, xNNyNNN)", MODE_USGS_1M),
            ("USGS 10m DEM (1/3 arc-sec, 1°×1°, Nationwide)", MODE_USGS_10M),
            ("USGS 30m DEM (1 arc-sec, 1°×1°, Nationwide)", MODE_USGS_30M),
        ],
    },
    "zh": {
        "basemap_btn": "卫星底图",
        "basemap_tip": "在图层树最底层一键加载 Esri 高清卫星底图。",
        "best_size": "最佳尺寸",
        "best_size_tip": "恢复推荐右侧停靠宽度和区块列表高度。",
        "float_win": "浮动",
        "dock_win": "停靠",
        "float_tip": "需要更大工作区时，可临时切换为浮动窗口。",
        "intro": (
            "全美 USGS 3DEP 多精度支持（1m 10km 网格 + 10m/30m 1°×1° 网格）。"
            "支持按点击、当前范围或地块图层检测，导入时可自动无缝拼接 VRT 并生成山体阴影。"
        ),
        "sec1": "1. 区域定位 / 检测",
        "source_label": "数据精度：",
        "pick_btn": "① 地图点击",
        "extent_btn": "② 当前屏幕范围",
        "layer_btn": "③ 按地块/图层",
        "layer_tip": "直接按当前激活的 Parcel 地块或矢量图层范围检测所需 DEM 瓦片。",
        "radius_label": "额外显示周边 DEM：",
        "radius_tip": "1圈=在检测到的必要 Tile 外再显示一圈参考 Tile。",
        "query_check": "自动查询 USGS 版本",
        "status_wait": "等待选择区域。",
        "sec2": "2. DEM 区块 / 地图状态",
        "height_label": "结果区高度：",
        "height_tip": "只调整第 2 区区块列表的高度。",
        "max_list": "最大化区块列表",
        "restore_list": "恢复列表",
        "zoom_btn": "缩放到 DEM 网格",
        "headers": ["下载", "Tile", "方位", "类型", "版本数", "推荐版本", "状态"],
        "query_btn": "重新查询 USGS",
        "open_btn": "打开选中产品",
        "download_btn": "下载勾选 DEM",
        "clear_btn": "清除结果",
        "sec3": "3. 本地 DEM 管理 / 下载",
        "cache_label": "固定目录：",
        "change_cache": "更改目录",
        "refresh_local": "刷新本地状态",
        "import_req": "一键导入所需 DEM",
        "import_chk": "导入勾选本地 DEM",
        "clean_part": "清理未完成文件",
        "build_vrt": "多瓦片自动无缝拼接为单图层 (VRT)",
        "hillshade": "导入时自动生成山体阴影 (Hillshade)",
        "manual_hint": (
            "注意：定位后只检测并标记本地状态，只有点击“导入”按钮才会加载本地 DEM。"
        ),
        "local_hint": "地图颜色：绿色=本地已下载；橙色=必须但未下载；蓝色=周边参考。",
        "progress_idle": "尚未开始下载。",
        "add_after": "下载完成后自动加入 QGIS",
        "cancel_dl": "取消全部下载",
        "sec4": "4. 选中瓦片详情",
        "modes": [
            ("自动（优先 1m → 无覆盖自动回退 10m / 30m）", MODE_AUTO),
            ("USGS 1m DEM（10km UTM 网格，xNNyNNN）", MODE_USGS_1M),
            ("USGS 10m DEM（1/3 arc-sec，1°×1° 网格，全美无缝）", MODE_USGS_10M),
            ("USGS 30m DEM（1 arc-sec，1°×1° 网格，大范围分析）", MODE_USGS_30M),
        ],
    },
    "es": {
        "basemap_btn": "Mapa base",
        "basemap_tip": "Añadir imagen satelital Esri World Imagery al fondo de las capas.",
        "best_size": "Tamaño",
        "best_size_tip": "Restaurar el ancho del panel y la altura de la lista recomendados.",
        "float_win": "Flotar",
        "dock_win": "Acoplar",
        "float_tip": "Cambiar a ventana flotante para obtener más espacio.",
        "intro": (
            "Soporte nacional USGS 3DEP en EE. UU. (1m UTM 10km + 10m/30m 1°×1°). "
            "Use Importar para cargar DEM locales (con mosaico VRT continuo y sombreado Hillshade opcional)."
        ),
        "sec1": "1. Detección de Área y Resolución",
        "source_label": "Resolución:",
        "pick_btn": "① Punto",
        "extent_btn": "② Extensión",
        "layer_btn": "③ Parcela/Capa",
        "layer_tip": "Detectar celdas DEM que cubren la capa de parcela o vectorial activa.",
        "radius_label": "Anillos vecinos extra:",
        "radius_tip": "1 anillo = mostrar un anillo de referencia alrededor de las celdas requeridas.",
        "query_check": "Consultar versiones USGS automáticamente",
        "status_wait": "Esperando selección de área.",
        "sec2": "2. Celdas DEM / Estado del Mapa",
        "height_label": "Altura de lista:",
        "height_tip": "Ajustar la altura de la tabla de celdas DEM.",
        "max_list": "Maximizar lista",
        "restore_list": "Restaurar lista",
        "zoom_btn": "Zoom a cuadrícula DEM",
        "headers": ["Bajar", "Tile", "Dirección", "Tipo", "Versiones", "Recomendado", "Estado"],
        "query_btn": "Reconsultar USGS",
        "open_btn": "Abrir producto",
        "download_btn": "Descargar DEM marcados",
        "clear_btn": "Limpiar",
        "sec3": "3. Caché DEM Local / Descarga",
        "cache_label": "Carpeta caché:",
        "change_cache": "Cambiar carpeta",
        "refresh_local": "Actualizar estado local",
        "import_req": "Importar DEM requeridos",
        "import_chk": "Importar DEM locales marcados",
        "clean_part": "Limpiar incompletos",
        "build_vrt": "Unir múltiples celdas en un mosaico VRT continuo",
        "hillshade": "Generar capa de sombreado (Hillshade) automáticamente",
        "manual_hint": (
            "Nota: La detección solo marca el estado local. Haga clic en Importar para añadir DEM a QGIS."
        ),
        "local_hint": "Colores: Verde = local listo; Naranja = requerido sin descargar; Azul = vecino.",
        "progress_idle": "Sin descargas activas.",
        "add_after": "Añadir a QGIS al terminar descarga",
        "cancel_dl": "Cancelar descargas",
        "sec4": "4. Detalles de Celda Seleccionada",
        "modes": [
            ("Auto (Preferir 1m → Respaldo 10m / 30m)", MODE_AUTO),
            ("USGS 1m DEM (Cuadrícula UTM 10km, xNNyNNN)", MODE_USGS_1M),
            ("USGS 10m DEM (1/3 arc-sec, 1°×1°, Todo EE. UU.)", MODE_USGS_10M),
            ("USGS 30m DEM (1 arc-sec, 1°×1°, Todo EE. UU.)", MODE_USGS_30M),
        ],
    },
    "fr": {
        "basemap_btn": "Fond carte",
        "basemap_tip": "Ajouter l'imagerie satellite Esri World Imagery en fond de carte.",
        "best_size": "Taille",
        "best_size_tip": "Restaurer la largeur du panneau et la hauteur de liste recommandées.",
        "float_win": "Flotter",
        "dock_win": "Ancrer",
        "float_tip": "Basculer en fenêtre flottante pour un espace de travail plus grand.",
        "intro": (
            "Support national USGS 3DEP aux États-Unis (1m UTM 10km + 10m/30m 1°×1°). "
            "Cliquez sur Importer pour charger les MNT (avec mosaïque VRT et ombrage Hillshade en option)."
        ),
        "sec1": "1. Détection de Zone et Résolution",
        "source_label": "Résolution :",
        "pick_btn": "① Point",
        "extent_btn": "② Emprise",
        "layer_btn": "③ Parcelle/Couche",
        "layer_tip": "Détecter les dalles DEM couvrant la couche de parcelle ou vectorielle active.",
        "radius_label": "Anneaux voisins suppl. :",
        "radius_tip": "1 anneau = afficher un anneau de référence autour des dalles requises.",
        "query_check": "Requête auto des versions USGS",
        "status_wait": "En attente de sélection de zone.",
        "sec2": "2. Dalles DEM / État de la Carte",
        "height_label": "Hauteur liste :",
        "height_tip": "Ajuster la hauteur de la liste des dalles.",
        "max_list": "Maximiser liste",
        "restore_list": "Restaurer liste",
        "zoom_btn": "Zoom sur grille DEM",
        "headers": ["Téléch.", "Dalle", "Direction", "Type", "Versions", "Recommandé", "État"],
        "query_btn": "Relancer USGS",
        "open_btn": "Ouvrir produit",
        "download_btn": "Télécharger DEM cochés",
        "clear_btn": "Effacer",
        "sec3": "3. Cache DEM Local / Téléchargement",
        "cache_label": "Dossier cache :",
        "change_cache": "Changer dossier",
        "refresh_local": "Actualiser état local",
        "import_req": "Importer DEM requis",
        "import_chk": "Importer DEM locaux cochés",
        "clean_part": "Nettoyer fichiers incomplets",
        "build_vrt": "Fusionner plusieurs dalles en mosaïque VRT continue",
        "hillshade": "Générer une couche d'ombrage (Hillshade) automatiquement",
        "manual_hint": (
            "Note : La détection indique uniquement l'état local. Cliquez sur Importer pour charger dans QGIS."
        ),
        "local_hint": "Couleurs : Vert = prêt en local ; Orange = requis manquant ; Bleu = voisin.",
        "progress_idle": "Aucun téléchargement actif.",
        "add_after": "Ajouter à QGIS après téléchargement",
        "cancel_dl": "Annuler téléchargements",
        "sec4": "4. Détails de la Dalle Sélectionnée",
        "modes": [
            ("Auto (Préférer 1m → Repli 10m / 30m)", MODE_AUTO),
            ("USGS 1m DEM (Grille UTM 10km, xNNyNNN)", MODE_USGS_1M),
            ("USGS 10m DEM (1/3 arc-sec, 1°×1°, États-Unis)", MODE_USGS_10M),
            ("USGS 30m DEM (1 arc-sec, 1°×1°, États-Unis)", MODE_USGS_30M),
        ],
    },
}


class FinderDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("USGS DEM Tile Finder", parent)
        self.setObjectName("USGSDEMTileFinderDock")
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )

        self.lang = "en"
        self.setMinimumWidth(420)
        self.setMinimumHeight(380)

        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        self.setWidget(root)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setFrameShape(QFrame.NoFrame)
        root_layout.addWidget(self.scroll)

        self.content = QWidget()
        self.content.setMinimumWidth(400)
        self.scroll.setWidget(self.content)

        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)

        # Header
        top_row = QHBoxLayout()
        top_row.setSpacing(4)
        self.title_label = QLabel("<b>USGS 3DEP DEM Finder</b>")
        self.basemap_btn = QPushButton("Basemap")
        self.basemap_btn.setMaximumWidth(80)
        self.best_size_btn = QPushButton("Best Size")
        self.best_size_btn.setMaximumWidth(78)

        self.float_btn = QPushButton("Float")
        self.float_btn.setMaximumWidth(68)

        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(96)
        for label, code in LANGUAGES:
            self.lang_combo.addItem(label, code)

        self.lang_btn = self.lang_combo

        top_row.addWidget(self.title_label)
        top_row.addStretch(1)
        top_row.addWidget(self.basemap_btn)
        top_row.addWidget(self.best_size_btn)
        top_row.addWidget(self.float_btn)
        top_row.addWidget(self.lang_combo)
        layout.addLayout(top_row)

        self.intro = QLabel()
        self.intro.setWordWrap(True)
        layout.addWidget(self.intro)

        # 1. Detection
        self.section1 = QGroupBox()
        s1 = QVBoxLayout(self.section1)
        s1.setContentsMargins(6, 6, 6, 6)
        s1.setSpacing(5)

        source_row = QHBoxLayout()
        self.source_label = QLabel()
        self.source_combo = QComboBox()
        self.source_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._populate_source_combo("en")
        source_row.addWidget(self.source_label)
        source_row.addWidget(self.source_combo, 1)
        s1.addLayout(source_row)

        detect_row = QHBoxLayout()
        detect_row.setSpacing(6)

        self.pick_btn = QPushButton()
        self.extent_btn = QPushButton()
        self.layer_btn = QPushButton()
        for b in (self.pick_btn, self.extent_btn, self.layer_btn):
            b.setMinimumHeight(30)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        detect_row.addWidget(self.pick_btn, 1)
        detect_row.addWidget(self.extent_btn, 1)
        detect_row.addWidget(self.layer_btn, 1)
        s1.addLayout(detect_row)

        neigh_row = QHBoxLayout()
        self.radius_label = QLabel()
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 3)
        self.radius_spin.setValue(1)
        self.query_check = QCheckBox()
        self.query_check.setChecked(True)

        neigh_row.addWidget(self.radius_label)
        neigh_row.addWidget(self.radius_spin)
        neigh_row.addWidget(self.query_check)
        neigh_row.addStretch(1)
        s1.addLayout(neigh_row)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        s1.addWidget(self.status_label)

        layout.addWidget(self.section1)

        # 2. DEM Tiles / map state
        self.section2 = QGroupBox()
        s2 = QVBoxLayout(self.section2)
        s2.setContentsMargins(6, 6, 6, 6)
        s2.setSpacing(5)

        result_controls = QHBoxLayout()
        self.result_height_label = QLabel()
        self.result_height_spin = QSpinBox()
        self.result_height_spin.setRange(160, 700)
        self.result_height_spin.setSingleStep(40)
        self.result_height_spin.setValue(240)
        self.result_height_spin.setSuffix(" px")

        self.max_results_btn = QPushButton()
        self.zoom_btn = QPushButton()

        result_controls.addWidget(self.result_height_label)
        result_controls.addWidget(self.result_height_spin)
        result_controls.addWidget(self.max_results_btn)
        result_controls.addWidget(self.zoom_btn)
        result_controls.addStretch(1)
        s2.addLayout(result_controls)

        self.table = QTableWidget(0, 7)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setMinimumHeight(160)
        self.table.setMaximumHeight(700)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.resizeSection(0, 48)
        header.resizeSection(1, 86)
        header.resizeSection(2, 74)
        header.resizeSection(3, 84)
        header.resizeSection(4, 64)
        header.resizeSection(5, 210)
        header.resizeSection(6, 100)
        header.setStretchLastSection(True)
        s2.addWidget(self.table)

        result_btns = QHBoxLayout()
        self.query_btn = QPushButton()
        self.open_btn = QPushButton()
        self.download_btn = QPushButton()
        self.clear_btn = QPushButton()

        for b in (self.query_btn, self.open_btn, self.download_btn, self.clear_btn):
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        result_btns.addWidget(self.query_btn)
        result_btns.addWidget(self.open_btn)
        result_btns.addWidget(self.download_btn)
        result_btns.addWidget(self.clear_btn)
        s2.addLayout(result_btns)

        layout.addWidget(self.section2)

        # 3. Local DEM / download
        self.section3 = QGroupBox()
        s3 = QVBoxLayout(self.section3)
        s3.setContentsMargins(6, 6, 6, 6)
        s3.setSpacing(5)

        cache_row = QHBoxLayout()
        self.cache_path_label = QLabel()
        self.cache_path_edit = QLineEdit()
        self.cache_path_edit.setReadOnly(True)
        self.change_cache_btn = QPushButton()
        cache_row.addWidget(self.cache_path_label)
        cache_row.addWidget(self.cache_path_edit, 1)
        cache_row.addWidget(self.change_cache_btn)
        s3.addLayout(cache_row)

        local_actions1 = QHBoxLayout()
        self.refresh_local_btn = QPushButton()
        self.import_required_btn = QPushButton()
        local_actions1.addWidget(self.refresh_local_btn)
        local_actions1.addWidget(self.import_required_btn)
        s3.addLayout(local_actions1)

        local_actions2 = QHBoxLayout()
        self.import_checked_btn = QPushButton()
        self.clean_partial_btn = QPushButton()
        local_actions2.addWidget(self.import_checked_btn)
        local_actions2.addWidget(self.clean_partial_btn)
        s3.addLayout(local_actions2)

        mosaic_row = QHBoxLayout()
        self.build_vrt_check = QCheckBox()
        self.build_vrt_check.setChecked(True)
        self.hillshade_check = QCheckBox()
        self.hillshade_check.setChecked(False)
        mosaic_row.addWidget(self.build_vrt_check)
        mosaic_row.addWidget(self.hillshade_check)
        mosaic_row.addStretch(1)
        s3.addLayout(mosaic_row)

        self.manual_import_hint = QLabel()
        self.manual_import_hint.setWordWrap(True)
        self.manual_import_hint.setStyleSheet("color: #8a5a00; font-weight: 600;")
        s3.addWidget(self.manual_import_hint)

        self.local_hint = QLabel()
        self.local_hint.setWordWrap(True)
        self.local_hint.setStyleSheet("color: #666;")
        s3.addWidget(self.local_hint)

        self.progress_label = QLabel()
        self.progress_label.setWordWrap(True)
        self.progress_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        s3.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        s3.addWidget(self.progress_bar)

        download_opts = QHBoxLayout()
        self.add_after_download = QCheckBox()
        self.add_after_download.setChecked(False)
        self.cancel_download_btn = QPushButton()
        self.cancel_download_btn.setEnabled(False)
        download_opts.addWidget(self.add_after_download)
        download_opts.addWidget(self.cancel_download_btn)
        download_opts.addStretch(1)
        s3.addLayout(download_opts)

        layout.addWidget(self.section3)

        # 4. Detail
        self.section4 = QGroupBox()
        s4 = QVBoxLayout(self.section4)
        s4.setContentsMargins(6, 6, 6, 6)

        self.details = QTextBrowser()
        self.details.setOpenExternalLinks(True)
        self.details.setMinimumHeight(120)
        self.details.setMaximumHeight(240)
        s4.addWidget(self.details)

        layout.addWidget(self.section4)
        layout.addStretch(1)

        # Signals
        self.result_height_spin.valueChanged.connect(self.set_results_height)
        self.max_results_btn.clicked.connect(self.toggle_max_results)
        self.best_size_btn.clicked.connect(self.apply_best_size)
        self.float_btn.clicked.connect(self.toggle_floating_window)

        self.set_language("en")
        self.apply_best_size()

    def _t(self, key):
        pack = UI_TEXTS.get(self.lang, UI_TEXTS["en"])
        return pack.get(key, UI_TEXTS["en"].get(key, key))

    def _populate_source_combo(self, lang="en"):
        current = self.source_combo.currentData() if self.source_combo.count() else MODE_AUTO
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        items = UI_TEXTS.get(lang, UI_TEXTS["en"])["modes"]
        for label, code in items:
            self.source_combo.addItem(label, code)
        idx = self.source_combo.findData(current)
        self.source_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.source_combo.blockSignals(False)

    def current_source_mode(self):
        return self.source_combo.currentData() or MODE_AUTO

    def set_results_height(self, value):
        value = max(160, min(700, int(value)))
        self.table.setMinimumHeight(value)
        self.table.setMaximumHeight(value)

    def toggle_max_results(self):
        current = self.table.height()
        if current < 650:
            self.result_height_spin.setValue(650)
            self.max_results_btn.setText(self._t("restore_list"))
        else:
            self.result_height_spin.setValue(240)
            self.max_results_btn.setText(self._t("max_list"))

    def apply_best_size(self):
        self.resize(500, 820)
        self.result_height_spin.blockSignals(True)
        self.result_height_spin.setValue(240)
        self.result_height_spin.blockSignals(False)
        self.set_results_height(240)
        self.best_size_btn.setText(self._t("best_size"))

    def toggle_floating_window(self):
        target = not self.isFloating()
        self.setFloating(target)
        if target:
            self.resize(900, 850)
            self.float_btn.setText(self._t("dock_win"))
        else:
            self.resize(500, 820)
            self.float_btn.setText(self._t("float_win"))

    def set_language(self, lang):
        if lang not in UI_TEXTS:
            lang = "en"
        self.lang = lang

        idx = self.lang_combo.findData(lang)
        if idx >= 0 and self.lang_combo.currentIndex() != idx:
            self.lang_combo.blockSignals(True)
            self.lang_combo.setCurrentIndex(idx)
            self.lang_combo.blockSignals(False)

        self.basemap_btn.setText(self._t("basemap_btn"))
        self.basemap_btn.setToolTip(self._t("basemap_tip"))
        self.best_size_btn.setText(self._t("best_size"))
        self.best_size_btn.setToolTip(self._t("best_size_tip"))
        self.float_btn.setText(self._t("dock_win") if self.isFloating() else self._t("float_win"))
        self.float_btn.setToolTip(self._t("float_tip"))
        self._populate_source_combo(lang)

        self.intro.setText(self._t("intro"))
        self.section1.setTitle(self._t("sec1"))
        self.source_label.setText(self._t("source_label"))
        self.pick_btn.setText(self._t("pick_btn"))
        self.extent_btn.setText(self._t("extent_btn"))
        self.layer_btn.setText(self._t("layer_btn"))
        self.layer_btn.setToolTip(self._t("layer_tip"))
        self.radius_label.setText(self._t("radius_label"))
        self.radius_spin.setToolTip(self._t("radius_tip"))
        self.query_check.setText(self._t("query_check"))

        wait_texts = {v["status_wait"] for v in UI_TEXTS.values()} | {""}
        if self.status_label.text() in wait_texts:
            self.status_label.setText(self._t("status_wait"))

        self.section2.setTitle(self._t("sec2"))
        self.result_height_label.setText(self._t("height_label"))
        self.result_height_spin.setToolTip(self._t("height_tip"))
        self.max_results_btn.setText(
            self._t("restore_list") if self.table.height() >= 650 else self._t("max_list")
        )
        self.zoom_btn.setText(self._t("zoom_btn"))
        self.table.setHorizontalHeaderLabels(self._t("headers"))
        self.query_btn.setText(self._t("query_btn"))
        self.open_btn.setText(self._t("open_btn"))
        self.download_btn.setText(self._t("download_btn"))
        self.clear_btn.setText(self._t("clear_btn"))

        self.section3.setTitle(self._t("sec3"))
        self.cache_path_label.setText(self._t("cache_label"))
        self.change_cache_btn.setText(self._t("change_cache"))
        self.refresh_local_btn.setText(self._t("refresh_local"))
        self.import_required_btn.setText(self._t("import_req"))
        self.import_checked_btn.setText(self._t("import_chk"))
        self.clean_partial_btn.setText(self._t("clean_part"))
        self.build_vrt_check.setText(self._t("build_vrt"))
        self.hillshade_check.setText(self._t("hillshade"))
        self.manual_import_hint.setText(self._t("manual_hint"))
        self.local_hint.setText(self._t("local_hint"))

        idle_texts = {v["progress_idle"] for v in UI_TEXTS.values()} | {""}
        if self.progress_label.text() in idle_texts:
            self.progress_label.setText(self._t("progress_idle"))

        self.add_after_download.setText(self._t("add_after"))
        self.cancel_download_btn.setText(self._t("cancel_dl"))
        self.section4.setTitle(self._t("sec4"))

    def set_status(self, text):
        self.status_label.setText(text)
