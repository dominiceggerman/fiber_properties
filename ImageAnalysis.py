"""ImageAnalysis.py was written by Ryan Petersburg for use with fiber
characterization on the EXtreme PRecision Spectrograph
"""

import numpy as np
from scipy.signal import medfilt2d as median_filter
from NumpyArrayHandler import NumpyArrayHandler
from Calibration import Calibration

class ImageAnalysis(NumpyArrayHandler):
    """Fiber face image analysis class

    Class that conducts image analysis on a fiber face image after it has been
    corrected by the given dark and flat field images. Also contains information
    about the CCD that took the image. Public methods in this class allow
    calculation of the image's centroid as well as multiple methods to find the
    fiber center and diameter
    """
    def __init__(self, image_input, calibration=Calibration(None, None, None),
                 pixel_size=None, camera=None, threshold=None, kernel_size=5):
        self.pixel_size = pixel_size
        self.camera = camera
        self.kernel_size = kernel_size

        self._image_array = None
        self.setImageArray(image_input)
        self._image_array = calibration.executeErrorCorrections(self._uncorrected_image,
                                                                self.exp_time)
        self._image_height, self._image_width = self._image_array.shape
        self._filtered_image = self.getFilteredImage()

        if threshold is None:
            self.threshold = calibration.dark_image.max()
        else:
            self.threshold = threshold

        #Approximate the Fiber Center and Diameter
        self._left_edge = None
        self._right_edge = None
        self._top_edge = None
        self._bottom_edge = None
        self._fiber_diameter_edge = None
        self._center_y_edge = None
        self._center_x_edge = None
        self.setFiberCenterEdgeMethod()

        self._centroid_y = None
        self._centroid_x = None

        self._fiber_diameter_circle = None
        self._center_y_circle = None
        self._center_x_circle = None
        self._array_sum_circle = None

        self._fiber_diameter_radius = None
        self._center_y_radius = None
        self._center_x_radius = None
        self._array_sum_radius = None

        self._fiber_diameter_gaussian = None
        self._center_y_gaussian = None
        self._center_x_gaussian = None

        self._gaussian_fit = None

        # Golden Ratio for optimization tests
        self._phi = (5 ** 0.5 - 1) / 2

#=============================================================================#
#==== Private Variable Setters ===============================================#
#=============================================================================#

    def setImageArray(self, image_input):
        """Sets the uncorrected image to be analyzed

        Args:
            image_input: see convertImageToArray for options

        Sets:
            self._image_array
        """
        self._uncorrected_image, output_dict = self.convertImageToArray(image_input, True)

        self.setImageProperties(output_dict)

        if self._image_array is not None:
            self.executeErrorCorrections()   

    def setImageProperties(self, output_dict):
        if 'pixel_size' in output_dict:
            self.pixel_size = output_dict['pixel_size']
        if 'bit_depth' in output_dict:
            self.bit_depth = output_dict['bit_depth']
        if 'exp_time' in output_dict:
            self.exp_time = output_dict['exp_time']
        if 'date_time' in output_dict:
            self.date_time = output_dict['date_time']
        if 'temp' in output_dict:
            self.temp = output_dict['temp']
        if 'camera' in output_dict:
            self.camera = output_dict['camera']
        if 'test' in output_dict:
            self.test = output_dict['test']

        self.magnification = None
        if self.camera == 'nf' or self.camera == 'in':
            self.magnification = 10.0
        if self.camera == 'ff':
            self.magnification = 1.0

        if self.pixel_size is None:
            raise RuntimeError('Pixel Size needs to be set externally')
        if self.magnification is None:
            raise RuntimeError('Magnification needs to be set externally')

