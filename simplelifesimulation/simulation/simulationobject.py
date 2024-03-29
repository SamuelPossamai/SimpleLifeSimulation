
from abc import ABC, abstractmethod

import pymunk

class SimulationObject(ABC):

    _fromDictClasses = {}

    class Painter(ABC):

        @abstractmethod
        def drawCircle(self, color, center, radius, width=0):
            pass

        @abstractmethod
        def drawLine(self, color, start, end, width=1):
            pass

        @abstractmethod
        def drawRect(self, color, start, end, width=0):
            pass

        @abstractmethod
        def drawArc(self, color, center, radius, angle, open_angle, width=None):
            pass

    @classmethod
    def initclass(cls):
        SimulationObject._fromDictClasses[cls.__name__] = cls

    def __init__(self, space, body, shape, x, y):

        shape.simulation_object = self

        body.position = x, y

        space.add(body, shape)
        self._shape = shape
        self._space = space
        self.__destroyed = False

    def destroy(self):
        if self.__destroyed is False:
            del self.shape.simulation_object
            self._space.remove(self.shape, self.body)
            self.__destroyed = True

    @staticmethod
    def newBody(mass, inertia):
        return pymunk.Body(mass, inertia)

    @staticmethod
    def newBody(mass, inertia):
        return pymunk.Body(mass, inertia)

    @staticmethod
    def newBodyFromDict(info):

        body_info = info.get('body', {})

        body = pymunk.Body(
            body_info.get('mass', 1), body_info.get('inertia', 1))

        body.position = body_info.get('position', (0, 0))
        body.angle = body_info.get('angle', 0)
        body.velocity = body_info.get('velocity', (0, 0))
        body.angular_velocity = body_info.get('angular_velocity', 0)
        body.body_type = body_info.get('body_type', pymunk.Body.DYNAMIC)

        return body

    @property
    def destroyed(self):
        return self.__destroyed

    @property
    def shape(self):
        return self._shape

    @property
    def body(self):
        return self._shape.body

    @staticmethod
    def fromDict(space, info):
        obj_cls = SimulationObject._fromDictClasses.get(info.get('type'))

        if obj_cls is None:
            return None

        return obj_cls(space, info)

    def toDict(self):

        body = self.body

        return {
            'type': self.__class__.__name__,
            'body': {
                'mass': body.mass,
                'moment': body.moment,
                'position': list(body.position),
                'angle': body.angle,
                'velocity': list(body.velocity),
                'angular_velocity': body.angular_velocity,
                'body_type': body.body_type
            }
        }

    @abstractmethod
    def draw(self, painter):
        pass

class CircleSimulationObject(SimulationObject):

    def __init__(self, space, *args, **kwargs):

        if len(args) == 1 and not kwargs:
            info = args[0]

            body = SimulationObject.newBodyFromDict(info)

            circle_info = info.get('circle-shape', {})


            shape = pymunk.Circle(body, circle_info.get('radius', 1), (0, 0))
            shape.elasticity = circle_info.get('elasticity', 0.5)
            shape.friction = circle_info.get('friction', 0.2)

            x, y = body.position

            super().__init__(space, body, shape, x, y)
        else:
            self.__construct(space, *args, **kwargs)

    def __construct(self, space, mass, radius, x, y, elasticity=0.5,
                    friction=0.2):

        inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))

        body = SimulationObject.newBody(mass, inertia)

        shape = pymunk.Circle(body, radius, (0, 0))
        shape.elasticity = elasticity
        shape.friction = friction

        super().__init__(space, body, shape, x, y)

    def draw(self, painter, color=(0, 0, 0)):

        position = self.body.position
        if position[0] == position[0] and position[1] == position[1]:
            painter.drawCircle(color, self.body.position, self.shape.radius)

    def toDict(self):

        base_dict = super().toDict()

        base_dict['circle-shape'] = {
            'radius': self.shape.radius,
            'elasticity': self.shape.elasticity,
            'friction': self.shape.friction
        }

        return base_dict
