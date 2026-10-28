import json
import os
from pathlib import Path
import sys
from PySide6.QtCore import QProcess, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLayout, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget)
from . import __version__
from .catalog import MODELS, get_model
from .core import Request, load_settings, model_root, save_settings

STYLE = """
QWidget { background:#11121a; color:#e8e8f2; font-family:'Segoe UI','Arial'; font-size:13px; }
QFrame#sidebar { background:#181923; border-right:1px solid #303142; }
QLabel#brand { color:#c3b0ff; font-size:18px; font-weight:800; }
QLabel#headline { font-size:30px; font-weight:800; }
QLabel#muted { color:#9b9eb4; }
QLabel#badge { background:#213c34; color:#8de8bc; border-radius:10px; padding:8px 12px; }
QFrame#card { background:#1b1c29; border:1px solid #333448; border-radius:16px; }
QFrame#card QLabel { background:transparent; }
QLineEdit,QPlainTextEdit,QComboBox,QSpinBox,QDoubleSpinBox { background:#202132; border:1px solid #3a3c53; border-radius:8px; padding:9px; selection-background-color:#7956d6; }
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox { min-height:18px; }
QScrollArea { border:0; }
QScrollBar:vertical { background:#191a26; width:8px; border:0; }
QScrollBar::handle:vertical { background:#45425c; min-height:30px; border-radius:4px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QLineEdit:focus,QPlainTextEdit:focus { border:1px solid #a387f7; }
QPushButton { background:#292a3d; border:1px solid #41435c; border-radius:9px; padding:11px; font-weight:600; }
QPushButton:hover { background:#383650; border-color:#9e81ee; }
QPushButton:checked { background:#423461; color:#dfd0ff; border-color:#9871f2; }
QPushButton#primary { background:#a582fa; color:#151123; border:0; padding:14px; font-size:15px; }
QPushButton:disabled { color:#747689; background:#232435; }
QProgressBar { background:#28293c; border:0; border-radius:6px; height:10px; text-align:center; }
QProgressBar::chunk { background:#a582fa; border-radius:6px; }
QCheckBox { spacing:8px; }
"""


