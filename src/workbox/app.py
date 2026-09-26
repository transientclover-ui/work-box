"""A small native Qt shell; project data and process logic remain independent."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
from PySide6.QtCore import Qt, QTimer, QUrl, QSettings
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem, QTextEdit,
    QFileDialog, QInputDialog, QMessageBox, QGroupBox)
from .storage import Box
from .workers import WORKERS
from .runner import Run


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.box = None
        self.run = None
        self.closing = False
        self.readiness = {}
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.probes = {}
        self.settings = QSettings('WorkBox', 'WorkBox')
        self.setWindowTitle('Work Box')
        self.setWindowIcon(QIcon.fromTheme('folder'))
        self.resize(860, 780)
        self.setAcceptDrops(True)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        top = QHBoxLayout()
        self.create_button = self.button('Create Box…', self.create_box)
        self.open_button = self.button('Open Box…', self.open_box)
        top.addWidget(self.create_button)
        top.addWidget(self.open_button)
        top.addStretch()
        top.addWidget(QLabel('Appearance'))
        self.appearance = QComboBox()
        self.appearance.addItems(['System', 'Light', 'Dark'])
        self.appearance.setCurrentText(self.settings.value('appearance', 'System'))
        self.appearance.currentTextChanged.connect(self.theme)
        top.addWidget(self.appearance)
        layout.addLayout(top)
        self.heading = QLabel('A place for your project.')
        font = self.heading.font()
        font.setPointSize(font.pointSize() + 10)
        font.setBold(True)
        self.heading.setFont(font)
        layout.addWidget(self.heading)
        self.subtitle = QLabel('Create or open a Box. Your files stay where you keep them.')
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)
        self.content = QGroupBox('In this Box')
        content = QVBoxLayout(self.content)
        self.files = QListWidget()
        self.files.setMinimumHeight(140)
        self.files.itemDoubleClicked.connect(self.open_item)
        content.addWidget(self.files)
        row = QHBoxLayout()
        row.addWidget(self.button('Add files…', self.add_files))
        row.addWidget(self.button('Associate folder…', lambda: self.add_folder('location')))
        row.addWidget(self.button('Set repository…', lambda: self.add_folder('repository')))
        row.addWidget(self.button('Open selected', self.open_selected))
        content.addLayout(row)
        note = QLabel('Drop files or folders here to reference them in place. Nothing is moved or copied.')
        note.setWordWrap(True)
        content.addWidget(note)
        layout.addWidget(self.content)
        work = QGroupBox('Give work')
        wl = QVBoxLayout(work)
        row = QHBoxLayout()
        self.worker = QComboBox()
        self.worker.addItems([w.name for w in WORKERS])
        self.worker.currentIndexChanged.connect(self.refresh_readiness)
        row.addWidget(self.worker)
        self.refresh_button = self.button('Refresh workers', self.detect)
        row.addWidget(self.refresh_button)
        row.addStretch()
        wl.addLayout(row)
        self.worker_status = QLabel('Checking installed workers…')
        self.worker_status.setWordWrap(True)
        wl.addWidget(self.worker_status)
        self.cwd = QComboBox()
        self.cwd.setToolTip('The worker may edit files in this working folder.')
        wl.addWidget(QLabel('Working folder'))
        wl.addWidget(self.cwd)
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText('What would you like done? Include which files may be changed.')
        self.prompt.setMaximumHeight(100)
        self.prompt.textChanged.connect(self.update_buttons)
        wl.addWidget(self.prompt)
        self.scope = QLabel('Codex may edit the working folder using its workspace sandbox. Other locations are references. Authentication stays with the installed worker.')
        self.scope.setWordWrap(True)
        wl.addWidget(self.scope)
        row = QHBoxLayout()
        self.give = self.button('Give Work', self.give_work)
        row.addWidget(self.give)
        row.addStretch()
        self.halt = self.button('HALT', self.halt_work)
        self.halt.setStyleSheet('QPushButton {background: #ad3037; color: white; font-weight: bold; padding: 10px 28px;}')
        row.addWidget(self.halt)
        wl.addLayout(row)
        layout.addWidget(work)
        self.status = QLabel('No work running.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(QLabel('Recent tasks · double-click to open saved work'))
        self.history = QListWidget()
        self.history.setMaximumHeight(110)
        self.history.setToolTip('Double-click a task to open its durable request, context, and log folder.')
        self.history.itemDoubleClicked.connect(self.open_item)
        layout.addWidget(self.history)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(150)
        self.theme(self.appearance.currentText())
        self.detect()
        self.update_buttons()

    def button(self, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

    def guarded(self, callback):
        try:
            callback()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, 'Work Box', str(exc))

    def theme(self, text):
        scheme = {'System': Qt.ColorScheme.Unknown, 'Light': Qt.ColorScheme.Light, 'Dark': Qt.ColorScheme.Dark}[text]
        QApplication.styleHints().setColorScheme(scheme)
        self.settings.setValue('appearance', text)

    def select_box(self, box):
        if self.box:
            self.box.close()
        self.box = box
        self.refresh_box()

    def create_box(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choose the Box metadata folder')
        if not folder:
            return
        name, ok = QInputDialog.getText(self, 'Create Box', 'Project name', text=Path(folder).name)
        if ok:
            self.guarded(lambda: self.select_box(Box.create(Path(folder), name)))

    def open_box(self):
        folder = QFileDialog.getExistingDirectory(self, 'Open a folder containing .workbox')
        if folder:
            self.guarded(lambda: self.select_box(Box(Path(folder))))

    def refresh_box(self):
        self.heading.setText(self.box.data['name'])
        self.subtitle.setText(str(self.box.root))
        self.files.clear()
        self.cwd.clear()
        for entry in self.box.data['locations']:
            path = entry['path']
            label = 'Repository' if path == self.box.data['repository'] else 'Location'
            self.add_item(self.files, f'{label}  ·  {path}', path)
            if Path(path).is_dir():
                self.cwd.addItem(path)
        if self.box.data['repository']:
            self.cwd.setCurrentText(self.box.data['repository'])
        for entry in self.box.data['materials']:
            self.add_item(self.files, f'Material  ·  {entry["path"]}', entry['path'])
        self.refresh_history()
        self.update_buttons()

    def add_item(self, widget, text, path):
        item = QListWidgetItem(text + ('  [missing]' if not Path(path).exists() else ''))
        item.setData(Qt.ItemDataRole.UserRole, str(path))
        item.setToolTip(str(path))
        widget.addItem(item)

    def associate(self, paths, kind='material'):
        for path in paths:
            self.box.associate(Path(path), kind)
        self.refresh_box()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Reference files in this Box')
        self.guarded(lambda: self.associate(paths))

    def add_folder(self, kind):
        path = QFileDialog.getExistingDirectory(self, 'Associate existing folder')
        if path:
            self.guarded(lambda: self.associate([path], kind))

    def open_item(self, item):
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        if not path.exists():
            QMessageBox.warning(self, 'Missing location', str(path))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path if path.is_dir() else path.parent)))

    def open_selected(self):
        if self.files.currentItem():
            self.open_item(self.files.currentItem())

    def dragEnterEvent(self, event):
        if self.box and not self.active() and event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if self.box and not self.active():
            self.guarded(lambda: self.associate([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]))
            event.acceptProposedAction()

    def detect(self):
        if self.probes:
            return
        self.probes = {w.id: self.pool.submit(w.detect) for w in WORKERS}
        self.refresh_button.setEnabled(False)

    def refresh_readiness(self):
        adapter = WORKERS[self.worker.currentIndex()]
        ready = self.readiness.get(adapter.id)
        text = 'Checking installed workers…' if ready is None else f'{ready.version}\n{ready.detail}'
        if not adapter.can_launch:
            text += ' · detection only in this release'
        self.worker_status.setText(text)
        self.update_buttons()

    def active(self):
        return self.run is not None and self.run.active

    def update_buttons(self):
        active = self.active()
        adapter = WORKERS[self.worker.currentIndex()]
        ready = self.readiness.get(adapter.id)
        self.give.setEnabled(bool(self.box and not active and adapter.can_launch and ready and ready.executable and self.prompt.toPlainText().strip() and self.cwd.currentText()))
        self.halt.setVisible(active)
        for widget in (self.create_button, self.open_button, self.worker, self.cwd, self.prompt):
            widget.setEnabled(not active)
        self.content.setEnabled(self.box is not None and not active)

    def give_work(self):
        def start():
            adapter = WORKERS[self.worker.currentIndex()]
            self.run = Run(self.box, adapter, self.readiness[adapter.id].executable,
                           Path(self.cwd.currentText()), self.prompt.toPlainText())
            self.update_buttons()
            self.refresh_history()
        self.guarded(start)

    def halt_work(self):
        if self.run:
            # Pipe close still reaches watchdog if the disk cannot record intent.
            try:
                self.run.halt()
            except OSError as exc:
                if self.run.process.stdin and not self.run.process.stdin.closed:
                    self.run.process.stdin.close()
                self.status.setText(f'Stopping. Could not persist HALT marker: {exc}')

    def refresh_history(self):
        self.history.clear()
        if self.box:
            for path, task in reversed(self.box.tasks()):
                self.add_item(self.history, f'{task["status"].capitalize()}  ·  {task["created_at"][:19]}  ·  {", ".join(task["authorized_workers"])}', path.parent)

    def tick(self):
        if self.probes and all(p.done() for p in self.probes.values()):
            self.readiness = {key: p.result() for key, p in self.probes.items()}
            self.probes = {}
            self.refresh_button.setEnabled(True)
            self.refresh_readiness()
        if self.run:
            try:
                state = self.run.state()
                self.status.setText(f'{state["status"].capitalize()} · {state.get("detail", "Results and logs are being saved to the Box.")}')
                if not self.run.active:
                    self.run.process.stdin.close()
                    self.run = None
                    self.box.recover()
                    self.refresh_history()
                    self.update_buttons()
                    if self.closing:
                        self.close()
            except (OSError, ValueError) as exc:
                self.status.setText(f'Task record unavailable: {exc}. HALT remains available.')

    def closeEvent(self, event):
        if self.active():
            self.closing = True
            self.halt_work()
            event.ignore()
            return
        self.pool.shutdown(wait=False)
        if self.box:
            self.box.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Work Box')
    window = Window()
    if len(sys.argv) > 1:
        window.guarded(lambda: window.select_box(Box(Path(sys.argv[1]))))
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
