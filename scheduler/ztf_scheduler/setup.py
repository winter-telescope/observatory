#! /usr/bin/env python
#
# Copyright (C) 2015-17 California Institute of Technology

DESCRIPTION = "ztf_scheduler: Interface to the production scheduler for the Zwicky Transient Facility"
LONG_DESCRIPTION = """\
Interface to the production scheduler for the Zwicky Transient Facility.
"""

DISTNAME = 'ztf_scheduler'
MAINTAINER = 'Eric Bellm'
MAINTAINER_EMAIL = 'ecbellm@uw.edu'
URL = 'https://github.com/ZwickyTransientFacility/ztf_scheduler/'
LICENSE = 'BSD (3-clause)'
DOWNLOAD_URL = 'https://github.com/ZwickyTransientFacility/ztf_scheduler/'
VERSION = '0.0.1.dev'

try:
    from setuptools import setup
    _has_setuptools = True
except ImportError:
    from distutils.core import setup

def check_dependencies():
    install_requires = []

    # Just make sure dependencies exist
    try:
        import ztf_sim
    except ImportError:
        install_requires.append('ztf_sim')
    try:
        import gurobi
    except ImportError:
        install_requires.append('gurobi')

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
        packages=['ztf_scheduler'],
        classifiers=[
                     'Intended Audience :: Science/Research',
                     'Programming Language :: Python :: 3.6',
                     'License :: OSI Approved :: BSD License',
                     'Topic :: Scientific/Engineering :: Visualization',
                     'Operating System :: POSIX',
                     'Operating System :: Unix',
                     'Operating System :: MacOS'],
          )

