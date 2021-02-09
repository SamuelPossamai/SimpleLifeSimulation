
class CreatureMaterial:

    def __init__(self, name, description=None, mass=1, density=1,
                 structure_efficiency=0, energy_efficiency=0,
                 waste_material=None, is_waste=False):

        self.__name = name
        self.__desc = description
        self.__mass = mass
        self.__density = density
        self.__struct_ef = structure_efficiency
        self.__en_ef = energy_efficiency
        self.__is_waste = is_waste
        self.__related_rules = set()
        self.__waste_material = waste_material

    def addRule(self, rule):
        self.__related_rules.add(rule)

    @property
    def name(self):
        return self.__name

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
                 structure_multiplier=1, ingredient_multiplier=1, speed=1e-4,
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

        reactions = rate*self.__speed*self.__join_func(
            factor for factor in factors if factor is not None)

        if reactions <= 0:
            return

        if reactions > max_reactions:
            reactions = max_reactions

        for qtd, material_info in zip(current_qtd_for_input, self.__input_list):
            materials[material_info.material] = \
                qtd - reactions*material_info.quantity

        for material_info in self.__output_list:
            materials[material_info.material] -= \
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

PLANT_MATERIAL = CreatureMaterial('plant_matter')
WASTE = CreatureMaterial('waste', is_waste=True)

CREATURE_MATERIALS = {
    material.name: material for material in (
        CreatureMaterial('energy', energy_efficiency=1, waste_material=WASTE),
        CreatureMaterial('structure', structure_efficiency=1),
        CreatureMaterial('storage'),
        WASTE,
        PLANT_MATERIAL
    )
}

energy = CREATURE_MATERIALS['energy']
structure = CREATURE_MATERIALS['structure']
storage = CREATURE_MATERIALS['storage']

CREATURE_MATERIAL_RULES = (
    CreatureMaterialConvertionRule(
        'digest',
        [
            CreatureMaterialConvertionRule.MaterialInfo(PLANT_MATERIAL, 1)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(energy, 1)
        ]
    ),
    CreatureMaterialConvertionRule(
        'create_structure',
        [
            CreatureMaterialConvertionRule.MaterialInfo(energy, 3)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(structure, 2),
            CreatureMaterialConvertionRule.MaterialInfo(WASTE, 1)
        ]
    ),
    CreatureMaterialConvertionRule(
        'create_storage',
        [
            CreatureMaterialConvertionRule.MaterialInfo(structure, 4)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(storage, 3),
            CreatureMaterialConvertionRule.MaterialInfo(WASTE, 1)
        ]
    ),
    CreatureMaterialConvertionRule(
        'revert_to_energy',
        [
            CreatureMaterialConvertionRule.MaterialInfo(storage, 2),
            CreatureMaterialConvertionRule.MaterialInfo(WASTE, 1)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(energy, 3)
        ]
    )
)

del energy
del structure
del storage

ENERGY_MATERIALS = tuple(material for material in
                         CREATURE_MATERIALS.values()
                         if material.is_energy_source)
STRUCTURE_MATERIALS = tuple(material for material in
                            CREATURE_MATERIALS.values()
                            if material.is_structure)
WASTE_MATERIALS = tuple(material for material in
                        CREATURE_MATERIALS.values()
                        if material.is_waste)
