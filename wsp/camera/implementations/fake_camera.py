import time

from wsp.camera.camera import BaseCamera
from wsp.utils.paths import CONFIG_PATH, WSP_PATH
from wsp.utils.utils import loadconfig


class FakeCamera(BaseCamera):
    """
    Fake Camera implementation.
    This class extends BaseCamera to provide specific functionality for the Fake camera.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization if needed


config = loadconfig(CONFIG_PATH)

cam = FakeCamera(
    base_directory=WSP_PATH,
    config=config,
    camname="WINTER-deep",
    daemon_pyro_name="FakeCamera",
    logger=None,
    verbose=False,
)
