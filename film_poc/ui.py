import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QComboBox,
                               QFileDialog, QMessageBox, QLineEdit, QListWidget,
                               QListWidgetItem, QAbstractItemView, QSplitter, QProgressBar, QInputDialog)
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
        self.setWindowTitle('Film POC · 0.4 · biblioteca de películas')
        user_library.load_library(LOOKS)
        reference_thumbnails.cache_clear()
        self.resize(1380, 820)
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
        bar = QHBoxLayout()
        self.open_button = QPushButton('Importar RAW')
        self.open_button.setObjectName('primary')
        self.look = QComboBox()
        self.look.addItems(LOOKS)
        self.look.setMinimumContentsLength(30)
        self.grain = QComboBox()
        self.grain.addItems(GRAIN)
        self.grain.setToolTip('Grano monocromático: desactivado, suave o fuerte')
        self.save_button = QPushButton('Exportar JPEG')
        for widget in (self.open_button, QLabel('Grano'), self.grain, self.save_button):
            bar.addWidget(widget)
        layout.addLayout(bar)
        subtitle=QLabel('FILM POC    /    Importa · elige una película · exporta')
        subtitle.setObjectName('muted')
        layout.addWidget(subtitle)
        splitter = QSplitter()
        sidebar = QWidget()
        side = QVBoxLayout(sidebar)
        heading = QLabel('Simulaciones')
        heading.setStyleSheet('font-size: 19px; font-weight: bold;')
        side.addWidget(heading)
        self.origin = QComboBox()
        self.origin.addItems(['Todos los orígenes', *origins()])
        self.origin.setAccessibleName('Filtrar simulaciones por origen')
        side.addWidget(self.origin)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Buscar película o simulación…')
        self.search.setAccessibleName('Buscar simulación')
        side.addWidget(self.search)
        side.addWidget(self.look)
        self.count = QLabel()
        side.addWidget(self.count)
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setMovement(QListWidget.Movement.Static)
        self.gallery.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.gallery.setIconSize(QSize(140,95))
        self.gallery.setGridSize(QSize(156,160))
        self.gallery.setWordWrap(True)
        self.gallery.setSpacing(3)
        self.gallery.setAccessibleName('Galería de simulaciones sobre una referencia fija')
        side.addWidget(self.gallery,1)
        self.details = QLabel('Selecciona un look. Las tarjetas muestran una foto de referencia fija.')
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(64)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        side.addWidget(self.details)
        reference_note=QLabel('Referencia fija ilustrativa · sin grano. Tu foto se compara a la derecha.')
        reference_note.setObjectName('muted')
        reference_note.setWordWrap(True)
        side.addWidget(reference_note)
        self.import_button=QPushButton('Añadir LUT o receta…')
        self.recipe_button=QPushButton('Guardar receta…')
        side.addWidget(self.import_button)
        side.addWidget(self.recipe_button)
        sidebar.setMinimumWidth(355)
        sidebar.setMaximumWidth(460)
        splitter.addWidget(sidebar)
        compare = QWidget()
        panes = QHBoxLayout()
        self.views = []
        for title in ('Antes · revelado base sRGB', 'Después · simulación'):
            column = QVBoxLayout()
            column.addWidget(QLabel(title))
            view = QLabel('Importa un archivo .ARW')
            view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            view.setMinimumSize(200, 200)
            view.setStyleSheet('background: #202226; color: #ddd;')
            column.addWidget(view, 1)
            self.views.append(view)
            panes.addLayout(column)
        compare.setLayout(panes)
        splitter.addWidget(compare)
        splitter.setStretchFactor(1,1)
        layout.addWidget(splitter,1)
        self.status = QLabel('Listo')
        layout.addWidget(self.status)
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
        self.count.setText(f'{len(names)} / {len(LOOKS)} simulaciones')
        self.selected_look()

    def selected_card(self, item, previous=None):
        if item:
            self.look.setCurrentText(item.data(Qt.ItemDataRole.UserRole))

    def selected_look(self, *_):
        name = self.look.currentText()
        if name:
            info = metadata(name)
            self.details.setText(info['label']+'\n'+info['detail'])
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
