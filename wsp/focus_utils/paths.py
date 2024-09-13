import os
from pathlib import Path

BASE_CODE_DIR = Path(__file__).parent.parent.resolve()
CONFIG_DIR = Path(BASE_CODE_DIR, "config", "focus_config")

astrom_scamp = CONFIG_DIR.joinpath("scamp.conf")
astrom_sex = CONFIG_DIR.joinpath("astrom.sex")
astrom_param = CONFIG_DIR.joinpath("astrom.param")
astrom_filter = CONFIG_DIR.joinpath("default.conv")
astrom_swarp = CONFIG_DIR.joinpath("config.swarp")
astrom_nnw = CONFIG_DIR.joinpath("default.nnw")
photom_sex = CONFIG_DIR.joinpath("photomCat.sex")

DATA_DIR = os.path.join(os.getenv("HOME"), "data", "image-daemon-data", "data")

MASK_DIR = Path(DATA_DIR, "masks")
MASTERDARK_DIR = Path(DATA_DIR, "masterdarks")
MASTERFLAT_DIR = Path(DATA_DIR, "masterflats")

DEFAULT_OUTPUT_DIR = Path().home().joinpath("winterutils_output")
DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)

MASTERBIAS_DIR = Path(DATA_DIR, "masterbias")

print(f"astro_scamp = {astrom_scamp}")
print(f"masterbias_dir = {MASTERBIAS_DIR}")
