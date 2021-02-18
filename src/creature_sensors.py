
from math import pi, cos, sin

import pymunk

from .collisiontypes import (
    SOUND_SENSOR_COLLISION_TYPE, VISION_SENSOR_COLLISION_TYPE
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
