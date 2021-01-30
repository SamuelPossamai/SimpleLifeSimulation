
from collections import namedtuple
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

class CreatureMaterial:

    def __init__(self, name, description=None, mass=1, density=1,
                 structure_efficiency=0, energy_efficience=0,
                 is_waste=False):

        self.__name = name
        self.__desc = description
        self.__mass = mass
        self.__density = density
        self.__struct_ef = structure_efficiency
        self.__en_ef = energy_efficience
        self.__is_waste = is_waste
        self.__related_rules = set()

    def addRule(self, rule):
        self.__related_rules.add(rule)

    @property
    def name(self):
        return self.__name

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
    def energy_efficience(self):
        return self.__en_ef

    @property
    def is_waste(self):
        return self.__is_waste

    def __str__(self):
        return self.__name

    def __repr__(self):
        return f'CreatureMaterial({self.__name})'

class CreatureMaterialConvertionRule:

    class MaterialInfo:

        def __init__(self, material, quantity):
            self.__material = material
            self.__quantity = quantity

        @property
        def material(self):
            return self.__material

        @property
        def quantity(self):
            return self.__quantity

        def __str__(self):
            return f'{self.__quantity}*{self.__material}'

        def __repr__(self):
            return (f'MaterialInfo(material={repr(self.__material)}, '
                    f'quantity={self.__quantity})')

    def __init__(self, input_list, output_list):

        for material_info in input_list:
            material_info.material.addRule(self)

        for material_info in output_list:
            material_info.material.addRule(self)

        self.__input_list = tuple(input_list)
        self.__output_list = tuple(output_list)

    def __str__(self):
        eq_l = ' + '.join(str(mat_info) for mat_info in self.__input_list)
        eq_r = ' + '.join(str(mat_info) for mat_info in self.__output_list)

        return f'{eq_l} -> {eq_r}'

    def __repr__(self):
        return f'CreatureMaterialConvertionRule({str(self)})'

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

    def valuesSimilarity(self, val1, val2):

        if val1 == val2:
            return 1

        similarity = 0
        if self.__prop_mut:

            if val1 > val2:
                return val2/val1

            return val1/val2

        return 1 - abs(val1 - val2)/(self.__max - self.__min)


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

CREATURE_MATERIALS = {
    material.name: material for material in (
        CreatureMaterial('energy', energy_efficience=1),
        CreatureMaterial('structure', structure_efficiency=1),
        CreatureMaterial('storage'),
        CreatureMaterial('waste', is_waste=True)
    )
}

energy = CREATURE_MATERIALS['energy']
structure = CREATURE_MATERIALS['structure']
storage = CREATURE_MATERIALS['storage']
waste = CREATURE_MATERIALS['waste']

CREATURE_MATERIAL_RULES = (
    CreatureMaterialConvertionRule(
        [
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['energy'], 3)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['structure'], 2),
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['waste'], 1)
        ]
    ),
    CreatureMaterialConvertionRule(
        [
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['structure'], 4)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['storage'], 3),
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['waste'], 1)
        ]
    ),
    CreatureMaterialConvertionRule(
        [
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['storage'], 2),
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['waste'], 1)
        ],
        [
            CreatureMaterialConvertionRule.MaterialInfo(
                CREATURE_MATERIALS['energy'], 3)
        ]
    )
)

del energy
del structure
del storage
del waste

ENERGY_RESOURCES = tuple(material for material in
                         CREATURE_MATERIALS.values()
                         if material.is_energy_source)
STRUCTURE_RESOURCES = tuple(material for material in
                            CREATURE_MATERIALS.values()
                            if material.is_structure)
WASTE_RESOURCES = tuple(material for material in
                        CREATURE_MATERIALS.values()
                        if material.is_waste)

print(ENERGY_RESOURCES, STRUCTURE_RESOURCES, WASTE_RESOURCES, CREATURE_MATERIAL_RULES)

