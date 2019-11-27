from __future__ import print_function
import time
import serial


class TriggerDevice(serial.Serial):

    ResetSleepDt = 2.0
    Baudrate = 115200

    CmdSetTriggerLow = 0
    CmdSetTriggerHigh = 1

    def __init__(self,port,timeout=10.0):
        param = {'baudrate': self.Baudrate, 'timeout': timeout}
        super(TriggerDevice,self).__init__(port,**param)
        time.sleep(self.ResetSleepDt)
        self.is_high = None
        self.set_low();

    def set_low(self):
        if (self.is_high is None) or self.is_high:
            self.write('[{0}]\n'.format(self.CmdSetTriggerLow).encode())
            self.is_high = False

    def set_high(self):
        if (self.is_high is None) or not self.is_high:
            self.write('[{0}]\n'.format(self.CmdSetTriggerHigh).encode())
            self.is_high = True


# ------------------------------------------------------------------------------
if __name__ == '__main__':

    dev = TriggerDevice('/dev/ttyUSB0')
    state = False

    while True:

        if state:
            dev.set_low()
            state = False
            print('set_high')
        else:
            dev.set_high()
            state = True
            print('set_low')

        time.sleep(0.1)
    



