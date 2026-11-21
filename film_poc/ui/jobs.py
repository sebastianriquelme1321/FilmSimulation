"""Background work: a logging QThread and a helper that wires and starts one."""
import logging

from PySide6.QtCore import QThread, Signal


class Job(QThread):
    """Run a callable off the UI thread; emit its result or the error message."""

    done = Signal(object)
    failed = Signal(str)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.done.emit(self.operation())
        except Exception as exc:
            logging.exception('Background job failed')
            self.failed.emit(str(exc))


def make_job(operation, parent, done=None, failed=None, finished=None):
    """Create a Job with the given callbacks connected; the caller starts it."""
    job = Job(operation, parent)
    if done:
        job.done.connect(done)
    if failed:
        job.failed.connect(failed)
    if finished:
        job.finished.connect(finished)
    return job
