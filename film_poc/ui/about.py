"""Ayuda > Acerca de: version, license, repository and the independence disclaimer."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from ..services.diagnostics import REPO_URL, app_version

DESCRIPTION = 'Simulación de película para fotos RAW, en local y sin conexión.'
DISCLAIMER = (
    'Proyecto independiente, sin afiliación ni respaldo de Kodak, Fujifilm, Ilford u otras '
    'marcas citadas. Los nombres de películas se usan solo para describir qué se aproxima. '
    'Los looks son aproximaciones y no equivalen a los procesos originales. Todo se procesa '
    'en tu equipo; la aplicación no envía datos.')


class AboutDialog(QDialog):
    """Modal about box."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Acerca de FilmSimulation')
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        title = QLabel(f'<h2>FilmSimulation {app_version()}</h2>')
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)
        body = QLabel(
            f'<p>{DESCRIPTION}</p>'
            '<p>Software libre bajo licencia GPL-3.0-or-later.<br>'
            f'Repositorio: <a href="{REPO_URL}">{REPO_URL}</a><br>'
            'Avisos de terceros: consulta THIRD_PARTY_NOTICES.md en el repositorio.</p>'
            f'<p><b>Aviso.</b> {DISCLAIMER}</p>')
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        body.setOpenExternalLinks(True)
        layout.addWidget(body)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.body = body
