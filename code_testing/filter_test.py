import time
from scipy.signal import medfilt2d, order_filter
import numpy as np
from fiber_properties import FiberImage, filter_image, plot_image, show_plots, crop_image
import pstats, cProfile

kernel = 51
a = 2**16 * np.random.rand(500,500)
# a = FiberImage('../data/modal_noise/Kris_data/rectangular_100x300um/unagitated/nf_corrected.fit').get_image()
# im_obj = FiberImage('../data/modal_noise/coupled_fibers/200-200um_test2/agitated_both/nf_corrected.fit', threshold=10000)
# radius = im_obj.get_fiber_radius()
# center = im_obj.get_fiber_center()
# a = crop_image(im_obj.get_image(), center, radius, False)

plot_image(a)

start = time.time()
b = filter_image(a, kernel, quick=True)
end = time.time()
print(end-start)
plot_image(b)

start = time.time()
c = filter_image(a, kernel, quick=False, cython=False, zero_fill=True)
end = time.time()
print(end-start)
plot_image(c)

start = time.time()
d = filter_image(a, kernel, quick=False, cython=True, zero_fill=False)
end = time.time()
print(end-start)
plot_image(d)

# radius = (kernel-1) / 2
# x_array, y_array = np.meshgrid(np.arange(kernel),
#                                np.arange(kernel))
# mask = ((x_array-radius)**2 + (y_array-radius)**2 <= radius**2).astype('int')
# half = mask.sum()/2
# start = time.time()
# d = order_filter(a, mask, half)
# end = time.time()
# print(end-start)
# plot_image(d)

show_plots()

# cProfile.runctx('filter_image(a, kernel, quick=False, cython=False, zero_fill=True)', globals(), locals(), 'Profile.prof')
# s = pstats.Stats('Profile.prof')
# s.strip_dirs().sort_stats('time').print_stats()