#=============================================================================#
#==== Private Variable Getters ===============================================#
#=============================================================================#

    def getImageArray(self):
        """Getter for the image array

        Returns:
            self._image_array
        """
        return self._image_array

    def getImageHeight(self):
        """Getter for the image height

        Returns:
            self._image_height
        """
        return self._image_height

    def getImageWidth(self):
        """Getter for the image width

        Returns:
            self._image_width
        """
        return self._image_width

    def getFiberRadius(self, method=None, show_image=False, tol=1, test_range=None, units='pixels'):
        """Getter for the fiber radius

        Finds the radius of the fiber using the given method or, if no method
        is given, the most precise method already completed

        Args:
            method (optional): string representing the fiber centering method

        Returns:
            fiber radius (pixels)
        """
        return self.getFiberDiameter(method, show_image, tol, test_range, units) / 2.0

    def getFiberDiameter(self, method=None, show_image=False, tol=1, test_range=None, units='pixels'):
        """Getter for the fiber diameter in pixels

        Find the diameter of the fiber using the given method or, if no method
        is given, the most precise method already completed

        Args:
            method (optional): string representing the fiber centering method

        Returns:
            fiber diameter (pixels)
        """
        if method is None:
            if self._fiber_diameter_radius is not None:
                method = 'radius'
            elif self._fiber_diameter_gaussian is not None:
                method = 'gaussian'
            else:
                method = 'edge'

        _, _ = self.getFiberCenter(method, show_image, tol, test_range, units)

        if 'radius' in method:
            diameter = self._fiber_diameter_radius
        elif 'gaussian' in method:
            diameter = self._fiber_diameter_gaussian
        elif 'edge' in method:
            diameter = self._fiber_diameter_edge
        else:
            raise RuntimeError('Incorrect string for method type')

        if units == 'pixels':
            return diameter
        elif units == 'microns':
            return diameter * self.pixel_size / self.magnification
        else:
            raise RuntimeError('Incorrect string for units')

    def getFiberCenter(self, method=None, show_image=True, tol=1, test_range=None, units='pixels'):
        """Getter for the fiber center in pixels

        Find the center position of the fiber using the given method or, if no
        method is given, the most precise method already completed

        Args:
            method (optional): string representing the fiber centering method
            show_image (optional): boolean for whether or not to show image of
                completed method
            tol (optional): tolerance value passed to 
                getFiberCenterRadiusMethod()and getFiberCenterCircleMethod()
            test_range (optional): range of tested values passed to
                getFiberCenterRadiusMethod() and getFiberCenterCircleMethod()

        Returns:
            center y (pixels), center x (pixels)
        """
        if method is None:
            if self._center_x_radius is not None:
                method = 'radius'
            elif self._center_x_gaussian is not None:
                method = 'gaussian'
            elif self._center_x_circle is not None:
                method = 'circle'
            else:
                method = 'edge'

        if 'radius' in method:
            center = self.getFiberCenterRadiusMethod(tol=tol,
                                                     test_range=test_range,
                                                     show_image=show_image)
        elif 'gaussian' in method:
            center = self.getFiberCenterGaussianMethod(show_image=show_image)
        elif 'circle' in method:
            center = self.getFiberCenterCircleMethod(tol=tol,
                                                     test_range=test_range,
                                                     show_image=show_image)
        elif 'edge' in method:
            center = self.getFiberCenterEdgeMethod(show_image=show_image)
        else:
            raise RuntimeError('Incorrect string for method type')

        if units == 'pixels':
            return center
        elif units == 'microns':
            return tuple(np.array(center) * self.pixel_size / self.magnification)
        else:
            raise RuntimeError('Incorrect string for units')

    def getFiberCenterRadiusMethod(self, tol=1, test_range=None, show_image=True):
        """Getter for the fiber center using the radius method

        See setFiberCenterRadiusMethod() for method details

        Args:
            show_image (optional): boolean for whether or not to show image of
                completed method

        Returns:
            center y (pixels), center x (pixels)
        """
        if self._center_x_radius is None:
            self.setFiberCenterRadiusMethod(tol, test_range)
            if show_image:
                self.showOverlaidTophat(self._center_x_radius,
                                        self._center_y_radius,
                                        self._fiber_diameter_radius / 2.0,
                                        tol=tol)        

        return self._center_y_radius, self._center_x_radius

    def getFiberCenterCircleMethod(self, radius=None, tol=1, test_range=None, show_image=True):
        """Getter for the fiber center using the circle method

        See setFiberCenterCircleMethod() for method details

        Args:
            show_image (optional): boolean for whether or not to show image of
                completed method

        Returns:
            center y (pixels), center x (pixels)
        """
        if radius is None:
            radius = self.getFiberRadius()
        if self._center_x_circle is not None:
            show_image = False

        self.setFiberCenterCircleMethod(radius, tol, test_range)
                  
        if show_image:
            self.showOverlaidTophat(self._center_x_circle,
                                    self._center_y_circle,
                                    self._fiber_diameter_circle / 2.0,
                                    tol=tol)        

        return self._center_y_circle, self._center_x_circle

    def getFiberCenterEdgeMethod(self, show_image=True):
        """Getter for the fiber center using the edge method

        See setFiberCenterEdgeMethod() for method details

        Args:
            show_image (optional): boolean for whether or not to show image of
                completed method

        Returns:
            center y (pixels), center x (pixels)
        """
        if self._center_y_edge is None:
            self.setFiberCenterEdgeMethod()

        if show_image:
            self.showOverlaidTophat(self._center_x_edge,
                                    self._center_y_edge,
                                    self._fiber_diameter_edge / 2.0)

        return self._center_y_edge, self._center_x_edge

    def getFiberCenterGaussianMethod(self, show_image=True):
        """Getter for the fiber center using the gaussian method

        See setFiberCenterGaussianMethod() for method details

        Args:
            show_image (optional): boolean for whether or not to show image of
                completed method

        Returns:
            center y (pixels), center x (pixels)
        """
        if self._center_x_gaussian is None:
            self.setFiberCenterGaussianMethod()

        if show_image:
            self.showImageArray(self._gaussian_fit)
            self.plotOverlaidCrossSections(self._image_array, self._gaussian_fit,
                                           self._center_y_gaussian, self._center_x_gaussian)

        return self._center_y_gaussian, self._center_x_gaussian

    def getFiberCentroid(self, radius_factor=1.05):
        """Getter for the fiber centroid

        See setFiberCentroid() for method details

        Returns:
            centroid y (pixels), centroid x (pixels)
        """
        self.setFiberCentroid(radius_factor)
        return self._centroid_y, self._centroid_x

    def getGaussianFit(self, image_array=None, initial_guess=None, full_output=False):
        if image_array is None:
            if self._gaussian_fit is None:
                self.setFiberCenterGaussianMethod()
            return self._gaussian_fit
        return super(ImageAnalysis, self).getGaussianFit(image_array, initial_guess, full_output)

    def getMeshGrid(self, image_array=None):
        if image_array is None:
            image_array = self._image_array
        return super(ImageAnalysis, self).getMeshGrid(image_array)

    def getPolynomialFit(self, image_array=None, deg=6, x0=None, y0=None):
        if image_array is None:
            image_array = self._image_array
        return super(ImageAnalysis, self).getPolynomialFit(image_array, deg, x0, y0)

    def getTophatFit(self):
        y0, x0 = self.getFiberCenter(show_image=False)
        radius = self.getFiberRadius()
        return self.circleArray(self.getMeshGrid(), x0, y0, radius, res=10)

    def getFilteredImage(self, image_array=None, kernel_size=None):
        if image_array is None:
            image_array = self._image_array
        if kernel_size is None:
            kernel_size = self.kernel_size
        return super(ImageAnalysis, self).getFilteredImage(image_array, kernel_size)    

    def getDarkImage(self):
        return calibration.dark_image

    def getAmbientImage(self):
        return calibration.ambient_image

    def getFlatImage(self):
        return calibration.flat_image

