import numpy as np
import matplotlib.pyplot as plt
from NumpyArrayHandler import NumpyArrayHandler

class ModalNoise(NumpyArrayHandler):

    def __init__(self, image_obj, camera='nf'):
        self.plot_buffer = 1.1
        self.setImageObject(image_obj)
        self.setCamera(camera)        

    def setImageObject(self, image_obj):
        self.image_obj = image_obj

    def setCamera(self, camera):
        self.camera = camera

    def getImageObject(self):
        return self.image_obj

    def getCamera(self):
        return self.camera

    @staticmethod
    def getImageData(image_obj):
        y0, x0 = image_obj.getFiberCenter(method='edge', tol=1, test_range=10, show_image=False)
        radius = image_obj.getFiberRadius()        
        image_array = image_obj.getImageArray()
        #image_array = np.ones_like(image_array)
        #image_array = image_obj.getTophatFit()
        return image_array, y0, x0, radius

    def getGiniCoefficient(self, test_array):
        """Finds gini coefficient for intensities in given array

        Args:
            test_array: arbitrary-dimension numpy array

        Returns:
            gini coefficient
        """
        test_array = test_array.ravel()
        gini_coeff = 0.0
        for i in xrange(test_array.size):
            gini_coeff += np.abs(test_array[i] - test_array).sum()
        norm = 2.0 * test_array.sum() * test_array.size

        return gini_coeff / norm