CREATURE_TRAITS = [

    CreatureTrait('speed', 0, 1),
    CreatureTrait('eatingspeed', 0, 1),
    CreatureTrait('visiondistance', 0, 1),
    CreatureTrait('visionangle', 0, 1),
    CreatureTrait('structpercentage', 0.2, 0.8),
    CreatureTrait('storagepercentage', 0, 0.8),
    CreatureTrait('excessenergytoreproduce', 0, 2),
    CreatureTrait('childsizepercentage', 0.05, 0.5),
    CreatureTrait('structmax', 1.e6, 1.e9, integer_only=True,
                  exponential_random=True, proportional_mutation=True),
    CreatureTrait('density', 0.3, 3),
    CreatureTrait('walkpriority', 0, 16, integer_only=True),
    CreatureTrait('runpriority', 0, 16, integer_only=True),
    CreatureTrait('fastrunpriority', 0, 16, integer_only=True),
    CreatureTrait('idlepriority', 0, 16, integer_only=True),
    CreatureTrait('rotatepriority', 0, 16, integer_only=True)
]

class Species:

    __all_species = []

    def __init__(self, traits, ancestor=None):

        self.__name = Species.__getName()
        self.__traits = traits
        self.__ancestor = ancestor

        Species.__all_species.append(self)

    @property
    def name(self):
        return self.__name

    @staticmethod
    def __getName():

        name = ''
        i = len(Species.__all_species)

        first_letter_val = ord('A')
        interval_size = ord('Z') - first_letter_val + 1
        while i >= interval_size:

            name = chr(first_letter_val + i%interval_size) + name

            i //= interval_size
            i -= 1

        return chr(first_letter_val + i) + name

    def getChildSpecies(self, traits):

        similarity = 0

        for trait in CREATURE_TRAITS:
            parent_val = self.__traits.get(trait.name)
            child_val = traits.get(trait.name)

            similarity += trait.valuesSimilarity(
                parent_val, child_val)/len(CREATURE_TRAITS)

            if similarity > 0.8:
                return self

        return Species(traits, ancestor=self)

    @staticmethod
    def searchByName(name):
        for species in Species.__all_species:
            if species.name == name:
                return species

        return None

    def loadFromDict(info):

        species = Species(info.get('traits'),
                          Species.searchByName(info.get('ancestor')))

        species.__name = info.get('name', 'UNKNOWN')

        return species

    def toDict(self):
        return {
            'name': self.__name,
            'traits': self.__traits,
            'ancestor': (None if self.__ancestor is None
                         else self.__ancestor.name)
        }

    @staticmethod
    def getAllSpecies():
        return iter(Species.__all_species)

