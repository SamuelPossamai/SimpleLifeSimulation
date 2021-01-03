
import pymunk

class SimulationObject:

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

    @property
    def shape(self):
        return self._shape

    @property
    def body(self):
        return self._shape.body

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

class CircleSimulationObject(SimulationObject):

    def __init__(self, space, mass, radius, x, y, elasticity=0.5, friction=0.2):

        inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))

        body = SimulationObject.newBody(mass, inertia)

        shape = pymunk.Circle(body, radius, (0, 0))
        shape.elasticity = elasticity
        shape.friction = friction

        super().__init__(space, body, shape, x, y)

    def draw(self, painter, color=(0, 0, 0)):

        painter.drawCircle(color, self.body.position, self.shape.radius)

    def toJSON(self):

        base_dict = super().toDict()

        base_dict['circle'] = {
            'radius': self.shape.radius,
            'elasticity': self.shape.elasticity,
            'friction': self.shape.friction
        }

        return base_dict
