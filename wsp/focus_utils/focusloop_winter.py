"""
Module for doing a focus loop with the WINTER camera.
"""
from astropy.io import fits
import numpy as np
import matplotlib.pyplot as plt

from scipy.optimize import curve_fit
import os
from glob import glob
import argparse
from winter_utils.quick_calibrate_images import subtract_dark, flat_correct
from winter_utils.mask import make_mask
from astropy.table import Table, vstack
from astropy.stats import sigma_clipped_stats
import matplotlib
from matplotlib.gridspec import GridSpec
import subprocess
import pandas as pd
from pathlib import Path
from winter_utils.ldactools import get_table_from_ldac
from contextlib import redirect_stdout
import warnings

from winter_utils.paths import astrom_sex, astrom_param, astrom_filter, astrom_nnw, MASK_DIR, MASTERDARK_DIR, MASTERFLAT_DIR, DEFAULT_OUTPUT_DIR
from winter_utils.io import get_focus_images_in_directory

matplotlib.use('Agg')


def matplotlib_init():
    """
    Set up matplotlib to make pretty plots.

    Returns
    -------
        None
    """

    matplotlib.rcParams['xtick.minor.size'] = 6
    matplotlib.rcParams['xtick.major.size'] = 6
    matplotlib.rcParams['ytick.major.size'] = 6
    matplotlib.rcParams['ytick.minor.size'] = 6
    matplotlib.rcParams['lines.linewidth'] = 1.5
    matplotlib.rcParams['axes.linewidth'] = 1.5
    matplotlib.rcParams['font.size'] = 16
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rcParams['xtick.major.width'] = 2.
    matplotlib.rcParams['ytick.major.width'] = 2.
    matplotlib.rcParams['ytick.direction'] = 'in'
    matplotlib.rcParams['xtick.direction'] = 'in'



def run_sextractor(
        imgname: str | Path,
        pixscale: float = 1.00,
        regions: bool = True,
        weightimg: str = 'weight.fits'
):
    """
    Run sextractor on the proc image file

    Parameters
    ----------
    imgname: Name of the image to run sextractor on
    pixscale: Pixel scale of the image
    regions: boolean whether to write out regions
    weightimg: Weight image to use

    Returns
    -------
    None

    """
    try:
        command = f'sex -c {astrom_sex} {imgname} -CATALOG_NAME {imgname}.cat ' + \
                  f'-CATALOG_TYPE FITS_LDAC -PARAMETERS_NAME {astrom_param} ' + \
                  f'-FILTER_NAME {astrom_filter} -STARNNW_NAME {astrom_nnw} ' \
                  f'-PIXEL_SCALE {pixscale} -DETECT_THRESH 3 -ANALYSIS_THRESH 3 ' \
                  f'-SATUR_LEVEL 60000 -WEIGHT_TYPE MAP_WEIGHT ' \
                  f'-WEIGHT_IMAGE {weightimg} -CHECKIMAGE_TYPE BACKGROUND ' \
                  f'-CHECKIMAGE_NAME {imgname}.back.fits'

        print('Executing command : %s' % (command))
        subprocess.run(command.split(), check=True, capture_output=True)

    except subprocess.CalledProcessError as err:
        print('Could not run sextractor with error %s.' % (err))
        return

    if regions:
        t = get_table_from_ldac(imgname + '.cat')
        with open(imgname + '.cat' + '.stats.reg', 'w') as f:
            f.write('image\n')
            for row in t:
                f.write('CIRCLE(%s,%s,%s) # text={%.2f}\n' % (
                    row['X_IMAGE'], row['Y_IMAGE'], row['FWHM_IMAGE'] / 2,
                    row['FWHM_IMAGE']))


edge_limits = {'0': [50, 1930, 50, 1050],
               '1': [100, 1700, 50, 1050],
               '2': [100, 1900, 50, 1050],
               '3': [100, 1900, 50, 1050],
               '4': [100, 1900, 50, 1050],
               '5': [100, 1900, 50, 1050],
               }


