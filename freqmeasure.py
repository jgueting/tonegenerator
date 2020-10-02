import numpy as np
import scipy.signal as ss

def get_dom_freq(data_block, samplerate):
    # calculating fourier transform
    fourier = np.fft.rfft(data_block)

    # calculating dominant frequency
    max_bin_index = np.argmax(np.absolute(fourier))
    coarse_freq = np.fft.rfftfreq(data_block.size, 1. / samplerate)[max_bin_index]
    freq_adjuster = ((np.pi / 2 + np.angle(fourier[max_bin_index])) / np.pi) / data_block.size * samplerate

    return coarse_freq + freq_adjuster


def get_per_freq(data_block, samplerate):
    # calculating auto correlation
    periods = ss.correlate(data_block, data_block, mode='full')
    periods = periods[len(periods) // 2:]

    peaks = ss.find_peaks(periods)[0]
    print(f'peaks:\n{peaks}')
    proms = ss.peak_prominences(periods, peaks)[0]
    print(f'proms:\n{proms}')
    fundamental_peak = peaks[np.argmax(proms)]
    print(f'most prominent peak: {fundamental_peak}')

    return samplerate / fundamental_peak



if __name__ == '__main__':
    import numpy.random as npr
    from helpers.converter import ToneFrequencyConverter

    converter = ToneFrequencyConverter()

    ### simulate signal
    # time line
    sample_rate = 100000.  #frames per second
    time = np.arange(0., .1, 1. / sample_rate, dtype=float)  #time values in seconds
    # print(time)

    # defining the signal
    signal_frequency = 100.2  #Hz
    signal_amplitude = 1.

    signal = signal_amplitude * np.sin(2 * np.pi * signal_frequency * time)
    # print(signal)

    # defining noise
    noise = 1 * (1 - 2 * npr.random_sample(time.size))
    # print(noise)

    ### "measure" frequency
    # converter.frequency = get_dom_freq(signal + noise, sample_rate)
    converter.frequency = get_per_freq(signal + noise, sample_rate)
    print(f'tone: {converter.tone}')
    print(f'frequency: {converter.frequency:7.5f} Hz')
