
from math import cos, sin

import pygame

class Painter:

    def __init__(self, screen, multiplier):

        self.__screen = screen
        self.__mul = multiplier
        self.__xoff = 0
        self.__yoff = 0

    def drawCircle(self, color, center, radius, width=0):
        pygame.draw.circle(self.__screen, color,
                           self.mapPointToScreen(center),
                           int(radius*self.__mul), width)

    def drawLine(self, color, start, end, width=1):
        pygame.draw.line(self.__screen, color,
                         self.mapPointToScreen(start),
                         self.mapPointToScreen(end),
                         width)

    def drawRect(self, color, start, end, width=0):
        x_start, y_start = self.mapPointToScreen(start)
        x_end, y_end = self.mapPointToScreen(end)
        pygame.draw.rect(self.__screen, color,
                         (x_start, y_start, x_end - x_start, y_end - y_start),
                         width)

    def drawArc(self, color, center, radius, angle, open_angle, width=None):

        radius *= self.__mul
        radius = int(radius)

        center = self.mapPointToScreen(center)

        points = [center]

        point_count = int(10*open_angle) + 2

        cur_angle = open_angle/2 + angle
        angle_diff = open_angle/(point_count-1)
        for _ in range(point_count):

            pos = (center[0] + radius*cos(cur_angle),
                   center[1] + radius*sin(cur_angle))
            points.append(pos)
            cur_angle -= angle_diff

        pygame.draw.polygon(self.__screen, color, points, width)

    def mapPointToScreen(self, point):
        return (int((point[0] + self.__xoff)*self.__mul),
                int((point[1] + self.__yoff)*self.__mul))

    def mapPointFromScreen(self, point):
        return (point[0]/self.__mul - self.__xoff,
                point[1]/self.__mul - self.__yoff)

    @property
    def multiplier(self):
        return self.__mul

    @multiplier.setter
    def multiplier(self, mul):
        self.__mul = mul

    @property
    def xoffset(self):
        return self.__xoff

    @xoffset.setter
    def xoffset(self, new_val):
        self.__xoff = new_val

    @property
    def yoffset(self):
        return self.__yoff

    @yoffset.setter
    def yoffset(self, new_val):
        self.__yoff = new_val

    @property
    def offset(self):
        return (self.__xoff, self.__yoff)

    @offset.setter
    def offset(self, offset_val):
        self.__xoff, self.__yoff = offset_val
