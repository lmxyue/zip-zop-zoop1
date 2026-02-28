import os, sys, shutil, tempfile, zipfile, uuid
from pathlib import Path

from PyQt5.QtCore   import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QListWidget, QPushButton,
    QLabel, QPlainTextEdit, QMessageBox, QCheckBox
)

# WORKER THREAD  
class FlattenerWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, folders, super_flatten: bool, dry_run: bool):
        super().__init__()
        self.folders        = folders           
        self.super_flatten  = super_flatten
        self.dry_run        = dry_run

    # ── thread entrypoint
    def run(self):
        for folder in self.folders:
            self.progress.emit(f"\n▶ Folder: {folder}")
            for outer_zip in folder.glob("*.zip"):
                try:
                    has_inner_zips = self._flatten_zip(outer_zip)
                    tag = " [DRY-RUN]" if self.dry_run else ""
                    if has_inner_zips:
                        self.progress.emit(
                            f"  ✔ {'Super‑' if self.super_flatten else ''}Flattened {outer_zip.name}{tag}"
                        )
                    else:
                        self.progress.emit(
                            f"  ✔ {outer_zip.name} (no inner zips){tag}"
                        )
                except Exception as exc:
                    tag = " [DRY-RUN]" if self.dry_run else ""
                    self.progress.emit(f"  ✖ {outer_zip.name} → {exc}{tag}")
        self.finished.emit()

    # core routine
    def _flatten_zip(self, outer_zip_path: Path) -> bool:
        """
        Rewrites *outer_zip_path* so every inner zip is unpacked and –
        if super_flatten is True – any single top‑level folder layer is removed.
        Returns True if inner zips were found, False otherwise.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            with zipfile.ZipFile(outer_zip_path) as zf:
                zf.extractall(tmp_dir)

            inner_zips = list(tmp_dir.rglob("*.zip"))
            if not inner_zips:
                return False

            for inner in inner_zips:
                with zipfile.ZipFile(inner) as inz:
                    inz.extractall(tmp_dir / inner.stem)
                inner.unlink()

            if self.super_flatten:
                self._strip_one_folder_level(tmp_dir)

            if self.dry_run:
                return True

            tmp_zip = outer_zip_path.with_suffix(".tmp")
            with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in tmp_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(tmp_dir))

            shutil.move(tmp_zip, outer_zip_path)
            return True

    # helper: move all files up one level, resolve name clashes
    def _strip_one_folder_level(self, root: Path):
        """
        If every item in *root* is a directory, move the *files* inside those
        dirs up to *root*, flattening the structure one level deep.
        """
        top_items = list(root.iterdir())
        if not top_items or not all(p.is_dir() for p in top_items):
            return  # nothing to peel

        for sub in top_items:
            for file in sub.rglob("*"):
                if file.is_file():
                    target = root / file.name
                    if target.exists():
                        # ensure unique filename
                        stem, suf = file.stem, file.suffix
                        target = root / f"{stem}_{uuid.uuid4().hex[:6]}{suf}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file), target)
            shutil.rmtree(sub)

# MAIN WINDOW
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zip‑in‑Zip Flattener 🔧 – drag folders here")
        self.resize(700, 440)
        self.setAcceptDrops(True)

        # widgets
        self.folder_list  = QListWidget()
        self.log_box      = QPlainTextEdit(readOnly=True)
        self.flatten_btn  = QPushButton("Flatten Zips")
        self.sflatten_btn = QPushButton("Super Flatten Zips")
        self.clear_btn    = QPushButton("Clear List")
        self.dry_run_cb   = QCheckBox("dry-run (log only no write)")

        # layout
        lay = QVBoxLayout()
        lay.addWidget(QLabel("Queued Folders (drag & drop):"))
        lay.addWidget(self.folder_list, 1)
        lay.addWidget(self.flatten_btn)
        lay.addWidget(self.sflatten_btn)
        lay.addWidget(self.dry_run_cb)
        lay.addWidget(self.clear_btn)
        lay.addWidget(QLabel("Log:"))
        lay.addWidget(self.log_box, 2)
        container = QWidget(); container.setLayout(lay)
        self.setCentralWidget(container)

        # signals
        self.flatten_btn.clicked .connect(lambda: self._start(False))
        self.sflatten_btn.clicked.connect(lambda: self._start(True))
        self.clear_btn.clicked   .connect(self.folder_list.clear)

    # drag‑and‑drop support
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir() and p not in self._current_folders():
                self.folder_list.addItem(str(p))

    def _current_folders(self):
        return [Path(self.folder_list.item(i).text()) for i in range(self.folder_list.count())]

    # launch worker
    def _start(self, super_flat):
        folders = self._current_folders()
        if not folders:
            QMessageBox.warning(self, "No folders", "Drag some folders onto the window first.")
            return

        dry_run = self.dry_run_cb.isChecked()

        self.flatten_btn.setEnabled(False)
        self.sflatten_btn.setEnabled(False)

        self.worker = FlattenerWorker(folders, super_flatten=super_flat, dry_run=dry_run)
        self.worker.progress.connect(self.log_box.appendPlainText)
        self.worker.finished.connect(self._done)
        self.worker.start()

    def _done(self):
        self.flatten_btn.setEnabled(True)
        self.sflatten_btn.setEnabled(True)
        self.log_box.appendPlainText("\n✓ All done!\n")
        QMessageBox.information(self, "Finished", "Processing complete.")

# main 
if __name__ == "__main__":
    # Optional: avoid rare macOS layer bug
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
