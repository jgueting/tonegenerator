import matplotlib
matplotlib.use('Qt5Agg')

import queue
import sys

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as ss
import sounddevice as sd


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

channels = [1]       # input channels to plot
device = 0           # input device (numeric ID or substring)
window = 100         # visible time slot (ms)
interval = 50        # minimum time between plot updates (ms)
blocksize = None     # block size (in samples)
samplerate = 44100   # sampling rate of audio device
downsample = 1       # display every Nth sample

mapping = [c - 1 for c in channels]  # Channel numbers start with 1
q = queue.Queue()


def audio_callback(indata, frames, time, status):
    """This is called (from a separate thread) for each audio block."""
    if status:
        print(status, file=sys.stderr)
    # Fancy indexing with mapping creates a (necessary!) copy:
    q.put(indata[::downsample, mapping])


def update_plot(frame):
    """This is called by matplotlib for each plot update.

    Typically, audio callbacks happen more frequently than plot updates,
    therefore the queue tends to contain multiple blocks of audio data.

    """
    global plotdata
    global magnitude
    global peak_tracker

    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break
        shift = len(data)
        plotdata = np.roll(plotdata, -shift, axis=0)
        plotdata[-shift:, :] = data

    # calc the fourier-transform
    fourier = np.fft.rfft(plotdata, axis=0)

    # to plot the power spectrum calc the magnitude values
    magnitude = np.absolute(fourier) / plotdata.size

    # find peaks to show their frequency
    peaks = list(ss.find_peaks(magnitude.reshape(magnitude.size), threshold=.02)[0])

    # check tracked peaks against newly detected peaks
    for tracked in peak_tracker:
        index = -1
        for peak in peaks:
            # raise tracked peaks if existing
            if abs(tracked['index'] - peak) <= 2:
                tracked['index'] = peak
                if tracked['weight'] < 5:
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
        if tracked['weight'] >= 5:
            tracked['active'] = True
        if tracked['weight'] < 3:
            tracked['active'] = False

    # print(f'left over newly detected peaks: {peaks}')

    # add new peaks to the tracker
    for peak in peaks:
        mag = float(magnitude[peak])
        peak_tracker.append({'index': peak,
                             'weight': 2,
                             'active': False,
                             'mag': mag if mag < .4 else .4
                             })

    # remove non-existing peaks from tracker
    index = 0
    while index < len(peak_tracker):
        if peak_tracker[index]['weight'] <= 0:
            peak_tracker.pop(index)
        else:
            index += 1

    # print(f'tracked peaks (post): {[tracked["index"] for tracked in peak_tracker]}')
    for i in range(5):
        if i in range(len(peak_tracker)) and peak_tracker[i]['active']:
            freq = float(frequency[peak_tracker[i]['index']])
            peak_tracker[i]['mag'] += (float(magnitude[peak_tracker[i]['index']]) - peak_tracker[i]['mag']) * .08
            annotations[i].xy = (freq, peak_tracker[i]['mag'])
            annotations[i].set_position((freq, peak_tracker[i]['mag']))
            annotations[i]._text = f"{freq:2.0f}±5Hz"
        else:
            annotations[i]._text = ''

    for column, line in enumerate(lines):
        line.set_ydata(magnitude[:, column])
    return lines, annotations


try:
    if samplerate is None:
        device_info = sd.query_devices(device, 'input')
        samplerate = device_info['default_samplerate']

    length = int(window * samplerate / (1000 * downsample))
    plotdata = np.zeros((length, len(channels)))
    # magnitude = np.absolute(np.fft.rfft(plotdata, axis=0, norm='ortho'))
    magnitude = np.absolute(np.fft.rfft(plotdata, axis=0)) / plotdata.size
    frequency = np.fft.rfftfreq(plotdata.size, 1. / samplerate).reshape(-1, 1)

    fig, ax = plt.subplots()
    lines = ax.plot(frequency, magnitude)
    if len(channels) > 1:
        ax.legend(['channel {}'.format(c) for c in channels],
                  loc='lower left', ncol=len(channels))
    ax.set_xscale('log')
    ax.set_xlabel('Frequency [Hz]')

    peak_tracker = []
    annotations = [ax.annotate('', (20., .0),
                             rotation='vertical',
                             horizontalalignment='right',
                             fontsize = 'large')
                   for i in range(5)]
    # ax.set_yscale('log')
    ax.axis((20, 20000 if max(frequency) >= 20000 else max(frequency), 0., .5))
    ax.set_yticks([0])
    ax.yaxis.grid(True)
    ax.tick_params(bottom=True, top=False, labelbottom=True,
                   right=False, left=False, labelleft=False)
    fig.tight_layout(pad=1)

    stream = sd.InputStream(
        device=device, channels=max(channels),
        samplerate=samplerate, callback=audio_callback)
    plot_ani = FuncAnimation(fig, update_plot, interval=interval, blit=False)
    with stream:
        plt.show()
except Exception as e:
    print(type(e).__name__ + ': ' + str(e))
