#!/usr/bin/env python3
# pylint: disable=W,C

from setuptools import setup, find_packages
setup(
    name = "moonbook",
    version = "0.1.0",
    author = "Jacob Hipps",
    author_email = "jacob@ycnrg.org",
    license = "MIT",
    description = "Cataclysm DDA update tool for Linux and Mac",
    keywords = "cataclysm update automatic game tools",
    url = "https://git.ycnrg.org/projects/GTOOL/repos/upcata",

    packages = find_packages(),
    scripts = [],

    install_requires = ['arrow', 'requests'],

    package_data = {
        '': [ '*.md' ],
    },

    entry_points = {
        'console_scripts': [ 'upcata = upcata:_main' ]
    }

    # could also include long_description, download_url, classifiers, etc.
)
