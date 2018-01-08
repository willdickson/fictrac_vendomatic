from fictrac_vendomatic import FicTracVendomatic

param = { 
        'redis_channel': 'fictrac',
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

client = FicTracVendomatic(param=param)
client.run()
