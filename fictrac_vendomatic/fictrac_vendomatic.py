from __future__ import print_function
import sys
import time
import redis
import json
import threading
import Queue
import math
import numpy
import matplotlib.pyplot as plt
import atexit
from trigger_device import TriggerDevice


class FicTracVendomatic:

    """

    Notes: 

        stim_inner_radius             - inner radius for stim - fly need to enter this trigger stimuls pulses
        stim_outer_radius             - outer radius for stim - protocol not reset if fly stays inside circle 
        stim_startup_delay            - delay before stim can start
        stim_startup_path_length      - minimum path length before stim can start
        stim_threshold_distance       - distance threshold for triggering stim (measured over threshold window)
        stim_threshold_window         - time window over which threhold distance is measured
        stim_pulse_on_window          - time window for pulse on
        tim_pulse_off_window          - time window for pulse off (always off for at least this long after being on)
        protocol_reset_window         - time after which protocol reset if fly outside of outer radius

    """

    default_param = {
            'redis_channel': 'fictrac',
            'loop_dt': 0.001,
            'ball_radius': 1.0,
            'display_xlim': (-20,20),
            'display_ylim': (-20,20),
            'path_color': 'b',
            'path_window' : 60.0*60.0*10.0,
            'stim_inner_color': 'r',
            'stim_outer_color': 'g',
            'stim_inner_radius': 2.0,   
            'stim_outer_radius': 4.0,   
            'stim_startup_delay': 5.0, 
            'stim_startup_path_length' : 5.0,
            'stim_threshold_distance' : 4.0,
            'stim_threshold_window' : 5.0, 
            'stim_pulse_on_window':  1.0,
            'stim_pulse_off_window': 9.0,
            'protocol_reset_window': 15.0,
            'trigger_device_port': '/dev/ttyUSB0',
            }


    def __init__(self,param = default_param):

        self.param = param
        self.data = FlyData(self.param)
        self.display = BasicDisplay(self.param)
        self.protocol = Protocol(self.param)
        self.reset()

        self.trigger_device = TriggerDevice(self.param['trigger_device_port'])
        self.trigger_device.set_low()

        # Setup message queue, redis and worker thread
        self.message_queue = Queue.Queue()
        self.redis_client = redis.StrictRedis()
        self.redis_pubsub = self.redis_client.pubsub()
        self.redis_pubsub.subscribe(self.param['redis_channel'])
        self.redis_worker = threading.Thread(target=self.message_reciever)
        self.redis_worker.daemon = True
        self.redis_worker.start()

    def reset(self):
        self.data.reset()
        self.protocol.reset()
        self.display.reset()
        self.time_start = time.time()
        self.time_now = time.time()

    @property
    def time_elapsed(self):
        return self.time_now - self.time_start

    def run(self):

        while True:
            # Pull latest redis message from queue

            while self.message_queue.qsize() > 0:

                self.time_now = time.time()
                have_new_message = False 
                message = ''

                try:
                    message = self.message_queue.get(False)
                    have_new_message = True
                except Queue.Empty: 
                    pass 

                if have_new_message: 
                    self.message_switchyard(message)

                self.protocol.update(self.time_elapsed, self.data)
                if self.protocol.active: 
                    self.display.set_stim_center(self.protocol.stim_x, self.protocol.stim_y) 
                    self.display.set_stim_enabled(True)
                else:
                    self.display.set_stim_enabled(False)

            if self.protocol.pulse_on:
                self.trigger_device.set_high()
            else:
                self.trigger_device.set_low()
        
            self.display.update(self.data)


    def message_switchyard(self,message):
        if message['type'] == 'reset':
            self.on_reset_message(message)
        elif message['type'] == 'data':
            self.on_data_message(message)
        else:
            flush_print('unkwon message type')

    def on_reset_message(self,message):
        #flush_print('reset')
        self.reset()

    def on_data_message(self,message):

        # Adjust position for ball size
        message['posx'] *= self.param['ball_radius']
        message['posy'] *= self.param['ball_radius']
        message['velx'] *= self.param['ball_radius']
        message['vely'] *= self.param['ball_radius']

        self.data.add(self.time_elapsed, message)

        flush_print('time          = {0:1.3f}'.format(self.time_elapsed))
        flush_print('frame         = {0:1.3f}'.format(self.time_elapsed))
        flush_print('pos x         = {0:1.3f}'.format(self.data.posx))
        flush_print('pos y         = {0:1.3f}'.format(self.data.posy))
        flush_print('path_len      = {0:1.3f}'.format(self.data.path_len))
        flush_print('ready         = {0}'.format(self.protocol.ready))
        flush_print('win_dist      = {0:1.3f}'.format(self.protocol.get_window_distance(self.time_elapsed,self.data)))
        if self.protocol.ready:
            flush_print('active        = {0}'.format(self.protocol.active))
        else:
            flush_print('active        = --- ')
        if self.protocol.ready and self.protocol.active:
            flush_print('outside_dt    = {0:1.3f}'.format(self.time_elapsed - self.protocol.time_outer_circle))
            flush_print('pulse_on      = {0}'.format(self.protocol.pulse_on))
            flush_print('pulse_on_dt   = {0:1.3f}'.format(self.time_elapsed - self.protocol.time_pulse_on))
        else:
            flush_print('outer_dt      = --- ')
            flush_print('pulse_on      = --- ')
            flush_print('pulse_on_dt   = --- ')
        flush_print()


    def message_reciever(self):
        """
        Called in separate thread - puts new messages on 
        """
        for item in self.redis_pubsub.listen():
            if item['data'] == 1:
                continue
            message = json.loads(item['data'])
            self.message_queue.put(message)

    def clean_up(self):
        if self.trigger_device.isOpen():
            self.trigger_device.set_low()