#=============================================================================#
#==== Image Centroiding ======================================================#
#=============================================================================#

    def setFiberCentroid(self, radius_factor=1.05):
        """Finds the centroid of the fiber face image

        Args:
            radius_factor: the factor by which the radius is multiplied when
                isolating the fiber face in the image

        Sets:
            centroid_y
            centroid_x
        """
        y0, x0 = self.getFiberCenter(method='edge', show_image=False)
        radius = self.getFiberRadius(method='edge', show_image=False)
        image_array_iso = self.isolateCircle(self._image_array, x0, y0,
                                             radius*radius_factor, res=1)

        #self.showImageArray(image_array_iso)

        x_array, y_array = self.getMeshGrid()
        self._centroid_x = (image_array_iso * x_array).sum() / image_array_iso.sum()
        self._centroid_y = (image_array_iso * y_array).sum() / image_array_iso.sum()

#=============================================================================#
#==== Image Centering ========================================================#
#=============================================================================#

    def setFiberCenterGaussianMethod(self):
        """Finds fiber center using a Gaussian Fit

        Uses Scipy.optimize.curve_fit method to fit fiber image to
        self.gaussianArray. The radius found extends to 2-sigma of the gaussian
        therefore encompassing ~95% of the imaged light. Use previous methods
        of center-finding to approximate the location of the center

        Sets:
            fiber_diameter_gaussian: diameter of the fiber (gaussian method)
            center_y_gaussian: y-position of center (gaussian method)
            center_x_gaussian: x-position of center (gaussian method)
        """
        #initial_guess = (50,50,50,50)
        y0, x0 = self.getFiberCenter(show_image=False)
        initial_guess = (x0, y0, self.getFiberRadius(),
                         self._image_array.max(), self._image_array.min())

        self._gaussian_fit, opt_parameters = self.getGaussianFit(self._image_array,
                                                                 initial_guess=initial_guess,
                                                                 full_output=True)

        self._center_x_gaussian = opt_parameters[0]
        self._center_y_gaussian = opt_parameters[1]
        self._fiber_diameter_gaussian = opt_parameters[2] * 2

    def setFiberCenterRadiusMethod(self, tol=1, test_range=None):
        """Finds fiber center using a dark circle with various radii

        Uses a golden mean optimization method to find the optimal radius of the
        dark circle that covers the fiber image used in
        getFiberCenterCircleMethod(). The optimization is for a parameter
        array_sum which is weighted by the area of the circle, meaning that a
        smaller circle is preferred over one that simply covers the entire image

        Args:
            tol: minimum possible range of radius values before ending iteration
            test_range: range of tested radii. If None, uses full possible range

        Sets:
            fiber_diameter_radius: diameter of the fiber (radius method)
            center_y_radius: y-position of center (radius method)
            center_x_radius: x-position of center (radius method)
        """
        # Initialize range of tested radii
        r = np.zeros(4).astype(float)

        if test_range is not None:
            approx_radius = self.getFiberRadius()
            test_range = test_range / 2.0

            r[0] = approx_radius - test_range
            if r[0] < 0.0:
                r[0] = 0.0
            r[3] = approx_radius + test_range
        else:
            r[0] = 0
            r[3] = min(self._image_height, self._image_width) / 2.0

        r[1] = r[0] + (1 - self._phi) * (r[3] - r[0])
        r[2] = r[0] + self._phi * (r[3] - r[0])

        array_sum = np.zeros(2).astype(float)
        for i in xrange(2):
            self.setFiberCenterCircleMethod(r[i+1], tol, test_range)
            array_sum[i] = self._array_sum_circle + self.threshold * np.pi * r[i+1]**2

        min_index = np.argmin(array_sum) # Integer 0 or 1 for min of r[1], r[2]

        while abs(r[3]-r[0]) > tol:
            if min_index == 0:
                r[3] = r[2]
                r[2] = r[1]
                r[1] = r[0] + (1 - self._phi) * (r[3] - r[0])
            else:
                r[0] = r[1]
                r[1] = r[2]
                r[2] = r[0] + self._phi * (r[3] - r[0])

            array_sum[1 - min_index] = array_sum[min_index]

            self.setFiberCenterCircleMethod(r[min_index+1], tol, test_range)
            array_sum[min_index] = (self._array_sum_circle 
                                    + self.threshold * np.pi * r[min_index+1]**2)

            min_index = np.argmin(array_sum) # Integer 0 or 1 for min of r[1], r[2]

        self._fiber_diameter_radius = r[min_index+1] * 2
        self._center_y_radius = self._center_y_circle
        self._center_x_radius = self._center_x_circle
        self._array_sum_radius = np.amin(array_sum)

    def setFiberCenterCircleMethod(self, radius, tol=1, test_range=None):
        """Finds fiber center using a dark circle of set radius

        Uses golden mean method to find the optimal center for a circle
        covering the fiber image. The optimization is for a parameter array_sum
        that simply sums over the entire fiber image array

        Args:
            radius: circle radius to test
            tol: minimum possible range of center_x or center_y values before
                ending iteration
            test_range: initial range of tested center values. If None, uses
                full range.
        """
        #print "Testing Radius:", radius
        res = int(1.0/tol)

        # Create four "corners" to test center of the removed circle
        x = np.zeros(4).astype(float)
        y = np.zeros(4).astype(float)

        if test_range is not None:
            approx_center = self.getFiberCenter(method='edge', show_image=False)
            test_range = test_range / 2.0

            x[0] = approx_center[1] - test_range
            if x[0] < radius:
                x[0] = radius
            x[3] = approx_center[1] + test_range
            if x[3] > self._image_width - radius:
                x[3] = self._image_width - radius

            y[0] = approx_center[0] - test_range
            if y[0] < radius:
                y[0] = radius
            y[3] = approx_center[0] + test_range
            if y[3] > self._image_height - radius:
                y[3] = self._image_height - radius

        else:
            x[0] = radius
            x[3] = self._image_width - radius

            y[0] = radius
            y[3] = self._image_height - radius

        x[1] = x[0] + (1 - self._phi) * (x[3] - x[0])
        x[2] = x[0] + self._phi * (x[3] - x[0])

        y[1] = y[0] + (1 - self._phi) * (y[3] - y[0])
        y[2] = y[0] + self._phi * (y[3] - y[0])

        # Initialize array sums to each corner
        array_sum = np.zeros((2, 2)).astype(float)
        for i in xrange(2):
            for j in xrange(2):
                removed_circle_array = self.removeCircle(self._filtered_image,
                                                         x[i+1], y[j+1],
                                                         radius, res)
                array_sum[j, i] = self.getArraySum(removed_circle_array)

        # Find the index of the corner with minimum array_sum
        min_index = np.unravel_index(np.argmin(array_sum), (2, 2)) # Tuple

        while abs(x[3] - x[0]) > tol and abs(y[3] - y[0]) > tol:
            # Move the other corners to smaller search area
            if min_index[0] == 0:
                y[3] = y[2]
                y[2] = y[1]
                y[1] = y[0] + (1 - self._phi) * (y[3] - y[0])
            else:
                y[0] = y[1]
                y[1] = y[2]
                y[2] = y[0] + self._phi * (y[3] - y[0])
            if min_index[1] == 0:
                x[3] = x[2]
                x[2] = x[1]
                x[1] = x[0] + (1 - self._phi) * (x[3] - x[0])
            else:
                x[0] = x[1]
                x[1] = x[2]
                x[2] = x[0] + self._phi * (x[3] - x[0])

            # Replace the opposite corner array sum (so it doesn't need to be recalculated)
            array_sum[1 - min_index[0], 1 - min_index[1]] = array_sum[min_index]
            min_index = (1 - min_index[0], 1 - min_index[1])

            # Recalculate new sums for all four corners
            for i in xrange(2):
                for j in xrange(2):
                    if i != min_index[1] or j != min_index[0]:
                        removed_circle_array = self.removeCircle(self._filtered_image,
                                                                 x[i+1], y[j+1],
                                                                 radius, res)
                        array_sum[j, i] = self.getArraySum(removed_circle_array)

            min_index = np.unravel_index(np.argmin(array_sum), (2, 2))

        self._center_x_circle = x[min_index[1]+1]
        self._center_y_circle = y[min_index[0]+1]
        self._fiber_diameter_circle = radius * 2.0
        self._array_sum_circle = np.amin(array_sum)

    def setFiberCenterEdgeMethod(self):
        """The averages of the fiber edges gives the fiber center

        Returns:
            center_y, center_x
        """
        self.setFiberEdges()

        self._center_y_edge = (self._top_edge + self._bottom_edge) / 2.0
        self._center_x_edge = (self._left_edge + self._right_edge) / 2.0

    def setFiberEdges(self):
        """Set fiber edge pixel values

        Sets the left, right, top, and bottom edges of the fiber by finding where
        the maxima of each row and column cross the given threshold. Also sets
        the width of the fiber by the maximum of the horizontal and vertical
        lengths

        Sets:
            self._left_edge
            self._right_edge
            self._top_edge
            self._bottom_edge
            self._fiber_diameter_edge
        """
        left = -1
        right = -1
        for index in xrange(self._image_width):
            if left < 0:
                if self._filtered_image[:, index].max() > self.threshold:
                    left = index
            else:
                if self._filtered_image[:, index].max() > self.threshold:
                    right = index

        top = -1
        bottom = -1
        for index in xrange(self._image_height):
            if top < 0:
                if self._filtered_image[index, :].max() > self.threshold:
                    top = index
            else:
                if self._filtered_image[index, :].max() > self.threshold:
                    bottom = index

        self._left_edge = left
        self._right_edge = right
        self._top_edge = top
        self._bottom_edge = bottom
        self._fiber_diameter_edge = max(right - left, bottom - top)

