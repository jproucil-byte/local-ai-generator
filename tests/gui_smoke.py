"""Optional Qt smoke test. No models or torch required."""
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from localaigenerator.gui import Window, STYLE

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
with tempfile.TemporaryDirectory() as folder:
    os.environ["LOCALAIGENERATOR_HOME"] = folder
    window = Window()
    window.show()
    app.processEvents()
    for kind in ("image", "video", "audio"):
        window.change_kind(kind)
        assert window.models.count() == (3 if kind == "image" else 1)
    window.change_kind("image")
    # The hardware command must either report actual hardware or a clean error,
    # and in either case the UI must recover from its busy state.
    window.launch("hardware")
    deadline = time.monotonic() + 20
    while window.process and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert window.process is None, "Worker did not finish"
    assert window.generate_button.isEnabled(), "UI remained busy"
    # Run a deliberately long subprocess to verify real process cancellation.
    from PySide6.QtCore import QProcess
    window.process = QProcess(window)
    window.process.setProgram(sys.executable)
    window.process.setArguments(["-c", "import time; time.sleep(20)"])
    window.process.finished.connect(window.finished)
    window.received_done = window.received_error = False
    window.cancelled = False
    window.set_busy(True)
    window.process.start()
    assert window.process.waitForStarted(3000)
    window.cancel()
    deadline = time.monotonic() + 5
    while window.process and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert window.process is None
    assert "Stopped" in window.status.text()
    window.close()
print("GUI smoke: modes, subprocess completion/error, cancellation OK")
