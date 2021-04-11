
from math import pi

from kivy.graphics import Color, Ellipse

from ...simulation.simulationobject import SimulationObject

class Painter(SimulationObject.Painter):

    def __init__(self, multiplier):

        self.__mul = multiplier
        self.__xoff = 0
        self.__yoff = 0

    def drawCircle(self, color, center, radius, width=0):
        Color(*(component/255 for component in color), mode='rbg')

        diameter = 2*radius*self.__mul
        Ellipse(pos=self.mapPointToScreen(center),
                size=(diameter, diameter))

    def drawLine(self, color, start, end, width=1):
        Color(*(component/255 for component in color), mode='rbg')
        pygame.draw.line(points=[*self.mapPointToScreen(start),
                                 *self.mapPointToScreen(end)],
                         width=width)

    def drawRect(self, color, start, end, width=0):
        return
        x_start, y_start = self.mapPointToScreen(start)
        x_end, y_end = self.mapPointToScreen(end)
        pygame.draw.rect(self.__screen, color,
                         (x_start, y_start, x_end - x_start, y_end - y_start),
                         width)

    def drawArc(self, color, center, radius, angle, open_angle, width=None):

        angle *= -180/pi
        open_angle *= -180/pi

        angle += 90

        Color(*(component/255 for component in color), mode='rbg')

        diameter = 2*radius*self.__mul
        Ellipse(pos=self.mapPointToScreen(center),
                size=(diameter, diameter),
                angle_start=angle-open_angle/2, angle_end=angle+open_angle/2)

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
