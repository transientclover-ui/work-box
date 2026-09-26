import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSettings
from workbox.app import Window
from workbox.storage import Box


def test_shell_box_and_appearance(tmp_path):
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName('WorkBoxTests')
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / 'settings'))
    window = Window()
    assert not window.give.isEnabled()
    window.select_box(Box.create(tmp_path, 'Test Box'))
    window.show(); app.processEvents()
    assert window.heading.text() == 'Test Box'
    assert window.files.count() == 1
    for theme in ('Light', 'Dark', 'System'):
        window.theme(theme)
        app.processEvents()
    window.close()


def test_drop_references_file_without_copy(tmp_path):
    from PySide6.QtCore import QMimeData, QPointF, QUrl
    from PySide6.QtGui import QDropEvent
    app = QApplication.instance() or QApplication([])
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / 'settings'))
    project = tmp_path / 'project'; project.mkdir()
    source = tmp_path / 'notes.txt'; source.write_text('keep')
    window = Window(); window.select_box(Box.create(project, 'Test'))
    mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    window.dropEvent(event)
    assert window.box.data['materials'][0]['path'] == str(source)
    assert source.read_text() == 'keep'
    assert not (project / source.name).exists()
    window.close()
