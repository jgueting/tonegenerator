import numpy as np

def get_dom_freq(data_block, samplerate):
    # calculating fourier transform
    fourier = np.fft.rfft(data_block)

    # calculating dominant frequency
    max_bin_index = np.argmax(np.absolute(fourier))
    coarse_freq = np.fft.rfftfreq(data_block.size, 1. / samplerate)[max_bin_index]
    freq_adjuster = ((np.pi / 2 + np.angle(fourier[max_bin_index])) / np.pi) / data_block.size * samplerate

    return coarse_freq + freq_adjuster

if __name__ == '__main__':
    import numpy.random as npr
    from helpers.converter import ToneFrequencyConverter

    converter = ToneFrequencyConverter()

    ### simulate signal
    # time line
    sample_rate = 96000.  #frames per second
    time = np.arange(0., .1, 1. / sample_rate, dtype=float)  #time values in seconds
    # print(time)

    # defining the signal
    signal_frequency = 440.0  #Hz
    signal_amplitude = 1.

    signal = signal_amplitude * np.sin(2 * np.pi * signal_frequency * time)
    # print(signal)

    # defining noise
    noise = 2 * (1 - 2 * npr.random_sample(time.size))
    # print(noise)

    ### "measure" frequency
    converter.frequency = get_dom_freq(signal + noise, sample_rate)
    print(f'tone: {converter.tone}')
    print(f'frequency: {converter.frequency:7.5f} Hz')
