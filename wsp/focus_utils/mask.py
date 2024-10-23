import numpy as np
import astropy
from astropy.io import fits


def mask_datasec(data: np.ndarray, header: astropy.io.fits.Header) -> np.ndarray:
    """
    Function to mask the data section of an image
    """
    datasec = header["DATASEC"].replace("[", "").replace("]", "").split(",")
    datasec_xmin = int(datasec[0].split(":")[0])
    datasec_xmax = int(datasec[0].split(":")[1])
    datasec_ymin = int(datasec[1].split(":")[0])
    datasec_ymax = int(datasec[1].split(":")[1])

    data[:, :datasec_xmin] = np.nan
    data[:, datasec_xmax:] = np.nan
    data[:datasec_ymin, :] = np.nan
    data[datasec_ymax:, :] = np.nan
    return data


def make_mask(imgname, boardid: int, maskname: str=None, write:bool=True):
    """
    Deprecated, should be replaced by get_raw_winter_mask
    :param imgname:
    :param boardid:
    :param maskname:
    :param write:
    :return:
    """
    img_data = fits.getdata(imgname)
    img_header = fits.getheader(imgname)
    img_data = mask_datasec(img_data, img_header)

    if boardid == 0:
        # data[:500, 700:1500] = np.nan
        img_data[1075:, :] = np.nan
        img_data[:, 1950:] = np.nan
        img_data[:20, :] = np.nan

    if boardid == 1:
        img_data[1075:, :] = np.nan
        img_data[:, 1950:] = np.nan
        img_data[:20, :] = np.nan

    if boardid == 2:
        img_data[1085:, :] = np.nan
        img_data[:, 1970:] = np.nan
        img_data[:55, :] = np.nan
        img_data[:, :20] = np.nan
        img_data[349:352, :] = np.nan
        img_data[:, 1564:1566] = np.nan

    if boardid == 3:
        img_data[1085:, :] = np.nan
        img_data[:, 1970:] = np.nan
        img_data[:55, :] = np.nan
        img_data[:, :20] = np.nan

    if boardid == 4:
        # data[610:, :280] = np.nan
        img_data[:, 1948:] = np.nan
        img_data[:, :61] = np.nan
        img_data[:20, :] = np.nan
        img_data[1060:, :] = np.nan
        # img_data[:, 999:1002] = np.nan
        img_data[650:, :230] = np.nan

    if boardid == 5:
        # data[740:, 1270: 1850] = np.nan
        img_data[1072:, :] = np.nan
        img_data[:, 1940:] = np.nan
        img_data[:15, :] = np.nan
        img_data[760:, 1300:1760] = np.nan
        # data[data > 25000] = np.nan

    mask = np.isnan(img_data)
    mask = (mask == 0)
    maskhdu = fits.PrimaryHDU(mask.astype(float))
    maskhdu.writeto(maskname, overwrite=True)
    return mask


def get_raw_winter_mask(data, header) -> np.ndarray:
    """
    Get mask for raw winter image.
    """

    mask = np.zeros(data.shape)
    if header["BOARD_ID"] == 0:
        # Mask the outage in the bottom center
        mask[:500, 700:1600] = 1.0
        mask[1075:, :] = 1.0
        mask[:, 1950:] = 1.0
        mask[:20, :] = 1.0

    if header["BOARD_ID"] == 1:
        pass

    if header["BOARD_ID"] == 2:
        mask[1060:, :] = 1.0
        mask[:, 1970:] = 1.0
        mask[:55, :] = 1.0
        mask[:, :20] = 1.0

    if header["BOARD_ID"] == 3:
        mask[1085:, :] = 1.0
        mask[:, 1970:] = 1.0
        mask[:55, :] = 1.0
        mask[:, :20] = 1.0

    if header["BOARD_ID"] == 4:
        # # Mask the region to the top left
        mask[610:, :250] = 1.0
        # # There seems to be a dead spot in the middle of the image
        mask[503:518, 390:405] = 1.0
        mask[:, 1948:] = 1.0
        mask[:, :61] = 1.0
        mask[:20, :] = 1.0
        mask[1060:, :] = 1.0
        mask[:, 999:1002] = 1.0

    if header["BOARD_ID"] == 5:
        # Mask the outage in the top-right.
        mask[700:, 1200:1900] = 1.0
        mask[1072:, :] = 1.0
        mask[:, 1940:] = 1.0
        mask[:15, :] = 1.0

    return mask.astype(bool)
