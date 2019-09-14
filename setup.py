#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import io
import sys
from glob import glob
from os.path import basename, dirname, join, splitext

from setuptools import find_packages, setup

# this file needs to be run with python 3.5 or later because of the dict
# unpacking below (PEP 448)
if sys.version_info < (3, 5):
    raise RuntimeError("Python version >= 3.5 required")


def read(*names, **kwargs):
    filename = join(dirname(__file__), *names)
    encoding = kwargs.get("encoding", "utf8")

    with io.open(filename, encoding=encoding) as fh:
        return fh.read()


# =============================================================================
# Package metadata
# =============================================================================

# complete classifier list: https://pypi.org/classifiers/
CLASSIFIERS = [
    # status
    "Development Status :: 3 - Alpha",

    # who this project is for
    "Intended Audience :: Developers",
    "Intended Audience :: Education",
    "Intended Audience :: Science/Research",

    # lawyer stuff
    "License :: OSI Approved",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",

    # operating system
    "Operating System :: OS Independent",

    # natural language
    "Natural Language :: English",

    # programming language
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: Implementation :: CPython",

    # topic
    "Topic :: Education",
    "Topic :: Scientific/Engineering",
    "Topic :: Scientific/Engineering :: Physics",
    "Topic :: Software Development :: Libraries",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

metadata = dict(
    name="billiards",
    version="0.0.0",
    license="GNU General Public License v3 or later (GPLv3+)",
    description="A 2D physics engine for simulating dynamical billiards.",
    long_description=read("README.rst"),
    author="Markus Ebke",
    author_email="markus.ebke92@gmail.com",
    url="https://github.com/markus-ebke/python-billiards",
    classifiers=CLASSIFIERS,
    project_urls={
        "Source Code": "https://github.com/markus-ebke/python-billiards",
        "Bug Reports": "https://github.com/markus-ebke/python-billiards/issues",
    },
    keywords=["python3", "physics-engine", "physics-2d"],
)


# =============================================================================
# Build options
# =============================================================================

options = dict(
    python_requires=">=3.5",
    install_requires=[
        "numpy",
    ],
    setup_requires=[
        "pytest-runner",
    ],
    tests_require=[
        "pytest",
        "pytest-cov",
    ],
    packages=find_packages(where="src", exclude="docs"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
)


# =============================================================================
# Main setup
# =============================================================================
setup(**metadata, **options)
