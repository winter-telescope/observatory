# https://gist.github.com/jbn/fc90e3ddbc5c60c698d07b3df30004c8
import os
import time
import inspect
import logging
import logging.config

BASE_DIR = os.path.dirname(os.path.abspath(inspect.getfile(
                inspect.currentframe()))) + '/'

TARGET_OUTPUT_DIR = BASE_DIR+'../'

# TODO: handle FILTER_EMPTY
ROZ_FILTER_NAME_TO_ID = {'FILTER_ZTF_G': 1, 'FILTER_ZTF_R': 2, 
        'FILTER_ZTF_I': 3, 'FILTER_EMPTY': None}
FILTER_ID_TO_ROZ_NAME = {v: k for k, v in list(ROZ_FILTER_NAME_TO_ID.items())}

# if testing, use a fixed past time
TESTING = (int(os.environ['TEST_ZTF_SCHEDULER']) == 1)


class UTCFormatter(logging.Formatter):
    """Output logs in UTC"""
    converter = time.gmtime


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'utc': {
            '()': UTCFormatter,
            'format': '%(asctime)s %(levelname)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console':{
            'level':'INFO',
            'class':'logging.StreamHandler',
            'formatter': 'simple',
            'stream'  : 'ext://sys.stdout'
        },
        'logfile': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': f'{BASE_DIR}/../logs/ztf.log',
            'formatter': 'utc',
            'when': 'midnight',
            'utc': 'True'
        }
    },
    'loggers': {
        '': { # this is the root logger; doesn't work if we call it root
            'handlers':['console','logfile'],
            'level':'INFO',
        },
        'aiohttp': {
            'handlers':['logfile'],
            'level':'INFO',
        }
    }
}
