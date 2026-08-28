from PySide6.QtGui import Qt
from PySide6.QtWidgets import QCheckBox, QWidget

from songs_to_youtube.field import checkstate_to_int


class SettingCheckBox(QCheckBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTristate()

    def nextCheckState(self) -> None:
        # don't let user select inbetween state
        if self.checkState() == Qt.CheckState.PartiallyChecked:
            self.setCheckState(Qt.CheckState.Checked)
        else:
            self.setChecked(not self.isChecked())
        self.stateChanged.emit(checkstate_to_int(self.checkState()))
