
from math import pi
import itertools

import pygame

# pylint: disable=no-name-in-module
from pygame.constants import (
    QUIT, KEYDOWN, K_ESCAPE, K_SPACE, K_p, MOUSEBUTTONUP, K_EQUALS, K_KP_PLUS,
    K_KP_MINUS, K_MINUS, KMOD_LCTRL, KMOD_RCTRL, K_a, K_s, K_d, K_w, K_LEFT,
    K_DOWN, K_RIGHT, K_UP, KEYUP, K_PAGEDOWN, K_PAGEUP, MOUSEBUTTONDOWN,
    MOUSEMOTION, K_DELETE
)
# pylint: enable=no-name-in-module

from ...simulation.collisiontypes import CREATURE_COLLISION_TYPE
from ...creatures.creature import Creature

from .painter import Painter

class Window:

    def __init__(self, simulation, screen_size, size, has_wall=True,
                 ticks_per_second=50):

        self.__use_wall = has_wall

        self.__simulation = simulation
        self.__lat_column_size = 300

        self._ticks = ticks_per_second

        self._size = screen_size

        self.__max_lat_column_y_offset = 0
        self.__cur_lat_column_y_offset = 0

        screen_size = (screen_size[0] + self.__lat_column_size, screen_size[1])

        pygame.display.init()
        pygame.font.init()

        self.__until_event = {}
        self.__events_happening = set()

        self._small_font = pygame.font.SysFont('Arial', 12, bold=True)
        self._medium_font = pygame.font.SysFont('Arial', 18, bold=True)
        pygame.display.set_caption("Simulation")

        self._screen = pygame.display.set_mode(screen_size)
        self._clock = pygame.time.Clock()

        self.__start_painter_mult = 300/size
        self._painter = Painter(self._screen, self.__start_painter_mult)

        self.__original_size = (self._size[0]/self.__start_painter_mult,
                                self._size[1]/self.__start_painter_mult)

        self._show_creature = None

        self.__grab_lateral_screen_point = None

        self._running = True
        self._paused = False

    def update(self):

        pygame.display.set_caption('Simulation')

        self.__processEvents()
        self._screen.fill((100, 100, 100) if self.__use_wall is True
                          else (255, 255, 255))
        self.__drawObjects()
        self.__drawSideInfo()
        pygame.display.flip()

        self._clock.tick(self._ticks)

    def run(self):

        while self._running:

            if self._paused is False:
                self.__simulation.step()

            self.update()

    def __processEvents(self):

        for event in pygame.event.get():
            if event.type == QUIT:
                self.quit()
            elif event.type == KEYDOWN:
                key = event.key
                if key == K_ESCAPE:
                    self._painter.offset = (0, 0)
                    self._painter.multiplier = self.__start_painter_mult
                elif key in (K_SPACE, K_p):
                    self._paused = not self._paused
                elif key in (K_a, K_LEFT):
                    self.__until_event[self.moveLeft] = 10
                elif key in (K_s, K_DOWN):
                    self.__until_event[self.moveDown] = 10
                elif key in (K_d, K_RIGHT):
                    self.__until_event[self.moveRight] = 10
                elif key in (K_w, K_UP):
                    self.__until_event[self.moveUp] = 10
                elif (key in (K_EQUALS, K_KP_PLUS)) and \
                    (pygame.key.get_mods() in (KMOD_LCTRL, KMOD_RCTRL)):

                    self.__until_event[self.zoomIn] = 10
                elif (key in (K_MINUS, K_KP_MINUS)) and \
                    (pygame.key.get_mods() in (KMOD_LCTRL, KMOD_RCTRL)):

                    self.__until_event[self.zoomOut] = 10
                elif key == K_PAGEDOWN:
                    self.__until_event[self.moveLateralColumnDown] = 10
                elif key == K_PAGEUP:
                    self.__until_event[self.moveLateralColumnUp] = 10
                elif key == K_DELETE:
                    if self._show_creature is not None:
                        self._show_creature.kill(self.__simulation)

            elif event.type == MOUSEBUTTONDOWN:

                screen_pos = pygame.mouse.get_pos()

                if screen_pos[0] > self._size[0]:
                    self.__grab_lateral_screen_point = screen_pos
                    continue

            elif event.type == MOUSEMOTION:

                if self.__grab_lateral_screen_point is not None:

                    new_mouse_pos = pygame.mouse.get_pos()

                    pos_y_diff = self.__grab_lateral_screen_point[1] - \
                        new_mouse_pos[1]

                    if pos_y_diff > 0:
                        self.moveLateralColumnDown(pos_y_diff)
                    else:
                        self.moveLateralColumnUp(-pos_y_diff)

                    self.__grab_lateral_screen_point = new_mouse_pos

            elif event.type == MOUSEBUTTONUP:

                if self.__grab_lateral_screen_point is not None:
                    self.__grab_lateral_screen_point = None
                    continue

                pos = self._painter.mapPointFromScreen(pygame.mouse.get_pos())

                mask = (1 << (CREATURE_COLLISION_TYPE - 1))

                for creature in self.__simulation.creatures:
                    dist = creature.body.position.get_distance(pos)
                    if dist < creature.shape.radius:
                        clicked = creature
                        break
                else:
                    clicked = None

                if self._show_creature is not None:
                    self._show_creature.selected = False

                if clicked is None:
                    self._show_creature = None
                else:
                    self._show_creature = clicked.shape.simulation_object
                    self._show_creature.selected = True
            elif event.type == KEYUP:
                key = event.key
                if key in (K_EQUALS, K_KP_PLUS):
                    self.__removeEvent(self.zoomIn, apply_at_least_once=True)
                elif key in (K_MINUS, K_KP_MINUS):
                    self.__removeEvent(self.zoomOut, apply_at_least_once=True)
                elif key in (K_a, K_LEFT):
                    self.__removeEvent(self.moveLeft, apply_at_least_once=True)
                elif key in (K_s, K_DOWN):
                    self.__removeEvent(self.moveDown, apply_at_least_once=True)
                elif key in (K_d, K_RIGHT):
                    self.__removeEvent(self.moveRight, apply_at_least_once=True)
                elif key in (K_w, K_UP):
                    self.__removeEvent(self.moveUp, apply_at_least_once=True)
                elif key == K_PAGEDOWN:
                    self.__removeEvent(self.moveLateralColumnDown,
                                       apply_at_least_once=True)
                elif key == K_PAGEUP:
                    self.__removeEvent(self.moveLateralColumnUp,
                                       apply_at_least_once=True)

        events_to_remove = []
        for event, turns_until_event in self.__until_event.items():
            if turns_until_event <= 0:
                self.__events_happening.add(event)
                events_to_remove.append(event)
            else:
                self.__until_event[event] = turns_until_event - 1

        for event in events_to_remove:
            del self.__until_event[event]

        for event in self.__events_happening:
            event()

    def __removeEvent(self, event, apply_at_least_once=False):

        try:
            self.__events_happening.remove(event)
        except KeyError:
            self.__until_event.pop(event, None)
            if apply_at_least_once:
                event()

    def __drawSideInfo(self):

        materials = self.__simulation.creature_config.materials.materials
        screen_size = pygame.display.get_surface().get_size()
        start_point = screen_size[0] - self.__lat_column_size, 0
        creature = self._show_creature
        if creature is not None and creature.destroyed:
            creature = self._show_creature = None

        pygame.draw.rect(self._screen, (200, 200, 200),
                         (start_point[0], start_point[1],
                          self.__lat_column_size, screen_size[1]))

        textsurface = self._medium_font.render('Environment', False,
                                               (0, 0, 0))
        text_size, _ = textsurface.get_size()

        self._screen.blit(
            textsurface,
            (start_point[0] + (self.__lat_column_size - text_size)/2,
             start_point[1] + 20 - self.__cur_lat_column_y_offset))

        creature_total_mass = 0
        for creature in self.__simulation.creatures:
            creature_total_mass += creature.body.mass

        creature_total_mass = round(creature_total_mass)

        resources_total_mass = 0
        non_alocated_total_mass = 0
        for resource in self.__simulation.plant_resources:
            resources_total_mass += resource.external_resources
            non_alocated_total_mass += resource.internal_resources

        resources_total_mass = round(
            resources_total_mass*Creature.MASS_MULTIPLIER)
        non_alocated_total_mass = round(
            non_alocated_total_mass*Creature.MASS_MULTIPLIER)

        meat_total_mass = 0
        for meat in self.__simulation.meat_resources:
            meat_total_mass += meat.materials_mass

        meat_total_mass = round(meat_total_mass)

        to_write_list = (
            ('Creatures Total Mass', str(creature_total_mass)),
            ('Plants Total Mass', str(resources_total_mass)),
            ('Meat Total Mass', str(meat_total_mass)),
            ('Non Allocated Mass', str(non_alocated_total_mass)),
            ('Total Mass', str(creature_total_mass +
                               resources_total_mass +
                               non_alocated_total_mass +
                               meat_total_mass))
        )

        start_y = start_point[1] + 50 - self.__cur_lat_column_y_offset
        last_y_end = self.__writeText(to_write_list, start_point, start_y)

        if creature is None:
            creature_number_text = '-'
        else:
            creature_number_text = 'Creature %d' % creature.id_

        textsurface = self._medium_font.render(creature_number_text, False,
                                               (0, 0, 0))
        text_size, _ = textsurface.get_size()

        self._screen.blit(
            textsurface,
            (start_point[0] + (self.__lat_column_size - text_size)/2,
             last_y_end + 10))

        labels = ('Species', 'Structure', 'Energy', 'Weight', 'Radius',
                  'Position', 'Speed', 'Vision Dist.', 'Vision Angle')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            values = (creature.species.name, creature.structure,
                      creature.energy, creature.body.mass,
                      creature.shape.radius,
                      ', '.join('%i' % i for i in creature.body.position),
                      creature.currentspeed, creature.currentvisiondistance,
                      180*creature.currentvisionangle/pi)
            values = (val if isinstance(val, str) else
                      '%d' % val if isinstance(val, int) else
                      '%0.2f' % val if val < 10000 else '%.2E' % val
                      for val in values)

        to_write_list = zip(labels, values)

        start_y = last_y_end + 40
        last_y_end = self.__writeText(to_write_list, start_point, start_y)

        if creature is not None:
            materials_text = (
                (material.short_name, '%.1E' % creature.getMaterial(material))
                for material in materials.values()
            )

            last_y_end = self.__writeText(materials_text, start_point,
                                          last_y_end + 10, double=True)

        textsurface = self._medium_font.render('Genes', False, (0, 0, 0))
        text_size, _ = textsurface.get_size()

        materials_text_offset = -self.__cur_lat_column_y_offset + 20*(
            1 + len(self.__simulation.creature_config.materials)//2)
        self._screen.blit(
            textsurface,
            (start_point[0] + (self.__lat_column_size - text_size)/2,
             last_y_end + 10))

        labels = ('Speed', 'Eating Speed', 'Vision Dist.', 'Vision Angle')

        if creature is None:
            values = ('-' for i in range(len(labels)))
        else:
            pvalues = (creature.getTrait('speed'),
                       creature.getTrait('eatingspeed'),
                       creature.getTrait('visiondistance'),
                       creature.getTrait('visionangle'))

            values = (val if isinstance(val, str) else '%.1f%%' % (100*val)
                      for val in pvalues)

        to_write_list = zip(labels, values)

        start_y = self.__writeText(to_write_list, start_point,
                                   last_y_end + 40)

        if creature is not None:
            rules_text = (
                (str(rule), '%d%%' %
                 creature.getTrait(f'{rule.name}_convertionrate'))
                for rule in self.__simulation.creature_config.material_rules)

            self.__max_lat_column_y_offset = self.__writeText(
                rules_text, start_point, start_y)

            childqtd_text = []
            childqtd_min_to_reproduce_text = []

            for material_name, material in materials.items():

                if material.ignore_for_child:
                    continue

                if len(material_name) > 15:
                    material_label = material.short_name
                else:
                    material_label = material_name

                child_qtd = creature.getTrait(f'{material_name}_childqtd')
                min_to_reproduce = creature.getTrait(
                    f'{material_name}_childqtd_min_to_reproduce')

                childqtd_text.append(
                    (f'Child {material_label}', '%.2E' % child_qtd))
                childqtd_min_to_reproduce_text.append(
                    (f'{material_label} to reproduce',
                     '%.2E' % (min_to_reproduce*child_qtd)))

            start_y = self.__writeText(
                childqtd_text, start_point, self.__max_lat_column_y_offset)
            start_y = self.__writeText(
                childqtd_min_to_reproduce_text, start_point, start_y)

            self.__max_lat_column_y_offset = self.__writeText(
                rules_text, start_point, start_y)
        else:
            self.__max_lat_column_y_offset = start_y

        self.__max_lat_column_y_offset += (
            self.__cur_lat_column_y_offset - screen_size[1] + 30
        )

        if self.__max_lat_column_y_offset < 0:
            self.__max_lat_column_y_offset = 0

        if self.__cur_lat_column_y_offset > self.__max_lat_column_y_offset:
            self.__cur_lat_column_y_offset = self.__max_lat_column_y_offset

    def __writeText(self, to_write_list, start_point, start_y, double=False):

        x_offset = 0

        column_size = self.__lat_column_size
        if double:
            column_size /= 2

        for prop, val_str in to_write_list:

            textsurface = self._small_font.render(prop + ':', False, (0, 0, 0))
            self._screen.blit(textsurface,
                              (start_point[0] + 10 + x_offset,
                               start_point[1] + start_y))

            textsurface = self._small_font.render(val_str, False, (0, 0, 0))
            text_size, _ = textsurface.get_size()
            val_x = x_offset + start_point[0] + column_size - 20 - text_size
            self._screen.blit(textsurface, (val_x, start_point[1] + start_y))

            if double and x_offset == 0:
                x_offset = column_size
                continue
            else:
                start_y += 20
                x_offset = 0

        return start_y

    def __drawObjects(self):

        self._painter.drawRect((255, 255, 255), (0, 0), self.__original_size)

        for obj in itertools.chain(self.__simulation.resources,
                                   self.__simulation.creatures):
            obj.draw(self._painter)

    def zoomIn(self):
        self._painter.multiplier *= 1.05

    def zoomOut(self):
        self._painter.multiplier /= 1.05

    def __moveOffset(self):
        return 5/self._painter.multiplier

    def moveUp(self):
        self._painter.yoffset += self.__moveOffset()

    def moveDown(self):
        self._painter.yoffset -= self.__moveOffset()

    def moveRight(self):
        self._painter.xoffset -= self.__moveOffset()

    def moveLeft(self):
        self._painter.xoffset += self.__moveOffset()

    def moveLateralColumnUp(self, quantity=10):
        self.__cur_lat_column_y_offset -= quantity
        if self.__cur_lat_column_y_offset < 0:
            self.__cur_lat_column_y_offset = 0

    def quit(self):
        self._running = False

    def moveLateralColumnDown(self, quantity=10):
        self.__cur_lat_column_y_offset += quantity
        if self.__cur_lat_column_y_offset > self.__max_lat_column_y_offset:
            self.__cur_lat_column_y_offset = self.__max_lat_column_y_offset
