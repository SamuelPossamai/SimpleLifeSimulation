
import random

from math import sqrt, floor, pi, cos, sin, ceil

import numpy
import pymunk

from .behaviours import BasicBehaviour

from .simulationobject import CircleSimulationObject

from .collisiontypes import (
    SOUND_SENSOR_COLLISION_TYPE, VISION_SENSOR_COLLISION_TYPE,
    CREATURE_COLLISION_TYPE
)

class SoundSensor:

    def __init__(self, creature, sensor_range):

        self._shape = pymunk.Circle(creature.body, sensor_range, (0, 0))

        self._shape.collision_type = SOUND_SENSOR_COLLISION_TYPE
        self._shape.filter = pymunk.ShapeFilter(
            categories=(1 << (SOUND_SENSOR_COLLISION_TYPE - 1)))
        self._shape.sensor = True

        self._shape.creature = creature

        creature.body.space.add(self._shape)

class VisionSensor:

    def __init__(self, creature, sensor_range, sensor_angle,
                 offset_angle=0):

        if sensor_angle > pi:
            shapes = (self.__createShape(creature, sensor_range,
                                         sensor_angle/2,
                                         offset_angle + sensor_angle/4),
                      self.__createShape(creature, sensor_range,
                                         sensor_angle/2,
                                         offset_angle - sensor_angle/4))
        else:
            shapes = (self.__createShape(creature, sensor_range,
                                         sensor_angle, offset_angle),)

        self._shapes = shapes
        self._angle = sensor_angle

    @staticmethod
    def __createShape(creature, sensor_range, sensor_angle, offset_angle):

        points = VisionSensor.__getArcPoints(
            sensor_range, sensor_angle, offset_angle)
        points.append((0, 0))

        shape = pymunk.Poly(creature.body, points)

        shape.collision_type = VISION_SENSOR_COLLISION_TYPE
        shape.filter = pymunk.ShapeFilter(
            categories=(1 << (VISION_SENSOR_COLLISION_TYPE - 1)))
        shape.sensor = True

        shape.creature = creature

        creature.body.space.add(shape)

        return shape

    @staticmethod
    def __getArcPoints(sensor_range, sensor_angle, angle_offset):

        points = []

        n = int(10*sensor_angle) + 2

        cur_angle = sensor_angle/2 + angle_offset
        angle_diff = sensor_angle/(n-1)
        for _ in range(n):

            x = sensor_range*cos(cur_angle)
            y = sensor_range*sin(cur_angle)
            points.append((x, y))
            cur_angle -= angle_diff

        return points

    @property
    def distance(self):
        for vertice in self._shapes[0].get_vertices():
            if vertice.x != 0 or vertice.y != 0:
                return vertice.length

        return 0

    @distance.setter
    def distance(self, new_value):

        for shape in self._shapes:

            vision_vertices = shape.get_vertices()

            for i, vertice in enumerate(vision_vertices):
                if vertice.x != 0 or vertice.y != 0:
                    vision_vertices[i].length = new_value

            shape.unsafe_set_vertices(vision_vertices)

    @property
    def shapes(self):
        return self._shapes

    @property
    def angle(self):
        return self._angle

class CreatureTrait:

    def __init__(self, name, min_val, max_val, integer_only=False,
                 mutation_rate=0.1, proportional_mutation=False,
                 exponential_random=False):

        self.__name = name
        self.__min = min_val
        self.__max = max_val
        self.__int_only = integer_only
        self.__mut = mutation_rate
        self.__prop_mut = proportional_mutation
        self.__exp_rnd = exponential_random

    @property
    def name(self):
        return self.__name

    def random(self):

        diff = self.__max - self.__min

        if self.__exp_rnd:

            value = self.__min + min(numpy.random.exponential(diff)/1000,
                                     diff)

            if self.__int_only:
                return int(value)

            return value

        if self.__int_only:
            return random.randint(self.__min, self.__max)

        return random.random()*(diff) + self.__min

    def mutate(self, val):

        if self.__prop_mut:
            mut_base = val
        else:
            mut_base = self.__max - self.__min

        rand_n = 2*(0.5 - random.random())*mut_base
        val += rand_n*self.__mut

        if self.__int_only:
            val = round(val)

        if val < self.__min:
            val = self.__min

        if val > self.__max:
            val = self.__max

        return val

def addcreaturetraitproperties(traits, property_name_modifier=None):

    def decorator(baseclass):
        for trait in traits:
            if property_name_modifier is None:
                property_name = trait.name
            else:
                property_name = property_name_modifier(trait.name)
            setattr(baseclass, property_name,
                    property(lambda self, name=trait.name: self.getTrait(name)))
        return baseclass

    return decorator

