from PyQt5.QtCore import QObject, pyqtSignal
from transitions import Machine, State


class RoboController(QObject):