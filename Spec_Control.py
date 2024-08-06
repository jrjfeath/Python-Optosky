import matplotlib.pyplot as plt
from DriverApp import Spectrometer

# If there is an error the function returns True (1)

# Connect to the spec
Spec = Spectrometer()
# Acquire a spectrum for X ms
if Spec.acquire_spectrum(1000):
    Spec.disconnect_spectrometer()
    exit()
# Get the spectrum
if Spec.read_spectrum():
    Spec.disconnect_spectrometer()
    exit()
# Disconnect from the spec
Spec.disconnect_spectrometer()

# Plot the spec
plt.plot(Spec.wavelengths, Spec.intensities)
plt.show()