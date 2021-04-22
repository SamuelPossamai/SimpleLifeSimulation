
from math import sqrt

import pymunk

from ..simulation.simulationobject import CircleSimulationObject
from ..simulation.collisiontypes import MEAT_COLLISION_TYPE

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

        super().__init__(space, 1, self.__getRadius(), x, y)

        self.shape.collision_type = MEAT_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (MEAT_COLLISION_TYPE - 1)))

    def step(self, simulation):
        for material, qtd in self.__materials.items():

            diff_qtd = Math.ceil(material.decomposition_rate*qtd)

            self.__materials[material] -= diff_qtd
            self.__decomposed += diff_qtd*material.mass

    def consume(self, _simulation, quantity):
        pass

    def __getRadius(self):
        return self.__materials.radius

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
