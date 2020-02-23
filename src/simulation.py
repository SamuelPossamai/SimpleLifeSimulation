
import os

import random
from random import randint

from math import pi
import itertools

import pygame

# pylint: disable=no-name-in-module
from pygame.constants import (
    QUIT, KEYDOWN, K_ESCAPE, K_SPACE, K_p, MOUSEBUTTONUP, K_EQUALS, K_KP_PLUS,
    K_KP_MINUS, K_MINUS, KMOD_LCTRL, KMOD_RCTRL, K_a, K_s, K_d, K_w, K_LEFT,
    K_DOWN, K_RIGHT, K_UP, KEYUP
)
# pylint: enable=no-name-in-module

import pymunk

from .painter import Painter

from .resource_ import Resource
from .creature import Creature

from .collisiontypes import (
    CREATURE_COLLISION_TYPE, SOUND_SENSOR_COLLISION_TYPE,
    VISION_SENSOR_COLLISION_TYPE, RESOURCE_COLLISION_TYPE, WALL_COLLISION_TYPE
)

class Simulation:

    def __init__(self, population_size=16, starting_resources=20, size=1000,
                 out_file=None, in_file=None, screen_size=(600, 600),
                 use_graphic=True, quiet=False):

        self.__lat_column_size = 250
        screen_size = (screen_size[0] + self.__lat_column_size, screen_size[1])

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

        self._quiet = quiet

        self._show_creature = None
        self._paused = False

        if out_file is not None:
            try:
                os.remove(out_file)
            except FileNotFoundError:
                pass

        self._out_file = out_file

        self.__until_event = {}
        self.__events_happening = set()

        self._use_graphic = use_graphic
        if use_graphic is True:

            pygame.display.init()
            pygame.font.init()
            self._small_font = pygame.font.SysFont('Arial', 12, bold=True)
            self._medium_font = pygame.font.SysFont('Arial', 18, bold=True)
            pygame.display.set_caption("Simulation")

            self._screen = pygame.display.set_mode(screen_size)
            self._clock = pygame.time.Clock()

            self.__start_painter_mult = 300/size
            self._painter = Painter(self._screen, self.__start_painter_mult)

        self._time = 0

        self._space = pymunk.Space()
        self._space.damping = 0.25
        self._physics_steps_per_frame = 1

        self._dt = 1/15
        self._ticks = 50

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
            CREATURE_COLLISION_TYPE, RESOURCE_COLLISION_TYPE)
        handler.pre_solve = self.__resourceCreatureCollision

        handler = self._space.add_collision_handler(
            CREATURE_COLLISION_TYPE, WALL_COLLISION_TYPE)
        handler.pre_solve = self.__creatureWallCollision

        self._creatures = []
        self._resources = []

        self._running = True
        mul = size/300
        self._size = ((screen_size[0] - self.__lat_column_size)*mul,
                      screen_size[1]*mul)

        for _ in range(randint(self._population_size_min,
                               self._population_size_max)):
            self.newCreature(self._size[0]*(0.1 + 0.8*random.random()),
                             self._size[1]*(0.1 + 0.8*random.random()),
                             2000000, 8000000)

        self.__generateResources()

        self.__addWalls()

    def __generateResources(self):

        resources_qtd = randint(self._resources_min, self._resources_max)
        for _ in range(resources_qtd):
            self.newResource(self._size[0]*(0.1 + 0.8*random.random()),
                             self._size[1]*(0.1 + 0.8*random.random()),
                             5000000, 0)

    def run(self):

        while self._running:

            if self._paused is False:
                for _ in range(self._physics_steps_per_frame):
                    self._space.step(self._dt)

                for creature in self._creatures:
                    creature.act(self)

                for resource in self._resources:
                    resource.step()

            if self._use_graphic is True:

                pygame.display.set_caption('Simulation')

                self.__processEvents()
                self._screen.fill((100, 100, 100))
                self.__drawObjects()
                self.__drawSideInfo()
                pygame.display.flip()

                self._clock.tick(self._ticks)

    def __processEvents(self):

        for event in pygame.event.get():
            if event.type == QUIT:
                self._running = False
            elif event.type == KEYDOWN:
                key = event.key
                if key == K_ESCAPE:
                    self._painter.offset = (0, 0)
                    self._painter.multiplier = self.__start_painter_mult
                elif key in (K_SPACE, K_p):
                    self._paused = not self._paused
                elif key in (K_a, K_LEFT):
                    self.__until_event[self.moveLeft] = 10
                elif key in (K_s, K_DOWN):
                    self.__until_event[self.moveDown] = 10
                elif key in (K_d, K_RIGHT):
                    self.__until_event[self.moveRight] = 10
                elif key in (K_w, K_UP):
                    self.__until_event[self.moveUp] = 10
                elif (key in (K_EQUALS, K_KP_PLUS)) and \
                    (pygame.key.get_mods() in (KMOD_LCTRL, KMOD_RCTRL)):

                    self.__until_event[self.zoomIn] = 10
                elif (key in (K_MINUS, K_KP_MINUS)) and \
                    (pygame.key.get_mods() in (KMOD_LCTRL, KMOD_RCTRL)):

                    self.__until_event[self.zoomOut] = 10
            elif event.type == MOUSEBUTTONUP:
                pos = self._painter.mapPointFromScreen(pygame.mouse.get_pos())
                mask = (1 << (CREATURE_COLLISION_TYPE - 1))
                clicked = next(iter(self._space.point_query(
                    pos, 0, pymunk.ShapeFilter(mask=mask))), None)

                if self._show_creature is not None:
                    self._show_creature.selected = False

                if clicked is None:
                    self._show_creature = None
                else:
                    self._show_creature = clicked.shape.simulation_object
                    self._show_creature.selected = True
            elif event.type == KEYUP:
                key = event.key
                if key in (K_EQUALS, K_KP_PLUS):
                    self.__removeEvent(self.zoomIn, apply_at_least_once=True)
                elif key in (K_MINUS, K_KP_MINUS):
                    self.__removeEvent(self.zoomOut, apply_at_least_once=True)
                elif key in (K_a, K_LEFT):
                    self.__removeEvent(self.moveLeft, apply_at_least_once=True)
                elif key in (K_s, K_DOWN):
                    self.__removeEvent(self.moveDown, apply_at_least_once=True)
                elif key in (K_d, K_RIGHT):
                    self.__removeEvent(self.moveRight, apply_at_least_once=True)
                elif key in (K_w, K_UP):
                    self.__removeEvent(self.moveUp, apply_at_least_once=True)

        events_to_remove = []
        for event, turns_until_event in self.__until_event.items():
            if turns_until_event <= 0:
                self.__events_happening.add(event)
                events_to_remove.append(event)
            else:
                self.__until_event[event] = turns_until_event - 1

        for event in events_to_remove:
            del self.__until_event[event]

        for event in self.__events_happening:
            event()

    def __removeEvent(self, event, apply_at_least_once=False):

        try:
            self.__events_happening.remove(event)
        except KeyError:
            self.__until_event.pop(event, None)
            if apply_at_least_once:
                event()

    def newCreature(self, x, y, structure, energy, parent=None):

        creature = Creature(self._space, x, y, structure, energy, parent=parent)

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

        resource = Resource(self._space, x, y, ext_rsc, int_rsc)

        self._resources.append(resource)

        return resource

    def __drawSideInfo(self):

        screen_size = pygame.display.get_surface().get_size()
        start_point = screen_size[0] - self.__lat_column_size, 0
        creature = self._show_creature

        pygame.draw.rect(self._screen, (200, 200, 200),
                         (start_point[0], start_point[1],
                          self.__lat_column_size, screen_size[1]))

        if self._show_creature is None:
            creature_number_text = '-'
        else:
            creature_number_text = 'Creature %d' % self._show_creature.id_

        textsurface = self._medium_font.render(creature_number_text, False,
                                               (0, 0, 0))
        text_size, _ = textsurface.get_size()

        self._screen.blit(
            textsurface,
            (start_point[0] + (self.__lat_column_size - text_size)/2,
             start_point[1] + 20))

        textsurface = self._medium_font.render('Genes', False, (0, 0, 0))
        text_size, _ = textsurface.get_size()

        self._screen.blit(
            textsurface,
            (start_point[0] + (self.__lat_column_size - text_size)/2,
             screen_size[1] - 250))

        labels = ('Structure', 'Energy', 'Weight', 'Radius', 'Speed',
                  'Vision Dist.', 'Vision Angle')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            values = (creature.structure, creature.energy, creature.body.mass,
                      creature.shape.radius, creature.currentspeed,
                      creature.currentvisiondistance,
                      180*creature.currentvisionangle/pi)
            values = ('%d' % val if isinstance(val, int) else
                      '%0.2f' % val if val < 10000 else '%.2E' % val
                      for val in values)

        to_write_list = zip(labels, values)

        start_y = start_point[1] + 50
        self.__writeText(to_write_list, start_point, start_y)

        labels = ('Speed', 'Eating Speed', 'Vision Dist.', 'Vision Angle',
                  'Structure Percentage',  'Walk Priority', 'Run Priority',
                  'F. Run Priority', 'Idle Priority', 'Rotate Priority')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            pvalues = (creature.properties.speed,
                       creature.properties.eatingspeed,
                       creature.properties.visiondistance,
                       creature.properties.visionangle,
                       creature.properties.structpercentage)

            priority_values = (creature.properties.walkpriority,
                               creature.properties.runpriority,
                               creature.properties.fastrunpriority,
                               creature.properties.idlepriority + 1,
                               creature.properties.rotatepriority)
            pr_val_sum = sum(priority_values)
            priority_values = (val/pr_val_sum for val in priority_values)

            values = ('%.1f%%' % (100*val) for val in itertools.chain(
                pvalues, priority_values))

        to_write_list = zip(labels, values)

        start_y = screen_size[1] - 220
        self.__writeText(to_write_list, start_point, start_y)

    def __writeText(self, to_write_list, start_point, start_y):

        for prop, val_str in to_write_list:

            textsurface = self._small_font.render(prop + ':', False, (0, 0, 0))
            self._screen.blit(textsurface,
                              (start_point[0] + 10, start_point[1] + start_y))

            textsurface = self._small_font.render(val_str, False, (0, 0, 0))
            text_size, _ = textsurface.get_size()
            val_x = start_point[0] + self.__lat_column_size - 20 - text_size
            self._screen.blit(textsurface, (val_x, start_point[1] + start_y))

            start_y += 20

    def __drawObjects(self):

        self._painter.drawRect((255, 255, 255), (0, 0),
                               self._size)

        for obj in itertools.chain(self._resources, self._creatures):
            obj.draw(self._painter)

        #self._space.debug_draw(pymunk.pygame_util.DrawOptions(self._screen))

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

        creature = arbiter.shapes[0].simulation_object
        resource = arbiter.shapes[1].simulation_object

        creature_head_pos = creature.headposition
        resource_pos = resource.body.position

        res_dist = creature_head_pos.get_distance(resource_pos)
        if 3*res_dist < creature.shape.radius:
            creature.eat(self, resource)

        return False

    @staticmethod
    def __creatureWallCollision(arbiter, _space, _):

        creature = arbiter.shapes[0].simulation_object

        creature.stopAction()

        return True

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

    def zoomIn(self):
        self._painter.multiplier *= 1.05

    def zoomOut(self):
        self._painter.multiplier /= 1.05

    def __moveOffset(self):
        return 5/self._painter.multiplier

    def moveUp(self):
        self._painter.yoffset += self.__moveOffset()

    def moveDown(self):
        self._painter.yoffset -= self.__moveOffset()

    def moveRight(self):
        self._painter.xoffset -= self.__moveOffset()

    def moveLeft(self):
        self._painter.xoffset += self.__moveOffset()
