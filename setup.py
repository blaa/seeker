#!/usr/bin/env python
# coding: utf-8

from setuptools import setup

setup(
    name = "seeker",
    version = "v0.1",
    author = "Tomasz Fortuna",
    author_email = "bla@thera.be",
    description = ("Scripts which non-destructively measures multi-threaded "
                   "file/device IOPS/sequential read performance. "
                   "Made to compare/test backends for databases."),
    license = "MIT",
    keywords = "iops performance parallel disc ssd hdd",
    url = "https://github.com/blaa/seeker",
    scripts=['seeker'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)
