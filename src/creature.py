
from collections import namedtuple

from math import sqrt, floor, pi, cos, sin, ceil, isclose

import pymunk

from .behaviours import BasicBehaviour
from .simulationobject import CircleSimulationObject
from .species import Species

from .collisiontypes import CREATURE_COLLISION_TYPE
from .materials import (
    CREATURE_MATERIALS, ENERGY_MATERIALS, STRUCTURE_MATERIALS,
    CREATURE_MATERIAL_RULES, PLANT_MATERIAL, WASTE_MATERIALS
)
from .creature_traits import CREATURE_TRAITS, addcreaturetraitproperties
from .creature_sensors import VisionSensor

class Creature(CircleSimulationObject):

    LAST_ID = -1

    TRAITS = CREATURE_TRAITS

    Config = namedtuple(
        'CreatureConfig', ('energy_consume_multiplier', 'eating_multiplier'))
    Config.__new__.__defaults__ = (1, 1)

    EnergyMaterialInfo = namedtuple('EnergyMaterialInfo', ('priority',))

    MASS_MULTIPLIER = 1/10000

    @addcreaturetraitproperties(TRAITS)
    class Properties:

        def __init__(self, creature):
            self.__creature = creature

        def getTrait(self, trait):
            return self.__creature.getTrait(trait)

    def __init__(self, space, *args, **kwargs):

        self.__materials = {material: 0 for material in
                            CREATURE_MATERIALS.values()}

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
            self.__config = self.Config()
            self._is_eating = False
            self._action = None
            self._properties = Creature.Properties(self)
            self.selected = False
            self.__species = Species.searchByName(creature_info.get('species'))

            saved_materials = creature_info.get('materials')
            if saved_materials:
                for material, qtd in saved_materials.items():
                    self.__materials[CREATURE_MATERIALS.get(material)] = qtd

            super().__init__(space, info)

            self._behaviours = [BasicBehaviour(
                self.getTrait('idlepriority') + 1,
                self.getTrait('walkpriority'),
                self.getTrait('runpriority'),
                self.getTrait('fastrunpriority'),
                self.getTrait('rotatepriority'))]

            self._vision_sensor = VisionSensor(
                self, 10*self.shape.radius*self.getTrait('visiondistance'),
                pi*(10 + 210*self.getTrait('visionangle'))/180)

        else:
            self.__construct(space, *args, **kwargs)

        self.__energy_materials = self.__getMaterialInfo(
            '{}_energypriority', ENERGY_MATERIALS, Creature.EnergyMaterialInfo,
            lambda material, priority: priority/material.energy_efficiency)
        self.__structure = 0
        self.__energy = 0

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

    def __construct(self, space, x, y, structure, energy, parent=None,
                     config=None):

        if config is None:
            self.__config = Creature.Config()
        else:
            self.__config = config

        self.__materials[ENERGY_MATERIALS[0]] = energy
        self.__materials[STRUCTURE_MATERIALS[0]] = structure

        if parent is None:
            self.__traits = {trait.name: trait.random()
                             for trait in Creature.TRAITS}
            self.__species = Species(self.__traits)
        else:
            self.__traits = {trait.name:
                                 trait.mutate(parent.__traits[trait.name])
                             for trait in Creature.TRAITS}
            self.__species = parent.species.getChildSpecies(self.__traits)

        mass, radius = self.__getMassAndRadius()

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
            VisionSensor(self, 10*radius*self.getTrait('visiondistance'),
                         pi*(10 + 210*self.getTrait('visionangle'))/180)

        self._properties = Creature.Properties(self)
        self.selected = False

    def reproduce(self, simulation):

        #TODO: reproduction

        return

        child_percentage = self.getTrait('childsizepercentage')
        child_structure = int(self._structure*child_percentage)
        child_energy = int(self._energy*child_percentage) + 1

        if child_structure > 1000 and child_energy > 1000:

            self._structure -= child_structure
            self._energy -= child_energy

            pos = self.body.position
            simulation.newCreature(pos.x, pos.y, child_structure, child_energy,
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
        eat_speed = 50*self.__config.eating_multiplier*eat_speed_base
        energy_gained = resource.consume(simulation, self.body.mass*eat_speed)

        if energy_gained <= 0:
            return

        self.__materials[PLANT_MATERIAL] += energy_gained

        spent_to_eat = int((eat_speed_base/2)*energy_gained)

        #TODO: Consume energy for spent

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

    def __getMassAndRadius(self):
        total_mass = 0
        total_volume = 0
        for material, qtd in self.__materials.items():
            total_mass += material.mass*qtd
            total_volume += material.mass*qtd/material.density

        final_mass = total_mass*Creature.MASS_MULTIPLIER
        final_radius = sqrt(total_volume*Creature.MASS_MULTIPLIER)

        return final_mass, final_radius

    def __updateSelf(self):

        self.body.mass, new_radius = self.__getMassAndRadius()

        if not isclose(new_radius, self.shape.radius, rel_tol=0.05):
            self.shape.unsafe_set_radius(new_radius)
            self._vision_sensor.distance = \
                10*new_radius*self.getTrait('visiondistance')

    @property
    def eating(self):
        return self._is_eating > 0

    def act(self, simulation):

        structure = 0
        for material in STRUCTURE_MATERIALS:
            structure += \
                material.structure_efficiency*self.__materials[material]

        energy = 0
        for material in ENERGY_MATERIALS:
            energy += \
                material.energy_efficiency*self.__materials[material]

        for rule in CREATURE_MATERIAL_RULES:
            rule.convert(structure, self.__materials,
                         self.getTrait(f'{rule.name}_convertionrate'))

        self.__structure = structure
        self.__energy = energy

        energy_consume_vision = (0.1 + self.getTrait('visiondistance'))*\
            (1 + self.getTrait('visionangle'))
        energy_consume_speed = self.getTrait('speed')
        energy_consume_eat_speed = 0.2*self.getTrait('eatingspeed')
        base_energy_consume = self.body.mass*(energy_consume_vision + \
            energy_consume_speed + energy_consume_eat_speed)//100

        base_energy_consume = int(
            40*base_energy_consume*self.__config.energy_consume_multiplier) + 1

        if not self.__consumeEnergy(base_energy_consume):
            simulation.delCreature(self)
            simulation.newResource(*self.body.position, total_rsc, 0)
            return

        #TODO: Condition to reproduce

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
        for material in WASTE_MATERIALS:
            rsc_qtd = self.__materials.get(material, 0)
            if rsc_qtd < 1000:
                continue

            material_info = CREATURE_MATERIALS[material.name]
            material_mass = rsc_qtd*material_info.mass

            waste_desired_qtd = self.getTrait(
                f'{material.name}_waste_qtd_to_remove')

            if material_mass > (waste_desired_qtd + 0.05)*total_mass:
                simulation.newResource(*self.body.position, 0, rsc_qtd)

                waste_qtd = (material_mass - \
                    waste_desired_qtd*total_mass)/material_info.mass

                if waste_qtd > rsc_qtd:
                    self.__materials[material] = 0
                else :
                    self.__materials[material] -= int(waste_qtd)

        self.__updateSelf()

    def __doSpeed(self, factor):

        struct_factor = Creature.MASS_MULTIPLIER*self.__structure/self.body.mass

        speed_trait = self.getTrait('speed')
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

        struct_factor = Creature.MASS_MULTIPLIER*self.__structure/self.body.mass
        speed_trait_factor = self.getTrait('speed')*struct_factor/100
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
            color = (230*self.getTrait('eatingspeed'), 0,
                     230*self.getTrait('speed'))

        pos = self.body.position
        radius = self.shape.radius
        angle = self.body.angle

        if self.selected is True:
            painter.drawCircle((255, 80, 80), pos,
                               radius + 2/painter.multiplier)
        super().draw(painter, color)

        painter.drawArc((int(254*(1 - self.getTrait('visiondistance'))),
                         255, 50),
                        pos, radius, angle, self._vision_sensor.angle,
                        width=1)

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
            'materials': {material.name: quantity for material, quantity in
                          self.__materials.items()}
        }

        return base_dict

Creature.initclass()
