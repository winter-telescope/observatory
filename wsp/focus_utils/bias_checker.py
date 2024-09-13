"""class for validating the bias images against a template"""

import os
import sys

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

        template_data = WinterImage(template_path)

        # this was the old way: cycle through all layers in the template
        # all_addrs = self.template_data._layer_by_addr

        # instead:
        # cycle through all layers in the test data. ignore any offline sensors
        all_addrs = test_data.imgs.keys()

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
