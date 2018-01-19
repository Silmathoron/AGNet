#!/usr/bin/env python
#-*- coding:utf-8 -*-
#
# This file is part of the NNGT project to generate and analyze
# neuronal networks and their activity.
# Copyright (C) 2015-2017  Tanguy Fardet
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import warnings
import traceback

from setuptools import setup, Extension, find_packages
from distutils.command.build_ext import build_ext

import numpy

from nngt import __version__

try:
    from Cython.Build import cythonize
    import setuptools
    version = setuptools.__version__
    version = int(version[:version.index(".")])
    with_cython = (version >= 18)
    from _cpp_cleaner import clean_cpp
except ImportError as e:
    with_cython = False


# ------------------ #
# Paths and platform #
# ------------------ #

omp_pos = sys.argv.index("--omp") if "--omp" in sys.argv else -1
omp_lib_dir = "/usr/lib" if omp_pos == -1 else sys.argv[omp_pos + 1]

dirname = os.path.abspath(__file__)[:-8]
dirname += ("/" if dirname[-1] != "/" else "") + "nngt/generation/"

LINUX = (os.name == "posix")
MAC   = (os.name == "mac")
WIN   = (os.name == "nt")


# ------------------------ #
# Compiling OMP algorithms #
# ------------------------ #

# compiler options

copt =  {
    'msvc'    : ['/openmp', '/O2', '/fp:precise', '/favor:INTEL64'],
    'mingw32' : [
        '-fopenmp', '-O2', '-g', '-ffast-math', '-march=native', '-msse',
        '-ftree-vectorize',
    ],
    'unix'    : [
        '-Wno-cpp', '-Wno-unused-function', '-fopenmp', '-ffast-math',
        '-msse', '-ftree-vectorize', '-O2', '-g',
    ],
}

lopt =  {
    'mingw32' : ['-fopenmp'],
    'unix'    : ['-fopenmp']
}


class CustomBuildExt(build_ext):

    def build_extensions(self):
        c = self.compiler.compiler_type

        for e in self.extensions:
            e.extra_link_args.extend(lopt.get(c, []))
            e.extra_compile_args.extend(copt.get(c, []))

        build_ext.build_extensions(self)


# cython extensions

ext = '.pyx' if with_cython else '.cpp'

extensions = Extension(
    "nngt.generation.cconnect", # name of extension
    sources = [dirname + "cconnect" + ext, dirname + "func_connect.cpp"],
    extra_compile_args = ["-std=c++11"],
    language="c++",
    include_dirs=[dirname, numpy.get_include()],
    libraries = ['gomp'],
    library_dirs = [dirname, omp_lib_dir]
)


if with_cython:
    extensions = cythonize(extensions)
    clean_cpp(dirname + 'cconnect.cpp')
else:
    extensions = [extensions]


long_descr = '''
NNGT provides a unified interface to use three of the main
Python graph ''libraries (graph-tool, igraph, and networkx) in order to
generate and study neuronal networks. It allows the user to easily send this
graph to the NEST simulator, the analyze the resulting activity while taking
structure into account.
'''


# ----- #
# Setup #
# ----- #

setup_params = dict(
    name = 'nngt',
    version = __version__,
    description = 'Package to study structure and activity in ' +\
                  'neuronal networks',

    package_dir = {'': '.'},
    packages = find_packages('.'),

    cmdclass = {'build_ext': CustomBuildExt},

    # Include the non python files:
    package_data = {'': [
        '*.txt', '*.rst', '*.md', '*.default', '*.pyx', '*.pxd', '*.cpp',
        '*.h', '*.pyxbld',
    ]},

    # Requirements
    install_requires = ['numpy', 'scipy>=0.11'],
    python_requires = '>=2.7, <4',
    extras_require = {
        'matplotlib': 'matplotlib',
        'PySide': ['PySide'],
        'PDF':  ["ReportLab>=1.2", "RXP"],
        'reST': ["docutils>=0.3"],
        'nx': ['networkx>=2.0'],
        'ig': ['python-igraph']
    },

    # Cython module
    ext_modules = extensions,

    # Metadata
    url = 'https://github.com/Silmathoron/NNGT',
    author = 'Tanguy Fardet',
    author_email = 'tanguy.fardet@univ-paris-diderot.fr',
    license = 'GPL3',
    keywords = 'neuronal network graph structure simulation NEST ' +\
               'topology growth',
    long_description = long_descr,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Programming Language :: C++',
        'Programming Language :: Cython',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Bio-Informatics'
    ]
)


# Try to compile with multithreaded algorithms; if fails, pure python install

try:
    setup(**setup_params)
except (Exception, SystemExit) as e:
    sys.stderr.write(
        "Could not compile multithreading algorithms: {}\n".format(e))
    sys.stderr.write("Switching to pure python install.\n")
    sys.stderr.flush()

    setup_params["ext_modules"] = []
    setup(**setup_params)
    
