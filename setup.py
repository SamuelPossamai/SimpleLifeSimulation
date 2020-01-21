#!/usr/bin/env python

import os
from setuptools import setup

DIR_PATH = os.path.abspath(os.path.dirname(__file__))

with open(f'{DIR_PATH}/requirements.txt') as file:
    requirements = list(file)

setup(
    name='SimpleLifeSimulation',
    version='0.1',
    install_requires=requirements,
    packages=['simplelifesimulation'],
    package_dir={

        'simplelifesimulation': 'src',
    },
    entry_points={

        'gui_scripts': [
            'simplelifesimulation = simplelifesimulation.main:main',
        ]
    },
    license='LGPL-3.0'
)
