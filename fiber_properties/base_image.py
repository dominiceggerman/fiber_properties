"""base_image.py was written by Ryan Petersburg for use with fiber
characterization on the EXtreme PREcision Spectrograph
"""
from ast import literal_eval
from collections import Iterable
from datetime import datetime
import numpy as np
from PIL import Image
from astropy.io import fits
from .input_output import save_image_object, save_image, save_data, load_image_object
from .numpy_array_handler import mesh_grid_from_array
from .plotting import show_image
from .containers import convert_pixels_to_units, convert_microns_to_units

class BaseImage(object):
    """Base class for any image.

    Attributes
    ----------
    image_input : str
    pixel_size : float
    camera : str
    magnification : float

    object_file : string
        File location of the saved object. Only set if self.save_object is
        called
    image_file : string
        File location of the saved image. Only set if self.save_image is called
    data_file : string
        File location of the BaseImage data. Only set if self.save_data is
        called

    height : float
    width : float
    subframe_x : int
    subframe_y : int
    exp_time : float (seconds)
    bit_depth : int
    date_time : datetime.datetime object
    temp : float (Celcius)
    num_images : int
    folder : str
    test : str

    Args
    ----
    image_input : str, array_like, or None
        The input used to set the image array. Typically a string representing
        the file location or a list of these strings. See 
        self.convert_image_to_array() for details
    pixel_size : number, optional
        The side length of each CCD pixel in microns. This value should be
        contained in the image header, but if not, it needs to be defined
        upon initialization
    camera : None or str {'in','nf','ff'}, optional
        A string denoting the FCS camera type. Decides the magnification
        parameter (since it is known for the input and near field cameras),
        but otherwise is only used if printing or saving this information
        is necessary
    magnification : number, optional
        The magnification of the camera. Can also be set by choosing 'in' or
        'nf' for camera
    image_data : str, optional
        File location of previously calculated image data. Must be either a
        python pickle or text file containing a dictionary with image
        information formatted like the attributes in FiberImage
    """
    def __init__(self, image_input, pixel_size=None, camera=None,
                 magnification=None, image_data=None):
        self.image_input = image_input
        self.pixel_size = pixel_size
        self.camera = camera
        self.magnification = magnification

        self.image_file = None
        self.object_file = None
        self.data_file = None

        self.height = None
        self.width = None
        self.subframe_x = None
        self.subframe_y = None
        self.exp_time = None
        self.bit_depth = None
        self.date_time = None
        self.temp = None
        self.num_images = None
        self.folder = None
        self.test = None

        if image_data is None:
            self.set_image_info(image_input)
        else:
            self.load_data(image_data)

    def get_image(self):
        """Return the raw image without corrections or filtering.

        Returns
        -------
        uncorrected_image : 2D numpy array
            Raw image or average of images (depending on image_input)
        """
        if self.image_file is not None:
            return self.convert_image_to_array(self.image_file)
        return self.convert_image_to_array(self.image_input)

    def set_image_info(self, image_input):
        """Sets image info using convert_image_to_array()

        Args
        ----
        image_input : str, array_like, or None
            See class definition for details
        """
        self.convert_image_to_array(image_input, True)

        if self.magnification is None:
            if self.camera == 'nf' or self.camera == 'in':
                self.magnification = 10.0
            else:
                self.magnification = 1.0

    #=========================================================================#
    #==== Saving and Loading Data to File ====================================#
    #=========================================================================#

    def save(self):
        """Save the object, image, and data using the predetermined file names."""
        self.save_object()
        self.save_image()
        self.save_data()

    def save_object(self, file_name=None):
        """Pickle the entire BaseImage object.

        Saves
        -----
        self: BaseImage
            the entire object as .pkl
        """
        if file_name is None and self.object_file is None:
            self.object_file = self.folder + self.get_camera() + '_object.pkl'
        elif file_name is not None:
            self.object_file = file_name
        save_image_object(self, self.object_file)

    def save_image(self, file_name=None):
        """Save the corrected image as FITS

        Args
        ----
        file_name : {None, string}, optional
            The file name which is used to store the images. The file extension
            should be either '.fit' or '.tif'

        Saves
        -----
        image : 2D numpy.ndarray
            as FITS or TIFF
        """
        if file_name is None and self.image_file is None:
            file_name = self.folder + self.get_camera() + '_corrected.fit'
        elif file_name is None:
            file_name = self.image_file
        save_image(self.get_image(), file_name)
        if file_name.endswith('.fit'):
            self.image_file = file_name

    def set_image_file(self, image_file):
        """Sets the image file string

        Only call if an image has been properly calibrated and saved to file

        Args
        ----
        image_file : str

        Raises
        ------
        RuntimeError
            If the file is not FITS
        """
        if not image_file.endswith('.fit'):
            raise RuntimeError('Please set image file to FITS file')
        self.image_file = image_file

    def save_data(self, file_name=None):
        """Pickle the data and also save the data as a text file dictionary

        Args
        ----
        file_name : {None, string}, optional
            The file name which is used to store the images. The file extension
            should be either '.txt' or '.pkl'

        Saves
        -----
        _image_info : dict
        _analysis_info : dict
        _edges : dict
        _center : dict
        _diameter : dict
        _centroid : dict
        _array_sum : dict

        """
        if file_name is None and self.data_file is None:
            file_name = self.folder + self.get_camera() + '_data.txt'
        elif file_name is None:
            file_name = self.data_file
        save_data(self, file_name)
        self.data_file = file_name

    def load_data(self, file_name=None):
        """Loads data from a text file containing a python dictionary

        Args
        ----
        file_name : string
            The file where the data is located

        Raises
        ------
        RuntimeError
            if the file name does not end in '.txt'
        """
        if file_name is None:
            file_name = self.data_file

        if file_name.endswith('.txt'):
            with open(file_name, 'r') as load_file:
                data = literal_eval(load_file.read())
        else:
            raise RuntimeError('Incorrect file type to load into object')

        for key in data:
            setattr(self, key, data[key])

    #=========================================================================#
    #==== Private Variable Getters ===========================================#
    #=========================================================================#

    def get_pixel_size(self):
        """Return the pixel size in microns"""
        if self.pixel_size is None:
            raise RuntimeError('Pixel Size needs to be set externally')
        return self.pixel_size

    def get_height(self, units='pixels'):
        """Return the image height in units"""
        return self.convert_pixels_to_units(self.height, units)

    def get_width(self, units='pixels'):
        """Return the image width in units"""
        return self.convert_pixels_to_units(self.width, units)

    def get_magnification(self):
        """Return the magnification"""
        if self.magnification is None:
            raise RuntimeError('Magnification needs to be set externally')
        return self.magnification

    def set_magnification(self, value):
        """Sets the magnification of the image"""
        self.magnification = value

    def get_camera(self):
        """Return the string denoting the camera type"""
        if self.camera is None:
            raise RuntimeError('Camera needs to be set externally')
        return self.camera

    def get_mesh_grid(self):
        """Return a meshgrid of the same size as the stored image"""
        return mesh_grid_from_array(self.get_image())

    #=========================================================================#
    #==== Image Conversion Algorithms ========================================#
    #=========================================================================#

    def convert_image_to_array(self, image_input, return_image=True,
                               set_attributes=False):
        """Converts an image input to a numpy array or None

        Args
        ----
        image_input : {None, 1D iterable, 2D iterable, string}
            Inputting None simply returns None. Inputting a string of a file name
            returns the image contained within that file. Inputting an iterable
            containing strings returns all of the images in those files co-added
            together. Inputting a 2D iterable returns a 2D numpy.ndarray of the
            input iterable. Inputting a 1D iterable containing 2D iterables returns
            those 2D iterables co-added together in a single numpy.ndarray
        set_attributes : boolean, optional (default=False)
            Whether or not to include relevant information from the image header in
            the return. Automatically False if the image_input is an ndarray (and
            therefore without a header).

        Returns
        -------
        image : 2D numpy.ndarray or None
            2D numpy array if the image input checks out, None otherwise
        image_info : ImageInfo, optional
            ImageInfo object containing information from the image header
        """
        image = None

        if image_input is None:
            pass

        # Image input is a single file name
        elif isinstance(image_input, basestring):
            if image_input.endswith('.pkl') or image_input.endswith('.p'):
                old_im_obj = load_image_object(image_input)
                for attribute in vars(old_im_obj):
                    setattr(self, attribute, getattr(old_im_obj, attribute))
                image = self.get_image()
            else:
                image = self.image_from_file(image_input, set_attributes)
            if set_attributes:
                self.num_images = 1

        # Image input is a sequence of file names
        elif isinstance(image_input, Iterable) and isinstance(image_input[0], basestring):
            list_len = float(len(image_input))
            image = self.image_from_file(image_input[0], set_attributes)
            if set_attributes:
                self.num_images = list_len
            image /= list_len
            for image_string in image_input[1:]:
                image += self.image_from_file(image_string) / list_len

        # Image input is a single array
        elif isinstance(image_input, Iterable) and len(np.array(image_input).shape) == 2:
            image = np.array(image_input)
            if set_attributes:
                self.num_images = 1.0

        # Image input is a sequence of arrays
        elif isinstance(image_input, Iterable) and isinstance(image_input[0], Iterable):
            list_len = float(len(image_input))
            image_input = np.array(image_input)
            image = image_input[0] / list_len
            for image in image_input[1:]:
                image += image / list_len
            if set_attributes:
                self.num_images = list_len

        else:
            raise RuntimeError('Incorrect type for image input')

        if set_attributes:
            if image is not None:
                self.height, self.width = image.shape
        return image

    def image_from_file(self, image_string, set_attributes=False):
        """Returns image from file as 2D np.ndarray

        Args
        ----
        image_string : string
            File location of the image (FITS or TIFF) to be converted
        set_attributes : boolean, optional
            whether or not to include relevant information from the image header in
            the return

        Returns
        -------
        image : 2D numpy.ndarray
            2D numpy array of the file's image
        image_info : ImageInfo
            Object containing the information from the image header

        """
        if image_string[-3:] == 'fit':
            raw_image = fits.open(image_string, ignore_missing_end=True)[0]
            image = raw_image.data.astype('float64')
            if set_attributes:
                header = dict(raw_image.header)

        elif image_string[-3:] == 'tif':
            raw_image = Image.open(image_string)
            image = np.array(raw_image).astype('float64')
            if set_attributes:
                # Complicated way to get the header from a TIF image as a dictionary
                header = dict([i.split('=') for i in raw_image.tag[270][0].split('\r\n')][:-1])
                header['BITPIX'] = int(raw_image.tag[258][0])

        else:
            raise ValueError('Incorrect image file extension')

        if set_attributes:
            self.folder = '/'.join(image_string.split('/')[:-1]) + '/'

            if 'XORGSUBF' in header:
                self.subframe_x = int(header['XORGSUBF'])
                self.subframe_y = int(header['YORGSUBF'])

            self.bit_depth = int(header['BITPIX'])
            if 'XPIXSZ' in header:
                self.pixel_size = float(header['XPIXSZ'])
            if 'EXPTIME' in header:
                self.exp_time = float(header['EXPTIME'])
            if 'DATE-OBS' in header:
                try:
                    self.date_time = datetime.strptime(header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S.%f')
                except ValueError:
                    self.date_time = datetime.strptime(header['DATE-OBS'], '%Y-%m-%dT%H:%M:%S')
            if 'CCD-TEMP' in header:
                self.temp = float(header['CCD-TEMP'])

            if self.camera is None:
                image_string_list = image_string.split('/')
                if 'TELESCOP' in header:
                    self.camera = str(header['TELESCOP'])
                elif 'nf' in image_string_list or 'nf_' in image_string_list[-1]:
                    self.camera = 'nf'
                elif 'ff' in image_string_list or 'ff_' in image_string_list[-1]:
                    self.camera = 'ff'
                elif 'in' in image_string_list or 'in_' in image_string_list[-1]:
                    self.camera = 'in'

            if 'OBJECT' in header:
                self.test = str(header['OBJECT'])

        return image

    def show_image(self, image=None):
        """Shows the calibrated image"""
        if image is None:
            image = self.get_image()
        show_image(image)

    def convert_pixels_to_units(self, value, units):
        """Returns the pixel value in the proper units"""
        return convert_pixels_to_units(value,
                                       self.pixel_size,
                                       self.magnification,
                                       units)

    def convert_microns_to_units(self, value, units):
        """Returns the micron value in the proper units"""
        return convert_microns_to_units(value,
                                        self.pixel_size,
                                        self.magnification,
                                        units)