def get_img_fwhm(imgnames: str | list[str],
                 weightimages: str | list[str],
                 pixscale: float = 1.00,
                 exclude: bool = False,
                 regions: bool = True) -> tuple[float, float, float]:
    """
    Get the FWHM of the stars in the image

    Parameters
    ----------
    imgnames: list of image names
    weightimages: list of weight images
    pixscale: pixel scale of the image
    exclude: boolean whether to exclude the edge of the image
    regions: boolean whether to make regions files

    Returns
    -------

        mean FWFM, median FWHM, std FWHM
    """
    if isinstance(imgnames, str):
        imgnames = [imgnames]
    if isinstance(weightimages, str):
        weightimages = [weightimages]

    assert len(imgnames) == len(weightimages), 'Number of images and weight images ' \
                                               'must be the same.'
    full_img_cat = Table()

    print('requested', imgnames)
    for ind, imgname in enumerate(imgnames):

        weightimg = weightimages[ind]
        if not os.path.exists(imgname + '.cat'):
            print('Catalog does not exist.')
            run_sextractor(imgname, pixscale, weightimg=weightimg)

        img_cat = get_table_from_ldac(imgname + '.cat')
        print('Found %s sources in single image' % (len(img_cat)))

        boardid = fits.getval(imgname, 'BOARD_ID')
        xlolim, xuplim, ylolim, yuplim = edge_limits[str(boardid)]
        center_mask = (img_cat['X_IMAGE'] < xuplim) & (img_cat['X_IMAGE'] > xlolim) & (
                img_cat['Y_IMAGE'] < yuplim) & (img_cat['Y_IMAGE'] > ylolim) & \
                      (img_cat['FWHM_IMAGE'] > 0.2) & (img_cat['FLAGS'] == 0)
        if exclude:
            center_mask = np.invert(center_mask)
        if regions:
            with open(imgname + '.cat' + '.clean.reg', 'w') as f:
                f.write('image\n')
                for row in img_cat[center_mask]:
                    f.write('CIRCLE(%s,%s,%s) # text={%.2f}\n' % (
                        row['X_IMAGE'], row['Y_IMAGE'], row['FWHM_IMAGE'] / 2,
                        row['FWHM_IMAGE']))
        full_img_cat = vstack([full_img_cat, img_cat[center_mask]])

    print(f'Using {len(full_img_cat)} good sources in total')

    mean, median, std = sigma_clipped_stats(full_img_cat['FWHM_IMAGE'], sigma=2)
    return mean, median, std


def parabola(x: float, x0: float, A: float, B: float) -> float:
    """
    Basic function for fitting a parabola

    Parameters
    ----------
    x: value
    x0: center of parabola
    A: offset
    B: parabola offset

    Returns
    -------

    """
    return A + B * (x - x0) ** 2


def fit_parabola(focus_vals, fwhms, stds, plot: bool = True,
                 plotname=DEFAULT_OUTPUT_DIR.joinpath('focusloop.png'),
                 ax=None, save=True):
    """
    Uses scipy.optimize.curve_fit to fit a parabola to the focus loop data

    Parameters
    ----------
    focus_vals: values of focus
    fwhms: full-width-half-maximum values
    stds: standard deviations of fwhms
    plot: boolean whether to generate plot
    plotname: name of plot to create
    ax: matplotlib axis to plot on (default None)
    save: boolean whether to save plot

    Returns
    -------

    """
    p0 = [np.mean(focus_vals), np.min(fwhms), np.std(fwhms)]
    popt, pcov = curve_fit(parabola, xdata=focus_vals, ydata=fwhms, p0=p0, sigma=stds,
                           bounds=([np.min(focus_vals)-1000, 0, 0],
                                   [np.max(focus_vals)+2000, 10, np.inf]))
    if plot:
        if ax is None:
            plt.figure(figsize = (10,8))
            ax = plt.gca()
        ax.errorbar(focus_vals, fwhms, yerr=stds, fmt='.', c='red')
        plotfoc = np.linspace(np.min(focus_vals), np.max(focus_vals), 20)
        ax.plot(plotfoc, parabola(plotfoc, popt[0], popt[1], popt[2]))
        ax.plot(popt[0], parabola(popt[0], popt[0], popt[1], popt[2]),'ko')
        ax.text(0.5, 0.9, 'Best FWHM : %.1f arcsec, focus = %i, Fit Min Focus = %.1f'
                          '' % (np.min(fwhms), focus_vals[fwhms==np.min(fwhms)], popt[0]),
                     size=14, transform=ax.transAxes, ha='center')
        ax.set_xlabel('Focus position')
        ax.set_ylabel('FWHM')
        if save:
            plt.savefig(plotname, bbox_inches='tight')
    return popt


