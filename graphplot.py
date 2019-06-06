
import matplotlib.pyplot as plt

from simulation import Simulation

def plotDNAInfo(generations, parameter, save_to=None):
    
    for gen_number, generation_dnas in enumerate(generations):
        
        speed_points = []
        for creature_dna in generation_dnas:
            info = Simulation.Creature.readDNA(creature_dna, to_dict=True)
            speed_points.append(info[parameter])
        
        plt.plot([gen_number + 1]*len(speed_points), speed_points, 'o')
    
    plt.xticks(range(1, gen_number + 2))
    
    if save_to is None:
        plt.show()
    else:
        plt.savefig(save_to)

if __name__ == '__main__':
    
    import sys
    
    if len(sys.argv) != 3 and len(sys.argv) != 4:
    
        print(sys.argv)
        print('This program must receive exactly two or three arguments')
        exit()
    
    if len(sys.argv) == 4:
        save_to = sys.argv[3]
    else:
        save_to = None
    
    generations = []
    with open(sys.argv[1]) as f:
        
        for line in f:

            if not line:
                continue
            
            if line[0] == '[':
                generations.append([])
            else:
                generations[-1].append(line[:-1])

    plotDNAInfo(generations, sys.argv[2], save_to=save_to)
    
