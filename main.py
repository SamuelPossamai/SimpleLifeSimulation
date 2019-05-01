#!/usr/bin/env python3

import argparse

from simulation import Simulation

def integer_min_limit(arg_name, min_, x):
    
    x = int(x)
    
    if x < min_:
        raise argparse.ArgumentTypeError("%s must be higher or equal to %d" % (arg_name, min_))
    
    return x

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    
    parser.add_argument('-p', '--pop-size', type=lambda x : integer_min_limit('Population size', 2, x),
                        default=32, help='Number of starting creatures at the begin of each generation')
    parser.add_argument('-r', '--resources-qtd', type=lambda x : integer_min_limit('Resources starting quantity', 0, x),
                        default=20, help='Number of starting resources at the begin of each generation')
    parser.add_argument('-s', '--size', type=lambda x : integer_min_limit('Environment size', 100, x),
                        default=1000, help='Size of the environment')
    parser.add_argument('-W', '--screen-width', type=lambda x : integer_min_limit('Width', 100, x),
                        default=600, help='Window width')
    parser.add_argument('-H', '--screen-height', type=lambda x : integer_min_limit('Height', 100, x),
                        default=600, help='Window height')
    parser.add_argument('-o', '--out-file', default=None, help='Name of the output file')

    args = parser.parse_args()

    game = Simulation(population_size=args.pop_size, starting_resources=args.resources_qtd, 
                      size=args.size, out_file=args.out_file, 
                      screen_size=(args.screen_width, args.screen_height))
    game.run()
