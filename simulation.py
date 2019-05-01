
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

class Painter(object):
    
    def __init__(self, screen, multiplier):
        
        self._screen = screen
        self._mul = multiplier
    
    def drawCircle(self, color, center, radius, width=0):
        pygame.draw.circle(self._screen, color, (int(center[0]*self._mul), int(center[1]*self._mul)), int(radius*self._mul), width)
        
    def drawLine(self, color, start, end, width=1):
        pygame.draw.line(self._screen, color, (int(start[0]*self._mul), int(start[1]*self._mul)), (int(end[0]*self._mul), int(end[1]*self._mul)), width)
    
    def drawArc(self, color, center, radius, angle, open_angle, width=None):
        
        radius *= self._mul
        radius = int(radius)
        
        center = (int(center[0]*self._mul), int(center[1]*self._mul))
        
        points = [center]
        
        n = int(10*open_angle) + 2
        
        cur_angle = open_angle/2 + angle
        angle_diff = open_angle/(n-1)
        for i in range(n):
            
            x = center[0] + radius*cos(cur_angle)
            y = center[1] + radius*sin(cur_angle)
            points.append((x, y))
            cur_angle -= angle_diff
        
        pygame.draw.polygon(self._screen, color, points)
        
    @property
    def multiplier(self):
        return self._mul
    
    @multiplier.setter
    def multiplier(self, mul):
        self._mul = mul

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
        MUTATION = 0.02

        def __init__(self, space, x, y, structure, energy, dna_hex=None):
            
            self.dna_hex = dna_hex
            
            self._spent_resources = 0
            self._energy = int(energy)
            self._structure = int(structure)
            
            mass = self._get_mass()
            radius = self._get_radius(mass)
            super().__init__(space, mass, radius, x, y)
            
            self.shape.collision_type = Simulation.CREATURE_COLLISION_TYPE
            
            self._species = 'nameless'
            self._id = self._new_id()
            
            self._behaviours = [ BasicBehaviour() ]
            self._action = None
            
            self._is_eating = 0
          
            if dna_hex is not None:
                self._speed = Simulation.Creature.readGene(dna_hex, 0, 16)
                self._eating_speed = Simulation.Creature.readGene(dna_hex, 16, 16)
                self._vision_angle = Simulation.Creature.readGene(dna_hex, 32, 16)
                self._vision_distance = Simulation.Creature.readGene(dna_hex, 48, 16)
                self._sound_distance = Simulation.Creature.readGene(dna_hex, 64, 16)
            
            #self._sound_sensor = Simulation.SoundSensor(self, 200)
            self._vision_sensor = Simulation.VisionSensor(self, 10*radius*self._vision_distance, pi*(10 + 210*self._vision_angle)/180)
        
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
            energy_gained = resource.consume(simulation, self.body.mass*eat_speed)
            
            if energy_gained == 0:
                return None
            
            spent_to_eat = (eat_speed/2)*energy_gained
            
            self._spent_resources += spent_to_eat
            energy_gained -= spent_to_eat
            self._energy += energy_gained
            
            #print('Eating', energy_gained)
            
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
            
            print('Sound Alert')
            new_action = self._behaviours[-1].soundAlert(self, x, y)
            
            if new_action is not None:
                self._action = new_action
            
        def visionAlert(self, creature):
            
            print('Vision Alert')
            new_action = self._behaviours[-1].visionAlert(self, creature)
            
            if new_action is not None:
                self._action = new_action
        
        def visionResourceAlert(self, resource):
        
            print('Creature saw resource')
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
            
            self._consume_energy(int(0.1 + self._vision_distance)*(1 + self._vision_angle) + self._speed)
            
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
        
        def _do_speed(self, factor):
            
            speed = 50*(factor**2)*(self._speed + 0.01)
            if factor < 0:
                speed = -speed
            
            energy_consume = int(abs(speed*self.body.mass*factor*(1 + 2*abs(factor - 0.5))*sqrt(self._speed))//100 + 1)
            
            if not self._consume_energy(energy_consume):
                speed = 0
            
            angle = self.body.angle
            
            if factor < 0:
                speed /= 4
            
            self.body.velocity += ( speed*cos(angle), speed*sin(angle) )
        
        def _do_angle_speed(self, factor):
            
            velocity = self.body.velocity
            current_speed = sqrt(velocity.x**2 + velocity.y**2)
            
            angular_speed = (-1 if factor < 0 else 1)*(factor**2)*(current_speed + 40*sqrt(self._speed) + 40)/1000
            
            energy_consume = abs(floor(angular_speed*self.body.mass*factor*sqrt(self._speed)))//100
            
            if not self._consume_energy(energy_consume):
                angular_speed = 0
            
            self.body.angular_velocity += angular_speed
        
        def draw(self, painter):
            
            color = (230*self._eating_speed, 0, 230*self._speed)
            
            super().draw(painter, color)
            
            pos = self.body.position
            radius = self.shape.radius
            angle = self.body.angle
            
            painter.drawArc((int(254*(1 - self._vision_distance)), 255, 50), pos, radius, angle, self._vision_sensor.angle, width=1)
            #painter.drawLine((255, 255, 255), pos, (pos.x + radius*cos(angle), pos.y + radius*sin(angle)))
        
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
        def speed(self):
            return self._speed
        
        @property
        def energy(self):
            return self._energy
    
    def __init__(self, population_size = 16, starting_resources = 20, size=1000, out_file = None, screen_size=(600, 600)):
        
        self._population_size = population_size
        self._starting_resources = starting_resources
        
        if out_file is not None:
            try:
                os.remove(self._out_file)
            except FileNotFoundError:
                pass
        
        self._out_file = out_file

        pygame.init()
        pygame.display.set_caption("Simulation")
        
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

        self._screen = pygame.display.set_mode(screen_size)
        self._clock = pygame.time.Clock()
        
        self._painter = Painter(self._screen, 300/size)

        self._creatures = []
        self._resources = []

        self._running = True
        screen_size = self._screen.get_size()
        mul = 1/self._painter.multiplier
        self._size = (screen_size[0]*mul, screen_size[1]*mul)
        
        # dna_hex = speed + eating_speed + vision_angle + vision_distance + sound_distance
        #dna_hex = '5000' + '0000' + '0000' + '0000' + '0000'
        for i in range(self._population_size):
            
            dna_hex = ''.join(( '{:x}'.format(random.randint(0, 15)) for i in range(20)))
            print(dna_hex)
            self.newCreature(self._size[0]*(0.1 + 0.8*random.random()), self._size[1]*(0.1 + 0.8*random.random()), 500000, 500000, dna_hex=dna_hex)
            
        for i in range(self._starting_resources):
            self.newResource(self._size[0]*(0.1 + 0.8*random.random()), self._size[1]*(0.1 + 0.8*random.random()), 500000, 0)
            
        self._generation = 1
        self._save_generation_data()
        
        self._add_walls()
        
    def _select_parent(self):
        
        if len(self._creatures) == 0:
            return None
        
        while True:
            for creature in self._creatures:
                if random.random() < 0.15:
                    return creature
    
    @staticmethod
    def generateChildDNA(parent1, parent2):
        
        dna1 = bytearray.fromhex(parent1.dna_hex)
        dna2 = bytearray.fromhex(parent2.dna_hex)
        
        half = len(dna1)//2
        
        dna_child = dna1[:half] + dna2[half:]
        
        for i in range(10):        
            if random.random() < 0.3:
                
                n_byte = randint(0, len(dna_child) - 1)
                n_bit = randint(0, 7)
                dna_child[n_bit] ^= 1 << n_bit
        
        return dna_child.hex()
    
    def newChildDNA(self):
        
        parent1 = self._select_parent()
        
        parent2 = self._select_parent()
        while parent2 is parent1:
            if parent2 is None:
                return None
            parent2 = self._select_parent()
        
        return self.generateChildDNA(parent1, parent2)
    
    def endGeneration(self):
        
        self._creatures.sort(key=lambda creature : creature.energy, reverse=True)
        
        print(self._creatures)
        
        for obj in itertools.chain(self._creatures, self._resources):
            obj.destroy()
        
        new_children_dna = tuple(self.newChildDNA() for i in range(self._population_size))
        
        self._creatures = []
        self._resources = []
        
        for dna in new_children_dna:
            self.newCreature(self._size[0]*(0.1 + 0.8*random.random()), self._size[1]*(0.1 + 0.8*random.random()), 500000, 500000, dna_hex=dna)
            
        self._generation += 1
        self._save_generation_data()
        
        for i in range(self._starting_resources):
            self.newResource(self._size[0]*(0.1 + 0.8*random.random()), self._size[1]*(0.1 + 0.8*random.random()), 500000, 0)

    def run(self):
        
        while self._running:
        
            for x in range(self._physics_steps_per_frame):
                self._space.step(self._dt)

            self._process_events()
            self._clear_screen()
            self._draw_objects()
            pygame.display.flip()
            
            for creature in self._creatures:
                creature.act(self)
        
            self._clock.tick(self._ticks)
            
            self._time += 1
            
            if self._time == 2000:
                self.endGeneration()
                self._time = 0

    def _process_events(self):

        for event in pygame.event.get():
            if event.type == QUIT:
                self._running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self._running = False

    def newCreature(self, x, y, structure, energy, dna_hex = None):
        
        creature = self.Creature(self._space, x, y, structure, energy, dna_hex=dna_hex)
        
        self._creatures.append(creature)
        
        return creature
    
    def newResource(self, x, y, ext_rsc, int_rsc):
    
        resource = self.Resource(self._space, x, y, ext_rsc, int_rsc)
        
        self._resources.append(resource)
        
        return resource

    def _clear_screen(self):

        self._screen.fill(THECOLORS["white"])

    def _draw_objects(self):
        
        pygame.display.set_caption("Simulation - Generation %d" % self._generation)
        
        for creature in itertools.chain(self._resources, self._creatures):
            creature.draw(self._painter)
            
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
        
        for line in static_lines:
            line.elasticity = 0.3
            line.friction = 0.1
        
        self._space.add(static_lines)
    
    def _save_generation_data(self):
        
        if self._out_file is None:
            return
        
        with open(self._out_file, 'a') as f:
            f.write('[Generation %d]\n' % self._generation)
            for creature in self._creatures:
                f.write(creature.dna_hex + '\n')

