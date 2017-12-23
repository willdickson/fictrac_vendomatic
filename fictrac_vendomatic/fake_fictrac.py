from __future__ import print_function
import redis
import time
import json
import math
import random
from utils import degToRad 
from utils import radToDeg



class RandomFly:

    default_param = {
            'max_speed': 2.0,
            'min_speed': 0.0,
            'speed_delta': 0.2,
            'angle_delta': degToRad(10.0),
            }

    def __init__(self, dt, param=default_param):
        self.dt = dt
        self.param = param
        self.posx = 0.0
        self.posy = 0.0
        self.velx = 0.0
        self.vely = 0.0

    @property
    def speed(self):
        return math.sqrt(self.velx**2 + self.vely**2)

    @property
    def angle(self):
        return math.atan2(self.vely, self.velx)

    def get_new_speed(self):
        range_top = min([self.speed + self.param['speed_delta'], self.param['max_speed']])
        range_top = max([range_top, self.param['min_speed'] + self.param['speed_delta']])
        range_bot = max([self.speed - self.param['speed_delta'], self.param['min_speed']])
        range_bot = min([range_bot, self.param['max_speed'] - self.param['speed_delta']])
        return random.uniform(range_bot, range_top)

    def get_new_angle(self):
        return self.angle + random.uniform(-self.param['angle_delta'], self.param['angle_delta'])

    def update(self):
        new_speed = self.get_new_speed()
        new_angle = self.get_new_angle()
        self.velx = new_speed*math.cos(new_angle)
        self.vely = new_speed*math.sin(new_angle)
        self.posx += self.velx*self.dt
        self.posy += self.vely*self.dt


class FakeFicTrac:

    default_param = {
            'redis_channel' : 'fictrac',
            'loop_dt': 0.01,
            'fly': {
                'model': RandomFly,
                'param': {
                    'max_speed': 2.0,
                    'min_speed': 0.0,
                    'speed_delta': 0.2,
                    'angle_delta': degToRad(10.0),
                    },
                },
            }

    def __init__(self,param=default_param):
        self.param = param
        self.redis_client = redis.StrictRedis()
        self.frame = 0

    def publish_msg(self,msg):
        msg_json = json.dumps(msg)
        self.redis_client.publish(self.param['redis_channel'], msg_json)

    @property
    def t_elapsed(self):
        return self.frame*self.param['loop_dt']

    def run(self):


        fly = self.param['fly']['model'](self.param['loop_dt'],self.param['fly']['param'])

        msg = {'type': 'reset'}
        self.publish_msg(msg)

        while True:

            fly.update()

            print('frame:    {0}'.format(self.frame))
            print('posx:     {0}'.format(fly.posx))
            print('posy:     {0}'.format(fly.posy))
            print('velx:     {0}'.format(fly.velx))
            print('vely:     {0}'.format(fly.vely))
            print('angle:    {0}'.format(radToDeg(fly.angle)))
            print('speed:    {0}'.format(fly.speed))
            print()

            msg = {
                    'type': 'data',
                    'frame': self.frame,
                    'posx': fly.posx,
                    'posy': fly.posy, 
                    'velx': fly.velx,
                    'vely': fly.vely,
                    'heading': radToDeg(fly.angle),
                    }

            self.publish_msg(msg)
            time.sleep(self.param['loop_dt'])
            self.frame += 1




# -----------------------------------------------------------------------------
if __name__ == '__main__':


    param = { 
            'redis_channel' : 'fictrac',
            'loop_dt': 0.01,
            'fly': {
                'model': RandomFly,
                'param': {
                    'max_speed': 2.0,
                    'min_speed': 0.5,
                    'speed_delta': 0.2,
                    'angle_delta': degToRad(20.0),
                    },
                },
            }

    faker = FakeFicTrac(param=param)
    faker.run()






