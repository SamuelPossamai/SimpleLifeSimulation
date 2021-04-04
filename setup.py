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
    packages=[
        'simplelifesimulation',
        'simplelifesimulation.creatures',
        'simplelifesimulation.creatures.materials',
        'simplelifesimulation.simulation',
        'simplelifesimulation.plants',
        'simplelifesimulation.interface',
        'simplelifesimulation.interface.pygame',
        'simplelifesimulation.data'
    ],
    package_dir={
        'simplelifesimulation': 'simplelifesimulation',
        'simplelifesimulation.creatures': 'simplelifesimulation/creatures',
        'simplelifesimulation.creatures.materials':
            'simplelifesimulation/creatures/materials',
        'simplelifesimulation.simulation': 'simplelifesimulation/simulation',
        'simplelifesimulation.plants': 'simplelifesimulation/plants',
        'simplelifesimulation.interface': 'simplelifesimulation/interface',
        'simplelifesimulation.interface.pygame':
            'simplelifesimulation/interface/pygame',
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
