from wsp.camera.camera import BaseCamera
from wsp.utils.paths import CONFIG_PATH, WSP_PATH
from wsp.utils.utils import loadconfig


class SpringCamera(BaseCamera):
    """
    Spring Camera implementation.
    This class extends BaseCamera to provide specific functionality for the Spring camera.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization if needed


config = loadconfig(CONFIG_PATH)

cam = SpringCamera(
    base_directory=WSP_PATH,
    config=config,
    camname="spring",
    daemon_pyro_name="SpringCamera",
    logger=None,
    verbose=False,
)