def analyse_imgs_focus(imglists: list[list[str]],
                       pixscale=1.00, exclude: bool = False, focus_keyword='FOCPOS',
                       maskdir: str = None):
    """
    Function to analyse a set of images taken at different focus positions

    Parameters
    ----------
    imglists: list of lists of image names
    pixscale: pixel scale of the images
    exclude: boolean whether to exclude the edge of the image
    focus_keyword: header key for focus position
    maskdir: directory to save masks to (default None)

    Returns
    -------

    """
    med_fwhms = []
    std_fwhms = []
    focus_vals = []

    for imglist in imglists:
        boardids = [fits.getval(x, 'BOARD_ID') for x in imglist]
        masknames = [f'{maskdir}/mask_boardid_{x}.fits' for x in boardids]
        for ind, maskname in enumerate(masknames):
            if not os.path.exists(maskname):
                print(f'Mask {maskname} does not exist. Making it.')
                make_mask(imglist[ind], boardid=boardids[ind], maskname=maskname)

        print('imglist', imglist)
        img_focus_vals = [fits.getval(x, focus_keyword) for x in imglist]
        print('imgfocus', img_focus_vals)
        assert len(np.unique(img_focus_vals)) == 1
        img_focus_val = img_focus_vals[0]

        mean, med, std = get_img_fwhm(imglist, pixscale=pixscale, exclude=exclude,
                                      weightimages=masknames)
        med_fwhms.append(med * pixscale)
        std_fwhms.append(std * pixscale)
        focus_vals.append(img_focus_val)

    med_fwhms = np.array(med_fwhms)
    std_fwhms = np.array(std_fwhms)
    focus_vals = np.array(focus_vals)

    return med_fwhms, std_fwhms, focus_vals


