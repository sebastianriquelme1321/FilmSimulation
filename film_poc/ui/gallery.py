"""Film gallery: filtered cards, each with a fixed-reference thumbnail."""
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QListWidget, QListWidgetItem

from ..core.render import LOOKS
from ..services.catalog import filtered_names, metadata
from .film_badge import add_canister
from .images import pixmap

SHORT_ORIGINS = {'spektrafilm / Film Lab': 'spektrafilm', 'Pat David / HaldCLUT': 'Pat David'}


class Gallery(QListWidget):
    """Icon list of films; emits selected(name) when the user picks one."""

    selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setIconSize(QSize(140, 95))
        self.setGridSize(QSize(154, 152))
        self.setWordWrap(True)
        self.setSpacing(3)
        self.setAccessibleName('Galería de simulaciones sobre una referencia fija')
        self.thumbs = {}
        # The list is the visible selector; this hidden combo is its selection model.
        self.look = QComboBox(self)
        self.look.setAccessibleName('Simulación seleccionada')
        self.look.hide()
        self.look.currentTextChanged.connect(self._look_changed)
        self.itemClicked.connect(self._card_chosen)
        self.itemActivated.connect(self._card_chosen)

    def add_thumbnails(self, images):
        """Cache a canister-badged thumbnail for each known film in {name: rgb}."""
        for name, rgb in images.items():
            if name in LOOKS:
                self.add_thumbnail(name, rgb)

    def add_thumbnail(self, name, rgb):
        """Cache the canister-badged thumbnail of one film."""
        self.thumbs[name] = add_canister(pixmap(rgb), metadata(name)['label'])

    def populate(self, origin, query, active):
        """Show the films matching the filters, keep `active` highlighted; return the count."""
        names = filtered_names(origin, query)
        self.look.blockSignals(True)
        self.blockSignals(True)
        self.look.clear()
        self.clear()
        self.look.addItems(names)
        for name in names:
            self.addItem(self._card(name))
        index = names.index(active) if active in names else -1
        self.look.setCurrentIndex(index)
        self.setCurrentRow(index)
        self._reveal_current()
        self.look.blockSignals(False)
        self.blockSignals(False)
        return len(names)

    def _card(self, name):
        info = metadata(name)
        origin = SHORT_ORIGINS.get(info['origin'], info['origin'])
        item = QListWidgetItem(info['label'] + '\n' + origin)
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setToolTip(info['detail'] + '\nCarrete ilustrativo; no es fotografía del producto.')
        if name in self.thumbs:
            item.setIcon(QIcon(self.thumbs[name]))
        else:
            placeholder = QPixmap(140, 95)
            placeholder.fill(Qt.GlobalColor.darkGray)
            item.setIcon(QIcon(placeholder))
        return item

    def _card_chosen(self, item):
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if self.look.currentText() == name:
            self.selected.emit(name)
        else:
            self.look.setCurrentText(name)

    def _look_changed(self, name):
        if not name:
            return
        self.blockSignals(True)
        self.setCurrentRow(self.look.currentIndex())
        self.blockSignals(False)
        self._reveal_current()
        self.selected.emit(name)

    def _reveal_current(self):
        """Scroll so the active card is visible; a selection off-screen reads as none."""
        item = self.currentItem()
        if item is not None:
            self.scrollToItem(item, QAbstractItemView.ScrollHint.EnsureVisible)
