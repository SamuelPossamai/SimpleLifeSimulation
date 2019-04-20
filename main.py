#!/usr/bin/env python3

from abc import ABC, abstractmethod

import random
from random import randint

from math import cos, sin, sqrt, pi, ceil, floor, atan2

import pygame
from pygame.key import *
from pygame.locals import *
from pygame.color import *

from enum import Enum

import itertools

import pymunk
import pymunk.pygame_util

class AbstractAction(ABC):
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def doAction(self, creature):
        pass

class IdleAction(ABC):
    
    def __init__(self, time = 0):
        super().__init__()
        
        self._time = time
    
    def doAction(self, creature):
        
        if self._time <= 0:
            return None
        
        self._time -= 1
        
        return 0, 0

class GoToPointAction(AbstractAction):
    
    BODY_PART = Enum('BODY_PART', ('head', 'center'))
    
    def __init__(self, x, y, weight = 1, target_body_part = BODY_PART.center):
        
        super().__init__()
        
        self._weight = weight
        self._point = pymunk.Vec2d(x, y)
        self._target_body_part = target_body_part
    
    def doAction(self, creature):
        
        if self._target_body_part == GoToPointAction.BODY_PART.head:
            pos = creature.headPosition
        else:
            pos = creature.body.position
            
        x_diff = pos.x - self._point.x
        y_diff = pos.y - self._point.y
        
        distance = sqrt(x_diff**2 + y_diff**2)
        
        if 4*distance < creature.shape.radius:
            return None
        
        angle1 = creature.body.angle%(2*pi)
        angle2 = pi + atan2(y_diff, x_diff)%(2*pi)
        speed_factor = distance/((1 + creature.speed))
        
        angle_diff1 = abs(angle1 - angle2)
        angle_diff2 = 2*pi - abs(angle1 - angle2)
        
        angle_diff = min(angle_diff1, angle_diff2)
        
        if (angle1 > angle2) is (angle_diff1 < pi):
            angle_diff = -angle_diff
        
        if distance < creature.shape.radius and abs(angle_diff) > pi/2:
            return (-0.2, 0)
        
        velocity = creature.body.velocity
        current_speed = sqrt(velocity.x**2 + velocity.y**2)

        angle_factor = 200*angle_diff/(1 + 149*creature.speed)
        
        speed_factor = speed_factor/(0.1 + (100*(1 + creature.speed))*abs(angle_diff) + current_speed)
        
        if speed_factor > 1:
            speed_factor = 1
        
        if angle_factor > 1:
            angle_factor = 1
        elif angle_factor < -1:
            angle_factor = -1
        
        return speed_factor*self._weight, angle_factor

class WalkAction(GoToPointAction):
    
    def __init__(self, x, y, target_body_part = GoToPointAction.BODY_PART.center):
        super().__init__(x, y, weight=0.4, target_body_part=target_body_part)

class RunAction(GoToPointAction):
    
    def __init__(self, x, y, target_body_part = GoToPointAction.BODY_PART.center):
        super().__init__(x, y, weight=0.8, target_body_part=target_body_part)

class FastRunAction(GoToPointAction):
    
    def __init__(self, x, y, target_body_part = GoToPointAction.BODY_PART.center):
        super().__init__(x, y, weight=1, target_body_part=target_body_part)

class RotateAction(AbstractAction):
    
    def __init__(self, angle):
        super().__init__()
        
        self._angle = angle
    
    def doAction(self, creature):
        
        angle1 = creature.body.angle%(2*pi)
        angle2 = self._angle
        
        angle_diff1 = abs(angle1 - angle2)
        angle_diff2 = 2*pi - abs(angle1 - angle2)
        
        angle_diff = min(angle_diff1, angle_diff2)
        
        if abs(creature.body.angular_velocity) > 1.5:
            return 0, 0
        elif abs(angle_diff) < 0.08 and abs(creature.body.angular_velocity) < 0.03:
            return None
        else:
            if (angle1 > angle2) is (angle_diff1 < pi):
                angle_diff = -angle_diff
            
            return 0, angle_diff

class AbstractBehaviour(ABC):
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def selectAction(self, creature):
        pass
    
    @abstractmethod
    def visionAlert(self, creature, other):
        pass
    
    @abstractmethod
    def visionResourceAlert(self, creature, resource):
        pass
    
    @abstractmethod
    def soundAlert(self, creature, x, y):
        pass

class BasicBehaviour(AbstractBehaviour):
    
    def __init___(self):
        super().__init__()
    
    def selectAction(self, creature):

        select = randint(0, 3)
        
        if select == 0 or select == 1:
            pos = creature.body.position
            radius = creature.shape.radius
            
            dist = 20
            target_x = randint(int(pos.x - dist*radius), int(pos.x + dist*radius))
            target_y = randint(int(pos.y - dist*radius), int(pos.y + dist*radius))
            
            if select == 0:
                return WalkAction(target_x, target_y)
            else:
                return RunAction(target_x, target_y)
        elif select == 2:
            return IdleAction(randint(20, 80))
        elif select == 3:
            return RotateAction(2*pi*random.random())
    
    def visionAlert(self, creature, other):
        pass
        """
        if other.shape.radius < creature.shape.radius:
            creature._action = creature.ACTION_TYPE.chase
            creature._target_creature = creature
            creature._target = creature._target_creature.body.position
        """
    
    def visionResourceAlert(self, creature, resource):
        
        if creature.shape.radius < 4*resource.shape.radius:
            creature.pushBehaviour(EatingBehaviour(resource))
    
    def soundAlert(self, creature, x, y):
        return None
        pos = creature.body.position
        
        return RotateAction(atan2(y - pos.y, x - pos.x))