def spin(minimum, maximum, value, step=1):
    widget = QSpinBox()
    widget.setRange(minimum, maximum)
    widget.setSingleStep(step)
    widget.setValue(value)
    return widget


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local Ai Generator — Offline studio")
        self.resize(1200, 830)
        self.setMinimumSize(970, 720)
        self.process = None
        self.result = None
        self.buffer = b""
        self.stderr_buffer = ""
        self.kind = "image"
        self.settings = load_settings()
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(22, 30, 22, 24)
        logo = QLabel("◈ Local Ai Generator")
        logo.setObjectName("brand")
        nav.addWidget(logo)
        nav.addWidget(QLabel("AI STUDIO  /  " + __version__))
        nav.addSpacing(36)
        self.tabs = []
        for kind, label in (("image", "Obrázky"), ("video", "Video"), ("audio", "Zvuk")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, k=kind: self.change_kind(k))
            self.tabs.append((kind, button))
            nav.addWidget(button)
        nav.addStretch()
        privacy = QLabel("Tvoje nápady.\nTvůj počítač.\nBez API kreditů.")
        privacy.setObjectName("muted")
        nav.addWidget(privacy)
        help_button = QPushButton("Modely a licence ↗")
        help_button.clicked.connect(self.open_model_card)
        nav.addWidget(help_button)
        root.addWidget(sidebar)
        body = QVBoxLayout()
        body.setContentsMargins(30, 26, 30, 22)
        body.setSpacing(16)
        header = QHBoxLayout()
        self.title = QLabel("Vytvoř něco výjimečného.")
        self.title.setObjectName("headline")
        header.addWidget(self.title)
        header.addStretch()
        badge = QLabel("● OFFLINE GENEROVÁNÍ")
        badge.setObjectName("badge")
        header.addWidget(badge)
        body.addLayout(header)
        sub = QLabel("Obrázky, pohyb a zvuk. Model stáhneš jednou, tvoříš lokálně.")
        sub.setObjectName("muted")
        body.addWidget(sub)
        work = QHBoxLayout()
        editor = QVBoxLayout()
        editor.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        editor.setSpacing(10)
        editor.addWidget(QLabel("01  MODEL"))
        self.models = QComboBox()
        self.models.currentIndexChanged.connect(self.change_model)
        editor.addWidget(self.models)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("muted")
        editor.addWidget(self.note)
        model_actions = QHBoxLayout()
        self.download_button = QPushButton("Stáhnout model")
        self.download_button.clicked.connect(self.download_model)
        model_actions.addWidget(self.download_button)
        self.local_button = QPushButton("Lokální složka…")
        self.local_button.clicked.connect(self.choose_local)
        model_actions.addWidget(self.local_button)
        editor.addLayout(model_actions)
        self.local = QLineEdit()
        self.local.setPlaceholderText("Volitelná kompletní Diffusers složka")
        editor.addWidget(self.local)
        editor.addWidget(QLabel("02  POPIŠ SVOU PŘEDSTAVU"))
        self.prompt = QPlainTextEdit()
        self.prompt.setPlaceholderText("A cinematic mountain lake at sunrise, soft mist, natural light…")
        self.prompt.setMinimumHeight(110)
        self.prompt.setMaximumHeight(120)
        editor.addWidget(self.prompt)
        self.negative = QLineEdit()
        self.negative.setPlaceholderText("Negativní prompt: blurry, distorted…")
        editor.addWidget(self.negative)
        editor.addWidget(QLabel("03  NASTAVENÍ"))
        form = QFormLayout()
        self.device = QComboBox()
        for label, value in (("Auto — dostupné GPU / CPU", "auto"), ("CPU — kompatibilní základ", "cpu"), ("CUDA / ROCm — NVIDIA / vybrané AMD", "cuda"), ("MPS — Apple Silicon", "mps"), ("XPU — podporované Intel GPU", "xpu")):
            self.device.addItem(label, value)
        form.addRow("Zařízení", self.device)
        dimensions = QHBoxLayout()
        self.width = spin(256, 2048, 512, 32)
        self.height = spin(256, 2048, 512, 32)
        dimensions.addWidget(self.width)
        dimensions.addWidget(QLabel("×"))
        dimensions.addWidget(self.height)
        self.dimensions_widget = QWidget()
        self.dimensions_widget.setLayout(dimensions)
        form.addRow("Rozlišení", self.dimensions_widget)
        self.steps = spin(1, 150, 25)
        form.addRow("Kroky", self.steps)
        self.guidance = QDoubleSpinBox()
        self.guidance.setRange(0, 30)
        self.guidance.setValue(7.5)
        form.addRow("Guidance", self.guidance)
        self.seed = QLineEdit("-1")
        self.seed.setToolTip("-1 = náhodný; jinak 0–4294967295")
        form.addRow("Seed", self.seed)
        self.media = QStackedWidget()
        self.media.addWidget(QLabel("PNG + JSON s parametry"))
        video = QWidget()
        video_row = QHBoxLayout(video)
        video_row.setContentsMargins(0, 0, 0, 0)
        self.frames = spin(9, 161, 25, 8)
        self.fps = spin(1, 60, 24)
        video_row.addWidget(QLabel("Snímky"))
        video_row.addWidget(self.frames)
        video_row.addWidget(QLabel("FPS"))
        video_row.addWidget(self.fps)
        self.media.addWidget(video)
        self.seconds = spin(1, 10, 5)
        self.media.addWidget(self.seconds)
        form.addRow("Výstup / délka", self.media)
        self.offload = QCheckBox("Šetřit VRAM přes CPU offload (CUDA / ROCm)")
        self.offload.setChecked(True)
        form.addRow(self.offload)
        editor.addLayout(form)
        self.output = QLineEdit(self.settings.get("output", str(Path.home() / "Local-Ai-Generator-output")))
        output_row = QHBoxLayout()
        output_row.addWidget(self.output)
        self.output_button = QPushButton("…")
        self.output_button.clicked.connect(self.choose_output)
        output_row.addWidget(self.output_button)
        editor.addLayout(output_row)
        actions = QHBoxLayout()
        self.generate_button = QPushButton("✦  Vytvořit")
        self.generate_button.setObjectName("primary")
        self.generate_button.clicked.connect(self.start_generation)
        actions.addWidget(self.generate_button, 3)
        self.cancel_button = QPushButton("Zastavit")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        actions.addWidget(self.cancel_button, 1)
        editor_widget = QWidget()
        editor_widget.setLayout(editor)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(editor_widget)
        left = QVBoxLayout()
        left.addWidget(scroll, 1)
        left.addLayout(actions)
        work.addLayout(left, 6)
        right = QVBoxLayout()
        card = QFrame()
        card.setObjectName("card")
        preview_layout = QVBoxLayout(card)
        preview_layout.addWidget(QLabel("TVŮJ DALŠÍ VÝTVOR"))
        self.preview = QLabel("◈\n\nProstor pro tvoji představivost\n\nVýsledek se objeví tady.")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setMinimumSize(300, 300)
        preview_layout.addWidget(self.preview, 1)
        self.open_button = QPushButton("Otevřít výsledek ↗")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_result)
        preview_layout.addWidget(self.open_button)
        right.addWidget(card, 1)
        self.status = QLabel("Připraveno. Pro generování je potřeba lokální model.")
        self.status.setWordWrap(True)
        right.addWidget(self.status)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        right.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(180)
        self.log.setPlaceholderText("Průběh generování a případné chyby")
        right.addWidget(self.log)
        work.addLayout(right, 5)
        body.addLayout(work, 1)
        root.addLayout(body, 1)
        self.change_kind("image")

    def change_kind(self, kind):
        self.kind = kind
        for key, button in self.tabs:
            button.setChecked(key == kind)
        self.models.blockSignals(True)
        self.models.clear()
        for model in MODELS:
            if model.kind == kind:
                self.models.addItem(model.name, model.key)
        self.models.blockSignals(False)
        self.media.setCurrentIndex({"image": 0, "video": 1, "audio": 2}[kind])
        self.dimensions_widget.setEnabled(kind != "audio")
        self.local.clear()
        self.change_model()

    def change_model(self, *_):
        if not self.models.currentData():
            return
        model = get_model(self.models.currentData())
        self.width.setValue(model.width)
        self.height.setValue(model.height)
        self.steps.setValue(model.steps)
        self.guidance.setValue(model.guidance)
        self.local.clear()
        ready = any((model_root() / model.key / name).exists() for name in (".localaigenerator-complete", ".localaigenerator-complete"))
        self.note.setText(("✓ Staženo. " if ready else "Model zatím není stažen. ") + model.note)

    def choose_local(self):
        path = QFileDialog.getExistingDirectory(self, "Vyberte kompletní Diffusers model")
        if path:
            self.local.setText(path)

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Výstupní složka")
        if path:
            self.output.setText(path)

    def open_model_card(self):
        QDesktopServices.openUrl(QUrl(get_model(self.models.currentData()).url))

    def download_model(self):
        model = get_model(self.models.currentData())
        answer = QMessageBox.question(self, "Stáhnout model", f"{model.name}\n\nStažení potřebuje internet a může zabrat několik až desítky GB. Před použitím zkontrolujte licenci na kartě modelu. Některé modely vyžadují přijetí podmínek / HF přihlášení.\n\nZahájit stažení?")
        if answer == QMessageBox.StandardButton.Yes:
            self.launch("download", ["--model", model.key])

    def start_generation(self):
        try:
            request = Request(model=self.models.currentData(), prompt=self.prompt.toPlainText(), negative=self.negative.text(), output=self.output.text(), device=self.device.currentData(), width=self.width.value(), height=self.height.value(), steps=self.steps.value(), guidance=self.guidance.value(), seed=int(self.seed.text()), seconds=self.seconds.value(), frames=self.frames.value(), fps=self.fps.value(), offload=self.offload.isChecked(), local_model=self.local.text()).validate()
            save_settings({"output": request.output})
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Zkontrolujte nastavení", str(exc))
            return
        self.launch("generate", payload=request.to_dict())

    def launch(self, action, args=None, payload=None):
        if self.process:
            return
        self.buffer = b""
        self.stderr_buffer = ""
        self.cancelled = False
        self.received_done = False
        self.received_error = False
        self.progress.setRange(0, 0)
        self.status.setText("Spouštím…")
        self.log.clear()
        self.set_busy(True)
        process = QProcess(self)
        self.process = process
        process.setProgram(sys.executable)
        process.setArguments(["-u", "-m", "localaigenerator.worker", action] + (args or []))
        # Ensure source launch works from any current working directory.
        process.setWorkingDirectory(str(Path(__file__).resolve().parent.parent))
        process.readyReadStandardOutput.connect(self.read_stdout)
        process.readyReadStandardError.connect(self.read_stderr)
        process.finished.connect(self.finished)
        process.errorOccurred.connect(self.process_error)
        if payload is not None:
            process.started.connect(lambda: (process.write(json.dumps(payload).encode("utf-8")), process.closeWriteChannel()))
        process.start()

    def set_busy(self, busy):
        for widget in (self.generate_button, self.download_button, self.models, self.local_button):
            widget.setEnabled(not busy)
        for _, button in self.tabs:
            button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)

    def read_stdout(self):
        self.buffer += bytes(self.process.readAllStandardOutput())
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                event = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            if event.get("event") == "status":
                self.status.setText(event["text"])
                self.log.appendPlainText(event["text"])
            elif event.get("event") == "progress":
                self.progress.setRange(0, 100)
                self.progress.setValue(event["value"])
            elif event.get("event") == "error":
                self.received_error = True
                self.status.setText("Operace selhala. Podrobnosti jsou v protokolu.")
                self.log.appendPlainText(event["text"])
            elif event.get("event") == "done":
                self.received_done = True
                if "device" in event:
                    self.status.setText("Zařízení: " + event["name"])
                elif event.get("download"):
                    self.change_model()
                    self.status.setText("Model je stažený. Generování teď funguje offline.")
                else:
                    self.result = event["path"]
                    self.open_button.setEnabled(True)
                    pixmap = QPixmap(self.result)
                    if not pixmap.isNull():
                        self.preview.setPixmap(pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    else:
                        self.preview.setText("✓ Hotovo\n\n" + Path(self.result).name + "\n\nOtevři výsledek ve svém přehrávači.")
                    self.status.setText(f"Hotovo · seed {event['seed']}")
                    self.log.appendPlainText(self.result)

    def read_stderr(self):
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self.stderr_buffer = (self.stderr_buffer + text)[-12000:]
        self.log.appendPlainText(text.strip())

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.status.setText("Proces se nepodařilo spustit.")
            self.cleanup()

    def finished(self, code, *_):
        self.read_stdout()
        self.read_stderr()
        if self.cancelled:
            self.status.setText("Zastaveno. Případné neúplné soubory pending lze odstranit.")
        elif code != 0 and not self.received_error:
            self.status.setText("Proces selhal — může chybět paměť nebo AI závislosti. Viz protokol.")
        elif code == 0 and not self.received_done:
            self.status.setText("Proces skončil bez potvrzeného výsledku.")
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if self.received_done else 0)
        self.cleanup()

    def cleanup(self):
        if self.process:
            self.process.deleteLater()
        self.process = None
        self.set_busy(False)

    def cancel(self):
        if self.process:
            self.cancelled = True
            self.status.setText("Zastavuji…")
            self.process.kill()

    def open_result(self):
        if self.result:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.result))

    def closeEvent(self, event):
        if self.process:
            self.process.kill()
            self.process.waitForFinished(3000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
