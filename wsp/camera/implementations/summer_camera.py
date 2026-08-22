from wsp.camera.camera import BaseCamera
from wsp.utils.paths import CONFIG_PATH, WSP_PATH
from wsp.utils.utils import loadconfig


class SummerCamera(BaseCamera):
    """
    Summer Camera implementation.
    This class extends BaseCamera to provide specific functionality for the Summer camera.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional initialization if needed


config = loadconfig(CONFIG_PATH)

cam = SummerCamera(
    base_directory=WSP_PATH,
    config=config,
    camname="summer",
    daemon_pyro_name="SUMMERCamera",
    ns_host_camera="localhost",  # camera is run locally
    ns_host_hk="192.168.1.10",  # hk is run on the main computer
    logger=None,
    verbose=False,
)
