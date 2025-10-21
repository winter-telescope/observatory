"""
wsp: the WINTER Supervisor Program

This file is part of wsp

# PURPOSE #
This program is the top-level control loop which runs operations for the
WINTER instrument.



"""

# system packages
import getopt
import os
import signal
import sys

from PyQt5 import QtCore

from wsp.control import systemControl
from wsp.utils import logging_setup, utils
from wsp.utils.paths import CONFIG_DIR, CONFIG_PATH, WSP_PATH

# add the wsp directory to the PATH
wsp_path = WSP_PATH
print(f"wsp: wsp_path = {wsp_path}")


#######################################################################
# Captions and menu options for terminal interface
linebreak = "\n \033[34m####################################################################################"
caption1 = "\n\t\033[32mWSP - The WINTER Supervisor Program"
caption2 = "\n\t\033[32mPlease Select an Operating Mode:"
captions = [caption1, caption2]
main_opts = dict(
    {
        "R": "Robotic schedule File Mode",
        "I": "Instrument-only Mode",
        "M": "Manual Mode",
        "Q": "Exit",
    }
)

logo = []
logo.append("__      _____ _ __             _  _")
logo.append("\ \ /\ / / __| '_ \           | )/ )")
logo.append(" \ V  V /\__ \ |_) |       \ /|//,' __")
logo.append('  \_/\_/ |___/ .__/        (")(_)-=()))=-')
logo.append("             | |              (\\\\")
logo.append("             |_|  ")


# Logo Credit: https://ascii.co.uk/art/wasp


big_m = []
big_m.append("88888b     d88888")
big_m.append("888888b   d888888")
big_m.append("8888888b.d8888888")
big_m.append("88888Y88888P88888")
big_m.append("88888 Y888P 88888")
big_m.append("88888  Y8P  88888")
big_m.append('88888   "   88888')
big_m.append("88888       88888")

big_r = []
big_r.append("8888888888b.")
big_r.append("888888888888b.")
big_r.append("88888   Y8888b")
big_r.append("88888    88888")
big_r.append("88888   d8888P")
big_r.append('888888888P"')
big_r.append("88888 T8888b")
big_r.append("88888  T8888b")
big_r.append("88888   T8888b")

big_i = []
big_i.append("8888888888888 ")
big_i.append("8888888888888 ")
big_i.append("    88888     ")
big_i.append("    88888     ")
big_i.append("    88888     ")
big_i.append("    88888     ")
big_i.append("8888888888888 ")
big_i.append("8888888888888 ")

big_letter = dict({"m": big_m, "r": big_r, "i": big_i})


#########################################################################
def numbered_menu(captions, options):
    """Creates menu for terminal interface
    inputs:
        list captions: List of menu captions
        list options: List of menu options
    outputs:
        int opt: Integer corresponding to menu option chosen by user"""

    print(linebreak)
    for logo_line in logo:
        print("     ", logo_line)
    print("\t" + captions[0])
    print(linebreak)
    for i in range(len(options)):
        if i < 9:
            print("\t" + "\033[32m" + str(i) + " ..... " "\033[0m" + options[i] + "\n")
    print("\t" + captions[1] + "\n")
    for i in range(len(options)):
        if i >= 9:
            print("\t" + "\033[32m" + str(i) + " ..... " "\033[0m" + options[i] + "\n")
    opt = input().strip()
    return opt


def printlogo():
    print(linebreak)
    for logo_line in logo:
        print("     ", logo_line)
    print("\t" + captions[0])
    print(linebreak)


def dict_menu(captions, options):
    """Creates menu for terminal interface
    inputs:
        list captions: List of menu captions
        dict options: List of menu options
    outputs:
        int opt: Integer corresponding to menu option chosen by user
        list allowed_opts: list of all the lowercase menu opptions allowed to be chosen
    """

    printlogo()
    allowed_opts = []
    for key in options.keys():
        print("\t" + "\033[32m" + key + " ..... " "\033[0m" + options[key] + "\n")
        allowed_opts.append(key.lower())
    print("\t" + captions[1] + "\n")

    opt = input().strip().lower()
    return opt, allowed_opts


#########################################################################


def sigint_handler(*args):
    """Handler for the SIGINT signal."""
    print("exiting.")
    sys.stderr.write("\r")
    QtCore.QCoreApplication.quit()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    signal.signal(signal.SIGINT, sigint_handler)
    app = QtCore.QCoreApplication(argv)

    mode = None

    # GET ANY COMMAND LINE ARGUMENTS
    print(f"wsp: args = {argv}")

    options = "rimvn:s"
    long_options = [
        "robo",
        "instrument",
        "manual",
        "verbose",
        "ns_host=",
        "smallchiller",
        "nochiller",
        "sunsim",
        "domesim",
        "dometest",
        "mountsim",
        "shell",
        "disablewatchdog",
    ]
    arguments, values = getopt.getopt(argv, options, long_options)
    # checking each argument
    print()
    print(f"wsp: Parsing sys.argv...")
    print(f"wsp: arguments = {arguments}")
    print(f"wsp: values = {values}")
    for currentArgument, currentValue in arguments:
        if currentArgument in ("-r", "--robo"):
            mode = "r"

        elif currentArgument in ("-i", "--instrument"):
            mode = "i"

        elif currentArgument in ("-m", "--manual"):
            mode = "m"

    modes = dict()
    modes.update(
        {"r": "Entering [R]obotic schedule file mode (will initiate observations!)"}
    )
    modes.update(
        {
            "i": "Entering [I]nstrument mode: initializing instrument subsystems and waiting for commands"
        }
    )
    modes.update(
        {
            "m": "Entering fully [M]anual mode: initializing all subsystems and waiting for commands"
        }
    )

    opts = arguments

    printlogo()
    print()
    for line in big_letter[mode]:
        print("\t\t\t\t", line)
    print("\033[32m >>>> ", modes[mode])
    print()
    print(linebreak)
    print("\033[32m")

    # load the config
    config_file = CONFIG_PATH
    config = utils.loadconfig(config_file)
    # set up the logger
    logger = logging_setup.setup_logger(wsp_path, config)

    # housekeeping configuration
    hk_config_filepath = os.path.join(CONFIG_DIR, "hk_config.yaml")
    hk_config = utils.loadconfig(hk_config_filepath)

    # START UP THE CONTROL SYSTEM

    # If an option was specified from the command line, then use that
    if mode is not None:
        # print(f'Starting WSP with mode = {mode}, opts = {opts}')

        winter = systemControl.control(
            mode=mode,
            config=config,
            hk_config=hk_config,
            base_directory=wsp_path,
            logger=logger,
            opts=opts,
        )
    else:
        print("\033[31mError: No mode specified. Use -r, -i, or -m\033[0m")
        sys.exit(1)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