class Protocol:

    def __init__(self, param):
        self.param = param
        self.reset() # set initial values

    def reset(self):

        self.ready = False
        self.active = False
        self.pulse_on = False

        self.is_first_update = True
        self.is_first_pulse = True 

        self.time_start = 0.0
        self.time_ready = 0.0
        self.time_active = 0.0
        self.time_pulse_on = 0.0
        self.time_pulse_off = 0.0
        self.time_outer_circle = 0.0

        self.stim_x = 0.0
        self.stim_y = 0.0


    def update(self,t,data):
        if self.is_first_update:
            self.time_start = t
            self.is_first_update = False
        self.check_for_ready(t,data)
        self.check_for_activation(t,data)
        self.check_for_pulse_on(t,data)
        self.check_for_pulse_off(t,data)
        self.check_for_reset(t,data)

    def check_for_ready(self,t,data):
        """
        Check time and path length to see if they meet ready conditions.
        """
        if not self.ready:
            delay_test = t - self.time_start > self.param['stim_startup_delay']
            path_test  = data.path_len > self.param['stim_startup_path_length']
            self.ready = path_test and delay_test
            if self.ready:
                self.time_ready = t

    def check_for_activation(self,t,data):
        if not self.ready: 
            return
        if self.active:
            return
        window_distance = self.get_window_distance(t,data)
        if window_distance >= self.param['stim_threshold_distance']:
            self.active = True
            self.stim_x = data.posx
            self.stim_y = data.posy
            self.time_active = t

    def check_for_pulse_on(self,t,data):
        if not self.ready:
            return
        if not self.active:
            return
        if self.pulse_on:
            return

        # Check if we are in refractory period for pulses
        min_time_to_next_pulse = self.time_pulse_on + self.param['stim_pulse_on_window'] + self.param['stim_pulse_off_window']
        if not self.is_first_pulse and  (t < min_time_to_next_pulse):
            return

        if self.is_inside_inner_circle(data):
            self.is_first_pulse = False
            self.pulse_on = True
            self.time_pulse_on = t

    def check_for_pulse_off(self,t,data):
        if not self.pulse_on:
            # Pulse is already off
            return
        if t > (self.time_pulse_on + self.param['stim_pulse_on_window']):
            self.pulse_on = False
            self.time_pulse_off

    def check_for_reset(self,t,data):
        if not self.active:
            return
        if self.is_inside_outer_circle(data):
            self.time_outer_circle = t
        if t > self.time_outer_circle + self.param['protocol_reset_window']:
            self.reset()

    def get_window_distance(self,t,data):
        n = len(data.time_list)-1
        done = False
        while not done: 
            test0 = (t - data.time_list[n]) >= self.param['stim_threshold_window']
            test1 = (data.time_list[n] - self.time_start) <= self.param['stim_startup_delay']
            if test0 or test1 or n==0:
                done = True
            else:
                n -= 1
        p = data.posx, data.posy
        q = data.posx_list[n], data.posy_list[n]
        return distance(p,q)


    def is_inside_inner_circle(self,data):
        value = is_inside_circle(
                data.posx, 
                data.posy, 
                self.stim_x, 
                self.stim_y, 
                self.param['stim_inner_radius']
                )
        return value

    def is_inside_outer_circle(self,data):
        value = is_inside_circle(
                data.posx, 
                data.posy, 
                self.stim_x, 
                self.stim_y, 
                self.param['stim_outer_radius']
                )
        return value


class FlyData:

    zero_data = {
            'frame': 0,
            'posx': 0.0, 
            'posy': 0.0, 
            'velx': 0.0, 
            'vely': 0.0,
            'heading': 0.0
            }

    def __init__(self,param):
        self.param = param
        self.reset() # Initialize member data
        
    def add(self,t, data):

        # Add new data points
        self.prev_data = self.curr_data
        self.curr_data = data
        self.time_list.append(t)
        self.posx_list.append(data['posx'])
        self.posy_list.append(data['posy'])
        if self.count >= 2:
            dx = self.curr_data['posx'] - self.prev_data['posx']
            dy = self.curr_data['posy'] - self.prev_data['posy']
            self.path_len += length(dx,dy)
        self.count+=1

        # Cull old data points
        while (t - self.time_list[0]) > self.param['path_window']:
            self.time_list.pop(0)
            self.posx_list.pop(0)
            self.posy_list.pop(0)


    @property
    def frame(self):
        return self.curr_data['frame']

    @property
    def posx(self):
        return self.curr_data['posx']

    @property
    def posy(self):
        return self.curr_data['posy']

    @property
    def velx(self):
        return self.curr_data['velx']

    @property
    def vely(self):
        return self.curr_data['vely']

    @property
    def heading(self):
        return self.curr_data['heading']

    def reset(self):
        self.count = 0
        self.curr_data = self.zero_data
        self.prev_data = self.zero_data
        self.time_list = []
        self.posx_list = []
        self.posy_list = []
        self.heading_list = []
        self.path_len = 0

    def reset_path_len(self):
        self.path_len = 0
    


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
    



# Utility functions
# --------------------------------------------------------------------------------------

def flush_print(*arg,**kwarg):
    print(*arg,**kwarg)
    sys.stdout.flush()

def is_inside_circle(x, y, circle_x, circle_y, radius): 
    return distance((x,y), (circle_x, circle_y)) <= radius

def distance(p,q):
    return length(q[0]-p[0], q[1]-p[1])

def length(x,y):
    return math.sqrt(x**2 + y**2)



# ---------------------------------------------------------------------------------------
if __name__ == '__main__':

    client = FicTracVendomatic()
    client.run()
