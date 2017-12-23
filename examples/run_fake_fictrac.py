from fictrac_vendomatic import FakeFicTrac
from fictrac_vendomatic import RandomFly
from fictrac_vendomatic import degToRad

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
