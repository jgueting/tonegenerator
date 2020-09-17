import numpy as np

### simulate signal
# time line
sample_rate = 1000.  #frames per second
time = np.arange(0., 4., 1. / sample_rate, dtype=float)  #time values in seconds
# print(time)

# defining the signal
signal_frequency = 90.010019  #Hz
signal_amplitude = 1.

signal = signal_amplitude * np.sin(2 * np.pi * signal_frequency * time)
# print(signal)


### "measure" frequency
# calculating fourier transform
fourier = np.fft.rfft(signal)

# calc dominant frequency
max_bin_index = np.argmax(np.absolute(fourier))
coars_freq = np.fft.rfftfreq(signal.size, 1. / sample_rate)[max_bin_index]
freq_adjuster = ((np.pi / 2 + np.angle(fourier[max_bin_index])) / np.pi) / signal.size * sample_rate
print(f'frequency: {coars_freq + freq_adjuster:7.5f} Hz')

