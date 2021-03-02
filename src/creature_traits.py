
import random
import numpy

from .materials import ENERGY_MATERIALS, WASTE_MATERIALS, CREATURE_MATERIALS
from .material_rules import CREATURE_MATERIAL_RULES

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

def addcreaturetraitproperties(traits, property_name_modifier=None):

    def decorator(baseclass):
        for trait in traits:
            if property_name_modifier is None:
                property_name = trait.name
            else:
                property_name = property_name_modifier(trait.name)
            setattr(baseclass, property_name,
                    property(lambda self, name=trait.name: self.getTrait(name)))
        return baseclass

    return decorator

CREATURE_TRAITS = [

    CreatureTrait('speed', 0, 1),
    CreatureTrait('eatingspeed', 0, 1),
    CreatureTrait('visiondistance', 0, 1),
    CreatureTrait('visionangle', 0, 1),
    CreatureTrait('excessenergytoreproduce', 0, 2),
    CreatureTrait('childsizepercentage', 0.05, 0.5),
    CreatureTrait('walkpriority', 0, 16, integer_only=True),
    CreatureTrait('runpriority', 0, 16, integer_only=True),
    CreatureTrait('fastrunpriority', 0, 16, integer_only=True),
    CreatureTrait('idlepriority', 0, 16, integer_only=True),
    CreatureTrait('rotatepriority', 0, 16, integer_only=True),
]

for material in CREATURE_MATERIALS:
    CREATURE_TRAITS.append(CreatureTrait(
        f'{material}_childqtd', 1.e4, 1.e7, integer_only=True,
        exponential_random=True, proportional_mutation=True))
    CREATURE_TRAITS.append(CreatureTrait(
        f'{material}_childqtd_min_to_reproduce', 2, 100,
        proportional_mutation=True))

if len(ENERGY_MATERIALS) > 1:
    for material in ENERGY_MATERIALS:
        CREATURE_TRAITS.append(CreatureTrait(
            f'{material.name}_energypriority', 0, 32, integer_only=True))

for rule in CREATURE_MATERIAL_RULES:
    CREATURE_TRAITS.append(CreatureTrait(
        f'{rule.name}_convertionrate', 0, 32, integer_only=True))

for material in WASTE_MATERIALS:
    CREATURE_TRAITS.append(CreatureTrait(
        f'{material.name}_waste_qtd_to_remove', 0, 0.5))
