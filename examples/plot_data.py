from __future__ import print_function
import sys
import h5py
import json
import matplotlib.pyplot as plt

filename = sys.argv[1]
h5file = h5py.File(filename, 'r')

print()
print('datasets')
print('--------')
for name in h5file:
    print('  {0}, shape={1}, dtype={2}'.format(name,h5file[name].shape,h5file[name].dtype))
print()

print('attrs')
print('-----')
for k,v in h5file.attrs.iteritems():
    if not k == 'jsonparam':
        print('{0}: {1}'.format(k,v))
    else:
        print('{0}:'.format(k))
        param = json.loads(v)
        for kk,vv in param.iteritems():
            print('  {0}: {1}'.format(kk,vv))
print()


plt.figure(1)
plt.subplot(611)
plt.plot(h5file['time'], h5file['posx'])
plt.subplot(612)
plt.plot(h5file['time'], h5file['posy'])
plt.subplot(613)
plt.plot(h5file['time'], h5file['velx'])
plt.subplot(614)
plt.plot(h5file['time'], h5file['vely'])
plt.subplot(615)
plt.plot(h5file['time'], h5file['pulse_on'])
plt.subplot(616)
plt.plot(h5file['time'], h5file['pulse_on_dt'])
plt.show()


