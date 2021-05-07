
import itertools
import os
import random
from random import randint
import json
import importlib

import pymunk

from .simulationobject import SimulationObject
from .collisiontypes import (
    CREATURE_COLLISION_TYPE, SOUND_SENSOR_COLLISION_TYPE,
    VISION_SENSOR_COLLISION_TYPE, RESOURCE_COLLISION_TYPE, WALL_COLLISION_TYPE
)

from ..resources.plant import Plant
from ..resources.meat import Meat

from ..creatures.creature import Creature, Species

class Simulation:

    def __init__(self, population_size=16, starting_resources=20, size=1000,
                 out_file=None, in_file=None, screen_size=None,
                 ticks_per_second=50, use_graphic=True, quiet=False,
                 creature_config=None, creature_materials_start=None,
                 use_wall=True, resource_convert_interval=2000,
                 user_interface=None):

        self.__creature_config = creature_config
        self.__start_materials = creature_materials_start

        self.__resource_convert_interval = resource_convert_interval

        self.__use_wall = use_wall

        if in_file is not None:
            with open(in_file) as file:
                in_file_content = json.load(file)

            if screen_size is None:
                screen_size = in_file_content.get('size')
        else:
            in_file_content = None

        if screen_size is None:
            screen_size = (600, 600)

        mul = size/300

        self._size = (int(screen_size[0]*mul), int(screen_size[1]*mul))

        if isinstance(population_size, int):
            self._population_size_min = population_size
            self._population_size_max = population_size
        else:
            self._population_size_min = population_size[0]
            self._population_size_max = population_size[1]

        if isinstance(starting_resources, int):
            self._resources_min = starting_resources
            self._resources_max = starting_resources
        else:
            self._resources_min = starting_resources[0]
            self._resources_max = starting_resources[1]

        self.__ticks_to_save = 0

        self._quiet = quiet

        if out_file is not None:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

        self._out_file = out_file

        self._use_graphic = use_graphic
        if use_graphic is True:

            self.__interface_lib = importlib.import_module(*user_interface)

            self.__interface = self.__interface_lib.Window(
                self, screen_size, size, has_wall=use_wall,
                ticks_per_second=ticks_per_second)
        else:
            self.__interface = None

        self._time = 0

        self._space = pymunk.Space()
        self._space.damping = 0.25
        self._physics_steps_per_frame = 1

        self._dt = 1/15

        handler = self._space.add_collision_handler(
            CREATURE_COLLISION_TYPE, SOUND_SENSOR_COLLISION_TYPE)
        handler.begin = self.__sensorAlert

        handler = self._space.add_collision_handler(
            CREATURE_COLLISION_TYPE, VISION_SENSOR_COLLISION_TYPE)
        handler.begin = self.__visionAlert

        handler = self._space.add_collision_handler(
            RESOURCE_COLLISION_TYPE, VISION_SENSOR_COLLISION_TYPE)
        handler.begin = self.__resourceAlert

        handler = self._space.add_collision_handler(
            RESOURCE_COLLISION_TYPE, RESOURCE_COLLISION_TYPE)
        handler.begin = self.__resourceMerge

        handler = self._space.add_collision_handler(
            CREATURE_COLLISION_TYPE, RESOURCE_COLLISION_TYPE)
        handler.pre_solve = self.__resourceCreatureCollision

        handler = self._space.add_collision_handler(
            CREATURE_COLLISION_TYPE, WALL_COLLISION_TYPE)
        handler.pre_solve = self.__creatureWallCollision

        self._creatures = []
        self._resources = []
        self.__meat_rscs = []

        if in_file is None:

            for _ in range(randint(self._population_size_min,
                                self._population_size_max)):
                self.newCreature(self._size[0]*(0.1 + 0.8*random.random()),
                                 self._size[1]*(0.1 + 0.8*random.random()),
                                 self.__start_materials)

            self.__generateResources()
        else:
            for species in in_file_content.get('species', ()):
                Species.loadFromDict(species)

            self._creatures = [
                creature for creature in
                (Creature.fromDict(self._space, creature)
                for creature in in_file_content.get('creatures', ()))
                if creature is not None
            ]
            self._resources = [
                resource for resource in
                (Resource.fromDict(self._space, resource)
                for resource in in_file_content.get('resources', ()))
                if resource is not None
            ]
            self.__meat_rscs = [
                meat for meat in
                (Meat.fromDict(self._space, meat)
                for meat in in_file_content.get('meats', ()))
                if meat is not None
            ]

        if self.__use_wall is True:
            self.__addWalls()

    def __generateResources(self):

        resources_qtd = randint(self._resources_min, self._resources_max)
        for _ in range(resources_qtd):
            self.newResource(self._size[0]*(0.1 + 0.8*random.random()),
                             self._size[1]*(0.1 + 0.8*random.random()),
                             20000000, 0)

    def step(self):

        for _ in range(self._physics_steps_per_frame):

            self._space.step(self._dt)

            for creature in self._creatures:
                creature.act(self)

            for resource in self._resources:
                resource.step(self)

            self.__ticks_to_save -= 1
            if self.__ticks_to_save <= 0:
                self.__ticks_to_save = 1000
                self.save()

    def run(self):
        if self._use_graphic is True:
            self.__interface.run()
        else:
            while True:
                self.step()

    def save(self):

        if self._out_file is None:
            return

        with open(self._out_file, 'w') as file:
            json.dump({
                'size': self._size,
                'species': [species.toDict() for species in
                            Species.getAllSpecies()],
                'resources': [rsc.toDict() for rsc in self._resources],
                'creatures': [creature.toDict() for creature in self._creatures],
                'meats': [meat.toDict() for meat in self.__meat_rscs],
            }, file)

    @property
    def creatures(self):
        return self._creatures

    @property
    def resources(self):
        return itertools.chain(self._resources, self.__meat_rscs)

    @property
    def plant_resources(self):
        return self._resources

    @property
    def meat_resources(self):
        return self.__meat_rscs

    @property
    def creature_config(self):
        return self.__creature_config

    def newCreature(self, x, y, materials=None, parent=None):

        if materials is None:
            materials = self.__start_materials.copy()

        creature = Creature(self._space, x, y, parent=parent,
                            materials=materials, config=self.__creature_config)

        self._creatures.append(creature)

        return creature

    def delCreature(self, creature):

        try:
            self._creatures.remove(creature)
        except ValueError:
            return False

        creature.destroy()
        return True

    def newResource(self, x, y, ext_rsc, int_rsc):

        resource = Plant(self._space, x, y, ext_rsc, int_rsc,
                         convert_interval=self.__resource_convert_interval,
                         materials_config=self.__creature_config.materials)

        self._resources.append(resource)

        return resource

    def delResource(self, resource):

        try:
            self._resources.remove(resource)
        except ValueError:
            return False

        resource.destroy()
        return True

    def newMeatResource(self, x, y, materials):

        resource = Meat(self._space, x, y, materials=materials,
                        materials_config=self.__creature_config.materials)

        self.__meat_rscs.append(resource)

        return resource

    def delMeatResource(self, resource):

        try:
            self.__meat_rscs.remove(resource)
        except ValueError:
            return False

        resource.destroy()
        return True

    @staticmethod
    def __sensorAlert(arbiter, _space, _):

        sound_pos = arbiter.shapes[0].body.position
        arbiter.shapes[1].creature.soundAlert(sound_pos.x, sound_pos.y)

        return False

    @staticmethod
    def __visionAlert(arbiter, _space, _):

        vision_creature = arbiter.shapes[0].simulation_object
        arbiter.shapes[1].creature.visionAlert(vision_creature)

        return False

    @staticmethod
    def __resourceAlert(arbiter, _space, _):

        vision_resource = arbiter.shapes[0].simulation_object
        arbiter.shapes[1].creature.visionResourceAlert(vision_resource)

        return False

    def __resourceCreatureCollision(self, arbiter, _space, _):

        creature_shape = arbiter.shapes[0]
        creature = creature_shape.simulation_object
        resource_shape = arbiter.shapes[1]
        resource = resource_shape.simulation_object

        dis = creature.headposition.get_distance(resource.body.position)
        if dis < 1.2*resource_shape.radius:
            creature.eat(self, resource)

        if creature_shape.radius > 2*resource_shape.radius:
            return False

        return True

    @staticmethod
    def __creatureWallCollision(arbiter, _space, _):

        creature = arbiter.shapes[0].simulation_object

        creature.stopAction()

        return True

    @staticmethod
    def __resourceMerge(arbiter, _space, _):

        shapes = arbiter.shapes
        rsc1 = shapes[0].simulation_object
        rsc2 = shapes[1].simulation_object

        new_rsc = rsc1.merge(rsc2)

        return False

    def __addWalls(self):

        size = self._size

        static_body = self._space.static_body
        static_lines = [pymunk.Segment(static_body, (0, 0), (size[0], 0), 0.0),
                        pymunk.Segment(static_body, (size[0], 0),
                                       (size[0], size[1]), 0.0),
                        pymunk.Segment(static_body, (size[0], size[1]),
                                       (0, size[1]), 0.0),
                        pymunk.Segment(static_body, (0, size[1]), (0, 0), 0.0)]

        for shape in static_lines:
            shape.collision_type = WALL_COLLISION_TYPE
            shape.filter = pymunk.ShapeFilter(
                categories=(1 << (WALL_COLLISION_TYPE - 1)))

        for line in static_lines:
            line.elasticity = 0.3
            line.friction = 0.1

        self._space.add(static_lines)
