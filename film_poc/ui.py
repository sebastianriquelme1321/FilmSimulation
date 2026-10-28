import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QFileDialog, QMessageBox, QLineEdit, QListWidget,
                               QListWidgetItem, QAbstractItemView, QSplitter, QProgressBar, QInputDialog,
                               QFrame, QSizePolicy, QBoxLayout)
from .engine import decode, render_base, apply_look, uint8, export_jpeg, LOOKS, look_slug
from .grain import GRAIN, apply_grain
from .catalog import metadata, origins, filtered_names, reference_thumbnails, reference_linear
from .film_badge import add_canister
from . import user_library
from .theme import STYLE
import json


def load_photo(path):
    linear = decode(path)
    return path, linear


def pixmap(rgb):
    a = rgb.copy()
    return QPixmap.fromImage(QImage(a.data,a.shape[1],a.shape[0],a.strides[0],QImage.Format.Format_RGB888).copy())


class Job(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.done.emit(self.operation())
        except Exception as exc:
            self.failed.emit(str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('FilmSimulation · Film studio')
        user_library.load_library(LOOKS)
        reference_thumbnails.cache_clear()
        self.resize(1440, 900)
        self.setMinimumSize(940, 680)
        self.linear = None
        self.preview = None
        self.source = None
        self.job = None
        self.pixmaps = []
        self.thumbs = {name: add_canister(pixmap(rgb),metadata(name)['label'])
                       for name,rgb in reference_thumbnails().items()}
        self.busy = False
        root = QWidget()
        root.setObjectName('root')
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 16)
        layout.setSpacing(18)
        header = QHBoxLayout()
        identity = QVBoxLayout()
        identity.setSpacing(2)
        eyebrow = QLabel('THE EVERYDAY FILM STUDIO')
        eyebrow.setObjectName('eyebrow')
        identity.addWidget(eyebrow)
        brand = QLabel('FilmSimulation')
        brand.setObjectName('brand')
        identity.addWidget(brand)
        header.addLayout(identity)
        header.addStretch()
        self.open_button = QPushButton('Importar RAW')
        self.open_button.setMinimumHeight(42)
        self.save_button = QPushButton('Exportar JPEG')
        self.save_button.setObjectName('primary')
        self.save_button.setMinimumHeight(42)
        header.addWidget(self.open_button)
        header.addWidget(self.save_button)
        layout.addLayout(header)

        splitter = QSplitter()
        splitter.setHandleWidth(18)
        sidebar = QFrame()
        sidebar.setObjectName('library')
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 20, 18, 18)
        side.setSpacing(10)
        section = QHBoxLayout()
        heading = QLabel('Tu colección')
        heading.setObjectName('sectionTitle')
        section.addWidget(heading)
        section.addStretch()
        self.count = QLabel()
        self.count.setObjectName('count')
        section.addWidget(self.count)
        side.addLayout(section)
        helper = QLabel('Un poco de nostalgia, en cada foto.')
        helper.setObjectName('muted')
        side.addWidget(helper)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar película…')
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName('Buscar simulación')
        side.addWidget(self.search)
        self.origin = QComboBox()
        self.origin.addItems(['Todos los orígenes', *origins()])
        self.origin.setAccessibleName('Filtrar simulaciones por origen')
        side.addWidget(self.origin)
        self.look = QComboBox()
        self.look.addItems(LOOKS)
        self.look.setAccessibleName('Simulación seleccionada')
        # The gallery is the visible selector; keep the combo as selection model.
        self.look.hide()
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setMovement(QListWidget.Movement.Static)
        self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.gallery.setIconSize(QSize(140,95))
        self.gallery.setGridSize(QSize(154,152))
        self.gallery.setWordWrap(True)
        self.gallery.setSpacing(3)
        self.gallery.setAccessibleName('Galería de simulaciones sobre una referencia fija')
        side.addWidget(self.gallery,1)
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
        splitter.addWidget(sidebar)

        compare = QFrame()
        compare.setObjectName('workspace')
        workspace = QVBoxLayout(compare)
        workspace.setContentsMargins(20, 20, 20, 16)
        workspace.setSpacing(14)
        info = QHBoxLayout()
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
        info.addLayout(photo_info, 1)
        grain_label = QLabel('GRANO')
        grain_label.setObjectName('eyebrow')
        info.addWidget(grain_label)
        self.grain = QComboBox()
        self.grain.addItems(GRAIN)
        self.grain.setAccessibleName('Intensidad del grano')
        self.grain.setToolTip('Textura monocromática aplicada al JPEG final')
        self.grain.setMinimumWidth(122)
        info.addWidget(self.grain)
        workspace.addLayout(info)
        self.panes = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.panes.setSpacing(12)
        self.views = []
        self.after_title = None
        for index, title in enumerate(('ORIGINAL', 'CON PELÍCULA')):
            frame = QFrame()
            frame.setObjectName('photoFrame')
            column = QVBoxLayout(frame)
            column.setContentsMargins(10, 12, 10, 10)
            label = QLabel(title)
            label.setObjectName('photoLabel')
            label.setWordWrap(True)
            label.setToolTip('Revelado RAW de referencia en sRGB' if index == 0 else 'Simulación y grano seleccionados')
            column.addWidget(label)
            if index: self.after_title = label
            view = QLabel('Tu imagen empieza aquí\n\nImporta un archivo Sony .ARW' if index == 0
                          else 'Encuentra tu look\n\nElige una película de la colección')
            view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            view.setMinimumSize(160, 160)
            view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            view.setObjectName('photoView')
            column.addWidget(view, 1)
            self.views.append(view)
            self.panes.addWidget(frame, 1)
        workspace.addLayout(self.panes, 1)
        caption = QLabel('ANTES / DESPUÉS     ·     Misma foto, otra sensación.')
        caption.setObjectName('muted')
        workspace.addWidget(caption)
        splitter.addWidget(compare)
        splitter.setStretchFactor(1,1)
        splitter.setSizes([370, 1000])
        layout.addWidget(splitter,1)
        footer = QHBoxLayout()
        self.status = QLabel('Listo para revelar')
        self.status.setObjectName('muted')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        footer.addWidget(self.status, 1)
        signature = QLabel('RAW → FILM → JPEG')
        signature.setObjectName('eyebrow')
        footer.addWidget(signature)
        layout.addLayout(footer)
        self.progress=QProgressBar()
        self.progress.setRange(0,0)
        self.progress.setTextVisible(False)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.setCentralWidget(root)
        self.open_button.clicked.connect(self.open_raw)
        self.look.currentTextChanged.connect(self.selected_look)
        self.origin.currentTextChanged.connect(self.refresh_gallery)
        self.search.textChanged.connect(self.refresh_gallery)
        self.gallery.currentItemChanged.connect(self.selected_card)
        self.grain.currentTextChanged.connect(self.render)
        self.save_button.clicked.connect(self.save)
        self.import_button.clicked.connect(self.import_custom)
        self.recipe_button.clicked.connect(self.save_recipe)
        QShortcut(QKeySequence.StandardKey.Open,self,activated=self.open_raw)
        QShortcut(QKeySequence.StandardKey.SaveAs,self,activated=self.save)
        self.refresh_gallery()
        self.set_busy(False)

    def import_custom(self):
        path,_=QFileDialog.getOpenFileName(self,'Añadir perfil sRGB','','LUT o receta (*.cube *.png *.json)')
        if not path: return
        try:
            key=user_library.import_profile(Path(path),LOOKS)
            reference_thumbnails.cache_clear()
            thumb=uint8(apply_look(reference_linear(),key))
            self.thumbs[key]=add_canister(pixmap(thumb),metadata(key)['label'])
            self.origin.blockSignals(True)
            self.origin.clear()
            self.origin.addItems(['Todos los orígenes',*origins()])
            self.origin.setCurrentText('Comunidad / local')
            self.origin.blockSignals(False)
            self.search.clear()
            self.refresh_gallery()
            self.look.setCurrentText(key)
            self.status.setText('Perfil guardado en tu biblioteca local · entrada sRGB')
        except (OSError,ValueError,KeyError) as exc:
            self.error(str(exc))

    def save_recipe(self):
        base=self.look.currentText()
        if not base or LOOKS[base].get('backend')=='recipe':
            self.error('Selecciona una simulación o LUT base para crear una receta.')
            return
        name,ok=QInputDialog.getText(self,'Guardar receta','Nombre de tu receta:')
        if not ok or not name.strip(): return
        path,_=QFileDialog.getSaveFileName(self,'Guardar receta',name.strip()+'.json','Receta Film POC (*.json)')
        if path:
            data={'version':1,'name':name.strip(),'base_look':base,'strength':1.0,
                  'grain':self.grain.currentText(),'input_space':'sRGB'}
            try:
                user_library.validate_recipe(data,LOOKS)
                Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                self.status.setText('Receta guardada. Puedes compartir el JSON o añadirlo a tu biblioteca.')
            except (OSError,ValueError) as exc: self.error(str(exc))

    def refresh_gallery(self, *_):
        previous = self.look.currentText()
        names = filtered_names(self.origin.currentText(), self.search.text())
        self.look.blockSignals(True)
        self.gallery.blockSignals(True)
        self.look.clear()
        self.gallery.clear()
        self.look.addItems(names)
        for name in names:
            info = metadata(name)
            card_origin = {'spektrafilm / Film Lab':'spektrafilm',
                           'Pat David / HaldCLUT':'Pat David'}.get(info['origin'],info['origin'])
            item = QListWidgetItem(info['label']+'\n'+card_origin)
            item.setData(Qt.ItemDataRole.UserRole,name)
            item.setToolTip(info['detail']+'\nCarrete ilustrativo; no es fotografía del producto.')
            if name in self.thumbs:
                item.setIcon(QIcon(self.thumbs[name]))
            else:
                placeholder = QPixmap(140,95)
                placeholder.fill(Qt.GlobalColor.darkGray)
                item.setIcon(QIcon(placeholder))
            self.gallery.addItem(item)
        if names:
            self.look.setCurrentIndex(names.index(previous) if previous in names else 0)
            self.gallery.setCurrentRow(self.look.currentIndex())
        self.look.blockSignals(False)
        self.gallery.blockSignals(False)
        self.count.setText(f'{len(names)} / {len(LOOKS)}')
        self.selected_look()

    def selected_card(self, item, previous=None):
        if item:
            self.look.setCurrentText(item.data(Qt.ItemDataRole.UserRole))

    def selected_look(self, *_):
        name = self.look.currentText()
        if name:
            info = metadata(name)
            self.details.setText(info['label']+'\n'+info['detail'])
            self.after_title.setText('CON PELÍCULA · '+info['label'].upper())
            if LOOKS[name].get('backend')=='recipe':
                self.grain.blockSignals(True)
                self.grain.setCurrentText(LOOKS[name]['recipe'].get('grain','Desactivado'))
                self.grain.blockSignals(False)
            self.gallery.blockSignals(True)
            self.gallery.setCurrentRow(self.look.currentIndex())
            self.gallery.blockSignals(False)
        else:
            self.details.setText('Sin coincidencias. Cambia el origen o la búsqueda.')
        self.save_button.setEnabled(not self.busy and self.linear is not None and bool(name))
        self.render()

    def set_busy(self, busy):
        self.busy = busy
        self.open_button.setEnabled(not busy)
        self.look.setEnabled(not busy)
        self.grain.setEnabled(not busy)
        self.origin.setEnabled(not busy)
        self.search.setEnabled(not busy)
        self.gallery.setEnabled(not busy)
        self.import_button.setEnabled(not busy)
        self.recipe_button.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.save_button.setEnabled(not busy and self.linear is not None and bool(self.look.currentText()))

    def run_job(self, operation, callback, message):
        self.set_busy(True)
        self.status.setText(message)
        self.job = Job(operation, self)
        self.job.done.connect(callback)
        self.job.failed.connect(self.error)
        self.job.finished.connect(lambda: self.set_busy(False))
        self.job.start()

    def error(self, message):
        self.status.setText('No se pudo completar la operación.')
        QMessageBox.warning(self, 'Film POC', message)

    def open_raw(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Importar Sony RAW', '', 'Sony RAW (*.arw *.ARW)')
        if path:
            self.run_job(lambda: load_photo(Path(path)), self.loaded, 'Revelando RAW…')

    def loaded(self, result):
        self.source, self.linear = result[:2]
        self.photo_title.setText(self.source.name)
        self.photo_title.setToolTip(self.source.name)
        self.photo_meta.setText(f'{self.linear.shape[1]} × {self.linear.shape[0]} · Sony RAW')
        step = max(1, (max(self.linear.shape[:2])+1599)//1600)
        self.preview_step = step
        self.preview = self.linear[::step, ::step].copy()
        self.refresh_gallery()
        self.status.setText(f'{self.source.name} · {self.linear.shape[1]} × {self.linear.shape[0]}')

    def render(self, *_):
        if self.preview is None or not self.look.currentText():
            return
        self.pixmaps = []
        after = apply_grain(apply_look(self.preview, self.look.currentText()),
                            self.grain.currentText(), step=self.preview_step)
        for rgb in (render_base(self.preview), after):
            a = uint8(rgb)
            image = QImage(a.data, a.shape[1], a.shape[0], a.strides[0], QImage.Format.Format_RGB888).copy()
            self.pixmaps.append(QPixmap.fromImage(image))
        self.fit_images()

    def fit_images(self):
        for view, pixmap in zip(self.views, self.pixmaps):
            view.setPixmap(pixmap.scaled(view.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'panes'):
            direction = (QBoxLayout.Direction.TopToBottom if self.width() < 1180
                         else QBoxLayout.Direction.LeftToRight)
            self.panes.setDirection(direction)
        self.fit_images()

    def save(self):
        if self.linear is None or self.busy or not self.look.currentText(): return
        tag = look_slug(self.look.currentText())
        grain = self.grain.currentText()
        grain_tag = '' if grain == 'Desactivado' else '_grano_' + grain.lower()
        default = self.source.with_name(self.source.stem + f'_{tag}{grain_tag}_v3.jpg')
        path, _ = QFileDialog.getSaveFileName(self, 'Exportar JPEG', str(default), 'JPEG (*.jpg *.jpeg)')
        if path:
            destination = Path(path)
            if not destination.suffix:
                destination = destination.with_suffix('.jpg')
            name = self.look.currentText()
            self.run_job(lambda: export_jpeg(self.linear, name, destination, grain=grain),
                         lambda _: self.status.setText(f'Exportado: {destination}'), 'Exportando resolución completa…')

    def closeEvent(self, event):
        if self.job is not None and self.job.isRunning():
            self.status.setText('Espera a que termine la operación antes de cerrar.')
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
