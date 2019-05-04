
import matplotlib.pyplot as plt

from simulation import Simulation

def plotDNAInfo(generations, parameter):
    
    for gen_number, generation_dnas in enumerate(generations):
        
        speed_points = []
        for creature_dna in generation_dnas:
            info = Simulation.Creature.readDNA(creature_dna, to_dict=True)
            speed_points.append(info[parameter])
        
        plt.plot([gen_number + 1]*len(speed_points), speed_points, 'o')
    
    plt.xticks(range(1, gen_number + 2))
    
    plt.show()


if __name__ == '__main__':
    
    import sys
    
    if len(sys.argv) != 3:
        
        print('This program must receive exactly two arguments')
        exit()
    
    generations = []
    with open(sys.argv[1]) as f:
        
        for line in f:

            if not line:
                continue
            
            if line[0] == '[':
                generations.append([])
            else:
                generations[-1].append(line[:-1])

    plotDNAInfo(generations, sys.argv[2])
    
