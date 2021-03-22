#!/usr/bin/env python3

from pathlib import Path
import json

import argparse

from .simulation import Simulation
from .creature import Creature

from .material_rules import loadConvertionRules
from .materials import loadMaterials
from .creature_traits import getCreatureTraits

def interval_integer_min_limit(arg_name, min_, arg):

    values = arg.split('-')

    if len(values) > 2:
        raise argparse.ArgumentTypeError(
            "%s cannot contain more than one '-' character" % arg_name)

    if len(values) == 2:

        min_ = integer_min_limit(arg_name + '(min value)', min_, values[0])
        max_ = integer_min_limit(arg_name + '(max value)', min_, values[1])
        if min_ > max_:
            raise argparse.ArgumentTypeError(
                "%s min value must be lower than max value" % arg_name)

        return min_, max_

    return integer_min_limit(arg_name, min_, arg)

def integer_min_limit(arg_name, min_, x):

    try:
        x = int(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%s must be an integer" % arg_name)

    if x < min_:
        raise argparse.ArgumentTypeError(
            "%s must be higher or equal to %d" % (arg_name, min_))

    return x

def interval_integer(arg_name, min_, max_, x):

    x = integer_min_limit(arg_name, min_, x)

    if x > max_:
        raise argparse.ArgumentTypeError(
            "%s must be lower or equal to %d" % (arg_name, max_))

    return x

def real_min_limit(arg_name, min_, x):

    try:
        x = float(x)
    except ValueError:
        raise argparse.ArgumentTypeError("%s must be a number" % arg_name)

    if x < min_:
        raise argparse.ArgumentTypeError(
            "%s must be higher or equal to %d" % (arg_name, min_))

    return x

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--pop-size', type=lambda x : interval_integer_min_limit('Population size', 1, x),
                        default=32, help='Number of starting creatures at the begin of each generation, can be an interval min-max')
    parser.add_argument('-r', '--resources-qtd', type=lambda x : interval_integer_min_limit('Resources starting quantity', 0, x),
                        default=20, help='Number of starting resources at the begin of each generation, can be an inteval min-max')
    parser.add_argument('-S', '--simulation-speed', type=lambda x : integer_min_limit('Simulation speed', 1, x),
                        default=50, help='Speed of the simulation when running with graphics')
    parser.add_argument('-s', '--size', type=lambda x : integer_min_limit('Environment size', 100, x),
                        default=1000, help='Size of the environment')
    parser.add_argument('-W', '--screen-width', type=lambda x : integer_min_limit('Width', 100, x),
                        default=None, help='Window width')
    parser.add_argument('-H', '--screen-height', type=lambda x : integer_min_limit('Height', 100, x),
                        default=None, help='Window height')
    parser.add_argument('-o', '--out-file', default=None, help='Name of the output file')
    parser.add_argument('-i', '--in-file', default=None,
                        help='Name of the input file, if -p flag is specified it is ignored, the population size will be determined by the file')
    parser.add_argument('--no-graphic', dest='use_graphic', action='store_false', help='Do not run graphics')
    parser.add_argument('--quiet', action='store_true', help='Print less information')
    parser.add_argument('--material-rules-config', default=None, help='Name of the material convertion rules configuration file')
    parser.add_argument('--materials-config', default=None, help='Name of the materials configuration file')
    parser.add_argument('--materials-quantity', default=None, help='Name of the materials initial quantity configuration file')
    parser.add_argument('-c', '--config', default=None, help='Name of the materials configuration file')
    parser.add_argument('--no-wall', dest='use_wall', action='store_false', default=True, help='Remove frontier wall')
    parser.add_argument('-m', '--starting-materials-multiplier', type=lambda x : real_min_limit('Starting materials multiplier', 0.1, x),
                        default=1, help='Multiplier factor for creature starting materials')

    args = parser.parse_args()

    if args.screen_width is not None or args.screen_height is not None:
        screen_size = (args.screen_width or 600, args.screen_height or 600)
    else:
        screen_size = None

    creature_config_kwargs = {}

    material_rules_config_file = args.material_rules_config
    materials_config_file = args.materials_config
    materials_quantity_file = args.materials_quantity

    config_dir = args.config

    if config_dir is None:

        current_file_path = Path(__file__)
        config_dir = current_file_path.parent.joinpath('data')

        if not config_dir.exists():
            config_dir = current_file_path.parents[1].joinpath('data')

    config_dir = Path(config_dir)

    if material_rules_config_file is None:
        material_rules_config_file = config_dir.joinpath(
            'material_convertion_rules.json')

    if materials_config_file is None:
        materials_config_file = config_dir.joinpath('materials.json')

    if materials_quantity_file is None:
        materials_quantity_file = config_dir.joinpath(
            'materials_initial_quantity.json')

    materials, energy_materials, structure_materials, waste_materials = \
        loadMaterials(materials_config_file)

    creature_config_kwargs['materials'] = materials
    creature_config_kwargs['energy_materials'] = energy_materials
    creature_config_kwargs['structure_materials'] = structure_materials
    creature_config_kwargs['waste_materials'] = waste_materials

    if material_rules_config_file is None:
        material_rules_config_file = base_file_path.joinpath(
            'material_convertion_rules.json')

    convertion_rules = loadConvertionRules(
        material_rules_config_file, materials)
    creature_config_kwargs['material_rules'] = convertion_rules

    st_materials_mult = args.starting_materials_multiplier

    with open(materials_quantity_file) as file:
        materials_qtd_file_content = json.load(file)

    initial_materials = {
        material: materials_qtd_file_content.get(
            material.name, 0)*st_materials_mult
        for material in materials.values()
    }

    creature_config_kwargs['traits'] = getCreatureTraits(
        materials, energy_materials, waste_materials, convertion_rules,
        initial_materials)

    creature_config = None
    if creature_config_kwargs:
        creature_config = Creature.Config(**creature_config_kwargs)

    game = Simulation(population_size=args.pop_size,
                      ticks_per_second=args.simulation_speed,
                      starting_resources=args.resources_qtd,
                      size=args.size, out_file=args.out_file,
                      screen_size=screen_size,
                      in_file=args.in_file, use_graphic=args.use_graphic,
                      quiet=args.quiet, creature_config=creature_config,
                      creature_materials_start=initial_materials,
                      use_wall=args.use_wall)
    game.run()

if __name__ == '__main__':
    main()