def save_split_images(filename: str,
                      boardids: int | list[int],
                      output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[str]:
    """"
    Function to save individual extensions from a multi-extension fits file

    Parameters
    ----------
    filename: name of mef fits file
    boardids: board ids to save

    Returns
    list of new individual filenames
    """

    if not isinstance(boardids, list):
        boardids = [boardids]

    new_paths = []
    with fits.open(filename) as hdu:
        num_ext = len(hdu)
        hdr0 = hdu[0].header  # pylint: disable=no-member
        # zip hdr0's values and comments
        zipped = list(zip(hdr0.values(), hdr0.comments))
        for ext in range(1, num_ext):
            data = hdu[ext].data
            hdrext = hdu[ext].header

            extension_num_str = hdrext['BOARD_ID']

            if int(extension_num_str) not in boardids:
                continue

            # append hdr0 to hdrext
            for count, key in enumerate(list(hdr0.keys())):
                hdrext.append((key, zipped[count][0], zipped[count][1]))

            # save to new file with 1 extension
            # notmefpath = path.split("/mef/")[0] + path.split("/mef")[1]

            splitfile_basename = f"{os.path.basename(filename).replace('.fits', '')}_" \
                                 f"{extension_num_str}.fits"

            new = Path(filename).parts[-2]
            splitfile_basedir = Path(output_dir).joinpath(f"{new}/split")

            splitfile_basedir.mkdir(parents=True, exist_ok=True)

            splitfile_path = splitfile_basedir.joinpath(splitfile_basename)
            fits.writeto(
                splitfile_path, data, hdrext, overwrite=True
            )  # pylint: disable=no-member
            new_paths.append(splitfile_path.as_posix())
    return new_paths


def split_and_calibrate_images(imglist: list[str],
                               board_ids: list = [0],
                               masterdarks_dir: str | Path = MASTERDARK_DIR,
                               masterflats_dir: str | Path = MASTERFLAT_DIR,
                               saturate_value: int = 40000,
                               output_dir: str | Path = DEFAULT_OUTPUT_DIR,
                               ) -> list[list[str]]:
    """
    Function to split a list of images into individual extensions and calibrate them

    Parameters
    ----------
    imglist: list of image names
    board_ids: list of board ids to use
    masterdarks_dir: directory of masterdarks
    masterflats_dir: directory of masterflats
    saturate_value: value to set the saturation level to

    Returns
    -------
    List of lists of science+calibration images, divided by board id
    """

    split_path_list = []
    for imgname in imglist:
        split_paths = save_split_images(imgname, board_ids, output_dir = output_dir)
        split_cal_paths = []
        for split_path in split_paths:
            split_data = fits.getdata(split_path)
            split_header = fits.getheader(split_path)
            split_header['SATURATE'] = saturate_value
            master_darkname = os.path.join(masterdarks_dir,
                                           f"master_dark_boardid_"
                                           f"{split_header['BOARD_ID']}"
                                           f"_exptime_{int(np.rint(split_header['EXPTIME']))}"
                                           f".fits")
            master_flatname = os.path.join(masterflats_dir,
                                           f"master_flat_boardid_"
                                           f"{split_header['BOARD_ID']}"
                                           f"_filter_{split_header['FILTERID']}.fits")
            master_dark = fits.getdata(master_darkname) * split_header['EXPTIME']
            master_flat = fits.getdata(master_flatname)
            split_data = subtract_dark(split_data, master_dark)
            split_header['SATURATE'] -= np.nanmedian(master_dark)
            split_header['SATURATE'] /= np.nanmedian(master_flat)
            split_data = flat_correct(split_data, master_flat)
            cal_split_path = split_path.replace('.fits', '_cal.fits')
            fits.writeto(cal_split_path, split_data, split_header, overwrite=True)
            split_cal_paths.append(cal_split_path)
        split_path_list.append(split_cal_paths)

    return split_path_list


def subtract_sky(imagelist: [list[list[str]]]) -> list[list[str]]:
    """
    Function to subtract sky from a list of images

    :param imagelist: 2D array with boardids as first index and MEF image as second
    index
    :return: list of sky subtracted image paths
    """
    if not isinstance(imagelist, np.ndarray):
        imagelist = np.array(imagelist)
    print(imagelist)
    sky_subtracted_paths = []
    for boardid in range(imagelist.shape[1]):
        sky_sub_board_paths = []
        board_images = imagelist[:, boardid]
        board_ids = [fits.getval(x, 'BOARD_ID') for x in board_images]
        assert len(np.unique(board_ids)) == 1
        # Taking the median of all images to make a sky model
        board_image_data = [fits.getdata(x) for x in board_images]
        board_image_data = np.array(board_image_data)
        sky_model = np.median(board_image_data, axis=0)
        sky_model = np.array(sky_model, dtype=np.float32)

        sky_sub_data = board_image_data - sky_model

        for count, image in enumerate(board_images):
            sky_sub_header = fits.getheader(image)
            sky_sub_header['SATURATE'] -= np.nanmedian(sky_model)
            sky_sub_path = image.replace('.fits', '_sky.fits')
            fits.writeto(sky_sub_path, sky_sub_data[count], fits.getheader(image),
                         overwrite=True)
            sky_sub_board_paths.append(sky_sub_path)
        sky_subtracted_paths.append(sky_sub_board_paths)
    sky_subtracted_paths = np.array(sky_subtracted_paths).T
    return sky_subtracted_paths


def calculate_best_focus_from_images(image_dir: str | Path,
                                     masterdarks_dir: str | Path = MASTERDARK_DIR,
                                     masterflats_dir: str | Path = MASTERFLAT_DIR,
                                     board_ids_to_use: int | list[int] = [0],
                                     maskdir: str = MASK_DIR,
                                     skip_calibrate: bool = False,
                                     statsfile: str = 'focusloop_stats.txt',
                                     plot: bool = True,
                                     ) -> float:
    """
    Function to calculate the best focus from a set of images

    Parameters
    ----------
    image_dir: directory containing images
    masterdarks_dir: Directory containing masterdarks
    masterflats_dir Directory containing masterflats
    board_ids_to_use: Board ids to use
    maskdir: Directory to write masks to
    skip_calibrate: boolean to skip calibration
    statsfile: file to write stats to
    plot: Make plot?

    Returns
    -------

    Best focus value
    """
    if not skip_calibrate:
        imagelist = get_focus_images_in_directory(image_dir)
        # Use only focus images
        # imagelist = [x for x in imagelist if fits.getval(x, 'OBSTYPE') == 'FOCUS']
        split_paths_list = split_and_calibrate_images(imagelist,
                                                      masterdarks_dir=masterdarks_dir,
                                                      masterflats_dir=masterflats_dir,
                                                      board_ids=board_ids_to_use,
                                                      )

        split_paths_list = subtract_sky(split_paths_list)

    else:
        split_paths_list = glob(os.path.join(image_dir, 'split', '*.fits'))
        split_paths_list = [[x] for x in split_paths_list]

    print(f"Found {len(split_paths_list)} images  - {split_paths_list}")
    med_fwhms, std_fwhms, focus_vals = analyse_imgs_focus(split_paths_list,
                                                          maskdir=maskdir)

    nanmask = np.isnan(med_fwhms)
    med_fwhms = med_fwhms[~nanmask]
    std_fwhms = std_fwhms[~nanmask]
    focus_vals = focus_vals[~nanmask]

    print(med_fwhms, std_fwhms, focus_vals)
    best_pars = fit_parabola(focus_vals, med_fwhms, std_fwhms, plot=plot)
    best_focus = best_pars[0]

    split_paths_list = np.array(split_paths_list)
    sinds = np.argsort(med_fwhms)
    med_fwhms = med_fwhms[sinds]
    std_fwhms = std_fwhms[sinds]
    focus_vals = focus_vals[sinds]
    sorted_split_paths_list = split_paths_list[sinds]
    with open(statsfile, 'w') as f:
        f.write('Imgname, FWHM, FWHM_std, Focus\n')
        for img, fwhm, fwhm_std, focus in zip(sorted_split_paths_list,
                                              med_fwhms, std_fwhms, focus_vals):
            f.write(f"{img[0]}, {fwhm}, {fwhm_std}, {focus}\n")
    return best_focus


def plot_all_detectors_focus(files_dir: str | Path):
    """
    Function to plot all detectors focus

    Parameters
    ----------
    files_dir: directory containing focusloop_stats files

    Returns
    -------
    None
    """

    plt.figure(figsize=(15, 15))
    gs = GridSpec(nrows=3, ncols=2, hspace=0.3)

    best_focii, best_fwhms = [], []
    pixscale = 1.11
    board_ind_mapping = [3, 4, 1, 2, 0, 5]
    all_focus_table = pd.DataFrame()

    ax_0 = None

    for ind in range(6):
        focus = pd.read_csv(
            f'{files_dir}/focusloop_stats_{ind}.txt')
        focus['BOARDID'] = ind
        focus.columns = focus.columns.str.replace(' ', '')

        if ax_0 is None:
            ax = plt.subplot(gs[board_ind_mapping[ind]])
            ax_0 = ax
        else:
            ax = plt.subplot(gs[board_ind_mapping[ind]], sharex=ax_0, sharey=ax_0)

        best_pars = fit_parabola(focus['Focus'].values,
                                 focus['FWHM'].values * pixscale,
                                 focus['FWHM_std'].values,
                                 save=False,
                                 ax=ax)
        best_focii.append(best_pars[0])
        best_fwhms.append(focus['FWHM'].min() * pixscale)
        all_focus_table = pd.concat([all_focus_table, focus]).reset_index(drop=True)

    plt.savefig(f'{files_dir}/focusloop_all_detectors.png', bbox_inches='tight')
    plt.close()


def run(cmd_args) -> float:
    """
    Wrapper function to run the focus loop

    Parameters
    ----------
    cmd_args



    Returns
    -------

    """
    if cmd_args.board_ids_to_use is not None:
        board_ids_to_use = cmd_args.board_ids_to_use
    else:
        board_ids_to_use = [1, 2, 3, 4]

    matplotlib_init()
    best_focus = calculate_best_focus_from_images(cmd_args.image_dir,
                                                  masterdarks_dir=cmd_args.masterdarks_dir,
                                                  masterflats_dir=cmd_args.masterflats_dir,
                                                  maskdir=cmd_args.masks_dir,
                                                  board_ids_to_use=board_ids_to_use,
                                                  statsfile=os.path.join(cmd_args.output_dir,
                                                                         'focusloop_stats.txt')
                                                  )

    if cmd_args.plot_all:
        for board_id in range(6):
            _ = calculate_best_focus_from_images(cmd_args.image_dir,
                                                 masterdarks_dir=cmd_args.masterdarks_dir,
                                                 masterflats_dir=cmd_args.masterflats_dir,
                                                 maskdir=cmd_args.masks_dir,
                                                 board_ids_to_use=[board_id],
                                                 statsfile=
                                                 os.path.join(cmd_args.output_dir,
                                                              f'focusloop_stats_{board_id}'
                                                              f'.txt'),
                                                 plot=False
                                                 )

        plot_all_detectors_focus(cmd_args.output_dir)

    return best_focus


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image_dir', type=str)
    parser.add_argument('--masterdarks_dir', type=str,
                        default=MASTERDARK_DIR)
    parser.add_argument('--masterflats_dir', type=str,
                        default=MASTERFLAT_DIR)
    parser.add_argument('--masks_dir', type=str,
                        default=MASK_DIR)
    parser.add_argument('--output_dir', type=str,
                        default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--board_ids_to_use', type=int, nargs='+', default=None)
    parser.add_argument('--plot_all', action="store_true")
    parser.add_argument('--silent', action="store_true", default=False)
    args = parser.parse_args()

    if args.silent:
        # Catch literally everything going to stdout, and make it disappear
        with redirect_stdout(open(os.devnull, "w")):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("ignore")
                best_focus = run(args)
        print(best_focus)

    else:
        # Normal output
        best_focus = run(args)
        print(f"Best focus: {best_focus}")
