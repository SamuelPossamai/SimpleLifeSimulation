
import itertools

from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Ellipse
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window as KivyWindow

from .painter import Painter

class Window(App):

    def __init__(self, simulation, screen_size, size, has_wall=True,
                 ticks_per_second=50):
        super().__init__()

        self.__simulation = simulation

        Clock.schedule_interval(self.step, 1/ticks_per_second)

        self.__painter = Painter(300/size)

    def step(self, _dt):
        self.__simulation.step()

        self.__widget.canvas.clear()

        with self.__widget.canvas:

            for obj in itertools.chain(self.__simulation.resources,
                                       self.__simulation.creatures):
                obj.draw(self.__painter)

    def build(self):

        KivyWindow.clearcolor = (1, 1, 1, 1)

        self.__widget = Widget()

        layout = BoxLayout(size_hint=(1, None), height=50)

        root = BoxLayout(orientation='vertical')
        root.add_widget(self.__widget)
        root.add_widget(layout)

        return root
