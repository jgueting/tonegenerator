import matplotlib
matplotlib.use('Qt5Agg')

import queue
import sys

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as ss
import sounddevice as sd
from helpers.converter import ToneFrequencyConverter


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

device = 0             # input device (numeric ID or substring)
channels = [1]         # input channels to plot

window = 200           # visible time slot (ms)
interval = 50          # minimum time between plot updates (ms)
samplerate = 44100     # sampling rate of audio device
upsampling = 4         # factor for upsampling the input data to get more accurate frequency values
y_min_level = -40      # minium power level to be shown

# peak tracker
peaks_tracked = 1
activate = 5
sleep = 3

mapping = [c - 1 for c in channels]  # Channel numbers start with 1
q = queue.Queue()


def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    # Fancy indexing with mapping creates a (necessary!) copy:
    q.put(indata[::, mapping])


def update_plot(frame):
    """This is called by matplotlib for each plot update.

    Typically, audio callbacks happen more frequently than plot updates,
    therefore the queue tends to contain multiple blocks of audio data.

    """
    global plotdata
    global magnitude
    global peak_tracker
    global converter

    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break
        shift = len(data)
        plotdata = np.roll(plotdata, -shift, axis=0)
        plotdata[-shift:, :] = data

    length = plotdata.size

    # calc magnitudes in dB to plot the power spectrum
    magnitude = 10 * np.log10(np.absolute(np.fft.rfft(plotdata, axis=0)) / length)

    # find fundamental frequency
    freqdata = plotdata.reshape(length)
    freqdata = ss.resample(freqdata, freqdata.size * upsampling)
    periods = ss.correlate(freqdata, freqdata, mode='full')
    periods = periods[len(periods) // 2:]
    peaks = ss.find_peaks(periods, threshold=.2)[0]
    proms = ss.peak_prominences(periods, peaks)[0]
    if peaks.size > 0:
        peaks = [peaks[np.argmax(proms)]]
    else:
        peaks = []

    # check tracked peaks against newly detected peaks
    for tracked in peak_tracker:
        index = -1
        for peak in peaks:
            # raise tracked peaks if existing
            if abs(tracked['index'] - peak) <= 2:
                tracked['index'] = peak
                if tracked['weight'] < activate:
                    tracked['weight'] += 1
                index = peaks.index(peak)
                break

        if index > -1:
            # remove newly detected peak if already tracked
            peaks.pop(index)
        else:
            # degrade tracked peaks if not existing
            tracked['weight'] -= 1

        # switch them on/off according to their weight
        if tracked['weight'] >= activate:
            tracked['active'] = True
        if tracked['weight'] < sleep:
            tracked['active'] = False

    # print(f'left over newly detected peaks: {peaks}')

    # add new peaks to the tracker
    for peak in peaks:
        peak_tracker.append({'index': peak,
                             'weight': 2,
                             'active': False,
                             'freq': (samplerate * upsampling) / peak
                             })

    # remove non-existing peaks from tracker
    index = 0
    while index < len(peak_tracker):
        if peak_tracker[index]['weight'] <= 0:
            peak_tracker.pop(index)
        else:
            index += 1

    # display peaks
    for i in range(peaks_tracked):
        if i in range(len(peak_tracker)):
            peak_tracker[i]['freq'] += (((samplerate * upsampling) / peak_tracker[i]['index']) - peak_tracker[i]['freq']) * .07
            annotations[i].xy = (peak_tracker[i]['freq'], y_min_level * .3)
            annotations[i].set_position((peak_tracker[i]['freq'], y_min_level * .3))
            # annotations[i]._text = f"{peak_tracker[i]['freq']:3.1f}Hz"
            converter.frequency = peak_tracker[i]['freq']
            annotations[i]._text = f"{converter.tone}"
        else:
            annotations[i]._text = ''

    for column, line in enumerate(lines):
        line.set_ydata(magnitude[:, column])
    return lines, annotations


try:
    if samplerate is None:
        device_info = sd.query_devices(device, 'input')
        samplerate = device_info['default_samplerate']

    length = int(window / 1000 * samplerate)
    plotdata = np.zeros((length, len(channels)))
    magnitude = np.zeros((length // 2 + 1, len(channels)))
    frequency = np.fft.rfftfreq(plotdata.size, 1. / samplerate).reshape(-1, 1)

    fig, ax = plt.subplots(num='Tuner')
    lines = ax.plot(frequency, magnitude)
    if len(channels) > 1:
        ax.legend(['channel {}'.format(c) for c in channels],
                  loc='lower left', ncol=len(channels))
    ax.set_xscale('log')
    ax.set_xlabel('Frequency [Hz]')
    ax.set_ylabel('Power [dB]')

    peak_tracker = []
    annotations = [ax.annotate('', (20., .0),
                             rotation='vertical',
                             horizontalalignment='right',
                             fontsize = 'large')
                   for i in range(peaks_tracked)]
    ax.axis((20, 20000 if max(frequency) >= 20000 else max(frequency), y_min_level, 0.))
    ax.tick_params(bottom=True, top=False, labelbottom=True,
                   right=False, left=True, labelleft=True)
    fig.tight_layout(pad=0.5)

    converter = ToneFrequencyConverter()

    stream = sd.InputStream(
        device=device, channels=max(channels),
        samplerate=samplerate, callback=audio_callback)
    plot_ani = FuncAnimation(fig, update_plot, interval=interval, blit=False)
    with stream:
        plt.show()
except Exception as e:
    print(type(e).__name__ + ': ' + str(e))
