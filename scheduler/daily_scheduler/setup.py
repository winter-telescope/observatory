#! /usr/bin/env python
#
# Copyright (C) 2015-17 California Institute of Technology

DESCRIPTION = "winter_sim: Scheduling library for WINTER based \
on zrf_sim for the Zwicky Transient Facility"
LONG_DESCRIPTION = """\
Scheduling library for WINTER based on \
 the Zwicky Tranisent Facility
"""


DISTNAME = 'winter_sim'
MAINTAINER = 'Danielle Frostig'
MAINTAINER_EMAIL = 'frostig@mit.edu'
URL = 'https://magellomar-gitlab.mit.edu/WINTER/code/tree/master/scheduler/'
LICENSE = 'BSD (3-clause)'
DOWNLOAD_URL = 'https://magellomar-gitlab.mit.edu/WINTER/code/tree/master/scheduler/'
VERSION = '0.1'

'''
DISTNAME = 'ztf_sim'
MAINTAINER = 'Eric Bellm'
MAINTAINER_EMAIL = 'ecbellm@uw.edu'
URL = 'https://github.com/ZwickyTransientFacility/ztf_sim/'
LICENSE = 'BSD (3-clause)'
DOWNLOAD_URL = 'https://github.com/ZwickyTransientFacility/ztf_sim/'
VERSION = '1.0' '''

try:
    from setuptools import setup
    _has_setuptools = True
except ImportError:
    from distutils.core import setup

def check_dependencies():
    install_requires = []

    # Just make sure dependencies exist, I haven't rigorously
    # tested what the minimal versions that will work are
    # (help on that would be awesome)
    try:
        import numpy
    except ImportError:
        install_requires.append('numpy')
    try:
        import scipy
    except ImportError:
        install_requires.append('scipy')
    try:
        import astropy
    except ImportError:
        install_requires.append('astropy')
    try:
        import astroplan
    except ImportError:
        install_requires.append('astroplan')
    try:
        import pandas
    except ImportError:
        install_requires.append('pandas')
#    try:
#        import sklearn
#    except ImportError:
#        install_requires.append('sklearn')
#    try:
#        import sklearn_pandas
#    except ImportError:
#        install_requires.append('sklearn_pandas')
#    try:
#        import xgboost
#    except ImportError:
#        install_requires.append('xgboost')
    try:
        import transitions
    except ImportError:
        install_requires.append('transitions')
    try:
        import gurobipy
    except ImportError:
        install_requires.append('gurobipy')

    return install_requires

if __name__ == "__main__":

    install_requires = check_dependencies()

    setup(name=DISTNAME,
        author=MAINTAINER,
        author_email=MAINTAINER_EMAIL,
        maintainer=MAINTAINER,
        maintainer_email=MAINTAINER_EMAIL,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        license=LICENSE,
        url=URL,
        version=VERSION,
        download_url=DOWNLOAD_URL,
        install_requires=install_requires,
        include_package_data=True,
        zip_safe=False,
        packages=['ztf_sim'],
        scripts=['bin/run_ztf_sim', 'bin/analyze_ztf_sim', 'bin/load_ztf_sim'],
        classifiers=[
                     'Intended Audience :: Science/Research',
                     'Programming Language :: Python :: 3.6',
                     'License :: OSI Approved :: BSD License',
                     'Topic :: Scientific/Engineering :: Visualization',
                     'Operating System :: POSIX',
                     'Operating System :: Unix',
                     'Operating System :: MacOS'],
          )

