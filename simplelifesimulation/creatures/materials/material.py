
from math import sqrt
from collections.abc import MutableMapping
from collections import namedtuple
import json

class CreatureMaterial:

    def __init__(self, name, description=None, mass=1, density=1,
                 structure_efficiency=0, energy_efficiency=0,
                 is_plant_material=False, waste_material=None, is_waste=False,
                 short_name=None, decomposition_rate=1e-5,
                 undigested_material=None, ignore_for_child=False):

        self.__name = name
        self.__desc = description
        self.__mass = mass
        self.__density = density
        self.__struct_ef = structure_efficiency
        self.__en_ef = energy_efficiency
        self.__is_waste = is_waste
        self.__related_rules = set()
        self.__waste_material = waste_material
        self.__is_plant_material = is_plant_material
        self.__decompose = decomposition_rate
        self.__undigested = undigested_material
        self.__ignore_for_child = ignore_for_child

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
    def is_plant_material(self):
        return self.__is_plant_material

    @property
    def waste_material(self):
        return self.__waste_material

    @property
    def is_waste(self):
        return self.__is_waste

    @property
    def decomposition_rate(self):
        return self.__decompose

    @property
    def undigested_material(self):
        return self.__undigested

    @property
    def ignore_for_child(self):
        return self.__ignore_for_child

    def __str__(self):
        return self.__name

    def __repr__(self):
        return f'CreatureMaterial({self.__name})'

def __loadMaterial(name, material, loaded_materials, all_materials):

    if name in loaded_materials:
        return

    required_materials = [
        material.get('waste_material'),
        material.get('undigested_material')
    ]

    for i, required_material_name in enumerate(required_materials):

        if required_material_name is not None:
            required_material = loaded_materials.get(required_material_name)
            if required_material is None:
                required_material = all_materials.get(required_material_name)
                if required_material is not None:
                    required_materials[i] = __loadMaterial(
                        required_material_name,
                        required_material,
                        loaded_materials,
                        all_materials
                    )
                    continue

            required_materials[i] = None

    loaded_materials[name] = material = CreatureMaterial(
        name,
        density=material.get('density', 1),
        energy_efficiency=material.get('energy_efficiency', 0),
        structure_efficiency=material.get('structure_efficiency', 0),
        is_waste=material.get('is_waste', False),
        is_plant_material=material.get('is_plant_material', False),
        waste_material=required_materials[0],
        undigested_material=required_materials[1],
        decomposition_rate=material.get('decomposition_rate', 1e-5),
        ignore_for_child=material.get('ignore_for_child', False)
    )

    return material

class MaterialsGroup(MutableMapping):

    MASS_MULTIPLIER = 1/10000

    def __init__(self, materials, config=None):
        self.__materials = dict(materials)
        self.__config = config
        self.__mass = None
        self.__radius = None
        self.__mass_radius_ready = False

    def merge(self, other, multiplier=1):

        for material, qtd in other.__materials.items():
            self.__materials[material] = \
                self.__materials.get(material, 0) + multiplier*qtd

        self.__mass_radius_ready = False

    def __add__(self, other):
        if not isinstance(other, MaterialsGroup):
            return NotImplemented

        output = MaterialsGroup(self.__materials, self.__config)

        output.merge(other)

        return output

    def __sub__(self, other):
        if not isinstance(other, MaterialsGroup):
            return NotImplemented

        output = MaterialsGroup(self.__materials, self.__config, multiplier=-1)

        output.merge(other)

        return output

    def __getitem__(self, key):
        return self.__materials[key]

    def __setitem__(self, key, value):
        self.__materials[key] = value
        self.__mass_radius_ready = False

    def __delitem__(self, key):
        del self.__materials[key]
        self.__mass_radius_ready = False

    def __iter__(self):
        return iter(self.__materials)

    def __len__(self):
        return len(self.__materials)

    def items(self):
        return self.__materials.items()

    def values(self):
        return self.__materials.values()

    def keys(self):
        return self.__materials.keys()

    def get(self, key, *args):
        return self.__materials.get(key, *args)

    def __calcMassAndRadius(self):
        total_mass = 0
        total_volume = 0
        for material, qtd in self.__materials.items():
            total_mass += material.mass*qtd
            total_volume += material.mass*qtd/material.density

        final_mass = total_mass*MaterialsGroup.MASS_MULTIPLIER
        final_radius = sqrt(total_volume*MaterialsGroup.MASS_MULTIPLIER)

        self.__mass_radius_ready = True
        self.__mass = final_mass
        self.__radius = final_radius

        return final_mass, final_radius

    @property
    def mass(self):
        if self.__mass_radius_ready:
            return self.__mass
        return self.__calcMassAndRadius()[0]

    @property
    def radius(self):
        if self.__mass_radius_ready:
            return self.__radius
        return self.__calcMassAndRadius()[1]

    @property
    def structure(self):

        if self.__config is None:
            return float('NaN')

        structure = 0
        for material in self.__config.structure_materials:
            structure += \
                material.structure_efficiency*self.__materials[material]

        return structure

    @property
    def energy(self):

        if self.__config is None:
            return float('NaN')

        energy = 0
        for material in self.__config.energy_materials:
            energy += material.energy_efficiency*self.__materials[material]
        return energy

    @property
    def getSerializable(self):
        return {
            material.name: quantity for material, quantity in
            self.__materials.items()
        }

MaterialList = namedtuple('MaterialList', (
    'materials', 'energy_materials', 'structure_materials', 'waste_materials',
    'plant_material'
))

def loadMaterials(filename):

    with open(filename) as file:
        all_materials = json.load(file)
        materials = {}

        for material_name, material in all_materials.items():
            __loadMaterial(material_name, material, materials, all_materials)

    plant_materials = tuple(material for material in materials.values()
                            if material.is_plant_material)

    if len(plant_materials) != 1:
        raise Exception('Must have exactly one plant material')

    return MaterialList(
        materials,
        tuple(material for material in materials.values()
              if material.is_energy_source),
        tuple(material for material in materials.values()
              if material.is_structure),
        tuple(material for material in materials.values()
              if material.is_waste),
        plant_materials[0]
    )
