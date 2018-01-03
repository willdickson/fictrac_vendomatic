import numpy
import matplotlib.pyplot as plt

class BasicDisplay:

    def __init__(self, param):

        self.path_color = param['path_color']
        self.xlim_init = param['display_xlim'] 
        self.ylim_init = param['display_ylim'] 

        self.stim_inner_color = param['stim_inner_color']
        self.stim_outer_color = param['stim_outer_color']
        self.stim_inner_radius = param['stim_inner_radius']
        self.stim_outer_radius = param['stim_outer_radius']

        self.margin = 2.0

        plt.ion()
        self.fig = plt.figure(1)
        self.ax = plt.subplot(111) 

        self.pos_line, = plt.plot([0,1], [0,1],self.path_color)
        self.pos_dot, = plt.plot([0], [1], self.path_color+'o',markersize=3.0)
        self.stim_inner_circ, = plt.plot([0,1], [0,1],self.stim_inner_color)
        self.stim_outer_circ, = plt.plot([0,1], [0,1],self.stim_outer_color)
        plt.axis('equal')
        plt.grid('on')
        plt.xlabel('x pos')
        plt.ylabel('y pos')
        plt.title("FicTrac's Vend-O-matic ")
        self.reset()

        self.fig.canvas.flush_events()

    def update(self,data):
        self.draw_stim_circ()
        self.draw_path(data)
        self.set_xylim(data)
        self.fig.canvas.flush_events()

    def draw_path(self,data):
        self.pos_line.set_xdata(data.posx_list)
        self.pos_line.set_ydata(data.posy_list)
        self.pos_dot.set_xdata([data.posx])
        self.pos_dot.set_ydata([data.posy])

    def set_xylim(self,data):
        self.xlim = data.posx + self.xlim_init[0], data.posx + self.xlim_init[1]
        self.ylim = data.posy + self.ylim_init[0], data.posy + self.ylim_init[1]
        self.ax.set_xlim(*self.xlim)
        self.ax.set_ylim(*self.ylim)

    def draw_stim_circ(self):
        line_list = [self.stim_inner_circ, self.stim_outer_circ]
        if self.stim_enabled:
            s = numpy.linspace(0,1,100)
            radius_list = [self.stim_inner_radius, self.stim_outer_radius]
            for radius, line in zip(radius_list, line_list):
                circ_vals_x = radius*numpy.cos(2.0*numpy.pi*s) + self.stim_x
                circ_vals_y = radius*numpy.sin(2.0*numpy.pi*s) + self.stim_y
                minx = self.stim_x - radius
                maxx = self.stim_x + radius
                miny = self.stim_y - radius
                maxy = self.stim_y + radius
                line.set_xdata(circ_vals_x)
                line.set_ydata(circ_vals_y)
        else:
            for line in line_list:
                line.set_xdata([])
                line.set_ydata([])
            
    def set_stim_center(self,x,y):
        self.stim_x = x
        self.stim_y = y

    def set_stim_enabled(self,value):
        self.stim_enabled = value

    def reset(self):
        self.is_first = True 
        self.stim_enabled = False
        self.stim_x = 0.0
        self.stim_y = 0.0
        self.xlim = self.xlim_init
        self.ylim = self.ylim_init
        self.pos_line.set_xdata([])
        self.pos_line.set_ydata([])
        self.pos_dot.set_xdata([])
        self.pos_dot.set_ydata([])
        self.stim_inner_circ.set_xdata([])
        self.stim_inner_circ.set_ydata([])
        self.stim_outer_circ.set_xdata([])
        self.stim_outer_circ.set_ydata([])
        self.ax.set_xlim(*self.xlim)
        self.ax.set_ylim(*self.ylim)
        self.fig.canvas.flush_events()
    
