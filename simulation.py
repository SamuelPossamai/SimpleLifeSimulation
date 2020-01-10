
from pathlib import Path

import os

from abc import ABC, abstractmethod

import random
from random import randint

from math import cos, sin, sqrt, pi, ceil, floor

import pygame
from pygame.key import *
from pygame.locals import *
from pygame.color import *

import itertools

import pymunk
import pymunk.pygame_util

from behaviours import BasicBehaviour

from painter import Painter

class Simulation(object):

    CREATURE_COLLISION_TYPE = 1
    SOUND_SENSOR_COLLISION_TYPE = 2
    VISION_SENSOR_COLLISION_TYPE = 3
    RESOURCE_COLLISION_TYPE = 4
    WALL_COLLISION_TYPE = 5

    class Object(object):

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

        def __init__(self, space, mass, radius, x, y, elasticity = 0.5, friction = 0.2):

            inertia = pymunk.moment_for_circle(mass, 0, radius, (0, 0))

            body = Simulation.Object.newBody(mass, inertia)

            shape = pymunk.Circle(body, radius, (0, 0))
            shape.elasticity = elasticity
            shape.friction = friction

            super().__init__(space, body, shape, x, y)

        def draw(self, painter, color=(0, 0, 0)):

            painter.drawCircle(color, self.body.position, self.shape.radius)

    class SoundSensor(object):

        def __init__(self, creature, sensor_range):

            self._shape = pymunk.Circle(creature.body, sensor_range, (0, 0))

            self._shape.collision_type = Simulation.SOUND_SENSOR_COLLISION_TYPE
            self.shape.filter = pymunk.ShapeFilter(categories=(1 << (Simulation.SOUND_SENSOR_COLLISION_TYPE - 1)))
            self._shape.sensor = True

            self._shape.creature = creature

            creature.body.space.add(self._shape)

    class VisionSensor(object):

        def __init__(self, creature, sensor_range, sensor_angle, offset_angle = 0):

            if sensor_angle > pi:
                shapes = (self._create_shape(creature, sensor_range, sensor_angle/2, offset_angle + sensor_angle/4),
                          self._create_shape(creature, sensor_range, sensor_angle/2, offset_angle - sensor_angle/4))
            else:
                shapes = (self._create_shape(creature, sensor_range, sensor_angle, offset_angle),)

            self._shapes = shapes
            self._angle = sensor_angle

        @staticmethod
        def _create_shape(creature, sensor_range, sensor_angle, offset_angle):

            points = Simulation.VisionSensor._get_arc_points(sensor_range, sensor_angle, offset_angle)
            points.append((0, 0))

            shape = pymunk.Poly(creature.body, points)

            shape.collision_type = Simulation.VISION_SENSOR_COLLISION_TYPE
            shape.filter = pymunk.ShapeFilter(categories=(1 << (Simulation.VISION_SENSOR_COLLISION_TYPE - 1)))
            shape.sensor = True

            shape.creature = creature

            creature.body.space.add(shape)

            return shape

        @staticmethod
        def _get_arc_points(sensor_range, sensor_angle, angle_offset):

            points = []

            n = int(10*sensor_angle) + 2

            cur_angle = sensor_angle/2 + angle_offset
            angle_diff = sensor_angle/(n-1)
            for i in range(n):

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

            super().__init__(space, 1, self._get_radius(), x, y)

            self.shape.collision_type = Simulation.RESOURCE_COLLISION_TYPE
            self.shape.filter = pymunk.ShapeFilter(categories=(1 << (Simulation.RESOURCE_COLLISION_TYPE - 1)))

        def consume(self, simulation, quantity):

            if quantity >= self._ext_rsc:
                consumed = self._ext_rsc
                self._ext_rsc = 0

                new_radius = self._get_radius()
                if new_radius != self.shape.radius:
                    self.shape.unsafe_set_radius(new_radius)
                return consumed

            self._ext_rsc -= quantity
            new_radius = self._get_radius()
            if new_radius != self.shape.radius:
                self.shape.unsafe_set_radius(new_radius)
            return quantity

        def _get_radius(self):
            return sqrt((self._ext_rsc + self._int_rsc)/1000)

        def draw(self, painter):
            super().draw(painter, (0, 255, 0))

    class Creature(CircleObject):

        LAST_ID = -1

        class Properties(object):

            def __init__(self, creature):

                self._creature = creature

            @property
            def speed(self):
                return self._creature._speed

            @property
            def eatingSpeed(self):
                return self._creature._eating_speed

            @property
            def visionDistance(self):
                return self._creature._vision_distance

            @property
            def visionAngle(self):
                return self._creature._vision_angle

            @property
            def walkPriority(self):
                return self._creature._walk_priority

            @property
            def runPriority(self):
                return self._creature._run_priority

            @property
            def fastRunPriority(self):
                return self._creature._fast_run_priority

            @property
            def idlePriority(self):
                return self._creature._idle_priority

            @property
            def rotatePriority(self):
                return self._creature._rotate_priority

        def __init__(self, space, x, y, structure, energy, dna_hex):

            if len(dna_hex) != 26:
                raise ValueError('Hex DNA must have exactly 26 characters')

            self.dna_hex = dna_hex

            self._spent_resources = 0
            self._energy = int(energy)
            self._structure = int(structure)

            mass = self._get_mass()
            radius = self._get_radius(mass)

            super().__init__(space, mass, radius, x, y)

            self.shape.collision_type = Simulation.CREATURE_COLLISION_TYPE
            self.shape.filter = pymunk.ShapeFilter(categories=(1 << (Simulation.CREATURE_COLLISION_TYPE - 1)))

            self._species = 'nameless'
            self._id = self._new_id()

            self._is_eating = 0

            self._speed, self._eating_speed, self._vision_angle, \
            self._vision_distance, self._sound_distance, \
            self._walk_priority, self._run_priority, \
            self._fast_run_priority, self._idle_priority, self._rotate_priority = self.readDNA(dna_hex)

            self._behaviours = [ BasicBehaviour(self._idle_priority + 1, self._walk_priority,
                                                self._run_priority, self._fast_run_priority, self._rotate_priority) ]

            self._action = None

            #self._sound_sensor = Simulation.SoundSensor(self, 200)
            self._vision_sensor = Simulation.VisionSensor(self, 10*radius*self._vision_distance, pi*(10 + 210*self._vision_angle)/180)

            self._properties = Simulation.Creature.Properties(self)
            self.selected = False

        @staticmethod
        def readDNA(dna_hex, to_dict=False):

            speed, eating_speed, vision_ang, vision_dist, sound_dist = ( Simulation.Creature.readGene(dna_hex, 16*i, 16) for i in range(5) )
            priorities = tuple( Simulation.Creature.readGene(dna_hex, 80 + 4*i, 4, is_integer=True) for i in range(5) )

            if to_dict:
                return {'speed' : speed, 'eating_speed' : eating_speed, 'vision_angle' : vision_ang,
                        'vision_distance' : vision_dist, 'sound_distance' : sound_dist,
                        'walk_priority' : priorities[0], 'run_priority' : priorities[1],
                        'fast_run_priority' : priorities[2], 'idle_priority' : priorities[3],
                        'rotate_priority' : priorities[4] }

            return (speed, eating_speed, vision_ang, vision_dist, sound_dist, *priorities)

        @staticmethod
        def readGene(dna_hex, position, n_bits, is_integer = False):

            hex_pos = position//4
            start_after_n_bits = position%4

            number = int(dna_hex[hex_pos : hex_pos + ceil((n_bits + start_after_n_bits)/4)], 16)

            n_bits_mod4 = n_bits%4
            exclude_n_bits_after = ((4 - n_bits_mod4 if n_bits_mod4 != 0 else 0) + (4 - start_after_n_bits if start_after_n_bits != 0 else 0))%4

            number = ( (number >> exclude_n_bits_after) & (0xffffffff >> (32 - n_bits)))

            if is_integer is False:
                return number/((1 << n_bits) - 1)

            return number

        @property
        def headPosition(self):

            radius = self.shape.radius
            pos = self.body.position
            angle = self.body.angle

            pos.x += radius*cos(angle)
            pos.y += radius*sin(angle)

            return pos

        def eat(self, simulation, resource):

            eat_speed = (0.3 + self._eating_speed)/3
            energy_gained = int(resource.consume(simulation, self.body.mass*eat_speed))

            if energy_gained == 0:
                return None

            spent_to_eat = int((eat_speed/2)*energy_gained)

            self._spent_resources += spent_to_eat
            energy_gained -= spent_to_eat
            self._energy += energy_gained

            self._is_eating = 5

            self._update_self()

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

            new_action = self._behaviours[-1].visionAlert(self, creature)

            if new_action is not None:
                self._action = new_action

        def visionResourceAlert(self, resource):

            new_action = self._behaviours[-1].visionResourceAlert(self, resource)

            if new_action is not None:
                self._action = new_action

        def _get_radius(self, mass = None):

            if mass is None:
                mass = self.body.mass
            return sqrt(mass)

        def _get_mass(self):
            return (self._spent_resources + self._structure + self._energy)/1000

        def _update_self(self):

            self.body.mass = self._get_mass()

            new_radius = self._get_radius()
            if new_radius != self.shape.radius:
                self.shape.unsafe_set_radius(new_radius)
                self._vision_sensor.distance = 10*new_radius*self._vision_distance

        @property
        def eating(self):
            return self._is_eating > 0

        def act(self, simulation):

            energy_consume_vision = (0.1 + self._vision_distance)*(1 + self._vision_angle)
            energy_consume_speed = self._speed
            energy_consume_eat_speed = 0.2*self._eating_speed
            base_energy_consume = int(self.body.mass*(energy_consume_vision + energy_consume_speed + energy_consume_eat_speed)//100) + 1

            self._consume_energy(base_energy_consume)

            if self._is_eating > 0:
                self._is_eating -= 1

            if self._action is None:
                self._action = self._behaviours[-1].selectAction(self)

            action_result = self._action.doAction(self)

            if action_result is None:
                self._action = None
                return None

            speed_factor, angle_factor = action_result

            if speed_factor > 1:
                speed_factor = 1
            elif speed_factor < -1:
                speed_factor = -1

            if angle_factor > 1:
                angle_factor = 1
            elif angle_factor < -1:
                angle_factor = -1

            self._do_speed(speed_factor)
            self._do_angle_speed(angle_factor)

            if self._spent_resources > 0.05*(self._energy + self._structure):
                self._spent_resources = 0
                self._update_self()

        def _do_speed(self, factor):

            speed = 50*(factor**2)*(self._speed + 0.01)
            if factor < 0:
                speed = -speed

            energy_consume = int(abs(speed*self.body.mass*factor*(1 + 2*abs(factor - 0.5))*sqrt(self._speed + 0.01))//100)

            if not self._consume_energy(energy_consume):
                speed = 0

            angle = self.body.angle

            if factor < 0:
                speed /= 4

            self.body.velocity += ( speed*cos(angle), speed*sin(angle) )

        def _do_angle_speed(self, factor):

            velocity = self.body.velocity
            current_speed = sqrt(velocity.x**2 + velocity.y**2)

            angular_speed = (-1 if factor < 0 else 1)*(factor**2)*(current_speed + 40*sqrt(self._speed) + 40)/100

            energy_consume = abs(floor(angular_speed*self.body.mass*factor*sqrt(self._speed + 0.2)))//50

            if not self._consume_energy(energy_consume):
                angular_speed = 0

            self.body.angular_velocity += angular_speed

        def draw(self, painter):

            color = (230*self._eating_speed, 0, 230*self._speed)

            pos = self.body.position
            radius = self.shape.radius
            angle = self.body.angle

            if self.selected is True:
                painter.drawCircle((255, 80, 80), pos, radius + 8)
            super().draw(painter, color)

            painter.drawArc((int(254*(1 - self._vision_distance)), 255, 50), pos, radius, angle, self._vision_sensor.angle, width=1)

        def _consume_energy(self, qtd):

            if qtd < 0 or qtd > self._energy:
                return False

            self._energy -= qtd
            self._spent_resources += qtd

            return True

        def __repr__(self):
            return "Creature<{}>".format(self._id)

        @staticmethod
        def _new_id():
            Simulation.Creature.LAST_ID += 1
            return Simulation.Creature.LAST_ID

        @property
        def species(self):
            return self._name

        @property
        def id_(self):
            return self._id

        @property
        def energy(self):
            return self._energy

        @energy.setter
        def energy(self, e):
            self._energy = max(int(e), 0)
            self._update_self()

        @property
        def properties(self):
            return self._properties

        @property
        def currentSpeed(self):
            return self.body.velocity.length

        @property
        def currentVisionDistance(self):
            return self._vision_sensor.distance

        @property
        def currentVisionAngle(self):
            return self._vision_sensor.angle

    def __init__(self, population_size=16, starting_resources=20, size=1000,
                 out_file=None, in_file=None, screen_size=(600, 600),
                 use_graphic=True, quiet=False):

        screen_size = (screen_size[0] + 150, screen_size[1])

        if type(population_size) is int:
            self._population_size_min = population_size
            self._population_size_max = population_size
        else:
            self._population_size_min = population_size[0]
            self._population_size_max = population_size[1]

        if type(starting_resources) is int:
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

        self._use_graphic = use_graphic
        if use_graphic is True:

            pygame.init()
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

        handler = self._space.add_collision_handler(self.CREATURE_COLLISION_TYPE, self.SOUND_SENSOR_COLLISION_TYPE)
        handler.begin = self._sensor_alert

        handler = self._space.add_collision_handler(self.CREATURE_COLLISION_TYPE, self.VISION_SENSOR_COLLISION_TYPE)
        handler.begin = self._vision_alert

        handler = self._space.add_collision_handler(self.RESOURCE_COLLISION_TYPE, self.VISION_SENSOR_COLLISION_TYPE)
        handler.begin = self._resource_alert

        handler = self._space.add_collision_handler(self.CREATURE_COLLISION_TYPE, self.RESOURCE_COLLISION_TYPE)
        handler.pre_solve = self._resource_creature_collision

        handler = self._space.add_collision_handler(self.CREATURE_COLLISION_TYPE, self.WALL_COLLISION_TYPE)
        handler.pre_solve = self._creature_wall_collision

        self._creatures = []
        self._resources = []

        self._running = True
        screen_size = screen_size
        mul = size/300
        self._size = ((screen_size[0] - 150)*mul, screen_size[1]*mul)

        if in_file is None:

            dna_hex_list = (''.join(( '{:x}'.format(random.randint(0, 15)) for i in range(26)))
                            for i in range(randint(self._population_size_min, self._population_size_max)))

        else:

            with open(in_file) as f:
                content = f.read()
                dna_hex_list = content.rsplit(']\n', 1)[-1].split('\n')
                dna_hex_list.remove('')
                self._population_size_min = self._population_size_max = len(dna_hex_list)

        for dna_hex in dna_hex_list:
            self.newCreature(self._size[0]*(0.1 + 0.8*random.random()),
                             self._size[1]*(0.1 + 0.8*random.random()),
                             500000, 500000, dna_hex)

        self._generate_resources()

        self._add_walls()

    def _generate_resources(self):

        resources_qtd = randint(self._resources_min, self._resources_max)
        for i in range(resources_qtd):
            self.newResource(self._size[0]*(0.1 + 0.8*random.random()), self._size[1]*(0.1 + 0.8*random.random()), 500000, 0)

    def run(self):

        while self._running:

            if self._paused is False:
                for x in range(self._physics_steps_per_frame):
                    self._space.step(self._dt)

                for creature in self._creatures:
                    creature.act(self)

            if self._use_graphic is True:

                pygame.display.set_caption('Simulation')

                self._process_events()
                self._clear_screen()
                self._draw_side_info()
                self._draw_objects()
                pygame.display.flip()

                self._clock.tick(self._ticks)

    def _process_events(self):

        for event in pygame.event.get():
            if event.type == QUIT:
                self._running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self._running = False
                elif event.key == K_SPACE or event.key == K_p:
                    self._paused = not self._paused
            elif event.type == MOUSEBUTTONUP:

                pos = self._painter.mapPointFromScreen(pygame.mouse.get_pos())
                mask=( 1 << (Simulation.CREATURE_COLLISION_TYPE - 1) )
                clicked = next(iter(self._space.point_query(pos, 0, pymunk.ShapeFilter(mask=mask))), None)

                if self._show_creature is not None:
                    self._show_creature.selected = False

                if clicked is None:
                    self._show_creature = None
                else:
                    self._show_creature = clicked.shape.simulation_object
                    self._show_creature.selected = True

    def newCreature(self, x, y, structure, energy, dna_hex):

        creature = self.Creature(self._space, x, y, structure, energy, dna_hex)

        self._creatures.append(creature)

        return creature

    def newResource(self, x, y, ext_rsc, int_rsc):

        resource = self.Resource(self._space, x, y, ext_rsc, int_rsc)

        self._resources.append(resource)

        return resource

    def _clear_screen(self):

        self._screen.fill(THECOLORS["white"])

    def _draw_side_info(self):

        screen_size = pygame.display.get_surface().get_size()
        start_point = screen_size[0] - 150, 0
        creature = self._show_creature

        pygame.draw.rect(self._screen, (200, 200, 200), (start_point[0], start_point[1], 150, screen_size[1]))

        creature_number_text = '-' if self._show_creature is None else 'Creature %d' % self._show_creature.id_

        textsurface = self._medium_font.render(creature_number_text, False, (0, 0, 0))
        text_size, _ = textsurface.get_size()

        self._screen.blit(textsurface, (start_point[0] + (150 - text_size)/2, start_point[1] + 20))

        textsurface = self._medium_font.render('Genes', False, (0, 0, 0))
        text_size, _ = textsurface.get_size()

        self._screen.blit(textsurface, (start_point[0] + (150 - text_size)/2, screen_size[1] - 230))

        labels = ('Energy', 'Weight', 'Radius', 'Speed', 'Vision Dist.', 'Vision Angle')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            values = (creature.energy, creature.body.mass,
                      creature.shape.radius, creature.currentSpeed,
                      creature.currentVisionDistance,
                      180*creature.currentVisionAngle/pi)
            values = ('%d' % val if type(val) is int else '%0.2f' % val if val < 10000 else '%.2E' % val for val in values)

        to_write_list = zip(labels, values)

        start_y = start_point[1] + 50
        self._write_text(to_write_list, screen_size, start_point, start_y)

        labels = ('Speed', 'Eating Speed', 'Vision Dist.', 'Vision Angle', 'Walk Priority', 'Run Priority', 'F. Run Priority',
                  'Idle Priority', 'Rotate Priority')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            pvalues = (creature.properties.speed, creature.properties.eatingSpeed, creature.properties.visionDistance, creature.properties.visionAngle)

            priority_values = (creature.properties.walkPriority, creature.properties.runPriority, creature.properties.fastRunPriority,
                               creature.properties.idlePriority + 1, creature.properties.rotatePriority)
            pr_val_sum = sum(priority_values)
            priority_values = (val/pr_val_sum for val in priority_values)

            values = ('%.1f%%' % (100*val) for val in itertools.chain(pvalues, priority_values))

        to_write_list = zip(labels, values)

        start_y = screen_size[1] - 200
        self._write_text(to_write_list, screen_size, start_point, start_y)

    def _write_text(self, to_write_list, screen_size, start_point, start_y):

        for prop, val_str in to_write_list:

            textsurface = self._small_font.render(prop + ':', False, (0, 0, 0))
            self._screen.blit(textsurface, (start_point[0] + 10, start_point[1] + start_y))

            textsurface = self._small_font.render(val_str, False, (0, 0, 0))
            text_size, _ = textsurface.get_size()
            self._screen.blit(textsurface, (start_point[0] + 140 - text_size, start_point[1] + start_y))

            start_y += 20

    def _draw_objects(self):

        for obj in itertools.chain(self._resources, self._creatures):
            obj.draw(self._painter)

        #self._space.debug_draw(pymunk.pygame_util.DrawOptions(self._screen))

    def _sensor_alert(self, arbiter, space, _):

        sound_pos = arbiter.shapes[0].body.position
        arbiter.shapes[1].creature.soundAlert(sound_pos.x, sound_pos.y)

        return False

    def _vision_alert(self, arbiter, space, _):

        vision_creature = arbiter.shapes[0].simulation_object
        arbiter.shapes[1].creature.visionAlert(vision_creature)

        return False

    def _resource_alert(self, arbiter, space, _):

        vision_resource = arbiter.shapes[0].simulation_object
        arbiter.shapes[1].creature.visionResourceAlert(vision_resource)

        return False

    def _resource_creature_collision(self, arbiter, space, _):

        creature = arbiter.shapes[0].simulation_object
        resource = arbiter.shapes[1].simulation_object

        creature_head_pos = creature.headPosition
        resource_pos = resource.body.position

        if 3*creature_head_pos.get_distance(resource_pos) < creature.shape.radius:
            creature.eat(self, resource)

        return False

    def _creature_wall_collision(self, arbiter, space, _):

        creature = arbiter.shapes[0].simulation_object

        creature._action = None

        return True

    def _add_walls(self):

        size = self._size

        static_body = self._space.static_body
        static_lines = [pymunk.Segment(static_body, (0, 0), (size[0], 0), 0.0),
                        pymunk.Segment(static_body, (size[0], 0), (size[0], size[1]), 0.0),
                        pymunk.Segment(static_body, (size[0], size[1]), (0, size[1]), 0.0),
                        pymunk.Segment(static_body, (0, size[1]), (0, 0), 0.0)]

        for shape in static_lines:
            shape.collision_type = Simulation.WALL_COLLISION_TYPE
            shape.filter = pymunk.ShapeFilter(categories=(1 << (Simulation.WALL_COLLISION_TYPE - 1)))

        for line in static_lines:
            line.elasticity = 0.3
            line.friction = 0.1

        self._space.add(static_lines)
