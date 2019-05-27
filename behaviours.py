
from abc import ABC, abstractmethod

import random
from random import randint

from math import pi

from actions import IdleAction, WalkAction, RunAction, FastRunAction, RotateAction

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

class DefaultVisionSoundReactionBehaviour(AbstractBehaviour):
    
    def __init__(self):
        super().__init__()
    
    def visionAlert(self, creature, other):
        pass
    
    def visionResourceAlert(self, creature, resource):
        
        if creature.shape.radius < 4*resource.shape.radius:
            creature.pushBehaviour(EatingBehaviour(resource))
    
    def soundAlert(self, creature, x, y):
        return None
        pos = creature.body.position
        
        return RotateAction(atan2(y - pos.y, x - pos.x))

class BasicBehaviour(DefaultVisionSoundReactionBehaviour):
    
    def __init__(self, idle_priority, walk_priority, run_priority, fast_run_priority, rotate_priority):
        super().__init__()
        
        self._select_priorities = (walk_priority, run_priority, idle_priority, rotate_priority, fast_run_priority)
        self._priority_sum = sum(self._select_priorities)
    
    def selectAction(self, creature):

        value = randint(0, self._priority_sum - 1)
        
        select = 0
        for p in self._select_priorities:
            if value < p:
                break
            
            value -= p
            select += 1
        
        if select == 0 or select == 1 or select == 4:
            pos = creature.body.position
            radius = creature.shape.radius
            
            dist = 20
            target_x = randint(int(pos.x - dist*radius), int(pos.x + dist*radius))
            target_y = randint(int(pos.y - dist*radius), int(pos.y + dist*radius))
            
            if select == 0:
                return WalkAction(target_x, target_y)
            elif select == 1:
                return RunAction(target_x, target_y)
            
            return FastRunAction(target_x, target_y)
        
        elif select == 2:
            return IdleAction(randint(20, 80))
        elif select == 3:
            return RotateAction(2*pi*random.random())

class EatingBehaviour(DefaultVisionSoundReactionBehaviour):
    
    def __init__(self, resource):
        super().__init__()
        
        self._resource = resource
    
    def selectAction(self, creature):
        
        if creature.eating is False:
        
            if 3*creature.headPosition.get_distance(self._resource.body.position) < creature.shape.radius:
                creature.popBehaviour()
        
        pos = self._resource.body.position
        return RunAction(pos.x, pos.y, RunAction.BODY_PART.head)
    
    @staticmethod
    def _resource_squared_distance(creature, resource):
        
        c_pos = creature.body.position
        r_pos = resource.body.position
        
        return (c_pos.x - r_pos.x)**2 + (c_pos.y - r_pos.y)**2
    
    def visionResourceAlert(self, creature, resource):
        
        if self._resource_squared_distance(creature, resource) < self._resource_squared_distance(creature, self._resource):
            creature.swapBehaviour(EatingBehaviour(resource))