class EatingBehaviour(BasicBehaviour):
    
    def __init__(self, resource):
        super().__init__()
        
        self._resource = resource
    
    def selectAction(self, creature):
        
        if creature.eating is False:
            
            print('here')
        
            if 3*creature.headPosition.get_distance(self._resource.body.position) < creature.shape.radius:
                creature.popBehaviour()
        
        pos = self._resource.body.position
        return RunAction(pos.x, pos.y, GoToPointAction.BODY_PART.head)
    
    @staticmethod
    def _resource_squared_distance(creature, resource):
        
        c_pos = creature.body.position
        r_pos = resource.body.position
        
        return (c_pos.x - r_pos.x)**2 + (c_pos.y - r_pos.y)**2
    
    def visionResourceAlert(self, creature, resource):
        
        if self._resource_squared_distance(creature, resource) < self._resource_squared_distance(creature, self._resource):
            creature.swapBehaviour(EatingBehaviour(resource))

class Painter(object):
    
    def __init__(self, screen, multiplier):
        
        self._screen = screen
        self._mul = multiplier
    
    def drawCircle(self, color, center, radius, width=0):
        pygame.draw.circle(self._screen, color, (int(center[0]*self._mul), int(center[1]*self._mul)), int(radius*self._mul), width)
        
    def drawLine(self, color, start, end, width=1):
        pygame.draw.line(self._screen, color, (int(start[0]*self._mul), int(start[1]*self._mul)), (int(end[0]*self._mul), int(end[1]*self._mul)), width)
        
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
    
    class Object(object):
        
        def __init__(self, space, body, shape, x, y):
            
            shape.simulation_object = self
            
            body.position = x, y

            space.add(body, shape)
            self._shape = shape
        
        def destroy(self, space):
            space.remove(self.shape, self.body)
        
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
        def shapes(self):
            return self._shapes
    
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

        def __init__(self, space, x, y, structure, energy, parent=None):
            
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
            
            self._sound_sensor = Simulation.SoundSensor(self, 200)
            self._vision_sensor = Simulation.VisionSensor(self, 400, pi*(30)/180)
            
            self._is_eating = 0
            
            if parent is None:
                self._speed, self._attack, self._defense, self._eating_speed = ( random.random() for i in range(4) )
            else:
                self._speed, self._attack, self._defense = parent._speed, parent._attack, parent._defense
                self._mutate()
        
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
            
            print('Eating', energy_gained)
            
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
        
        def reproduce(self, sim):
            
            second_energy = self._energy//2
            self._energy -= second_energy
            
            second_structure = self._structure//2
            self._structure -= second_structure
            
            pos = self.body.position
            sim.newCreature(pos.x, pos.y, second_structure, second_energy, parent=self)
            
            self._update_self()
        
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
            
        @staticmethod
        def _mutate_single(val):
            new_val = val + 2*Simulation.Creature.MUTATION*(random.random() - .5)
            
            if new_val < 0: return 0
            if new_val > 1: return 1
            return new_val
        
        def _mutate(self):
            self._speed = self._mutate_single(self._speed)
            self._attack = self._mutate_single(self._attack)
            self._defense = self._mutate_single(self._attack)
        
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
        
        @property
        def eating(self):
            return self._is_eating > 0
        
        def act(self, simulation):
            
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
            
            energy_consume = abs(floor(speed*self.body.mass*factor*sqrt(self._speed)))//100 + 1
            
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
            
            color = (230*self._attack, 230*self._defense, 230*self._speed)
            
            super().draw(painter, color)
            
            pos = self.body.position
            radius = self.shape.radius
            angle = self.body.angle
            
            painter.drawLine((255, 255, 255), pos, (pos.x + radius*cos(angle), pos.y + radius*sin(angle)))
        
        def _consume_energy(self, qtd):
            
            if qtd < 0 or qtd > self._energy:
                return False
            
            self._energy -= qtd
            self._spent_resources += qtd
            
            return True
        
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
    
    def __init__(self):

        pygame.init()
        pygame.display.set_caption("Simulation")
        
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

        self._screen = pygame.display.set_mode((600, 600))
        self._clock = pygame.time.Clock()
        
        self._painter = Painter(self._screen, 0.3)

        self._creatures = []
        self._resources = []

        self._running = True
        
        for i in range(3):
            self.newCreature(500 + 150*i, 300 + 300*i, 500000 + 200000*i, 500000)
            
        for i in range(7):
            self.newResource(100 + 250*i, 700 + 250*sin(i), 500000, 0)
        
        #self.newCreature(200, 200, 50000, 50000)

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

    def _process_events(self):

        for event in pygame.event.get():
            if event.type == QUIT:
                self._running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self._running = False

    def newCreature(self, x, y, structure, energy, parent = None):
        
        creature = self.Creature(self._space, x, y, structure, energy, parent=parent)
        
        self._creatures.append(creature)
        
        return creature
    
    def newResource(self, x, y, ext_rsc, int_rsc):
    
        resource = self.Resource(self._space, x, y, ext_rsc, int_rsc)
        
        self._resources.append(resource)
        
        return resource

    def _clear_screen(self):

        self._screen.fill(THECOLORS["white"])

    def _draw_objects(self):
        
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

if __name__ == '__main__':
    game = Simulation()
    game.run()
