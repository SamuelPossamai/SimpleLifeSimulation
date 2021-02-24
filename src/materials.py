
import json
from math import ceil

class CreatureMaterial:

    def __init__(self, name, description=None, mass=1, density=1,
                 structure_efficiency=0, energy_efficiency=0,
                 waste_material=None, is_waste=False, short_name=None):

        self.__name = name
        self.__desc = description
        self.__mass = mass
        self.__density = density
        self.__struct_ef = structure_efficiency
        self.__en_ef = energy_efficiency
        self.__is_waste = is_waste
        self.__related_rules = set()
        self.__waste_material = waste_material

        if short_name is None:
            if len(name) > 2:
                name_parts = [part for part in name.split() if part]
                if len(name_parts) > 2:
                    self.__short_name = ''.join(
                        part[0].upper() for part in name_parts)
                elif len(name_parts) == 2:
                    first_part = name_parts[0]
                    sec_part = name_parts[1]
                    if len(sec_part) > 1:
                        self.__short_name = first_part[0].upper() + \
                            sec_part[0].upper() + sec_part[1].lower()
                    else:
                        self.__short_name = first_part[0].upper() + \
                            first_part[1].lower() + first_part[0].upper()
                else:
                    self.__short_name = name[0].upper() + name[1].lower()
            else:
                self.__short_name = name
        else:
            self.__short_name = short_name

    def addRule(self, rule):
        self.__related_rules.add(rule)

    @property
    def name(self):
        return self.__name

    @property
    def short_name(self):
        return self.__short_name

    @property
    def description(self):
        return self.__desc

    @property
    def mass(self):
        return self.__mass

    @property
    def density(self):
        return self.__density

    @property
    def is_structure(self):
        return self.__struct_ef > 0

    @property
    def structure_efficiency(self):
        return self.__struct_ef

    @property
    def is_energy_source(self):
        return self.__en_ef > 0

    @property
    def energy_efficiency(self):
        return self.__en_ef

    @property
    def waste_material(self):
        return self.__waste_material

    @property
    def is_waste(self):
        return self.__is_waste

    def __str__(self):
        return self.__name

    def __repr__(self):
        return f'CreatureMaterial({self.__name})'

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
            if max_reactions is None or qtd < max_reactions:
                max_reactions = qtd

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

def __loadMaterial(name, material, loaded_materials, all_materials):

    if name in loaded_materials:
        return

    waste_material_name = material.get('waste_material')
    if waste_material_name is None:
        waste_material = None
    else:
        waste_material = loaded_materials.get(waste_material_name)
        if waste_material is None:
            waste_material = all_materials.get(waste_material_name)
            if waste_material is not None:
                waste_material = __loadMaterial(
                    waste_material_name,
                    waste_material,
                    loaded_materials,
                    all_materials
                )

    loaded_materials[name] = material = CreatureMaterial(
        name,
        density=material.get('density', 1),
        energy_efficiency=material.get('energy_efficiency', 0),
        structure_efficiency=material.get('structure_efficiency', 0),
        is_waste=material.get('is_waste', False),
        waste_material=waste_material
    )

    return material

def __loadConvertionRuleMaterialInfo(material_info_list):
    return [
        CreatureMaterialConvertionRule.MaterialInfo(
            CREATURE_MATERIALS[input_info['material']],
            input_info.get('quantity', 1)
        ) for input_info in material_info_list
    ]

def __loadConvertionRule(name, rule):

    input_materials = __loadConvertionRuleMaterialInfo(rule['input'])
    output_materials = __loadConvertionRuleMaterialInfo(rule['output'])

    return CreatureMaterialConvertionRule(
        name,
        input_materials,
        output_materials,
        speed=rule.get('speed', 1)
    )

PLANT_MATERIAL = CreatureMaterial('plant material', density=1.2)

CREATURE_MATERIALS = {}

with open('data/materials.json') as file:
    all_materials = json.load(file)
    CREATURE_MATERIALS = {}

    for material_name, material in all_materials.items():
        __loadMaterial(material_name, material, CREATURE_MATERIALS,
                       all_materials)

    del all_materials

CREATURE_MATERIALS[PLANT_MATERIAL.name] = PLANT_MATERIAL

with open('data/material_convertion_rules.json') as file:
    CREATURE_MATERIAL_RULES = tuple(
        __loadConvertionRule(rule_name, rule)
        for rule_name, rule in json.load(file).items()
    )

ENERGY_MATERIALS = tuple(material for material in
                         CREATURE_MATERIALS.values()
                         if material.is_energy_source)
STRUCTURE_MATERIALS = tuple(material for material in
                            CREATURE_MATERIALS.values()
                            if material.is_structure)
WASTE_MATERIALS = tuple(material for material in
                        CREATURE_MATERIALS.values()
                        if material.is_waste)
