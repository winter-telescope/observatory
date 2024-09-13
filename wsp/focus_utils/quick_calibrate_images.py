import numpy as np
from astropy.io import fits
import argparse
import astropy


def subtract_dark(image: np.ndarray, masterdark: np.ndarray):
    """
    Subtract a master dark from an image

    :param image: image to subtract dark from
    :param masterdark: master dark to subtract
    :return: image with dark subtracted
    """
    return image - masterdark


def flat_correct(image: np.ndarray, masterflat: np.ndarray):
    """
    Flat correct an image

    :param image: image to flat correct
    :param masterflat: master flat to use
    :return: flat corrected image
    """
    return image / masterflat


def get_split_mef_fits_data(fits_filename: str) \
        -> (list[np.ndarray], list[astropy.io.fits.Header]):
    """
    Get the data from a MEF fits file as a numpy array
    :param fits_filename:
    :return:
    """
    split_data, split_headers = [], []
    with fits.open(fits_filename) as hdu:
        num_ext = len(hdu)
        for ext in range(1, num_ext):
            split_data.append(hdu[ext].data)
            split_headers.append(hdu[ext].header)

    return split_data, split_headers


def join_files_to_mef(fits_data: list[np.ndarray],
                      fits_headers: list[fits.Header],
                      primary_hdu: astropy.io.fits.hdu.image.PrimaryHDU,
                      write: bool = False,
                      write_filename: str = None) -> fits.HDUList:
    """

    :param fits_hdus:
    :param fits_headers:
    :param primary_hdu:
    :return:
    """
    hdu_list = [primary_hdu]
    for ind, data in enumerate(fits_data):
        hdu_list.append(fits.ImageHDU(data=data, header=fits_headers[ind]))

    hdulist = fits.HDUList(hdu_list)
    if write:
        if write_filename is None:
            raise ValueError(f"Please provide a name for the output file")
        hdulist.writeto(write_filename, overwrite=True)
    return hdulist


def calibrate_mef_files(fits_filename: str, master_darkname: str,
                        master_flatname: str):
    """
    Calibrate a MEF fits file
    :param fits_filename:
    :param master_darkname:
    :param master_flatname:
    :return:
    """
    split_fits_data, split_fits_headers = get_split_mef_fits_data(fits_filename)
    split_dark_data, _ = get_split_mef_fits_data(master_darkname)
    split_flat_data, _ = get_split_mef_fits_data(master_flatname)
    for i in range(len(split_fits_data)):
        split_fits_data[i] = subtract_dark(split_fits_data[i], split_dark_data[i])
        split_fits_data[i] = flat_correct(split_fits_data[i], split_flat_data[i])

    # with fits.open(fits_filename, 'update') as hdu:
    #     primary_hdu = hdu[0]

    hdulist = fits.open(fits_filename)
    primary_hdu = hdulist[0]
    calibrated_mef_hdulist = join_files_to_mef(split_fits_data,
                                               split_fits_headers,
                                               primary_hdu=primary_hdu,
                                               write=True,
                                               write_filename=
                                               fits_filename.replace('.fits',
                                                                     '_calibrated.fits'
                                                                     )
                                               )
    hdulist.close()
    return calibrated_mef_hdulist


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calibrate MEF fits files')
    parser.add_argument('fits_filename', type=str, help='MEF fits file to calibrate')
    parser.add_argument('master_darkname', type=str, help='Master dark to use')
    parser.add_argument('master_flatname', type=str, help='Master flat to use')
    args = parser.parse_args()
    calibrate_mef_files(args.fits_filename, args.master_darkname, args.master_flatname)
