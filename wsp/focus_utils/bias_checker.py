"""class for validating the bias images against a template"""

import os
import sys
from typing import Any, Dict, List, Optional

import numpy as np

# add the wsp directory to the PATH
wsp_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, wsp_path)
print(f"wsp_path = {wsp_path}")

from focus_utils.paths import DEFAULT_OUTPUT_DIR, MASTERBIAS_DIR
from focus_utils.winter_image import WinterImage


class BiasChecker:
    @classmethod
    def validate_image(
        cls,
        mef_file_path,
        template_path,
        addrs=None,
        comment="",
        plot=True,
        savepath=None,
    ):
        """
        compare the image specified to the template images and decide if it is
        in good shape. return a dictionary of the addresses and whether they're
        "okay" or suspicious and a reboot is merited.
        """
        results = dict()
        cmaps = dict()
        bad_chans = []
        good_chans = []

        # load the data
        test_data = WinterImage(mef_file_path)
        print("loaded test data")
        template_data = WinterImage(template_path)
        print("loaded template data")
        # this was the old way: cycle through all layers in the template
        # all_addrs = self.template_data._layer_by_addr

        # instead:
        # cycle through all layers in the test data. ignore any offline sensors
        all_addrs = test_data.imgs.keys()
        print(f"found data at addresses: {all_addrs}")
        if addrs is None:
            addrs = all_addrs

        # now loop through all the images and evaluate
        for addr in all_addrs:
            if addr in addrs:

                data = np.abs(1 - (test_data.imgs[addr] / template_data.imgs[addr]))

                std = np.std(data)
                mean = np.average(data)

                if (std > 0.5) or (mean > 0.1):
                    # image is likely bad!!
                    okay = False
                    cmaps.update({addr: "Reds"})
                    bad_chans.append(addr)
                else:
                    okay = True
                    cmaps.update({addr: "gray"})
                    good_chans.append(addr)

                results.update(
                    {
                        addr: {
                            "okay": okay,
                            "mean": float(mean),
                            "std": float(std),
                        }
                    }
                )
            else:
                # cmaps.append("gray")
                pass

        # print(f'cmaps = {cmaps}')

        # make an easy place to grab all the good and bad channels
        results.update({"bad_chans": bad_chans, "good_chans": good_chans})

        # now plot the result
        if plot:
            if len(bad_chans) == 0:
                suptitle = "No Bad Channels!"
            else:
                suptitle = f"Bad Channel(s): {bad_chans}"
            # title= f"\Huge{{{suptitle}}}\n{testdata.filename}"
            title = f"{suptitle}\n{test_data.filename}"
            if comment != "":
                title += f"\n{comment}"
            test_data.plot_mosaic(
                cmap=cmaps, title=title, norm_by="chan", savepath=savepath
            )

        return results


def validate_image(
    mef_file_path: str,
    template_path: str,
    addrs: Optional[List[str]] = None,
    comment: str = "",
    plot: bool = True,
    savepath: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compares the specified MEF FITS image to a template and determines the health of each sensor.

    :param mef_file_path: Path to the MEF FITS file to validate.
    :param template_path: Path to the template MEF FITS file.
    :param addrs: List of addresses to validate. If None, all addresses in the test data are validated.
                  Defaults to None.
    :param comment: Additional comments to include in the plot title. Defaults to an empty string.
    :param plot: Whether to generate and display a plot of the validation results. Defaults to True.
    :param savepath: Path to save the plotted validation results. If None, the plot is not saved. Defaults to None.
    :return: Dictionary containing validation results, including:
             - Each address with a sub-dictionary containing:
                 - "okay" (bool): Whether the sensor is in a good state.
                 - "mean" (float): Mean of the deviation from the template.
                 - "std" (float): Standard deviation of the deviation from the template.
             - "bad_chans" (List[str]): List of addresses with problematic sensors.
             - "good_chans" (List[str]): List of addresses with well-behaved sensors.
    """
    results: Dict[str, Any] = {}
    cmaps: Dict[str, str] = {}
    bad_chans: List[str] = []
    good_chans: List[str] = []

    # Load the test and template data
    test_data = WinterImage(data=mef_file_path)
    template_data = WinterImage(data=template_path)

    # Retrieve all addresses from the test data
    all_addrs = list(test_data.imgs.keys())

    if addrs is None:
        addrs = all_addrs

    # Loop through all addresses and evaluate
    for addr in all_addrs:
        if addr in addrs:
            if addr not in template_data.imgs:
                # Template data missing for this address
                test_data.log(
                    f"Address '{addr}' not found in template data.", logging.WARNING
                )
                results[addr] = {
                    "okay": False,
                    "mean": None,
                    "std": None,
                    "error": "Address not found in template data.",
                }
                bad_chans.append(addr)
                cmaps[addr] = "Reds"
                continue

            template_img = template_data.imgs[addr]
            test_img = test_data.imgs[addr]

            # Avoid division by zero and handle invalid values
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = np.true_divide(test_img, template_img)
                ratio[~np.isfinite(ratio)] = 0  # Set inf and NaN to 0
                data = np.abs(1 - ratio)

            std = np.std(data)
            mean = np.mean(data)

            if (std > 0.5) or (mean > 0.1):
                # Image is likely bad
                okay = False
                cmaps[addr] = "Reds"
                bad_chans.append(addr)
            else:
                # Image is good
                okay = True
                cmaps[addr] = "gray"
                good_chans.append(addr)

            results[addr] = {
                "okay": okay,
                "mean": float(mean),
                "std": float(std),
            }
        else:
            # Address not specified for validation; skip
            pass

    # Add summary of bad and good channels
    results.update({"bad_chans": bad_chans, "good_chans": good_chans})

    # Plot the validation results if requested
    if plot:
        if len(bad_chans) == 0:
            suptitle = "No Bad Channels!"
        else:
            suptitle = f"Bad Channel(s): {bad_chans}"
        title = f"{suptitle}\n{test_data.filename}"
        if comment:
            title += f"\n{comment}"
        test_data.plot_mosaic(
            cmap=cmaps, title=title, norm_by="chan", savepath=savepath
        )

    return results


if __name__ == "__main__":

    # Data directory
    data_dir = os.path.join(os.getenv("HOME"), "data", "images", "test")

    # Template image
    template_data_path = os.path.join(data_dir, "bias", "master_bias.fits")
    template_im = WinterImage(data=template_data_path)
    template_im.plot_mosaic()

    # Full image
    imgpath = os.path.join(data_dir, "bias", "test_bias.fits")
    im = WinterImage(data=imgpath)
    result = BiasChecker.validate_image(
        mef_file_path=imgpath,
        template_path=template_data_path,
        plot=True,
        savepath=os.path.join(DEFAULT_OUTPUT_DIR, "bias_validation.png"),
    )
    print(f"bad chans:  {result['bad_chans']}")
    print(f"good chans: {result['good_chans']}")
