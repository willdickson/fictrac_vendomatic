from __future__ import print_function

import sys
import time
import redis
import json
import threading
import Queue
import math
import atexit

import utils
from fly_data import FlyData
from trigger_device import TriggerDevice
from protocol import Protocol
from basic_display import BasicDisplay


class FicTracVendomatic:

    """
    Implements the vendomatic experiments. Receives position and heading data from 
    Fictrac and Triggers laser pulses (via USB/Serial trigger device) based fly's 
    position the fictitious arena. The stimulus region and various timings are determined
    via the experimental protocol and defined in by the Protocol class in protocol.py. 

    See protocol.py for a description and  summary of the relevant parameters.
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
            utils.flush_print('unkwon message type')

    def on_reset_message(self,message):
        #utils.flush_print('reset')
        self.reset()

    def on_data_message(self,message):

        # Adjust position for ball size
        message['posx'] *= self.param['ball_radius']
        message['posy'] *= self.param['ball_radius']
        message['velx'] *= self.param['ball_radius']
        message['vely'] *= self.param['ball_radius']

        self.data.add(self.time_elapsed, message)

        utils.flush_print('time          = {0:1.3f}'.format(self.time_elapsed))
        utils.flush_print('frame         = {0:1.3f}'.format(self.time_elapsed))
        utils.flush_print('pos x         = {0:1.3f}'.format(self.data.posx))
        utils.flush_print('pos y         = {0:1.3f}'.format(self.data.posy))
        utils.flush_print('path_len      = {0:1.3f}'.format(self.data.path_len))
        utils.flush_print('ready         = {0}'.format(self.protocol.ready))
        utils.flush_print('win_dist      = {0:1.3f}'.format(self.protocol.get_window_distance(self.time_elapsed,self.data)))
        if self.protocol.ready:
            utils.flush_print('active        = {0}'.format(self.protocol.active))
        else:
            utils.flush_print('active        = --- ')
        if self.protocol.ready and self.protocol.active:
            utils.flush_print('outside_dt    = {0:1.3f}'.format(self.time_elapsed - self.protocol.time_outer_circle))
            utils.flush_print('pulse_on      = {0}'.format(self.protocol.pulse_on))
            utils.flush_print('pulse_on_dt   = {0:1.3f}'.format(self.time_elapsed - self.protocol.time_pulse_on))
        else:
            utils.flush_print('outer_dt      = --- ')
            utils.flush_print('pulse_on      = --- ')
            utils.flush_print('pulse_on_dt   = --- ')
        utils.flush_print()


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




