
import os

import random
from random import randint

from math import cos, sin, sqrt, pi, floor
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

from behaviours import BasicBehaviour

from painter import Painter

class Simulation:

    CREATURE_COLLISION_TYPE = 1
    SOUND_SENSOR_COLLISION_TYPE = 2
    VISION_SENSOR_COLLISION_TYPE = 3
    RESOURCE_COLLISION_TYPE = 4
    WALL_COLLISION_TYPE = 5

    class Object:

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

    class CircleObject(Object):

        def __init__(self, space, mass, radius, x, y,
                     elasticity=0.5, friction=0.2):

            inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))

            body = Simulation.Object.newBody(mass, inertia)

            shape = pymunk.Circle(body, radius, (0, 0))
            shape.elasticity = elasticity
            shape.friction = friction

            super().__init__(space, body, shape, x, y)

        def draw(self, painter, color=(0, 0, 0)):

            painter.drawCircle(color, self.body.position, self.shape.radius)

    class SoundSensor:

        def __init__(self, creature, sensor_range):

            self._shape = pymunk.Circle(creature.body, sensor_range, (0, 0))

            self._shape.collision_type = Simulation.SOUND_SENSOR_COLLISION_TYPE
            self._shape.filter = pymunk.ShapeFilter(
                categories=(1 << (Simulation.SOUND_SENSOR_COLLISION_TYPE - 1)))
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

            points = Simulation.VisionSensor.__getArcPoints(
                sensor_range, sensor_angle, offset_angle)
            points.append((0, 0))

            shape = pymunk.Poly(creature.body, points)

            shape.collision_type = Simulation.VISION_SENSOR_COLLISION_TYPE
            shape.filter = pymunk.ShapeFilter(
                categories=(1 << (Simulation.VISION_SENSOR_COLLISION_TYPE - 1)))
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

    class Resource(CircleObject):

        def __init__(self, space, x, y, external_rsc, internal_rsc):

            self._ext_rsc = external_rsc
            self._int_rsc = internal_rsc

            super().__init__(space, 1, self.__getRadius(), x, y)

            self.shape.collision_type = Simulation.RESOURCE_COLLISION_TYPE
            self.shape.filter = pymunk.ShapeFilter(
                categories=(1 << (Simulation.RESOURCE_COLLISION_TYPE - 1)))

            self.__convert_interval = 1000
            self.__steps_to_convert = self.__convert_interval
            self.__convert_rsc_qtd = 10

        def step(self):

            if self.__steps_to_convert > 0:
                self.__steps_to_convert -= 1
            else:
                if self._int_rsc > 0:
                    if self._int_rsc < self.__convert_rsc_qtd:
                        cvt_qtd = self._int_rsc
                    else:
                        cvt_qtd = self.__convert_rsc_qtd
                    self._int_rsc -= cvt_qtd
                    self._ext_rsc += cvt_qtd
                    self.shape.unsafe_set_radius(self.__getRadius())

                self.__steps_to_convert = self.__convert_interval

        def consume(self, _simulation, quantity):

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
            return sqrt((self._ext_rsc + self._int_rsc)/1000)

        def draw(self, painter, color=(0, 255, 0)):
            super().draw(painter, color)

    class Creature(CircleObject):

        LAST_ID = -1

        class Properties:

            def __init__(self, creature):

                self._creature = creature

            @property
            def speed(self):
                return self._creature._speed # pylint: disable=protected-access

            @property
            def eatingspeed(self):
                return self._creature._eating_speed # pylint: disable=protected-access

            @property
            def visiondistance(self):
                return self._creature._vision_distance # pylint: disable=protected-access

            @property
            def visionangle(self):
                return self._creature._vision_angle # pylint: disable=protected-access

            @property
            def walkpriority(self):
                return self._creature._walk_priority # pylint: disable=protected-access

            @property
            def runpriority(self):
                return self._creature._run_priority # pylint: disable=protected-access

            @property
            def fastrunpriority(self):
                return self._creature._fast_run_priority # pylint: disable=protected-access

            @property
            def idlepriority(self):
                return self._creature._idle_priority # pylint: disable=protected-access

            @property
            def rotatepriority(self):
                return self._creature._rotate_priority # pylint: disable=protected-access

        def __init__(self, space, x, y, structure, energy, parent=None):

            self._spent_resources = 0
            self._energy = int(energy)
            self._structure = int(structure)

            mass = self.__getMass()
            radius = self.__getRadius(mass)

            super().__init__(space, mass, radius, x, y)

            self.shape.collision_type = Simulation.CREATURE_COLLISION_TYPE
            self.shape.filter = pymunk.ShapeFilter(
                categories=(1 << (Simulation.CREATURE_COLLISION_TYPE - 1)))

            self._species = 'nameless'
            self._id = self.__newId()

            self._is_eating = 0

            if parent is None:
                self._speed, self._eating_speed, self._vision_angle, \
                    self._vision_distance, self._sound_distance = \
                        (random.random() for _ in range(5))

                self._walk_priority, self._run_priority, \
                    self._fast_run_priority, self._idle_priority, \
                        self._rotate_priority = \
                            (random.randint(0, 32) for _ in range(5))

            self._behaviours = [BasicBehaviour(
                self._idle_priority + 1, self._walk_priority,
                self._run_priority, self._fast_run_priority,
                self._rotate_priority)]

            self._action = None

            #self._sound_sensor = Simulation.SoundSensor(self, 200)
            self._vision_sensor = \
                Simulation.VisionSensor(self,
                                        10*radius*self._vision_distance,
                                        pi*(10 + 210*self._vision_angle)/180)

            self._properties = Simulation.Creature.Properties(self)
            self.selected = False

        @property
        def headposition(self):

            radius = self.shape.radius
            pos = self.body.position
            angle = self.body.angle

            pos.x += radius*cos(angle)
            pos.y += radius*sin(angle)

            return pos

        def eat(self, simulation, resource):

            eat_speed = (0.3 + self._eating_speed)/3
            energy_gained = int(resource.consume(simulation,
                                                 self.body.mass*eat_speed))

            if energy_gained == 0:
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

            new_action = self._behaviours[-1].soundAlert(self, x, y)

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
            return (self._spent_resources + self._structure + self._energy)/1000

        def __updateSelf(self):

            self.body.mass = self.__getMass()

            new_radius = self.__getRadius()
            if new_radius != self.shape.radius:
                self.shape.unsafe_set_radius(new_radius)
                self._vision_sensor.distance = \
                    10*new_radius*self._vision_distance

        @property
        def eating(self):
            return self._is_eating > 0

        def act(self, simulation):

            energy_consume_vision = \
                (0.1 + self._vision_distance)*(1 + self._vision_angle)
            energy_consume_speed = self._speed
            energy_consume_eat_speed = 0.2*self._eating_speed
            base_energy_consume = int(self.body.mass*(energy_consume_vision + \
                energy_consume_speed + energy_consume_eat_speed)//100) + 1

            self.__consumeEnergy(base_energy_consume)

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

            speed = 50*(factor**2)*(self._speed + 0.01)
            if factor < 0:
                speed = -speed

            energy_consume = int(abs(speed*self.body.mass*factor* \
                (1 + 2*abs(factor - 0.5))*sqrt(self._speed + 0.01))//100)

            if not self.__consumeEnergy(energy_consume):
                speed = 0

            angle = self.body.angle

            if factor < 0:
                speed /= 4

            self.body.velocity += (speed*cos(angle), speed*sin(angle))

        def __doAngleSpeed(self, factor):

            velocity = self.body.velocity
            current_speed = sqrt(velocity.x**2 + velocity.y**2)

            angular_speed = (-1 if factor < 0 else 1)*(factor**2)* \
                (current_speed + 40*sqrt(self._speed) + 40)/100

            energy_consume = abs(floor(angular_speed*self.body.mass*factor* \
                sqrt(self._speed + 0.2)))//50

            if not self.__consumeEnergy(energy_consume):
                angular_speed = 0

            self.body.angular_velocity += angular_speed

        def draw(self, painter, color=None):

            if color is None:
                color = (230*self._eating_speed, 0, 230*self._speed)

            pos = self.body.position
            radius = self.shape.radius
            angle = self.body.angle

            if self.selected is True:
                painter.drawCircle((255, 80, 80), pos, radius + 8)
            super().draw(painter, color)

            painter.drawArc((int(254*(1 - self._vision_distance)), 255, 50),
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
            Simulation.Creature.LAST_ID += 1
            return Simulation.Creature.LAST_ID

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

            self._painter = Painter(self._screen, 300/size)

        self._time = 0

        self._space = pymunk.Space()
        self._space.damping = 0.25
        self._physics_steps_per_frame = 1

        self._dt = 1/15
        self._ticks = 50

        handler = self._space.add_collision_handler(
            self.CREATURE_COLLISION_TYPE, self.SOUND_SENSOR_COLLISION_TYPE)
        handler.begin = self.__sensorAlert

        handler = self._space.add_collision_handler(
            self.CREATURE_COLLISION_TYPE, self.VISION_SENSOR_COLLISION_TYPE)
        handler.begin = self.__visionAlert

        handler = self._space.add_collision_handler(
            self.RESOURCE_COLLISION_TYPE, self.VISION_SENSOR_COLLISION_TYPE)
        handler.begin = self.__resourceAlert

        handler = self._space.add_collision_handler(
            self.CREATURE_COLLISION_TYPE, self.RESOURCE_COLLISION_TYPE)
        handler.pre_solve = self.__resourceCreatureCollision

        handler = self._space.add_collision_handler(
            self.CREATURE_COLLISION_TYPE, self.WALL_COLLISION_TYPE)
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
                             500000, 500000)

        self.__generateResources()

        self.__addWalls()

    def __generateResources(self):

        resources_qtd = randint(self._resources_min, self._resources_max)
        for _ in range(resources_qtd):
            self.newResource(self._size[0]*(0.1 + 0.8*random.random()),
                             self._size[1]*(0.1 + 0.8*random.random()),
                             500000, 0)

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
                    self._running = False
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
                mask = (1 << (Simulation.CREATURE_COLLISION_TYPE - 1))
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

    def newCreature(self, x, y, structure, energy):

        creature = self.Creature(self._space, x, y, structure, energy)

        self._creatures.append(creature)

        return creature

    def newResource(self, x, y, ext_rsc, int_rsc):

        resource = self.Resource(self._space, x, y, ext_rsc, int_rsc)

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
             screen_size[1] - 230))

        labels = ('Energy', 'Weight', 'Radius', 'Speed', 'Vision Dist.',
                  'Vision Angle')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            values = (creature.energy, creature.body.mass,
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
                  'Walk Priority', 'Run Priority', 'F. Run Priority',
                  'Idle Priority', 'Rotate Priority')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            pvalues = (creature.properties.speed,
                       creature.properties.eatingspeed,
                       creature.properties.visiondistance,
                       creature.properties.visionangle)

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

        start_y = screen_size[1] - 200
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
            shape.collision_type = Simulation.WALL_COLLISION_TYPE
            shape.filter = pymunk.ShapeFilter(
                categories=(1 << (Simulation.WALL_COLLISION_TYPE - 1)))

        for line in static_lines:
            line.elasticity = 0.3
            line.friction = 0.1

        self._space.add(static_lines)

    def zoomIn(self):
        self._painter.multiplier *= 1.05

    def zoomOut(self):
        self._painter.multiplier /= 1.05

    def moveUp(self):
        self._painter.yoffset += 20

    def moveDown(self):
        self._painter.yoffset -= 20

    def moveRight(self):
        self._painter.xoffset -= 20

    def moveLeft(self):
        self._painter.xoffset += 20
