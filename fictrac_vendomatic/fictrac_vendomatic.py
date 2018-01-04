from __future__ import print_function

import sys
import time
import redis
import json
import threading
import Queue
import math
import signal

import utils
from fly_data import FlyData
from trigger_device import TriggerDevice
from protocol import Protocol
from basic_display import BasicDisplay
from h5_logger import H5Logger


class FicTracVendomatic(object):

    """
    Implements the vendomatic experiments. Receives position and heading data from 
    Fictrac and Triggers laser pulses (via USB/Serial trigger device) based fly's 
    position the fictitious arena. The stimulus region and various timings are determined
    via the experimental protocol and defined in by the Protocol class in protocol.py. 

    See protocol.py for a description and  summary of the relevant parameters.


    #########################################################################
    TODO:  Add parameters, packaged as JSON string, as attribute to log file.
    #########################################################################

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
            'logfile_name': 'data.hdf5',
            'logfile_auto_incr': True, 
            'logfile_auto_incr_format': '{0:06d}',
            'logfile_dt': 0.01,
            }


    def __init__(self,param = default_param):

        self.param = param
        self.data = FlyData(self.param)
        self.display = BasicDisplay(self.param)
        self.protocol = Protocol(self.param)
        self.logger = H5Logger(
                filename = self.param['logfile_name'],
                auto_incr = self.param['logfile_auto_incr'],
                auto_incr_format = self.param['logfile_auto_incr_format'],
                )
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

        self.done = False
        signal.signal(signal.SIGINT,self.sigint_handler)

    def reset(self):
        self.data.reset()
        self.protocol.reset()
        self.display.reset()
        self.time_start = time.time()
        self.time_now = self.time_start 
        self.time_log = None 

    @property
    def time_elapsed(self):
        return self.time_now - self.time_start

    def run(self):

        while not self.done:

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

                if self.protocol.pulse_on:
                    self.trigger_device.set_high()
                else:
                    self.trigger_device.set_low()

                self.write_logfile()

            # Update display
            if self.protocol.active: 
                self.display.set_stim_center(self.protocol.stim_x, self.protocol.stim_y) 
                self.display.set_stim_enabled(True)
            else:
                self.display.set_stim_enabled(False)

            self.display.update(self.data)


        # Run complete 
        utils.flush_print('Run finshed - quiting!')
        self.clean_up()



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
        utils.flush_print('frame         = {0}'.format(self.data.frame))
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

    def write_logfile(self):
        if self.time_log is None or ((self.time_elapsed - self.time_log) >  self.param['logfile_dt']):
            self.time_log = self.time_elapsed
            log_data = { 
                    'time': self.time_elapsed,
                    'frame': self.data.frame,
                    'posx': self.data.posx,
                    'posy': self.data.posy,
                    'velx': self.data.velx,
                    'vely': self.data.vely,
                    'path_len': self.data.path_len,
                    'ready': int(self.protocol.ready),
                    'win_dist': self.protocol.get_window_distance(self.time_elapsed, self.data),
                    'active': int(self.protocol.active),
                    'outside_dt': self.time_elapsed - self.protocol.time_outer_circle,
                    'pulse_on': int(self.protocol.pulse_on),
                    'pulse_on_dt': self.time_elapsed - self.protocol.time_pulse_on,
                    'stimx': self.protocol.stim_x,
                    'stimy': self.protocol.stim_y,
                    }
            self.logger.add(log_data)

    def sigint_handler(self, signum, frame):
        self.done = True

    def clean_up(self):
        self.logger.reset()
        if self.trigger_device.isOpen():
            self.trigger_device.set_low()