CREATURE_TRAITS = [

    CreatureTrait('speed', 0, 1),
    CreatureTrait('eatingspeed', 0, 1),
    CreatureTrait('visiondistance', 0, 1),
    CreatureTrait('visionangle', 0, 1),
    CreatureTrait('childsize', 0, 0.5),
    CreatureTrait('structpercentage', 0.2, 0.8),
    CreatureTrait('childsizepercentage', 0.05, 0.5),
    CreatureTrait('structmax', 1000, 1.e10, integer_only=True,
                  exponential_random=True),
    CreatureTrait('walkpriority', 0, 16, integer_only=True),
    CreatureTrait('runpriority', 0, 16, integer_only=True),
    CreatureTrait('fastrunpriority', 0, 16, integer_only=True),
    CreatureTrait('idlepriority', 0, 16, integer_only=True),
    CreatureTrait('rotatepriority', 0, 16, integer_only=True)
]

@addcreaturetraitproperties(CREATURE_TRAITS, lambda prop: prop + '_trait')
class Creature(CircleSimulationObject):

    LAST_ID = -1

    TRAITS = CREATURE_TRAITS

    @addcreaturetraitproperties(TRAITS)
    class Properties:

        def __init__(self, creature):
            self.__creature = creature

        def getTrait(self, trait):
            return self.__creature.getTrait(trait)

    def __init__(self, space, x, y, structure, energy, parent=None):

        self._spent_resources = 0
        self._energy = int(energy)
        self._structure = int(structure)

        mass = self.__getMass()
        radius = self.__getRadius(mass)

        super().__init__(space, mass, radius, x, y)

        self.shape.collision_type = CREATURE_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (CREATURE_COLLISION_TYPE - 1)))

        self._species = 'nameless'
        self._id = self.__newId()

        self._is_eating = 0

        if parent is None:
            self.__traits = {trait.name: trait.random()
                             for trait in Creature.TRAITS}
        else:
            self.__traits = {trait.name:
                                 trait.mutate(parent.__traits[trait.name])
                             for trait in Creature.TRAITS}

        self._behaviours = [BasicBehaviour(
            self.idlepriority_trait + 1, self.walkpriority_trait,
            self.runpriority_trait, self.fastrunpriority_trait,
            self.rotatepriority_trait)]

        self._action = None

        #self._sound_sensor = SoundSensor(self, 200)
        self._vision_sensor = \
            VisionSensor(self, 10*radius*self.visiondistance_trait,
                         pi*(10 + 210*self.visionangle_trait)/180)

        self._properties = Creature.Properties(self)
        self.selected = False

    def reproduce(self, simulation):

        child_percentage = self.childsizepercentage_trait
        child_structure = int(self._structure*child_percentage)
        child_energy = int(self._energy*child_percentage)

        if child_structure > 0 and child_energy > 0:

            self._structure -= child_structure
            self._energy -= child_energy

            pos = self.body.position
            simulation.newCreature(pos.x, pos.y, child_structure, child_energy,
                                   parent=self)

    def getTrait(self, trait):
        return self.__traits[trait]

    @property
    def headposition(self):

        radius = self.shape.radius
        pos = self.body.position
        angle = self.body.angle

        pos.x += radius*cos(angle)
        pos.y += radius*sin(angle)

        return pos

    def eat(self, simulation, resource):

        eat_speed = (0.3 + self.eatingspeed_trait)/3
        energy_gained = resource.consume(simulation, self.body.mass*eat_speed)

        if energy_gained <= 0:
            return

        spent_to_eat = int((eat_speed/2)*energy_gained)

        self._spent_resources += spent_to_eat
        energy_gained -= spent_to_eat
        self._energy += energy_gained

        self._is_eating = 5

        self.__updateSelf()

    def pushBehaviour(self, new_behaviour):

        self._behaviours.append(new_behaviour)
        self._action = None

    def popBehaviour(self):

        self._behaviours.pop()
        self._action = None

    def swapBehaviour(self, new_behaviour):

        self._behaviours[-1] = new_behaviour
        self._action = None

    def soundAlert(self, x, y):

        new_action = self._behaviours[-1].soundAlert(self, x, y) # pylint: disable=assignment-from-none

        if new_action is not None:
            self._action = new_action

    def visionAlert(self, creature):

        # pylint: disable=assignment-from-none
        new_action = self._behaviours[-1].visionAlert(self, creature)
        # pylint: enable=assignment-from-none

        if new_action is not None:
            self._action = new_action

    def visionResourceAlert(self, resource):

        # pylint: disable=assignment-from-none
        new_action = self._behaviours[-1].visionResourceAlert(
            self, resource)
        # pylint: enable=assignment-from-none

        if new_action is not None:
            self._action = new_action

    def __getRadius(self, mass=None):

        if mass is None:
            mass = self.body.mass
        return sqrt(mass)

    def __getMass(self):
        return self.__getTotalResources()/10000

    def __getTotalResources(self):
        return self._spent_resources + self._structure + self._energy

    def __updateSelf(self):

        self.body.mass = self.__getMass()

        new_radius = self.__getRadius()
        if new_radius != self.shape.radius:
            self.shape.unsafe_set_radius(new_radius)
            self._vision_sensor.distance = \
                10*new_radius*self.visiondistance_trait

    @property
    def eating(self):
        return self._is_eating > 0

    def act(self, simulation):

        total_rsc = self.__getTotalResources()
        if self._structure < self.structmax_trait and \
            self._structure < total_rsc*self.structpercentage_trait:

            energy_tranform = int(ceil(0.0001*total_rsc))
            if self._energy > energy_tranform:
                self._energy -= energy_tranform
                self._structure += energy_tranform

        energy_consume_vision = \
            (0.1 + self.visiondistance_trait)*(1 + self.visionangle_trait)
        energy_consume_speed = self.speed_trait
        energy_consume_eat_speed = 0.2*self.eatingspeed_trait
        base_energy_consume = int(self.body.mass*(energy_consume_vision + \
            energy_consume_speed + energy_consume_eat_speed)//100) + 1

        if not self.__consumeEnergy(base_energy_consume):
            simulation.delCreature(self)
            simulation.newResource(*self.body.position, total_rsc, 0)
            return

        if self._structure >= self.structmax_trait:
            self.reproduce(simulation)

        if self._is_eating > 0:
            self._is_eating -= 1

        if self._action is None:
            self._action = self._behaviours[-1].selectAction(self)

        action_result = self._action.doAction(self)

        if action_result is None:
            self._action = None
            return

        speed_factor, angle_factor = action_result

        if speed_factor > 1:
            speed_factor = 1
        elif speed_factor < -1:
            speed_factor = -1

        if angle_factor > 1:
            angle_factor = 1
        elif angle_factor < -1:
            angle_factor = -1

        self.__doSpeed(speed_factor)
        self.__doAngleSpeed(angle_factor)

        if self._spent_resources > 0.05*(self._energy + self._structure):
            simulation.newResource(*self.body.position, 0,
                                   self._spent_resources)
            self._spent_resources = 0
            self.__updateSelf()

    def __doSpeed(self, factor):

        struct_factor = self._structure/self.__getTotalResources()

        speed_trait = self.speed_trait
        speed = 50*(factor**2)*(speed_trait*struct_factor + 0.01)
        if factor < 0:
            speed = -speed

        energy_consume = int(abs(speed*self.body.mass*factor* \
            (1 + 2*abs(factor - 0.5))*sqrt(speed_trait + 0.01))//100)

        if not self.__consumeEnergy(energy_consume):
            speed = 0

        angle = self.body.angle

        if factor < 0:
            speed /= 4

        self.body.velocity += (speed*cos(angle), speed*sin(angle))

    def __doAngleSpeed(self, factor):

        struct_factor = self._structure/self.__getTotalResources()
        speed_trait_factor = self.speed_trait/struct_factor
        velocity = self.body.velocity
        current_speed = sqrt(velocity.x**2 + velocity.y**2)

        angular_speed = (-1 if factor < 0 else 1)*(factor**2)* \
            (current_speed + 40*sqrt(speed_trait_factor) + 40)/100

        energy_consume = abs(floor(angular_speed*self.body.mass*factor* \
            sqrt(speed_trait_factor + 0.2)))//50

        if not self.__consumeEnergy(energy_consume):
            angular_speed = 0

        self.body.angular_velocity += angular_speed

    def draw(self, painter, color=None):

        if color is None:
            color = (230*self.eatingspeed_trait, 0, 230*self.speed_trait)

        pos = self.body.position
        radius = self.shape.radius
        angle = self.body.angle

        if self.selected is True:
            painter.drawCircle((255, 80, 80), pos, radius + 8)
        super().draw(painter, color)

        painter.drawArc((int(254*(1 - self.visiondistance_trait)), 255, 50),
                        pos, radius, angle, self._vision_sensor.angle,
                        width=1)

    def __consumeEnergy(self, qtd):

        if qtd < 0 or qtd > self._energy:
            return False

        self._energy -= qtd
        self._spent_resources += qtd

        return True

    def __repr__(self):
        return "Creature<{}>".format(self._id)

    def stopAction(self):
        self._action = None

    @staticmethod
    def __newId():
        Creature.LAST_ID += 1
        return Creature.LAST_ID

    @property
    def species(self):
        return self._species

    @property
    def id_(self):
        return self._id

    @property
    def energy(self):
        return self._energy

    @energy.setter
    def energy(self, new_val):
        self._energy = max(int(new_val), 0)
        self.__updateSelf()

    @property
    def structure(self):
        return self._structure

    @property
    def properties(self):
        return self._properties

    @property
    def currentspeed(self):
        return self.body.velocity.length

    @property
    def currentvisiondistance(self):
        return self._vision_sensor.distance

    @property
    def currentvisionangle(self):
        return self._vision_sensor.angle
