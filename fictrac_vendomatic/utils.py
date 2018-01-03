from __future__ import print_function
import math 
import sys

def degToRad(deg):
    return deg*math.pi/180.0

def radToDeg(rad):
    return rad*180.0/math.pi

def flush_print(*arg,**kwarg):
    print(*arg,**kwarg)
    sys.stdout.flush()

def is_inside_circle(x, y, circle_x, circle_y, radius): 
    return distance((x,y), (circle_x, circle_y)) <= radius

def distance(p,q):
    return length(q[0]-p[0], q[1]-p[1])

def length(x,y):
    return math.sqrt(x**2 + y**2)

