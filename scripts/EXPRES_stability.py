import matplotlib.pyplot as plt
import numpy as np
import os
from fiber_properties import ImageAnalysis, load_image_object, image_list

plt.rc('font', size=16, family='serif')
plt.rc('figure', figsize=[20, 12.36])
plt.rc('xtick', labelsize=16)
plt.rc('ytick', labelsize=16)
plt.rc('lines', lw=4)

NEW_DATA = True
NUM_IMAGES = 150
CAMS = ['in', 'nf', 'ff']
FOLDER = '../data/EXPRES/bare_octagonal/stability/'

def plot_stability(data, cam):
    plt.figure() 
    plt.title(cam + 'stability')
    plt.subplot(311)
    plt.scatter(data.time, data.x_diff)
    plt.ylabel('X Centroid Shift [um]')
    plt.title('std: ' + str(np.std(data.x_diff)))

    plt.subplot(312)
    plt.scatter(data.time, data.y_diff)
    plt.ylabel('Y Centroid Shift [um]')
    plt.title('std: ' + str(np.std(data.y_diff)))

    plt.subplot(313)
    plt.scatter(data.time, data.diameter)
    plt.xlabel('Time [min]')
    plt.ylabel('Diameter Shift [um]')
    plt.title('std: ' + str(np.std(data.diameter)))

    plt.suptitle(cam + ' stability')

def save_objects(obj):
    

class StabilityInfo(object):
    def __init__(self):
        self.centroid = []
        self.center = []
        self.x_diff = []
        self.y_diff  = []
        self.diameter = []
        self.time = []

if __name__ == "__main__":
    data = {}
    data['spot'] = StabilityInfo()

    folder = 'stability/'
    for cam in CAMS:
        data[cam] = StabilityInfo()
        if cam == 'in' or cam == 'nf':
            method = 'radius'
        else:
            method = 'radius'

        for i in xrange(NUM_IMAGES):
            obj_file = cam + '_obj_' + str(i).zfill(3) + '.pkl'
            if obj_file not in os.listdir(folder):
                print 'saving ' + cam + ' ' + str(i)
                im_file = folder + cam + '_' + str(i).zfill(3) + '.fit'
                ImageAnalysis(im_file, threshold=1000).save_object(folder + obj_file)

            print 'loading ' + cam + ' ' + str(i)
            obj = load_image_object(folder + obj_file)
            data[cam].center.append(np.array(obj.get_fiber_center(method=method, units='microns')))
            data[cam].centroid.append(np.array(obj.get_fiber_centroid(method=method, units='microns')))
            data[cam].x_diff.append(data[cam].centroid[i][1] - data[cam].center[i][1])
            data[cam].y_diff.append(data[cam].centroid[i][0] - data[cam].center[i][0])
            data[cam].diameter.append(obj.get_fiber_diameter(method=method, units='microns'))
            data[cam].time.append(obj.get_image_info('date_time'))
            if cam == 'in':
                data['spot'].center.append(np.array(obj.get_fiber_center(method='gaussian', units='microns')))
                data['spot'].centroid.append(np.array(obj.get_fiber_centroid(method='gaussian', units='microns')))
                data['spot'].x_diff.append(data['spot'].center[i][1] - data[cam].center[i][1])
                data['spot'].y_diff.append(data['spot'].center[i][0] - data[cam].center[i][0])
                data['spot'].diameter.append(obj.get_fiber_diameter(method='gaussian', units='microns'))
                data['spot'].time.append(obj.get_image_info('date_time'))
            obj.save_object()


    for cam in ['in', 'nf', 'ff', 'spot']:
        init_center = np.copy(data[cam].center[0])
        init_centroid = np.copy(data[cam].centroid[0])
        init_x_diff = np.copy(data[cam].x_diff[0])
        init_y_diff = np.copy(data[cam].y_diff[0])
        init_diameter = np.copy(data[cam].diameter[0])
        init_time = np.copy(data[cam].time[0])
        for i in xrange(NUM_IMAGES):
            data[cam].center[i] -= init_center
            data[cam].centroid[i] -= init_centroid
            data[cam].x_diff[i] -= init_x_diff
            data[cam].y_diff[i] -= init_y_diff
            data[cam].diameter[i] -= init_diameter
            data[cam].time[i] -= init_time
            data[cam].time[i] = data[cam].time[i].total_seconds() / 60.0
        plot_stability(data[cam], cam)
        plt.savefig(FOLDER+'stability/' + cam + '_stability.png')
