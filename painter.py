
from math import cos, sin

import pygame

class Painter:

    def __init__(self, screen, multiplier):

        self._screen = screen
        self._mul = multiplier

    def drawCircle(self, color, center, radius, width=0):
        pygame.draw.circle(self._screen, color,
                           (int(center[0]*self._mul), int(center[1]*self._mul)),
                           int(radius*self._mul), width)

    def drawLine(self, color, start, end, width=1):
        pygame.draw.line(self._screen, color,
                         (int(start[0]*self._mul), int(start[1]*self._mul)),
                         (int(end[0]*self._mul), int(end[1]*self._mul)), width)

    # TODO: implement width
    def drawArc(self, color, center, radius, angle, open_angle, width=None):
        del width

        radius *= self._mul
        radius = int(radius)

        center = (int(center[0]*self._mul), int(center[1]*self._mul))

        points = [center]

        point_count = int(10*open_angle) + 2

        cur_angle = open_angle/2 + angle
        angle_diff = open_angle/(point_count-1)
        for _ in range(point_count):

            pos = (center[0] + radius*cos(cur_angle),
                   center[1] + radius*sin(cur_angle))
            points.append(pos)
            cur_angle -= angle_diff

        pygame.draw.polygon(self._screen, color, points)

    def mapPointToScreen(self, point):
        return (int(point[0]*self._mul), int(point[1]*self._mul))

    def mapPointFromScreen(self, point):
        return (point[0]/self._mul, point[1]/self._mul)

    @property
    def multiplier(self):
        return self._mul

    @multiplier.setter
    def multiplier(self, mul):
        self._mul = mul
