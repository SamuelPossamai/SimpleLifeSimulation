
import json

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

ENERGY_MATERIALS = tuple(material for material in
                         CREATURE_MATERIALS.values()
                         if material.is_energy_source)
STRUCTURE_MATERIALS = tuple(material for material in
                            CREATURE_MATERIALS.values()
                            if material.is_structure)
WASTE_MATERIALS = tuple(material for material in
                        CREATURE_MATERIALS.values()
                        if material.is_waste)
