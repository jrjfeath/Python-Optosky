import ctypes
import os
import time
import numpy as np

# Contains the device description
class DeviceDescriptor(ctypes.Structure):
    _fields_ = [("serial", ctypes.c_char * 128)]

# Stores information of up to 10 spectrometers
class SpectrumDeviceInfo(ctypes.Structure):
    _fields_ = [
        ("length", ctypes.c_int),
        ("descriptor", DeviceDescriptor * 10)
    ]

# Stores the pointers for the spectrum and error flag
class Spectrumsp(ctypes.Structure):
    _fields_ = [
        ("array", ctypes.POINTER(ctypes.c_int)),
        ("valid_flag", ctypes.c_int)
    ]

class Spectrometer():
    def __init__(self) -> None:
        self.error       : int = 0
        self.pixels      : int = 2047
        self.intensities : np.ndarray = np.zeros((0,self.pixels))
        self.wavelengths : np.ndarray = np.zeros((0,self.pixels))
        try:
            basepath = os.path.dirname(os.path.realpath(__file__))
            self.Spec = ctypes.cdll.LoadLibrary(os.path.join(basepath, 'Driver.dll'))
            print('Loaded DLL!')
        except FileNotFoundError:
            print('DLL not found!')
            self.error = 1
            return
        if self.find_spectrometer():
            return
        if self.connect_spectrometer():
            return
        self.get_wavelength()

    def find_spectrometer(self) -> bool:
        # Pass class as argtype and int as return: 0 Fail, 1 Pass
        self.Spec.findSpectraMeters.argtypes = [ctypes.POINTER(SpectrumDeviceInfo)]
        self.Spec.findSpectraMeters.restype = ctypes.c_int32
        # Create an instance of SpectrumDeviceInfo
        devices = SpectrumDeviceInfo()
        # Call the function
        self.error = self.Spec.findSpectraMeters(ctypes.byref(devices))
        if self.error: 
            print('Could not obtain spectrometer IDs!')
            return 1
        print("Number of devices:", devices.length)
        for i in range(devices.length):
            print(f"Device {i} Serial:", devices.descriptor[i].serial.decode('utf-8'))
        return 0

    def connect_spectrometer(self) -> bool:
        self.Spec.openSpectraMeter.restype = ctypes.c_int32
        self.error = self.Spec.openSpectraMeter()
        if self.error != 1:
            print('Could not connect to spectrometer!')
            return 1
        print('Found spectrometer!')
        self.Spec.initialize.restype = ctypes.c_int32
        self.error = self.Spec.initialize()
        if self.error == 1:
            print('Initialization thread error.')
        elif self.error == 2:
            print('Error reading out current integration time.')
        elif self.error == 4:
            print('Error reading out waveforms correction coefficient.')
        elif self.error == 8:
            print('Error reading out non-linear correction coefficient.')
        elif self.error == 10:
            print('Error reading out wavelength calibration coefficient.')
        elif self.error == 20:
            print('Error reading out dark current correction coefficient')
        elif self.error == 30:
            print('Device not found')
        else:
            print('Device initialised.')
            return 0
        # If there is an error return 1
        if self.error != 0: return 1

    def disconnect_spectrometer(self) -> bool:
        self.Spec.closeSpectraMeter.restype = ctypes.c_int32
        self.error = self.Spec.closeSpectraMeter()
        if self.error != 1:
            print('Could not disconnect to spectrometer!')
            return 1
        print('Device Disconnected.')
        return 0

    def acquire_spectrum(self,integration_time : int = 1000) -> bool:
        self.Spec.getSpectrum.restype = ctypes.c_int32
        self.Spec.findSpectraMeters.argtypes = [ctypes.c_uint32]
        start = time.time()
        self.error = self.Spec.getSpectrum(ctypes.c_int32(integration_time))
        if self.error != 1:
            print('Could not acquire spectrum, is spectrometer busy?')
            return 1
        print('Acquisition started.')
        self.spectrum_ready(start, integration_time)
        if self.error != 1: return 1
        return 0

    def spectrum_ready(self, start, integration_time) -> bool:
        self.error = 0
        self.Spec.getSpectrumDataReadyFlag.restype = ctypes.c_int32
        while start - time.time() < (integration_time * 2):
            self.error = self.Spec.getSpectrumDataReadyFlag()
            time.sleep(0.001)
            if self.error == 1:
                # self.Spec.ClearSpectrumDataReadyFlag()
                break
        if self.error == 0:
            print('Spectrum did not finish, did spectrometer disconnect?')
            return 1
        print('Acquisition completed.')
        return 0
    
    def read_spectrum(self,DarkCorr : bool = False, LinearCorr : bool = False, WaveformCorr : bool = False) -> bool:
        self.Spec.ReadSpectrum.restype = Spectrumsp
        data = self.Spec.ReadSpectrum()
        self.intensities = np.array([data.array[x] for x in range(self.pixels)])
        if data.valid_flag == 0: return 1
        if (not DarkCorr) & (not LinearCorr) & (not WaveformCorr): return 0
        datapower = (ctypes.c_int * 4096)()
        for i in range(4096):
            datapower[i] = data.array[i]
        self.Spec.dataProcess.restype = ctypes.POINTER(ctypes.c_int)
        value = self.Spec.dataProcess(
            datapower, 
            ctypes.c_int32(0), 
            ctypes.c_bool(DarkCorr), 
            ctypes.c_bool(LinearCorr), 
            ctypes.c_bool(WaveformCorr)
        )
        self.intensities = np.array([value[x] for x in range(self.pixels)], dtype = float)
        return 0

    def get_wavelength(self) -> None:
        self.Spec.getWavelength.restype = ctypes.POINTER(ctypes.c_float)
        # Call getWavelength
        p = self.Spec.getWavelength()
        self.wavelengths = np.array([p[x] for x in range(self.pixels)])