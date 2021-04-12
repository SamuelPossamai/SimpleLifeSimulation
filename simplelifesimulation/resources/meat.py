
from math import sqrt

import pymunk

from ..simulation.simulationobject import CircleSimulationObject
from ..simulation.collisiontypes import MEAT_COLLISION_TYPE

class Meat(CircleSimulationObject):

    def __init__(self, space, *args, **kwargs):

        if len(args) == 1 and not kwargs:

            info = args[0]

            resource_info = info.get('meat', {})

            self.__materials = resource_info.get('materials')

            super().__init__(space, info)
        else:
            self.__construct(space, *args, **kwargs)

    def __construct(self, space, x, y, materials):

        self.__materials = self.__materials.copy()

        super().__init__(space, 1, self.__getRadius(), x, y)

        self.shape.collision_type = MEAT_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (MEAT_COLLISION_TYPE - 1)))

    def step(self, simulation):
        pass

    def consume(self, _simulation, quantity):
        pass

    def __getRadius(self):
        pass

    def draw(self, painter, color=(255, 255, 50)):
        if self.shape.radius > 0:
            super().draw(painter, color)

    def toDict(self):

        base_dict = super().toDict()

        base_dict['meat'] = {
            'materials': self.__materials
        }

        return base_dict

Meat.initclass()
