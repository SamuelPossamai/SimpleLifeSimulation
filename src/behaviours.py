
from abc import ABC, abstractmethod

import random
from random import randint

from math import pi, inf

from .actions import (
    IdleAction, WalkAction, RunAction, FastRunAction, RotateAction
)

class AbstractBehaviour(ABC):

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
    def soundAlert(self, creature, x_pos, y_pos):
        pass

class DefaultVisionSoundReactionBehaviour(AbstractBehaviour): # pylint: disable=abstract-method

    def visionAlert(self, creature, other):
        return None

    def visionResourceAlert(self, creature, resource): # pylint: disable=useless-return

        if creature.shape.radius < 4*resource.shape.radius:
            creature.pushBehaviour(EatingBehaviour(resource))

        return None

    def soundAlert(self, creature, x_pos, y_pos):
        return None

        #pos = creature.body.position

        #return RotateAction(atan2(y - pos.y, x - pos.x))

class BasicBehaviour(DefaultVisionSoundReactionBehaviour):

    def __init__(self, idle_priority, walk_priority, run_priority,
                 fast_run_priority, rotate_priority):
        super().__init__()

        self._select_priorities = (walk_priority, run_priority, idle_priority,
                                   rotate_priority, fast_run_priority)
        self._priority_sum = sum(self._select_priorities)

    def selectAction(self, creature):

        if creature.eating:
            creature.pushBehaviour(EatingBehaviour())
            return None

        value = randint(0, self._priority_sum - 1)

        select = 0
        for priority in self._select_priorities:
            if value < priority:
                break

            value -= priority
            select += 1

        if select in (0, 1, 4):
            pos = creature.body.position
            radius = creature.shape.radius

            dist = 20
            target_x = randint(int(pos.x - dist*radius),
                               int(pos.x + dist*radius))
            target_y = randint(int(pos.y - dist*radius),
                               int(pos.y + dist*radius))

            if select == 0:
                return WalkAction(target_x, target_y)

            if select == 1:
                return RunAction(target_x, target_y)

            return FastRunAction(target_x, target_y)

        if select == 2:
            return IdleAction(randint(20, 80))

        if select == 3:
            return RotateAction(2*pi*random.random())

        return None

class EatingBehaviour(DefaultVisionSoundReactionBehaviour):

    def __init__(self, resource=None):
        super().__init__()

        self._resource = resource

    def selectAction(self, creature):

        if creature.eating is False:

            if self._resource is None:
                creature.popBehaviour()
                return None

            resource_distance = creature.headposition.get_distance(
                self._resource.body.position)
            if 3*resource_distance < creature.shape.radius:
                creature.popBehaviour()
                return None

            pos = self._resource.body.position
            return RunAction(pos.x, pos.y, RunAction.BODY_PART.head)

        return IdleAction(10)

    @staticmethod
    def _resourceSquaredDistance(creature, resource):

        if resource is None or resource.shape.radius == 0:
            return inf

        c_pos = creature.body.position
        r_pos = resource.body.position

        return (c_pos.x - r_pos.x)**2 + (c_pos.y - r_pos.y)**2

    def visionResourceAlert(self, creature, resource): # pylint: disable=useless-return

        if self._resourceSquaredDistance(creature, resource) < \
            self._resourceSquaredDistance(creature, self._resource):

            creature.swapBehaviour(EatingBehaviour(resource))

        return None
