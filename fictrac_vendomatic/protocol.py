import utils


class Protocol:
    """
    Implements experimental protocol ... TODO: description

    parameter summary  (param)

      stim_inner_radius             - inner radius for stim - fly need to enter this trigger stimuls pulses
      stim_outer_radius             - outer radius for stim - protocol not reset if fly stays inside circle 
      stim_startup_path_length      - minimum path length before stim can start
      stim_threshold_distance       - distance threshold for triggering stim (measured over threshold window)
      stim_threshold_window         - time window over which threhold distance is measured
      stim_pulse_on_window          - time window for pulse on
      tim_pulse_off_window          - time window for pulse off (always off for at least this long after being on)
      protocol_reset_window         - time after which protocol reset if fly outside of outer radius

    
    """

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
        return utils.distance(p,q)


    def is_inside_inner_circle(self,data):
        value = utils.is_inside_circle(
                data.posx, 
                data.posy, 
                self.stim_x, 
                self.stim_y, 
                self.param['stim_inner_radius']
                )
        return value

    def is_inside_outer_circle(self,data):
        value = utils.is_inside_circle(
                data.posx, 
                data.posy, 
                self.stim_x, 
                self.stim_y, 
                self.param['stim_outer_radius']
                )
        return value


