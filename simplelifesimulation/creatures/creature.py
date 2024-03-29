
from collections import namedtuple

from math import sqrt, floor, pi, cos, sin, ceil, isclose

import pymunk

from ..simulation.simulationobject import CircleSimulationObject
from ..simulation.collisiontypes import CREATURE_COLLISION_TYPE

from .behaviours import BasicBehaviour
from .species import Species
from .sensors import VisionSensor
from .materials.material import MaterialsGroup

class Creature(CircleSimulationObject):

    LAST_ID = -1

    Config = namedtuple(
        'CreatureConfig', ('energy_consume_multiplier', 'eating_multiplier',
                           'materials', 'material_rules', 'traits'))
    Config.__new__.__defaults__ = (
        1, 1, None, None, None
    )

    EnergyMaterialInfo = namedtuple('EnergyMaterialInfo', ('priority',))

    MASS_MULTIPLIER = MaterialsGroup.MASS_MULTIPLIER

    def __init__(self, space, *args, **kwargs):

        self.__config = kwargs.pop('config', None)
        self.__materials = MaterialsGroup(kwargs.pop('materials', None),
                                          self.__config.materials)

        if self.__config is None:
            self.__config = Creature.Config()

        if self.__materials is None:
            self.__materials = MaterialsGroup({
                material: 0 for material in
                self.__config.materials.materials.values()
            }, self.__config.materials)
        else:
            self.__materials = MaterialsGroup(
                self.__materials, self.__config.materials)

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
            self._is_eating = False
            self._action = None
            self.selected = False
            self.__species = Species.searchByName(creature_info.get('species'))

            saved_materials = creature_info.get('materials')
            if saved_materials:
                for material, qtd in saved_materials.items():
                    self.__materials[
                        self.__config.materials.materials.get(material)] = qtd

            super().__init__(space, info)

            self._behaviours = [BasicBehaviour(
                self.getTrait('idlepriority') + 1,
                self.getTrait('walkpriority'),
                self.getTrait('runpriority'),
                self.getTrait('fastrunpriority'),
                self.getTrait('rotatepriority'))]

            radius = self.shape.radius
            self._vision_sensor = VisionSensor(
                self, radius + 10*radius*self.getTrait('visiondistance'),
                pi*(10 + 210*self.getTrait('visionangle'))/180)

        else:
            self.__construct(space, *args, **kwargs)

        self.__energy_materials = self.__getMaterialInfo(
            '{}_energypriority', self.__config.materials.energy_materials,
            Creature.EnergyMaterialInfo,
            lambda material, priority: priority/material.energy_efficiency)
        self.__structure = 0
        self.__energy = 0

        self.__spent_energy = 0

    def __getMaterialInfo(self, priority_trait_formula, materials, info_class,
                          priority_function):
        if len(materials) == 1:
            material = next(iter(materials))
            return {
                material: info_class(priority_function(material, 1))
            }

        material_priorities = tuple(
            (material,
             self.getTrait(priority_trait_formula.format(material.name)))
            for material in materials
        )
        total_priority = sum(
            priority for _, priority in material_priorities)
        return {
            material: info_class(
                priority_function(material, priority/total_priority))
            for material, priority in material_priorities
        }

    def __construct(self, space, x, y, parent=None):

        if parent is None:
            self.__traits = {trait.name: trait.random()
                             for trait in self.__config.traits}
            self.__species = Species(self.__traits)
        else:
            self.__traits = {trait.name:
                                 trait.mutate(parent.__traits[trait.name])
                             for trait in self.__config.traits}
            self.__species = parent.species.getChildSpecies(
                self.__config.traits, self.__traits)

        mass = self.__materials.mass
        radius = self.__materials.radius

        super().__init__(space, mass, radius, x, y)

        self.shape.collision_type = CREATURE_COLLISION_TYPE
        self.shape.filter = pymunk.ShapeFilter(
            categories=(1 << (CREATURE_COLLISION_TYPE - 1)))

        self._id = self.__newId()

        self._is_eating = 0
        self._behaviours = [BasicBehaviour(
            self.getTrait('idlepriority') + 1, self.getTrait('walkpriority'),
            self.getTrait('runpriority'), self.getTrait('fastrunpriority'),
            self.getTrait('rotatepriority'))]

        self._action = None

        #self._sound_sensor = SoundSensor(self, 200)
        self._vision_sensor = \
            VisionSensor(self,
                         radius + 10*radius*self.getTrait('visiondistance'),
                         pi*(10 + 210*self.getTrait('visionangle'))/180)

        self.selected = False

    def reproduce(self, simulation):

        child_materials = {}
        for material_name, material in \
                self.__config.materials.materials.items():

            if material.ignore_for_child:
                continue

            material_qtd = self.__materials.get(material, 0)

            child_qtd = self.getTrait(f'{material_name}_childqtd')

            if material_qtd < child_qtd:
                child_qtd = material_qtd

            self.__materials[material] -= child_qtd
            child_materials[material] = child_qtd


        pos = self.body.position
        simulation.newCreature(pos.x, pos.y, materials=child_materials,
                               parent=self)

    def getMaterial(self, material):
        return self.__materials[material]

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

        eat_speed_base = (0.3 + self.getTrait('eatingspeed'))/3
        eat_speed = 40*self.__config.eating_multiplier*eat_speed_base
        materials_gained = resource.consume(
            simulation, self.body.mass*eat_speed)

        mass_gained = materials_gained.mass

        if mass_gained <= 0:
            return

        self.__materials.merge(materials_gained)

        self.__spent_energy += int((eat_speed_base/2)*mass_gained)

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

    def __updateSelf(self):

        self.body.mass = self.__materials.mass
        new_radius = self.__materials.radius

        if not isclose(new_radius, self.shape.radius, rel_tol=0.05):
            self.shape.unsafe_set_radius(new_radius)
            self._vision_sensor.distance = \
                new_radius + 10*new_radius*self.getTrait('visiondistance')

    @property
    def eating(self):
        return self._is_eating > 0

    def act(self, simulation):

        for rule in self.__config.material_rules:
            rule.convert(self.__structure, self.__materials,
                         self.getTrait(f'{rule.name}_convertionrate'))

        self.__structure = self.__materials.structure
        self.__energy = self.__materials.energy

        energy_consume_vision = (0.1 + self.getTrait('visiondistance'))*\
            (1 + self.getTrait('visionangle'))
        energy_consume_speed = self.getTrait('speed')
        energy_consume_eat_speed = 0.2*self.getTrait('eatingspeed')
        base_energy_consume = self.body.mass*(energy_consume_vision + \
            energy_consume_speed + energy_consume_eat_speed)//100

        base_energy_consume = int(
            40*base_energy_consume*self.__config.energy_consume_multiplier) + 1

        base_energy_consume += self.__spent_energy
        self.__spent_energy = 0

        if base_energy_consume > self.__energy:
            self.kill(simulation)
            return

        self.__consumeEnergy(base_energy_consume)

        for material_name, material in \
                self.__config.materials.materials.items():

            if material.ignore_for_child:
                continue

            material_qtd = self.__materials.get(material, 0)

            child_qtd = self.getTrait(f'{material_name}_childqtd')
            overflow_min = self.getTrait(
                f'{material_name}_childqtd_min_to_reproduce')

            if material_qtd < child_qtd*overflow_min:
                break
        else:
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

        total_mass = self.body.mass/Creature.MASS_MULTIPLIER
        for material in self.__config.materials.waste_materials:

            rsc_qtd = self.__materials.get(material, 0)
            if rsc_qtd < 1000:
                continue

            material_info = self.__config.materials.materials[material.name]
            material_mass = rsc_qtd*material_info.mass

            waste_desired_qtd = self.getTrait(
                f'{material.name}_waste_qtd_to_remove')

            if material_mass > (waste_desired_qtd + 0.05)*total_mass:

                waste_qtd = int((material_mass - \
                    waste_desired_qtd*total_mass)/material_info.mass)

                if waste_qtd > rsc_qtd:
                    self.__materials[material] = 0
                    waste_qtd = rsc_qtd
                else:
                    self.__materials[material] -= waste_qtd

                simulation.newResource(*self.body.position, waste_qtd, 0)

        self.__updateSelf()

    def kill(self, simulation):
        simulation.delCreature(self)
        simulation.newMeatResource(*self.body.position, self.__materials)

    def __doSpeed(self, factor):

        struct_factor = Creature.MASS_MULTIPLIER*self.__structure/self.body.mass

        speed_trait = self.getTrait('speed')
        speed = 50*(factor**2)*(speed_trait*struct_factor + 0.01)
        if factor < 0:
            speed = -speed

        energy_consume = int(abs(speed*self.body.mass*factor* \
            (1 + 2*abs(factor - 0.5))*sqrt(speed_trait + 0.01))//100)

        self.__spent_energy += energy_consume

        angle = self.body.angle

        if factor < 0:
            speed /= 4

        self.body.velocity += (speed*cos(angle), speed*sin(angle))

    def __doAngleSpeed(self, factor):

        struct_factor = Creature.MASS_MULTIPLIER*self.__structure/self.body.mass
        speed_trait_factor = max(self.getTrait('speed')*struct_factor/100, 0)
        velocity = self.body.velocity
        current_speed = sqrt(velocity.x**2 + velocity.y**2)

        angular_speed = (-1 if factor < 0 else 1)*(factor**2)* \
            (current_speed + 40*sqrt(speed_trait_factor) + 40)/100

        energy_consume = abs(floor(angular_speed*self.body.mass*factor* \
            sqrt(speed_trait_factor + 0.2)))//50

        self.__spent_energy += energy_consume

        self.body.angular_velocity += angular_speed

    def draw(self, painter, color=None):

        if color is None:
            color = (230*self.getTrait('eatingspeed'), 0,
                     230*self.getTrait('speed'))

        pos = self.body.position
        radius = self.shape.radius
        angle = self.body.angle

        vision_angle = self.currentvisionangle

        if self.selected is True:
            painter.drawCircle((255, 80, 80), pos,
                               radius + 2/painter.multiplier)
            painter.drawArc((0, 0, 0), pos, self.currentvisiondistance,
                            angle, vision_angle, width=1)

        super().draw(painter, color)

        painter.drawArc((int(254*(1 - self.getTrait('visiondistance'))),
                         255, 50),
                        pos, radius, angle, vision_angle,
                        width=0)

    def __consumeEnergy(self, qtd, iteration=0):

        missing_to_spent = 0
        for material, material_info in self.__energy_materials.items():
            material_qtd = self.__materials[material]
            material_consume = int(material_info.priority*qtd)
            if material_consume > material_qtd:
                missing_to_spent = (material_consume - material_qtd)*\
                    material.energy_efficiency
                material_consume = material_qtd
                material_qtd = 0
            else:
                material_qtd -= material_consume

            self.__materials[material] = material_qtd
            self.__materials[material.waste_material] += material_consume

        if missing_to_spent:

            if iteration < 2:
                return self.__consumeEnergy(
                    missing_to_spent, iteration=iteration + 1)

            for material, material_info in self.__energy_materials.items():
                material_qtd = self.__materials[material]
                material_consume = \
                    missing_to_spent/material.energy_efficiency
                if material_qtd > material_consume:
                    self.__materials[material] = material_qtd - material_consume
                    self.__materials[material.waste_material] += \
                        material_consume

                    return True

                missing_to_spent -= \
                    material_qtd*material.energy_efficiency

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
        return self.__energy

    @property
    def structure(self):
        return self.__structure

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
            'materials': self.__materials.getSerializable()
        }

        return base_dict

Creature.initclass()
