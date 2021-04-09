
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Ellipse
from kivy.app import App
from kivy.clock import Clock

class Window(App):

    def __init__(self, simulation, screen_size, size, has_wall=True,
                 ticks_per_second=50):
        super().__init__()

        self.__simulation = simulation

        Clock.schedule_interval(self.step, 1/ticks_per_second)

    def step(self, _dt):
        self.__simulation.step()

        self.__widget.canvas.clear()

        with self.__widget.canvas:

            for creature in self.__simulation.creatures:
                Color(0, 0, 255, mode='rgb')
                Ellipse(pos=creature.body.position,
                        size=(2*creature.shape.radius, 2*creature.shape.radius))

            for resource in self.__simulation.resources:
                Color(0, 255, 0, mode='rgb')
                Ellipse(pos=resource.body.position,
                        size=(2*resource.shape.radius, 2*resource.shape.radius))

    def add_rects(self, label, widget, count, *largs):
        label.text = str(int(label.text) + count)
        with widget.canvas:
            for x in range(count):
                Color(r(), 1, 1, mode='hsv')
                Circle(pos=(r() * widget.width + widget.x,
                               r() * widget.height + widget.y), size=(20, 20))

    def double_rects(self, label, widget, *largs):
        count = int(label.text)
        self.add_rects(label, widget, count, *largs)

    def reset_rects(self, label, widget, *largs):
        label.text = '0'


    def build(self):

        self.__widget = Widget()

        layout = BoxLayout(size_hint=(1, None), height=50)

        root = BoxLayout(orientation='vertical')
        root.add_widget(self.__widget)
        root.add_widget(layout)

        return root
