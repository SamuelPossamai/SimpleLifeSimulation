
import pymunk

class SimulationObject:

    def __init__(self, space, body, shape, x, y):

        shape.simulation_object = self

        body.position = x, y

        space.add(body, shape)
        self._shape = shape
        self._space = space

    def destroy(self):
        self._space.remove(self.shape, self.body)

    @staticmethod
    def newBody(mass, inertia):
        return pymunk.Body(mass, inertia)

    @property
    def shape(self):
        return self._shape

    @property
    def body(self):
        return self._shape.body

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
