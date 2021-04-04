
from abc import ABC, abstractmethod
from math import sqrt, pi, atan2
from enum import Enum

from pymunk import Vec2d

class AbstractAction(ABC):

    @abstractmethod
    def doAction(self, creature):
        pass

class IdleAction(ABC):

    def __init__(self, time=0):
        super().__init__()

        self._time = time

    def doAction(self, _creature):

        if self._time <= 0:
            return None

        self._time -= 1

        return 0, 0

class GoToPointAction(AbstractAction):

    BODY_PART = Enum('BODY_PART', ('head', 'center'))

    def __init__(self, x, y, weight=1, target_body_part=BODY_PART.center):

        super().__init__()

        self._weight = weight
        self._point = Vec2d(x, y)
        self._target_body_part = target_body_part

    def doAction(self, creature):

        if self._target_body_part == GoToPointAction.BODY_PART.head:
            pos = creature.headposition
        else:
            pos = creature.body.position

        x_diff = pos.x - self._point.x
        y_diff = pos.y - self._point.y

        distance = sqrt(x_diff**2 + y_diff**2)

        if 4*distance < creature.shape.radius:
            return None

        speed_trait = creature.getTrait('speed')

        angle1 = creature.body.angle%(2*pi)
        angle2 = pi + atan2(y_diff, x_diff)%(2*pi)
        speed_factor = distance/((1 + speed_trait))

        angle_diff1 = abs(angle1 - angle2)
        angle_diff2 = 2*pi - abs(angle1 - angle2)

        angle_diff = min(angle_diff1, angle_diff2)

        if (angle1 > angle2) is (angle_diff1 < pi):
            angle_diff = -angle_diff

        if distance < creature.shape.radius and abs(angle_diff) > pi/2:
            return (-0.2, 0)

        velocity = creature.body.velocity
        current_speed = sqrt(velocity.x**2 + velocity.y**2)

        angle_factor = 200*angle_diff/(1 + 149*speed_trait)

        speed_angle_div = 100*(1 + speed_trait)*abs(angle_diff)
        speed_factor = speed_factor/(0.1 + speed_angle_div + current_speed)

        if speed_factor > 1:
            speed_factor = 1

        if angle_factor > 1:
            angle_factor = 1
        elif angle_factor < -1:
            angle_factor = -1

        return speed_factor*self._weight, angle_factor

class WalkAction(GoToPointAction):

    def __init__(self, x, y, target_body_part=GoToPointAction.BODY_PART.center):
        super().__init__(x, y, weight=0.4, target_body_part=target_body_part)

class RunAction(GoToPointAction):

    def __init__(self, x, y, target_body_part=GoToPointAction.BODY_PART.center):
        super().__init__(x, y, weight=0.8, target_body_part=target_body_part)

class FastRunAction(GoToPointAction):

    def __init__(self, x, y, target_body_part=GoToPointAction.BODY_PART.center):
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
        angular_velocity_abs = abs(creature.body.angular_velocity)

        if angular_velocity_abs > 1.5:
            return 0, 0

        if abs(angle_diff) < 0.08 and angular_velocity_abs < 0.03:
            return None

        if (angle1 > angle2) is (angle_diff1 < pi):
            angle_diff = -angle_diff

        return 0, angle_diff
