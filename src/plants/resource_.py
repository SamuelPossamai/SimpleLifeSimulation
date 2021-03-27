
from math import sqrt

import pymunk

from ..simulation.simulationobject import CircleSimulationObject
from ..simulation.collisiontypes import RESOURCE_COLLISION_TYPE

class Resource(CircleSimulationObject):

    def __init__(self, space, *args, **kwargs):

        if len(args) == 1 and not kwargs:

            info = args[0]

            resource_info = info.get('resource', {})

            self._ext_rsc = resource_info.get('internal', 0)
            self._int_rsc = resource_info.get('external', 0)
            self.__convert_interval = resource_info.get('convert-interval', 0)
            self.__steps_to_convert = resource_info.get(
                'ticks-to-convert', 2000)

            super().__init__(space, info)
        else:
            self.__construct(space, *args, **kwargs)

    def merge(self, other):

        if other._ext_rsc > self._ext_rsc:
            return other.merge(self)

        self._ext_rsc += other._ext_rsc
        self._int_rsc += other._int_rsc

        other._ext_rsc = other._int_rsc = 0

        self.__steps_to_convert = min(self.__steps_to_convert,
                                      other.__steps_to_convert)

        self.shape.unsafe_set_radius(self.__getRadius())

        return self

    def __construct(self, space, x, y, external_rsc, internal_rsc,
                    rsc_density=10, convert_interval=2000):

        self._ext_rsc = external_rsc
        self._int_rsc = internal_rsc

        super().__init__(space, 1e8, self.__getRadius(), x, y)

        self.shape.collision_type = RESOURCE_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (RESOURCE_COLLISION_TYPE - 1)))

        self.__convert_interval = convert_interval
        self.__steps_to_convert = self.__convert_interval
        self.__convert_rsc_qtd = 0.1

    def step(self, simulation):

        if self.__steps_to_convert > 0:
            self.__steps_to_convert -= 1
        else:
            if self._int_rsc > 0:
                convert_quantity = self.__convert_rsc_qtd*self._ext_rsc
                if self._int_rsc < convert_quantity:
                    self._ext_rsc += self._int_rsc
                    self._int_rsc = 0
                else:
                    self._int_rsc -= convert_quantity
                    self._ext_rsc += convert_quantity
                self.shape.unsafe_set_radius(self.__getRadius())

            self.__steps_to_convert = self.__convert_interval

        if self._int_rsc <= 0 and self._ext_rsc <= 0:
            simulation.delResource(self)

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
        return sqrt(self._ext_rsc/20000)

    def draw(self, painter, color=(0, 255, 0)):
        if self.shape.radius > 0:
            super().draw(painter, color)

    def toDict(self):

        base_dict = super().toDict()

        base_dict['resource'] = {
            'internal': self._ext_rsc,
            'external': self._int_rsc,
            'ticks-to-convert': self.__steps_to_convert,
            'convert-interval': self.__convert_interval
        }

        return base_dict

Resource.initclass()
