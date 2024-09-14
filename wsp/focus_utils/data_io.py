from pathlib import Path

from astropy.io import fits


def get_focus_images_in_directory(
    directory: str | Path,
) -> list[Path]:
    """
    Function to get focus images in a directory. Only includes focus images with
    filter J and exposure time 30s for now, because these are the only masters available.

    Parameters
    ----------
    directory: directory to search

    Returns
    -------
    List of focus images
    """
    raw_image_list = Path(directory).glob("*_mef.fits")
    image_list = []

    for image_path in raw_image_list:
        try:
            # if Path(image_path).is_symlink():
            #    image_path = os.readlink(image_path)
            if fits.getval(image_path, "OBSTYPE") == "FOCUS":
                if fits.getval(image_path, "FILTERID") in ["J"]:
                    if fits.getval(image_path, "EXPTIME") in [30.0]:
                        image_list.append(image_path)
        except Exception as e:
            print(f"could not get file at image path = {image_path}: {e}")
    # print(image_list)
    return image_list
