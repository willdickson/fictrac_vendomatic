import utils

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
            self.path_len += utils.length(dx,dy)
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
    

