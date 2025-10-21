import os

# global variables for paths
WSP_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_DIR = os.path.join(WSP_PATH, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")
TELEMETRY_CONFIG_PATH = os.path.join(CONFIG_DIR, "telemetry_config.yaml")

CREDENTIALS_DIR = os.path.join(WSP_PATH, "credentials")
