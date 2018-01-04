from __future__ import print_function
import sys
import h5py
import matplotlib.pyplot as plt

filename = sys.argv[1]
h5file = h5py.File(filename, 'r')

print()
print('datasets')
print('--------')
for name in h5file:
    print('  {0}, {1}, {2}'.format(name,h5file[name].shape,h5file[name].dtype))
print()

print('attrs')
print('-----')
for k,v in h5file.attrs.iteritems():
    print(k,v)
print()


plt.figure(1)
plt.subplot(511)
plt.plot(h5file['time'], h5file['posx'])
plt.subplot(512)
plt.plot(h5file['time'], h5file['posy'])
plt.subplot(513)
plt.plot(h5file['time'], h5file['velx'])
plt.subplot(514)
plt.plot(h5file['time'], h5file['vely'])
plt.subplot(515)
plt.plot(h5file['time'], h5file['active'])
plt.show()


