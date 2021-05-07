
from math import sqrt, ceil

import pymunk

from ..simulation.simulationobject import CircleSimulationObject
from ..simulation.collisiontypes import RESOURCE_COLLISION_TYPE

from ..creatures.materials.material import MaterialsGroup

class Meat(CircleSimulationObject):

    def __init__(self, space, *args, **kwargs):

        self.__config = kwargs.pop('materials_config', None)
        self.__materials = MaterialsGroup(
            kwargs.pop('materials', None), self.__config)
        self.__decomposed = 0

        if len(args) == 1 and not kwargs:

            info = args[0]

            resource_info = info.get('meat', {})

            self.__materials = resource_info.get('materials')

            super().__init__(space, info)
        else:
            self.__construct(space, *args, **kwargs)

    def __construct(self, space, x, y):

        super().__init__(space, 1e8, self.__materials.radius, x, y)

        self.shape.collision_type = RESOURCE_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (RESOURCE_COLLISION_TYPE - 1)))

    @property
    def materials_mass(self):
        return self.__materials.mass

    def merge(self, other):
        return MaterialsGroup({})

    def step(self, simulation):
        for material, qtd in self.__materials.items():

            diff_qtd = Math.ceil(material.decomposition_rate*qtd)

            self.__materials[material] -= diff_qtd
            self.__decomposed += diff_qtd*material.mass

    def consume(self, _simulation, quantity):

        base_mass = self.__materials.base_mass

        if base_mass == 0:
            return

        mult = quantity/base_mass

        consumed_materials = {}

        for material, qtd in self.__materials.items():
            removed_qtd = ceil(qtd*mult/material.mass)

            if removed_qtd > qtd:
                removed_qtd = qtd

            self.__materials[material] = qtd - removed_qtd

            undigested_material = material.undigested_material
            if undigested_material is None:
                undigested_material = material

            consumed_materials[undigested_material] = removed_qtd

        self.shape.unsafe_set_radius(self.__materials.radius)

        return MaterialsGroup(consumed_materials)

    def draw(self, painter, color=(255, 100, 100)):
        if self.shape.radius > 0:
            super().draw(painter, color)

    def toDict(self):

        base_dict = super().toDict()

        base_dict['meat'] = {
            'materials': self.__materials.getSerializable()
        }

        return base_dict

Meat.initclass()
