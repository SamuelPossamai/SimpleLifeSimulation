
import random
import numpy

class CreatureTrait:

    def __init__(self, name, min_val, max_val, integer_only=False,
                 mutation_rate=0.1, proportional_mutation=False,
                 exponential_random=False):

        self.__name = name
        self.__min = min_val
        self.__max = max_val
        self.__int_only = integer_only
        self.__mut = mutation_rate
        self.__prop_mut = proportional_mutation
        self.__exp_rnd = exponential_random

    @property
    def name(self):
        return self.__name

    def valuesSimilarity(self, val1, val2):

        if val1 == val2:
            return 1

        similarity = 0
        if self.__prop_mut:

            if val1 > val2:
                return val2/val1

            return val1/val2

        return 1 - abs(val1 - val2)/(self.__max - self.__min)


    def random(self):

        diff = self.__max - self.__min

        if self.__exp_rnd:

            value = self.__min + min(numpy.random.exponential(diff)/1000,
                                     diff)

            if self.__int_only:
                return int(value)

            return value

        if self.__int_only:
            return random.randint(self.__min, self.__max)

        return random.random()*(diff) + self.__min

    def mutate(self, val):

        if self.__prop_mut:
            mut_base = val
        else:
            mut_base = self.__max - self.__min

        rand_n = 2*(0.5 - random.random())*mut_base
        val += rand_n*self.__mut

        if self.__int_only:
            val = round(val)

        if val < self.__min:
            val = self.__min

        if val > self.__max:
            val = self.__max

        return val

def getCreatureTraits(materials, energy_materials, waste_materials,
                      material_rules):

    traits = CREATURE_BASE_TRAITS.copy()

    for material in materials:
        traits.append(CreatureTrait(
            f'{material}_childqtd', 1.e4, 1.e7, integer_only=True,
            exponential_random=True, proportional_mutation=True))
        traits.append(CreatureTrait(
            f'{material}_childqtd_min_to_reproduce', 2, 100,
            proportional_mutation=True))

    if len(energy_materials) > 1:
        for material in energy_materials:
            traits.append(CreatureTrait(
                f'{material.name}_energypriority', 0, 32, integer_only=True))

    for rule in material_rules:
        traits.append(CreatureTrait(
            f'{rule.name}_convertionrate', 0, 32, integer_only=True))

    for material in waste_materials:
        traits.append(CreatureTrait(
            f'{material.name}_waste_qtd_to_remove', 0, 0.5))

    return traits

CREATURE_BASE_TRAITS = [

    CreatureTrait('speed', 0, 1),
    CreatureTrait('eatingspeed', 0, 1),
    CreatureTrait('visiondistance', 0, 1),
    CreatureTrait('visionangle', 0, 1),
    CreatureTrait('walkpriority', 0, 16, integer_only=True),
    CreatureTrait('runpriority', 0, 16, integer_only=True),
    CreatureTrait('fastrunpriority', 0, 16, integer_only=True),
    CreatureTrait('idlepriority', 0, 16, integer_only=True),
    CreatureTrait('rotatepriority', 0, 16, integer_only=True),
]