#=============================================================================#
#==== Modal Noise Methods ====================================================#
#=============================================================================#

    def getModalNoise(self, image_obj=None, method='fft', output='array', radius_factor=0.95, deg=4):
        """Finds modal noise of camera image using specified method

        Args:
            camera: string designating near, far, or input
            method: string designating tophat, polynomial, gaussian, gradient,
                contrast, fft, gini, or entropy

        Returns:
            modal noise parameter
        """
        if image_obj is None:
            image_obj = self.image_obj

        if len(method) < 3:
            raise ValueError('Incorrect string for method type')
        elif method in 'tophat':
            return self.getModalNoiseTophat(image_obj, output, radius_factor)
        elif method in 'fft' or method in 'fourier':
            return self.getModalNoiseFFT(image_obj, output, radius_factor)
        elif method in 'polynomial':
            return self.getModalNoisePolynomial(image_obj, output, radius_factor, deg=deg)
        elif method in 'gaussian':
            return self.getModalNoiseGaussian(image_obj, output, radius_factor)
        elif method in 'gradient':
            return self.getModalNoiseGradient(image_obj, output, radius_factor)
        elif method in 'contrast':
            return self.getModalNoiseContrast(image_obj, radius_factor)
        elif method in 'gini':
            return self.getModalNoiseGini(image_obj, radius_factor)
        elif method in 'entropy':
            return self.getModalNoiseEntropy(image_obj, radius_factor)
        else:
            raise ValueError('Incorrect string for method type')

    def getModalNoiseTophat(self, image_obj=None, output='array', radius_factor=0.95):
        """Finds modal noise of image assumed to be a tophat
        
        Modal noise is defined as the variance across the fiber face normalized
        by the mean across the fiber face

        Args:
            image_obj (optional): ImageAnalysis object to be used
            output: chooses whether to output as 'array' or 'parameter'
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            array: (circle_fit, image_array) 2D numpy arrays of the best fit
                tophat and the fiber image zoomed in to relevant area
            parameter: STDEV / MEAN for the intensities inside the fiber face
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
       
        intensity_array = self.getIntensityArray(image_array, x0, y0, radius*radius_factor)
        
        if len(output) < 3:
            raise ValueError('Incorrect output string')

        elif output in 'array': 
            circle_fit = intensity_array.mean() * self.circleArray(self.getMeshGrid(image_array),
                                                                   x0, y0, radius, res=10)
            image_array, x0_new, y0_new = self.cropImage(image_array, x0, y0, radius*self.plot_buffer)
            circle_fit = self.cropImage(circle_fit, x0, y0, radius*self.plot_buffer)[0]
            self.showImageArray(image_array)
            self.showImageArray(circle_fit)

            self.plotOverlaidCrossSections(image_array, circle_fit, y0_new, x0_new)
            return circle_fit, image_array

        elif output in 'parameter':
            return intensity_array.std() / intensity_array.mean()

        else:
            raise ValueError('Incorrect output string')

    def getModalNoiseGradient(self, image_obj=None, output='array', radius_factor=0.95):
        """Finds modal noise of image using the image gradient

        Args:
            image_obj (optional): ImageAnalysis object to be used
            output: chooses whether to output as 'array' or 'parameter'
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            array: (gradient_array, image_array) 2D numpy array representing magnitude of the gradient
            parameter: STDEV / MEAN for the gradient in the fiber image
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        image_array, x0, y0 = self.cropImage(image_array, x0, y0, radius*self.plot_buffer)

        gradient_y, gradient_x = np.gradient(image_array)
        gradient_array = np.sqrt(gradient_x**2 + gradient_y**2)

        if len(output) < 3:
            raise ValueError('Incorrect output string')

        elif output in 'array':
            self.showImageArray(gradient_array)
            self.plotOverlaidCrossSections(image_array, gradient_array, y0, x0)
            return gradient_array, image_array

        elif output in 'parameter':
            intensity_array = self.getIntensityArray(gradient_array, x0, y0, radius*radius_factor)
            image_intensity_array = self.getIntensityArray(image_array, x0, y0, radius*radius_factor)
            return intensity_array.std() / image_intensity_array.mean()

        else:
            ValueError('Incorrect output string')

    def getModalNoiseFFT(self, image_obj=None, output='array', radius_factor=1.05):
        """Finds modal noise of image using the image's power spectrum
        
        Args:
            image_obj (optional): ImageAnalysis object to be used
            output: chooses whether to output as 'array' or 'parameter'
            radius_factor (optional): fraction of the radius outside which
                the array is padded with zeros

        Returns:
            array: (fft_array, freq_array) where fft_array is the normalized
                azimuthally averaged power spectrum and freq_array are the
                respective frequencies in 1/um
            parameter: finds the Gini coefficient for the 2D power spectrum
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        height, width = image_array.shape

        image_array, x0, y0 = self.cropImage(image_array, x0, y0, radius*radius_factor)
        image_array = self.isolateCircle(image_array, x0, y0, radius*radius_factor)
        height, width = image_array.shape

        image_array = self.applyWindow(image_array)

        fft_length = 8 * min(height, width)
        fft_array = np.fft.fftshift(np.abs(np.fft.fft2(image_array, s=(fft_length, fft_length), norm='ortho')))
        fx0 = fft_length/2
        fy0 = fft_length/2

        max_freq = fft_length/2     

        if len(output) < 3:
            raise ValueError('Incorrect output string')

        elif output in 'array':
            bin_width = 1
            list_len = int(max_freq / bin_width) + 1

            fft_list = np.zeros(list_len).astype('float64')
            weight_list = np.zeros(list_len).astype('float64')
            freq_list = bin_width * np.arange(list_len).astype('float64')

            bottom_right = fft_array[fy0:fy0+max_freq, fx0:fx0+max_freq]
            bottom_left = fft_array[fy0:fy0+max_freq, fx0-max_freq+1:fx0+1][:, ::-1]
            top_left = fft_array[fy0-max_freq+1:fy0+1, fx0-max_freq+1:fx0+1][::-1, ::-1]
            top_right = fft_array[fy0-max_freq+1:fy0+1, fx0:fx0+max_freq][::-1, :]

            fft_array = (bottom_right + bottom_left + top_left + top_right) / 4.0
            #self.showImageArray(np.log(fft_array))

            for i in xrange(max_freq):
                for j in xrange(i+1):
                    freq = np.sqrt(i**2 + j**2)
                    if freq <= max_freq:
                        fft_list[int(freq/bin_width)] += fft_array[j, i] + fft_array[i, j]
                        weight_list[int(freq/bin_width)] += 2.0

            # Remove bins with nothing in them
            mask = (weight_list > 0.0).astype('bool')
            weight_list = weight_list[mask]
            freq_list = freq_list[mask]
            fft_list = fft_list[mask] / weight_list # Average out

            fft_list /= fft_list.max() # Normalize
            freq_list /= fft_length * image_obj.pixel_size / image_obj.magnification # Get frequencies in 1/um

            self.plotFFT([freq_list], [fft_list], labels=['Modal Noise Power Spectrum'])

            return fft_list, freq_list

        elif output in 'parameter':
            return self.getGiniCoefficient(self.getIntensityArray(fft_array, fx0, fy0, max_freq))

        else:
            ValueError('Incorrect output string')

    def getModalNoisePolynomial(self, image_obj=None, output='array', radius_factor=0.95, deg=4):
        """Finds modal noise of image using polynomial fit
        
        Crops image exactly around the circumference of the circle and fits a
        polynomial to the 2D image. Modal noise is then defined as the STDEV
        in the difference between the original image and the polynomial fit
        normalized by the mean value inside the fiber face

        Args:
            image_obj (optional): ImageAnalysis object to be used            
            output: chooses whether to output as 'array' or 'parameter'
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            array: (poly_fit, image_array) 2D numpy arrays of the best fit
                polynomial and the fiber image zoomed in to relevant area
            parameter: STDEV for the difference between the fiber image and
                poly_fit divided by the mean of the fiber image intensities
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        radius *= radius_factor / np.sqrt(2)

        image_array, x0, y0 = self.cropImage(image_array, x0, y0, radius)

        poly_fit = self.getPolynomialFit(image_array, deg=deg, x0=x0, y0=y0)

        if len(output) < 3:
            raise ValueError('Incorrect output string')

        elif output in 'array':
            self.plotOverlaidCrossSections(image_array, poly_fit, radius, radius)
            return poly_fit, image_array

        elif output in 'parameter':
            diff_array = image_array - poly_fit

            intensity_array = self.getIntensityArray(diff_array, x0, y0, radius * np.sqrt(2))
            image_intensity_array = self.getIntensityArray(image_array, x0, y0, radius * np.sqrt(2))

            return intensity_array.std() / image_intensity_array.mean()

        else:
            raise ValueError('Incorrect output string')

    def getModalNoiseGaussian(self, image_obj=None, output='array', radius_factor=0.95):
        """Finds modal noise of image using gaussian fit
        
        Crops image exactly around the circumference of the circle and fits a
        gaussian to the 2D image. Modal noise is then defined as the STDEV
        in the difference between the original image and the gaussian fit
        normalized by the mean value inside the fiber face

        Args:
            image_obj (optional): ImageAnalysis object to be used            
            output: chooses whether to output as 'array' or 'parameter'
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            array: (gauss_fit, image_array) 2D numpy arrays of the best fit
                polynomial and the fiber image zoomed in to relevant area
            parameter: STDEV for the difference between the fiber image and
                gauss_fit divided by the mean of the fiber image intensities
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        radius *= radius_factor / np.sqrt(2)

        image_array, x0, y0 = self.cropImage(image_array, x0, y0, radius)

        gauss_fit = self.getGaussianFit(image_array)

        if len(output) < 3:
            raise ValueError('Incorrect output string')

        elif output in 'array':
            self.showImageArray(gauss_fit)
            self.plotOverlaidCrossSections(image_array, gauss_fit, radius, radius)
            return gauss_fit, image_array

        elif output in 'parameter':
            diff_array = image_array - gauss

            intensity_array = self.getIntensityArray(diff_array, x0, y0, radius)
            image_intensity_array = self.getIntensityArray(image_array, x0, y0, radius)

            return intensity_array.std() / image_intensity_array.mean()

        else:
            raise ValueError('Incorrect output string')

    def getModalNoiseGini(self, image_obj=None, radius_factor=0.95):
        """Find modal noise of image using Gini coefficient

        Args:
            image_obj (optional): ImageAnalysis object to be used
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            array: 2D numpy array zoomed into the fiber face
            parameter: Gini coefficient for intensities inside fiber face
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        radius *= radius_factor        

        intensity_array = self.getIntensityArray(image_array, x0, y0, radius)

        return self.getGiniCoefficient(intensity_array)

    def getModalNoiseContrast(self, image_obj=None, radius_factor=0.95):
        """Finds modal noise of image using Michelson contrast
        
        Modal noise is defined as (I_max - I_min) / (I_max + I_min)

        Args:
            image_obj (optional): ImageAnalysis object to be used
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            parameter: (I_max - I_min) / (I_max + I_min) for intensities inside
                fiber face
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        radius *= radius_factor        
           
        intensity_array = self.getIntensityArray(image_array, x0, y0, radius)

        return (intensity_array.max() - intensity_array.min()) / (intensity_array.max() + intensity_array.min())     

    def getModalNoiseEntropy(self, image_obj=None, radius_factor=0.95):
        """Find modal noise of image using hartley entropy

        Args:
            image_obj (optional): ImageAnalysis object to be used
            radius_factor (optional): fraction of the radius inside which the
                modal noise calculation will be made

        Returns:
            modal noise parameter
        """
        if image_obj is None:
            image_obj = self.image_obj

        image_array, y0, x0, radius = self.getImageData(image_obj)
        radius *= radius_factor

        intensity_array = self.getIntensityArray(image_array, x0, y0, radius)
        intensity_array = intensity_array / intensity_array.sum()
        return (-intensity_array * np.log10(intensity_array)).sum()

#=============================================================================#
#==== Modal Noise Test =======================================================#
#=============================================================================#

if __name__ == '__main__':
    from ImageAnalysis import ImageAnalysis
    import os as os
    import matplotlib.pyplot as plt
    plt.rc('font', size=16, family='sans-serif')
    plt.rc('xtick', labelsize=14)
    plt.rc('ytick', labelsize=14)
    plt.rc('lines', lw=2)

    calibration_folder = "Calibration/TIF/"
    image_folder = '../Alignment Images/2016-07-12/'

    nf_led_images = []
    for i in xrange(3):
        nf_led_images.append(image_folder + 'nf_led_0um_' + str(i) + '_80ms.tif')

    nf_laser_images = []
    nf_laser_images_agitated = []
    for i in xrange(10):
        nf_laser_images.append(image_folder + 'nf_laser_noagitation_' + str(i) + '_1.8ms.tif')
        nf_laser_images_agitated.append(image_folder + 'nf_laser_agitation_' + str(i) + '_1.8ms.tif')    

    nf_dark_images = []
    nf_ambient_images = []
    for i in xrange(3):
        nf_dark_images.append(calibration_folder + 'nf_dark_' + str(i) + '_10ms.tif')
        nf_ambient_images.append(image_folder + 'nf_ambient_' + str(i) + '_1.8ms.tif')

    nf_flat_images = None
    #for i in xrange(8):
    #    nf_flat_images.append(calibration_folder + 'nf_flat_' + str(i) + '_1ms.tif')

    LED_nf = ImageAnalysis(nf_led_images, nf_dark_images,
                           nf_flat_images, nf_ambient_images,
                           magnification=10)
    print 'LED image initialized'
    laser_nf_agitated = ImageAnalysis(nf_laser_images_agitated, nf_dark_images,
                                      nf_flat_images, nf_ambient_images,
                                      magnification=10)
    print 'Agitated laser image initialized'
    laser_nf = ImageAnalysis(nf_laser_images, nf_dark_images,
                             nf_flat_images, nf_ambient_images,
                             magnification=10)
    print 'Unagitated laser image initialized'
    image_array, x0, y0, radius = ModalNoise.getImageData(LED_nf)
    mesh_grid = LED_nf.getMeshGrid()
    circle_nf = ImageAnalysis(NumpyArrayHandler.circleArray(mesh_grid, x0, y0, radius),
                              pixel_size=LED_nf.pixel_size, bit_depth=LED_nf.bit_depth,
                              magnification=10)
    print 'Circle baseline initialized'
    print

    laser_mn = ModalNoise(laser_nf)
    laser_mn_agitated = ModalNoise(laser_nf_agitated)
    LED_mn = ModalNoise(LED_nf)
    circle_mn = ModalNoise(circle_nf)

    r_f = 1.0
    print 'LED FFT'
    LED_fft, LED_freq = LED_mn.getModalNoise(method='fft', output='array', radius_factor=r_f)
    print 'Agitated laser FFT'
    laser_ag_fft, laser_ag_freq = laser_mn_agitated.getModalNoise(method='fft', output='array', radius_factor=r_f)
    print 'Unagitated laser FFT'
    laser_fft, laser_freq = laser_mn.getModalNoise(method='fft', output='array', radius_factor=r_f)
    print 'Circle FFT'
    circle_fft, circle_freq = circle_mn.getModalNoise(method='fft', output='array', radius_factor=r_f)
    print 'Combined'

    NumpyArrayHandler.plotFFT([LED_freq, laser_ag_freq, laser_freq, circle_freq],
                              [LED_fft, laser_ag_fft, laser_fft, circle_fft],
                              ['LED', 'Agitated laser', 'Unagitated laser', 'Baseline'])

    for method in ['tophat', 'gaussian', 'polynomial', 'gradient']:
        print
        print 'Method:', method
        print 'LED'
        _, _ = LED_mn.getModalNoise(method=method, output='array', deg=8)
        print 'Agitated Laser'
        _, _ = laser_mn_agitated.getModalNoise(method=method, output='array', deg=8)
        print 'Unagitated Laser'
        _, _ = laser_mn.getModalNoise(method=method, output='array', deg=8)

    

    