@addcreaturetraitproperties(CREATURE_TRAITS, lambda prop: prop + '_trait')
class Creature(CircleSimulationObject):

    LAST_ID = -1

    TRAITS = CREATURE_TRAITS

    Config = namedtuple(
        'CreatureConfig', ('energy_consume_multiplier', 'eating_multiplier'))
    Config.__new__.__defaults__ = (1, 1)

    @addcreaturetraitproperties(TRAITS)
    class Properties:

        def __init__(self, creature):
            self.__creature = creature

        def getTrait(self, trait):
            return self.__creature.getTrait(trait)

    def __init__(self, space, *args, **kwargs):

        if len(args) == 1 and not kwargs:

            info = args[0]

            creature_info = info.get('creature', {})

            self._id = creature_info.get('id', -1)

            species_name = creature_info.get('species')
            for species in Species.getAllSpecies():
                if species == species_name:
                    self.__species = species
                    break
            else:
                self.__species = None

            self.__traits = creature_info.get('traits')
            self._spent_resources = creature_info.get('spent_resources', 0)
            self._storage = creature_info.get('storage', 0)
            self._energy = creature_info.get('energy', 0)
            self._structure = creature_info.get('structure')
            self.__config = self.Config()
            self._is_eating = False
            self._action = None
            self._properties = Creature.Properties(self)
            self.selected = False
            self.__species = Species.searchByName(creature_info.get('species'))
            self.__materials = {CREATURE_MATERIALS.get(material): quantity
                                for material, quantity in
                                creature_info.get('materials', {}).items()}

            super().__init__(space, info)


            self._behaviours = [BasicBehaviour(
                self.idlepriority_trait + 1, self.walkpriority_trait,
                self.runpriority_trait, self.fastrunpriority_trait,
                self.rotatepriority_trait)]

            self._vision_sensor = VisionSensor(
                self, 10*self.shape.radius*self.visiondistance_trait,
                pi*(10 + 210*self.visionangle_trait)/180)

        else:
            self.__construct(space, *args, **kwargs)

    def __construct(self, space, x, y, structure, energy, parent=None,
                     config=None):

        if config is None:
            self.__config = Creature.Config()
        else:
            self.__config = config

        self._spent_resources = 0
        self._energy = int(energy)
        self._storage = 0
        self.__materials = {material: 0 for material in CREATURE_MATERIALS}

        if parent is None:
            self.__traits = {trait.name: trait.random()
                             for trait in Creature.TRAITS}
            self.__species = Species(self.__traits)
        else:
            self.__traits = {trait.name:
                                 trait.mutate(parent.__traits[trait.name])
                             for trait in Creature.TRAITS}
            self.__species = parent.species.getChildSpecies(self.__traits)

        self._structure = int(structure)

        mass = self.__getMass()
        radius = self.__getRadius(mass)

        super().__init__(space, mass, radius, x, y)

        self.shape.collision_type = CREATURE_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (CREATURE_COLLISION_TYPE - 1)))

        self._id = self.__newId()

        self._is_eating = 0
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
        child_energy = int(self._energy*child_percentage) + 1

        if child_structure > 1000 and child_energy > 1000:

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

        eat_speed_base = (0.3 + self.eatingspeed_trait)/3
        eat_speed = 50*self.__config.eating_multiplier*eat_speed_base
        energy_gained = resource.consume(simulation, self.body.mass*eat_speed)

        if energy_gained <= 0:
            return

        spent_to_eat = int((eat_speed_base/2)*energy_gained)

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
        return sqrt(mass/self.density_trait)

    def __getMass(self):
        return self.__getTotalResources()/10000

    def __getTotalResources(self):
        return self._spent_resources + self._structure + self._energy + \
            self._storage

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
        base_energy_consume = self.body.mass*(energy_consume_vision + \
            energy_consume_speed + energy_consume_eat_speed)//100

        base_energy_consume = int(
            40*base_energy_consume*self.__config.energy_consume_multiplier) + 1

        if not self.__consumeEnergy(base_energy_consume):
            simulation.delCreature(self)
            simulation.newResource(*self.body.position, total_rsc, 0)
            return

        if self._structure >= self.structmax_trait:
            excess_energy_percentage = \
                self._energy/total_rsc - 1 + self.structpercentage_trait
            if excess_energy_percentage > self.excessenergytoreproduce_trait:
                self.reproduce(simulation)

        if self._is_eating > 0:
            self._is_eating -= 1

        while self._action is None:
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

        if self._spent_resources > 0.1*(self._energy + self._structure):
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
            painter.drawCircle((255, 80, 80), pos,
                               radius + 2/painter.multiplier)
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
        return self.__species

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

    def toDict(self):

        base_dict = super().toDict()

        base_dict['creature'] = {
            'id': self._id,
            'species': self.__species.name,
            'traits': self.__traits,
            'spent_resources': self._spent_resources,
            'energy': self._energy,
            'storage': self._storage,
            'structure': self._structure,
            'materials': {material.name: quantity for material, quantity in
                          self.__materials.items()}
        }

        return base_dict

Creature.initclass()
