
from math import sqrt

import pymunk

from .simulationobject import CircleSimulationObject

from .collisiontypes import RESOURCE_COLLISION_TYPE

class Resource(CircleSimulationObject):

    def __init__(self, space, x, y, external_rsc, internal_rsc):

        self._ext_rsc = external_rsc
        self._int_rsc = internal_rsc

        super().__init__(space, 1, self.__getRadius(), x, y)

        self.shape.collision_type = RESOURCE_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (RESOURCE_COLLISION_TYPE - 1)))

        self.__convert_interval = 1000
        self.__steps_to_convert = self.__convert_interval
        self.__convert_rsc_qtd = 10

    def step(self):

        if self.__steps_to_convert > 0:
            self.__steps_to_convert -= 1
        else:
            if self._int_rsc > 0:
                if self._int_rsc < self.__convert_rsc_qtd:
                    cvt_qtd = self._int_rsc
                else:
                    cvt_qtd = self.__convert_rsc_qtd
                self._int_rsc -= cvt_qtd
                self._ext_rsc += cvt_qtd
                self.shape.unsafe_set_radius(self.__getRadius())

            self.__steps_to_convert = self.__convert_interval

    def consume(self, _simulation, quantity):

        quantity = int(quantity)

        if quantity >= self._ext_rsc:
            consumed = self._ext_rsc
            self._ext_rsc = 0

            new_radius = self.__getRadius()
            if new_radius != self.shape.radius:
                self.shape.unsafe_set_radius(new_radius)
            return consumed

        self._ext_rsc -= quantity
        new_radius = self.__getRadius()
        if new_radius != self.shape.radius:
            self.shape.unsafe_set_radius(new_radius)
        return quantity

    def __getRadius(self):
        return sqrt((self._ext_rsc + self._int_rsc)/10000)

    def draw(self, painter, color=(0, 255, 0)):
        super().draw(painter, color)