#=============================================================================#
#==== Overriding Methods =====================================================#
#=============================================================================#

    def showImageArray(self, image_array=None):
        if image_array is None:
            image_array = self._image_array
        super(ImageAnalysis, self).showImageArray(image_array)


    def showOverlaidTophat(self, x0, y0, radius, tol=1):
        res = int(1.0/tol)
        self.showImageArray(self.removeCircle(self._image_array, x0, y0, radius, res=res))
        self.plotOverlaidCrossSections(self._image_array,
                                       self._image_array.max()*self.circleArray(self.getMeshGrid(),
                                                                                x0, y0, radius,
                                                                                res=res),
                                       y0, x0)


if __name__ == "__main__":
    base_folder = '2016-07-22/'
    ambient_folder = base_folder + 'ambient/'
    dark_folder = base_folder + 'dark/'
    flat_folder = base_folder + 'flat/'
    unagitated_folder = base_folder + 'stability_unagitated/'
    file_extension = '.fit'

    calibration = Calibration([dark_folder + 'nf_dark_' + str(i).zfill(3) + file_extension for i in xrange(10)],
                              [flat_folder + 'nf_flat_' + str(i) + '_1ms' + file_extension for i in xrange(8)],
                              [ambient_folder + 'nf_ambient_' + str(i).zfill(3) + '_0.001' + file_extension for i in xrange(10)])

    nf_images = unagitated_folder + 'nf_stability_017_0.002.fit'

    imAnalysis = ImageAnalysis(nf_images, calibration, camera='nf', threshold=200, kernel_size=11)

    tol = 1
    test_range = 10
    factor = 1.00

    print 'Height:', imAnalysis.getImageHeight(), 'Width:', imAnalysis.getImageWidth()
    imAnalysis.showImageArray()
    print
    print 'Centroid'
    centroid_row, centroid_column = imAnalysis.getFiberCentroid(factor)
    print 'Centroid Row:', centroid_row, 'Centroid Column:', centroid_column
    print
    print 'Edge:'
    center_y, center_x = imAnalysis.getFiberCenter(method='edge')
    print 'Diameter:', imAnalysis.getFiberDiameter(method='edge', units='microns'), 'microns'
    print 'Center Row:', center_y, 'Center Column:', center_x
    print
    print 'Circle:'
    center_y, center_x = imAnalysis.getFiberCenterCircleMethod(tol=tol, test_range=test_range)
    print 'Center Row:', center_y, 'Center Column:', center_x
    print
    print 'Radius:'
    center_y, center_x = imAnalysis.getFiberCenterRadiusMethod(tol=tol, test_range=test_range)
    print 'Diameter:', imAnalysis.getFiberDiameter(method='radius', units='microns'), 'microns'
    print 'Center Row:', center_y, 'Center Column:', center_x
    # print
    # print 'Gaussian:'
    # center_y, center_x = imAnalysis.getFiberCenter(method='gaussian')
    # print 'Diameter:', imAnalysis.getFiberDiameter(method='gaussian', units='microns'), 'microns'
    # print 'Center Row:', center_y, 'Center Column:', center_x