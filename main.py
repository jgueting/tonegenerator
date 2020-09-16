import sounddevice as sd
import numpy as np
from converter import ToneFrequencyConverter


if __name__ == '__main__':
    print(sd.query_devices())
    deviceID = int(input('choose device (ID): '))
    start_idx = 0
    amplitude = 1.
    base_frequency = 440.0

    converter = ToneFrequencyConverter(base_frequency)

    tone = 'A4'

    converter.set(tone)
    errors = converter.errors
    if errors:
        raise ValueError(f'could not parse "{tone}": {errors}')
    print(f'frequency: {converter.frequency:5.3f} Hz')
    print(f'tone: {converter.tone}')

    print('opening sounddevice...')
    try:
        device = sd.query_devices(deviceID, 'output')
        for key in device:
            print(f'{key}: {device[key]}')
        samplerate = device['default_samplerate']

        def callback(outdata, frames, time, status):
            if status:
                print(status)

            global start_idx
            global frequency
            t = (start_idx + np.arange(frames)) / samplerate
            t = t.reshape(-1, 1)
            outdata[:] = amplitude * np.sin(2 * np.pi * converter.frequency * t)
            start_idx += frames

        input_text = tone

        print('generating sine wave...')
        with sd.OutputStream(device=deviceID, channels=1, callback=callback, samplerate=samplerate):
            while not input_text == 'quit':
                input_text = input('>> ')
                if not input_text == 'quit':
                    converter.set(input_text)
                    errors = converter.errors
                    if errors:
                        print(f'{errors}')
                    print(f'frequency: {converter.frequency:5.3f} Hz')
                    print(f'tone: {converter.tone}')

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'{type(e).__name__}: {e}')
    print('terminated.')