#!/usr/bin/env python

import os
from setuptools import setup, find_packages

DIR_PATH = os.path.abspath(os.path.dirname(__file__))

with open(f'{DIR_PATH}/requirements.txt') as file:
    requirements = list(file)

packages = find_packages()

packages.append('simplelifesimulation.data')

setup(
    name='SimpleLifeSimulation',
    version='0.1',
    install_requires=requirements,
    packages=packages,
    package_dir={
        'simplelifesimulation.data': 'data'
    },
    package_data={
        'simplelifesimulation.data': ['*.json']
    },
    entry_points={
        'gui_scripts': [
            'simplelifesimulation = simplelifesimulation.__main__:main',
        ]
    },
    license='LGPL-3.0'
)
