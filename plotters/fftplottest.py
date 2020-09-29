import matplotlib
matplotlib.use('Qt5Agg')

import queue
import sys

from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
import numpy as np
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
samplerate = 96000   # sampling rate of audio device
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
    global an_x
    global an_y
    global an_freq

    while True:
        try:
            data = q.get_nowait()
        except queue.Empty:
            break
        shift = len(data)
        plotdata = np.roll(plotdata, -shift, axis=0)
        plotdata[-shift:, :] = data

    # magnitude = np.absolute(np.fft.rfft(plotdata, axis=0, norm='ortho'))
    fourier = np.fft.rfft(plotdata, axis=0)
    magnitude = np.absolute(fourier) / plotdata.size
    index = ss.find_peaks(magnitude.reshape(magnitude.size), threshold=0.02)[0]
    freq = float(frequency[index]) + ((np.pi / 2 + float(np.angle(fourier[index]))) / np.pi) / plotdata.size * samplerate

    factor = .2
    an_x += (float(frequency[index]) - an_x) * factor
    an_y += (float(magnitude[index]) - an_y) * factor
    an_freq += (freq - an_freq) * factor
    if an_y > .02:
        annotation.xy = (an_x, an_y)
        annotation.set_position((an_x, an_y + .01 if an_y + .01 <= .5 else .5))
        annotation._text = f'{an_freq:3.1f}Hz'
    else:
        annotation._text = ''
    for column, line in enumerate(lines):
        line.set_ydata(magnitude[:, column])
    return lines, annotation


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
    an_x = 0.
    an_y = 0.
    an_freq = 20.
    annotation = ax.annotate('', (20., .0),
                             rotation='vertical',
                             horizontalalignment='center',
                             fontsize = 'large')
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