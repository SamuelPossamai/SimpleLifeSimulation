
import json
from math import ceil

from .materials import CREATURE_MATERIALS

class CreatureMaterialConvertionRule:

    REACTION_SPEED_BASE_MULT = 1e-4

    class MaterialInfo:

        def __init__(self, material, quantity):
            self.__material = material
            self.__quantity = quantity

        @property
        def material(self):
            return self.__material

        @property
        def quantity(self):
            return self.__quantity

        def __str__(self):
            return f'{self.__quantity}*{self.__material}'

        def __repr__(self):
            return (f'MaterialInfo(material={repr(self.__material)}, '
                    f'quantity={self.__quantity})')

    class CatalystInfo:

        def __init__(self, material, effect):
            self.__material = material
            self.__effect = effect

        @property
        def material(self):
            return self.__material

        @property
        def effect(self):
            return self.__effect

        def __str__(self):
            return f'{self.__material}({self.__effect})'

        def __repr__(self):
            return (f'CatalystInfo(material={repr(self.__material)}, '
                    f'effect={self.__effect})')

    def __init__(self, name, input_list, output_list, catalysts=None,
                 structure_multiplier=1, ingredient_multiplier=1, speed=1,
                 join_factors_function=min):

        for material_info in input_list:
            material_info.material.addRule(self)

        for material_info in output_list:
            material_info.material.addRule(self)

        self.__name = name
        self.__input_list = tuple(input_list)
        self.__output_list = tuple(output_list)
        self.__catalysts = tuple(catalysts) if catalysts is not None else None
        self.__struct_mult = structure_multiplier
        self.__ing_mult = ingredient_multiplier
        self.__speed = speed
        self.__join_func = join_factors_function

    def convert(self, structure, materials, rate):

        factors = [None, None, None]
        if self.__catalysts:
            factor = 0
            for catalyst_info in self.__catalysts:
                qtd = materials.get(catalyst_info.material)
                factor += qtd*catalyst_info.effect
            factors[0] = factor

        if self.__struct_mult:
            factors[1] = structure*self.__struct_mult

        current_qtd_for_input = tuple(materials.get(material_info.material)
                                      for material_info in self.__input_list)

        max_reactions = None
        for qtd, material_info in zip(current_qtd_for_input, self.__input_list):
            material_max_reactions = qtd//material_info.quantity
            if max_reactions is None or material_max_reactions < max_reactions:
                max_reactions = material_max_reactions

        if self.__ing_mult:
            factors[2] = max_reactions*self.__ing_mult

        reactions = ceil(rate*self.__speed*self.REACTION_SPEED_BASE_MULT*
                         self.__join_func(factor for factor in factors
                                          if factor is not None))

        if reactions > max_reactions:
            reactions = max_reactions

        reactions = int(reactions)

        if reactions <= 0:
            return

        for qtd, material_info in zip(current_qtd_for_input, self.__input_list):
            materials[material_info.material] = \
                qtd - reactions*material_info.quantity

        for material_info in self.__output_list:
            materials[material_info.material] += \
                reactions*material_info.quantity

    @property
    def name(self):
        return self.__name

    def __str__(self):
        eq_l = ' + '.join(str(mat_info) for mat_info in self.__input_list)
        eq_r = ' + '.join(str(mat_info) for mat_info in self.__output_list)

        return f'{eq_l} -> {eq_r}'

    def __repr__(self):
        return f'CreatureMaterialConvertionRule({str(self)})'

def __loadConvertionRuleMaterialInfo(material_info_list, materials):
    return [
        CreatureMaterialConvertionRule.MaterialInfo(
            materials[input_info['material']],
            input_info.get('quantity', 1)
        ) for input_info in material_info_list
    ]

def __loadConvertionRule(name, rule, materials):

    input_materials = __loadConvertionRuleMaterialInfo(
        rule['input'], materials)
    output_materials = __loadConvertionRuleMaterialInfo(
        rule['output'], materials)

    return CreatureMaterialConvertionRule(
        name,
        input_materials,
        output_materials,
        speed=rule.get('speed', 1)
    )

def loadConvertionRules(filename, materials):

    with open(filename) as file:
        return tuple(
            __loadConvertionRule(rule_name, rule, materials)
            for rule_name, rule in json.load(file).items()
        )
