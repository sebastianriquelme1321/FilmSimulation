"""Main window: top-level layout, signal wiring and background-job orchestration."""
import struct
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
)

from ..core import raw
from ..core.grain import GRAIN
from ..core.preview import PreviewPipeline
from ..core.render import LOOKS, apply_look, edit_settings, look_slug, uint8
from ..services import library
from ..services.catalog import metadata, origins, reference_linear, reference_thumbnails
from ..services.develop import decode, open_filter, supported_labels
from ..services.export_bundle import export_raw_bundle
from ..services.export_jpeg import export_jpeg
from ..services.preferences import load_theme, save_theme
from .adjustments_panel import AdjustmentsPanel
from .backdrop import StudioBackdrop
from .gallery import Gallery
from .images import pixmap
from .jobs import make_job
from .theme import DEFAULT_THEME, THEMES, stylesheet
from .viewer import CompareView

ALL_ORIGINS = 'Todos los orígenes'
HINT = 'Un poco de nostalgia, en cada foto.'


class Window(QMainWindow):
    """The FilmSimulation app window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmSimulation · Film studio')
        startup_warnings = library.startup()
        reference_thumbnails.cache_clear()
        self.resize(1440, 900)
        self.setMinimumSize(1120, 680)
        self.setAcceptDrops(True)
        self.linear = None
        self.preview = None
        self.preview_step = 1
        self.source = None
        self.job = None
        self.pixmaps = []
        self.gallery_job = None
        self.busy = False
        self.active_look = None
        self.preview_pipeline = PreviewPipeline()
        self.preview_job = None
        self.preview_pending = None
        self.preview_revision = 0
        self.closing_preview = False
        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.setInterval(75)
        self.render_timer.timeout.connect(self.render)
        self.theme_name = load_theme(THEMES, DEFAULT_THEME)
        root = StudioBackdrop(self.theme_name)
        self.backdrop = root
        root.setObjectName('root')
        self.setStyleSheet(stylesheet(self.theme_name))
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 16)
        layout.setSpacing(18)
        self._build_header(layout)
        splitter = QSplitter()
        splitter.setHandleWidth(18)
        splitter.addWidget(self._build_sidebar())
        splitter.addWidget(self._build_workspace())
        splitter.addWidget(self._build_inspector())
        splitter.setStretchFactor(1, 1)
        splitter.setCollapsible(1, False)
        splitter.setSizes([370, 700, 290])
        layout.addWidget(splitter, 1)
        self._build_footer(layout)
        self.setCentralWidget(root)
        self._connect_signals()
        if startup_warnings:
            self.status.setText(f'{len(startup_warnings)} entrada(s) de tu biblioteca no se '
                                'pudieron cargar.')
            self.status.setToolTip('\n'.join(startup_warnings))

    # ---- layout -------------------------------------------------------------------------

    def _build_header(self, layout):
        header = QHBoxLayout()
        identity = QVBoxLayout()
        identity.setSpacing(2)
        eyebrow = QLabel('THE EVERYDAY FILM STUDIO')
        eyebrow.setObjectName('eyebrow')
        identity.addWidget(eyebrow)
        self.brand = QLabel('FilmSimulation')
        self.brand.setObjectName('brand')
        identity.addWidget(self.brand)
        header.addLayout(identity)
        header.addStretch()
        self.open_button = QPushButton('Importar RAW')
        self.open_button.setMinimumHeight(42)
        self.save_button = QPushButton('Exportar')
        self.export_format = QComboBox()
        self.export_format.addItems(['JPEG procesado', 'RAW original + ajustes (.zip)'])
        self.export_format.setAccessibleName('Formato de exportación')
        self.export_format.setToolTip('RAW: copia intacta del ARW y receta FilmSimulation; '
                                      'no incorpora el look en los datos RAW.')
        self.save_button.setObjectName('primary')
        self.save_button.setMinimumHeight(42)
        header.addWidget(self.open_button)
        header.addWidget(self.export_format)
        header.addWidget(self.save_button)
        layout.addLayout(header)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName('library')
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 20, 18, 18)
        side.setSpacing(10)
        section = QHBoxLayout()
        heading = QLabel('Películas')
        heading.setObjectName('sectionTitle')
        section.addWidget(heading)
        section.addStretch()
        self.count = QLabel()
        self.count.setObjectName('count')
        section.addWidget(self.count)
        side.addLayout(section)
        self.library_hint = QLabel(HINT)
        self.library_hint.setObjectName('muted')
        side.addWidget(self.library_hint)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar película…')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('Buscar simulación')
        side.addWidget(self.search)
        self.origin = QComboBox()
        self.origin.addItems([ALL_ORIGINS, *origins()])
        self.origin.setAccessibleName('Filtrar simulaciones por origen')
        side.addWidget(self.origin)
        self.gallery = Gallery()
        side.addWidget(self.gallery, 1)
        self.details = QLabel()
        self.details.setObjectName('details')
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(60)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        side.addWidget(self.details)
        reference_note = QLabel('Muestra ilustrativa fija · sin grano')
        reference_note.setObjectName('muted')
        side.addWidget(reference_note)
        library_actions = QHBoxLayout()
        self.import_button = QPushButton('+ LUT / receta')
        self.import_button.setToolTip('Añadir una LUT sRGB o receta a tu biblioteca local')
        self.recipe_button = QPushButton('Guardar receta')
        library_actions.addWidget(self.import_button)
        library_actions.addWidget(self.recipe_button)
        side.addLayout(library_actions)
        sidebar.setMinimumWidth(364)
        sidebar.setMaximumWidth(410)
        return sidebar

    def _build_workspace(self):
        compare = QFrame()
        compare.setObjectName('workspace')
        workspace = QVBoxLayout(compare)
        workspace.setContentsMargins(4, 0, 4, 0)
        workspace.setSpacing(10)
        photo_info = QVBoxLayout()
        photo_info.setSpacing(3)
        self.photo_title = QLabel('Tu próxima foto favorita')
        self.photo_title.setObjectName('sectionTitle')
        self.photo_title.setTextFormat(Qt.TextFormat.PlainText)
        self.photo_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.photo_meta = QLabel('Importa un RAW para empezar a revelar.')
        self.photo_meta.setObjectName('muted')
        photo_info.addWidget(self.photo_title)
        photo_info.addWidget(self.photo_meta)
        workspace.addLayout(photo_info)
        self.viewer = CompareView()
        self.viewer.set_placeholder(f'Tu imagen empieza aquí\n\nImporta o arrastra un archivo '
                                    f'{supported_labels()}')
        workspace.addWidget(self.viewer, 1)
        workspace.addLayout(self._build_view_toolbar())
        return compare

    def _build_view_toolbar(self):
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.mode_buttons = {}
        for mode, text, tip in (('split', 'Dividido', 'Antes y después con divisor arrastrable'),
                                ('before', 'Antes', 'Solo la base ajustada'),
                                ('after', 'Después', 'Solo con película')):
            button = QPushButton(text)
            button.setObjectName('tool')
            button.setCheckable(True)
            button.setChecked(mode == 'split')
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, m=mode: self.set_view_mode(m))
            self.mode_buttons[mode] = button
            bar.addWidget(button)
        bar.addStretch()
        self.zoom_label = QLabel('100 %')
        self.zoom_label.setObjectName('muted')
        self.zoom_label.setMinimumWidth(56)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for text, tip, action in (('−', 'Alejar (−)', lambda: self.viewer.zoom_by(.8)),
                                  ('Ajustar', 'Ajustar a la ventana (0)', self.viewer.fit_view),
                                  ('100 %', 'Tamaño real (1)', self.viewer.actual_size),
                                  ('+', 'Acercar (+)', lambda: self.viewer.zoom_by(1.25))):
            button = QPushButton(text)
            button.setObjectName('tool')
            button.setToolTip(tip)
            button.clicked.connect(lambda _=False, a=action: a())
            bar.addWidget(button)
        bar.addWidget(self.zoom_label)
        self.viewer.zoom_changed.connect(self._zoom_changed)
        return bar

    def set_view_mode(self, mode):
        """Switch the viewer between divider, before-only and after-only."""
        self.viewer.set_mode(mode)
        for key, button in self.mode_buttons.items():
            button.setChecked(key == mode)

    def _zoom_changed(self, _):
        self.zoom_label.setText(f'{self.viewer.zoom_percent()} %')

    def _build_inspector(self):
        inspector = QFrame()
        inspector.setObjectName('library')
        column = QVBoxLayout(inspector)
        column.setContentsMargins(18, 20, 18, 18)
        column.setSpacing(10)
        heading = QLabel('Ajustes')
        heading.setObjectName('sectionTitle')
        column.addWidget(heading)
        self.adjustments = AdjustmentsPanel()
        column.addWidget(self.adjustments)
        column.addSpacing(8)
        column.addWidget(QLabel('Grano'))
        self.grain = QComboBox()
        self.grain.addItems(GRAIN)
        self.grain.setAccessibleName('Intensidad del grano')
        self.grain.setToolTip('Textura monocromática aplicada al JPEG final')
        column.addWidget(self.grain)
        column.addStretch()
        inspector.setMinimumWidth(250)
        inspector.setMaximumWidth(330)
        return inspector

    def _build_footer(self, layout):
        footer = QHBoxLayout()
        self.status = QLabel('Listo para revelar')
        self.status.setObjectName('muted')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        footer.addWidget(self.status, 1)
        footer.addWidget(QLabel('Tema'))
        self.theme_selector = QComboBox()
        for key, label in THEMES.items():
            self.theme_selector.addItem(label, key)
        self.theme_selector.setCurrentIndex(list(THEMES).index(self.theme_name))
        self.theme_selector.setAccessibleName('Tema visual de la aplicación')
        self.theme_selector.setToolTip('Cambia el aspecto de la app; mantiene el color de la foto.')
        footer.addWidget(self.theme_selector)
        layout.addLayout(footer)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)

    def _connect_signals(self):
        self.open_button.clicked.connect(self.open_raw)
        self.gallery.selected.connect(self.select_look)
        self.origin.currentTextChanged.connect(self.refresh_gallery)
        self.search.textChanged.connect(self.refresh_gallery)
        self.grain.currentTextChanged.connect(self.render)
        self.adjustments.changed.connect(self.render_timer.start)
        self.save_button.clicked.connect(self.save)
        self.import_button.clicked.connect(self.import_custom)
        self.recipe_button.clicked.connect(self.save_recipe)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.open_raw)
        QShortcut(QKeySequence.StandardKey.SaveAs, self, activated=self.save)
        self.refresh_gallery()
        self.set_busy(False)
        self.theme_selector.currentIndexChanged.connect(self.change_theme)
        self.apply_theme(self.theme_name)
        QTimer.singleShot(0, self.load_gallery)

    # ---- theme --------------------------------------------------------------------------

    def apply_theme(self, theme):
        """Restyle the window and backdrop for the given theme key."""
        self.theme_name = theme
        self.backdrop.theme = theme
        self.setStyleSheet(stylesheet(theme))
        self.brand.setText('Film<i>Simulation</i>' if theme == 'glass' else 'FilmSimulation')
        margin = 20 if theme == 'glass' else 16
        self.backdrop.layout().setContentsMargins(margin, 16, margin, 12)
        self.backdrop.layout().setSpacing(14 if theme == 'glass' else 10)
        self.backdrop.update()

    def change_theme(self, *_):
        """Apply the theme picked in the footer and remember it."""
        theme = self.theme_selector.currentData()
        self.apply_theme(theme)
        try:
            save_theme(theme, THEMES)
        except OSError:
            self.status.setText('Tema aplicado; no se pudo guardar la preferencia local.')

    # ---- gallery ------------------------------------------------------------------------

    def load_gallery(self):
        """Build the reference thumbnails in the background."""
        if self.closing_preview:
            return
        self.library_hint.setText('Preparando referencias…')
        self.gallery_job = make_job(
            reference_thumbnails, self, done=self.gallery_loaded,
            failed=lambda _: self.library_hint.setText('Referencias no disponibles'),
            finished=self.gallery_finished)
        self.gallery_job.start()

    def gallery_loaded(self, images):
        """Show the freshly built thumbnails."""
        if self.closing_preview:
            return
        self.gallery.add_thumbnails(images)
        self.library_hint.setText(HINT)
        self.refresh_gallery()

    def gallery_finished(self):
        """Release the thumbnail worker; finish a deferred close."""
        worker = self.gallery_job
        self.gallery_job = None
        if worker is not None:
            worker.deleteLater()
        if self.closing_preview:
            self.close()

    def refresh_gallery(self, *_):
        """Re-filter the gallery from the origin and search boxes."""
        total = self.gallery.populate(self.origin.currentText(), self.search.text(),
                                      self.active_look)
        self.count.setText(f'{total} / {len(LOOKS)}')
        if not self.active_look:
            self.details.setText('Elige una tarjeta y haz clic o pulsa Enter '
                                 'para aplicar la película.')

    def select_look(self, name):
        """Apply a film chosen in the gallery: update labels, load recipe values, re-render."""
        if name == self.active_look:
            return
        self.active_look = name
        info = metadata(name)
        self.details.setText(info['label'] + '\n' + info['detail'])
        self.viewer.set_after_label('CON PELÍCULA · ' + info['label'].upper())
        if LOOKS[name].backend == 'recipe':
            _, values = edit_settings(name)
            self.adjustments.set_values(values['exposure_ev'], values['temperature'],
                                        values['intensity'])
            self.grain.blockSignals(True)
            self.grain.setCurrentText(LOOKS[name].params['recipe'].get('grain', 'Desactivado'))
            self.grain.blockSignals(False)
        self.save_button.setEnabled(not self.busy and self.linear is not None)
        self.render()

    def import_custom(self):
        """Add a LUT or recipe file to the local library."""
        if self.busy or self.gallery_job is not None:
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Añadir perfil sRGB', '',
                                              'LUT o receta (*.cube *.png *.json)')
        if not path:
            return
        try:
            key = library.import_profile(Path(path))
            reference_thumbnails.cache_clear()
            self.gallery.add_thumbnail(key, uint8(apply_look(reference_linear(), key)))
            self.origin.blockSignals(True)
            self.origin.clear()
            self.origin.addItems([ALL_ORIGINS, *origins()])
            self.origin.setCurrentText('Comunidad / local')
            self.origin.blockSignals(False)
            self.search.clear()
            self.refresh_gallery()
            self.status.setText('Perfil guardado en tu biblioteca local · entrada sRGB')
        except (OSError, ValueError, KeyError, struct.error, ZeroDivisionError) as exc:
            self.error(str(exc))

    def save_recipe(self):
        """Save the current look and adjustments as a shareable JSON recipe."""
        if self.busy:
            return
        base = self.active_look
        if not base:
            return
        base, _ = edit_settings(base)
        name, ok = QInputDialog.getText(self, 'Guardar receta', 'Nombre de tu receta:')
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Guardar receta', name.strip() + '.json',
                                              'Receta Film POC (*.json)')
        if path:
            values = self.adjustments.values()
            data = {'version': 1, 'name': name.strip(), 'base_look': base,
                    'strength': values['intensity'], 'exposure_ev': values['exposure_ev'],
                    'temperature': values['temperature'], 'grain': self.grain.currentText(),
                    'input_space': 'sRGB'}
            try:
                library.save_recipe(data, path)
                self.status.setText('Receta guardada. Puedes compartir el JSON o añadirlo '
                                    'a tu biblioteca.')
            except (OSError, ValueError) as exc:
                self.error(str(exc))

    # ---- jobs ---------------------------------------------------------------------------

    def set_busy(self, busy):
        """Lock or unlock the controls while a background operation runs."""
        was_busy = self.busy
        self.busy = busy
        self.open_button.setEnabled(not busy)
        self.grain.setEnabled(not busy)
        self.origin.setEnabled(not busy)
        self.search.setEnabled(not busy)
        self.gallery.setEnabled(not busy)
        self.import_button.setEnabled(not busy)
        self.recipe_button.setEnabled(not busy)
        self.export_format.setEnabled(not busy)
        self.adjustments.set_editable(not busy)
        self.progress.setVisible(busy)
        self.save_button.setEnabled(not busy and self.linear is not None
                                    and bool(self.active_look))
        if was_busy and not busy:
            self.render()

    def run_job(self, operation, callback, message):
        """Run a blocking operation in the background with the UI locked."""
        self.set_busy(True)
        self.status.setText(message)
        self.job = make_job(operation, self, done=callback, failed=self.error,
                            finished=lambda: self.set_busy(False))
        self.job.start()

    def error(self, message):
        """Report a failed operation."""
        self.status.setText('No se pudo completar la operación.')
        QMessageBox.warning(self, 'FilmSimulation', message)

    def open_raw(self):
        """Ask for a RAW file and develop it."""
        if self.busy:
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Importar RAW', '', open_filter())
        if path:
            self.open_path(Path(path))

    def open_path(self, source):
        """Develop a RAW file in the background and show it."""
        if self.busy:
            return
        self.run_job(lambda: decode(source), lambda linear: self.loaded(source, linear),
                     'Revelando RAW…')

    def dragEnterEvent(self, event):
        """Accept a dragged RAW file."""
        if self._dropped_raw(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Open a dropped RAW file."""
        path = self._dropped_raw(event)
        if path is not None:
            self.open_path(path)

    def _dropped_raw(self, event):
        supported_labels()  # makes sure the decoders are registered
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in raw.supported_extensions():
                return path
        return None

    def loaded(self, source, linear):
        """Adopt a developed photo and render it."""
        self.source, self.linear = source, linear
        self.photo_title.setText(source.name)
        self.photo_title.setToolTip(source.name)
        self.photo_meta.setText(f'{linear.shape[1]} × {linear.shape[0]} · '
                                f'{self._format_label(source)}')
        self.preview_step = max(1, (max(linear.shape[:2]) + 1279) // 1280)
        self.preview = linear[::self.preview_step, ::self.preview_step].copy()
        self.refresh_gallery()
        self.render()
        self.status.setText(f'{source.name} · {linear.shape[1]} × {linear.shape[0]}')

    @staticmethod
    def _format_label(source):
        try:
            return raw.decoder_for(source).label
        except ValueError:
            return 'RAW'

    # ---- preview ------------------------------------------------------------------------

    def render(self, *_):
        """Queue a preview render; only the newest request is kept."""
        self.render_timer.stop()
        if self.busy:
            return
        self.preview_revision += 1
        if self.preview is None:
            self.preview_pending = None
            return
        self.preview_pending = (self.preview_revision, self.preview, self.active_look,
                                self.adjustments.values(), self.grain.currentText(),
                                self.preview_step)
        if self.preview_job is None:
            self.start_preview()

    def start_preview(self):
        """Start the pending preview render in the background."""
        if self.preview_pending is None or self.closing_preview:
            return
        revision, source, name, values, grain, step = self.preview_pending
        self.preview_pending = None
        if name:
            self.viewer.set_after_label('ACTUALIZANDO · ' + metadata(name)['label'].upper())
        self.preview_job = make_job(
            lambda: self.preview_pipeline.render(source, name, **values, grain=grain, step=step),
            self, done=lambda images: self.show_preview(revision, images),
            failed=lambda message: self.preview_failed(revision, message),
            finished=self.preview_finished)
        self.preview_job.start()

    def show_preview(self, revision, images):
        """Display rendered previews unless a newer render superseded them."""
        if revision != self.preview_revision or self.closing_preview:
            return
        self.backdrop.set_reference(images[0])
        self.pixmaps = [pixmap(rgb) if rgb is not None else None for rgb in images]
        self.viewer.set_after_label('CON PELÍCULA · ' + metadata(self.active_look)['label'].upper()
                                 if self.active_look else 'CON PELÍCULA')
        self.show_images()

    def preview_failed(self, revision, message):
        """Report a preview failure unless it is stale."""
        if revision == self.preview_revision and not self.closing_preview:
            self.error(message)

    def preview_finished(self):
        """Release the preview worker, then run the next queued render or finish closing."""
        worker = self.preview_job
        self.preview_job = None
        if worker is not None:
            worker.deleteLater()
        if self.closing_preview:
            self.close()
        else:
            self.start_preview()

    def show_images(self):
        """Hand the rendered previews to the viewer (or its empty state)."""
        before, after = (self.pixmaps + [None, None])[:2]
        self.viewer.set_placeholder('Elige una película de la colección\n'
                                    'Haz clic o pulsa Enter para aplicarla.'
                                    if before is not None else self.viewer.placeholder)
        self.viewer.set_images(before, after)

    # ---- export -------------------------------------------------------------------------

    def save(self):
        """Export the full-resolution JPEG or the RAW + recipe bundle."""
        if self.linear is None or self.busy or not self.active_look:
            return
        tag = look_slug(self.active_look)
        grain = self.grain.currentText()
        grain_tag = '' if grain == 'Desactivado' else '_grano_' + grain.lower()
        raw = self.export_format.currentIndex() == 1
        suffix = '.zip' if raw else '.jpg'
        default = self.source.with_name(self.source.stem + f'_{tag}{grain_tag}' + suffix)
        title = 'RAW original + ajustes (sin look incorporado)' if raw else 'Exportar JPEG'
        formats = 'RAW original y receta (*.zip)' if raw else 'JPEG (*.jpg *.jpeg)'
        path, _ = QFileDialog.getSaveFileName(self, title, str(default), formats)
        if path:
            destination = Path(path)
            if not destination.suffix:
                destination = destination.with_suffix(suffix)
            name = self.active_look
            values = self.adjustments.values()
            if raw:
                def operation():
                    return export_raw_bundle(self.source, name, destination, grain=grain, **values)
                message = 'Conservando RAW original y receta…'
            else:
                def operation():
                    return export_jpeg(self.linear, name, destination, grain=grain, **values)
                message = 'Exportando resolución completa…'
            self.run_job(operation, lambda _: self.status.setText(f'Exportado: {destination}'),
                         message)

    def closeEvent(self, event):
        """Refuse to close mid-export; defer closing until workers finish."""
        if self.job is not None and self.job.isRunning():
            self.status.setText('Espera a que termine la operación antes de cerrar.')
            event.ignore()
        elif self.preview_job is not None or self.gallery_job is not None:
            self.closing_preview = True
            self.preview_pending = None
            self.render_timer.stop()
            event.ignore()
        else:
            self.closing_preview = True
            self.render_timer.stop()
            self.preview_pending = None
            event.accept()


def main():
    """Launch the application."""
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
