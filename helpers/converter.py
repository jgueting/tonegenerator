import pyparsing as pp
import numpy as np


class ToneFrequencyConverter:
    def __init__(self, base_freq=440.0, amp=.5):
        self.base_freq = base_freq
        self.frequency = base_freq
        self.amplitude = amp
        self.__errors__ =''

        # parser definitions
        no_whites = pp.NotAny(pp.White())
        real = pp.Combine(pp.Word(pp.nums) + pp.Optional(pp.Char(',.') + pp.Word(pp.nums))).setParseAction(lambda t: float(t[0].replace(',', '.')))

        operator = pp.Char('+-')
        cent = (operator + no_whites + real).setParseAction(lambda t: float(t[0] + '1') * t[1] / 100)

        tone_name_offset = {
            'C': -9.,
            'D': -7.,
            'E': -5.,
            'F': -4.,
            'G': -2.,
            'A':  0.,
            'B':  2.
        }
        self.root = np.power(2, 1/12)
        tone_name = pp.Char('CDEFGAB').setParseAction(lambda t: tone_name_offset[t[0]])
        flat_sharp = pp.Char('#b').setParseAction(lambda t: 1. if t[0] == '#' else -1.)
        octave = pp.Char('012345678').setParseAction(lambda t: (int(t[0]) - 4) * 12.)

        self.tone_parser = (tone_name + no_whites + pp.Optional(flat_sharp) + no_whites + octave + pp.Optional(cent)
                            ).setParseAction(lambda t: self.base_freq * np.power(self.root, sum(t))).setResultsName('frequency')

        self.hertz_parser = (real + 'Hz'
                             ).setParseAction(lambda t: t[0]).setResultsName('frequency')

        self.amp_parser = (real + '%'
                           ).setParseAction(lambda t: t[0] / 100.).setResultsName('amplitude')

        self.base_parser = (pp.Literal('b').suppress() + no_whites + self.hertz_parser
                            ).setParseAction(lambda t: t[0]).setResultsName('base_freq')

        self.input_parser = self.tone_parser | self.base_parser | self.hertz_parser | self.amp_parser

    @property
    def base_freq(self):
        return self.__base_freq__

    @base_freq.setter
    def base_freq(self, new_freq):
        if isinstance(new_freq, str):
            try:
                new_freq = self.base_parser.parseString(new_freq)[0]
            except pp.ParseException as e:
                self.__errors__ += f'could not parse "{input}" @ col {e.col}; '
                self.__base_freq__ = 440.

        if isinstance(new_freq, (float, int)):
            upper = 554.3652619537443  # two full steps up from A4=440Hz
            lower = 349.2282314330038  # two full steps down from A4=440Hz
            self.__base_freq__ = new_freq if lower <= new_freq <= upper else lower if new_freq < lower else upper
        else:
            self.__errors__ += f'type error (must be int, float, or string); '
            self.__base_freq__ = 440.

    @property
    def frequency(self):
        return self.__frequency__

    @frequency.setter
    def frequency(self, new_freq):
        if isinstance(new_freq, (float, int)):
            if new_freq > 0.:
                self.__frequency__ = float(new_freq)
            else:
                self.__errors__ += f'input as int or float must be >0; '
                self.__frequency__ = 0.
        elif isinstance(new_freq, str):
            try:
                self.__frequency__ = self.hertz_parser.parseString(new_freq)[0]
            except pp.ParseException as e:
                self.__errors__ += f'could not parse "{input}" @ col {e.col}; '
                self.__frequency__ = 0.
        else:
            self.__errors__ += f'invalid input type: {type(new_freq).__name__}'

    @property
    def tone(self):
        if self.__frequency__ > 0:
            value = np.log10(self.__frequency__ / self.__base_freq__) / np.log10(self.root)
            steps = int(np.round(value))

            cents = str(int(np.round((value - steps) * 100)))
            cents_str = '' if cents == '0' else '+' + cents if not cents.startswith('-') else cents

            octave = int(np.ceil((steps - 2) / 12) + 4)

            names = {
                -9: f'C{octave}',
                -8: f'C#{octave}/Db{octave}',
                -7: f'D{octave}',
                -6: f'D#{octave}/Eb{octave}',
                -5: f'E{octave}',
                -4: f'F{octave}',
                -3: f'F#{octave}/Gb{octave}',
                -2: f'G{octave}',
                -1: f'G#{octave}/Ab{octave}',
                 0: f'A{octave}',
                 1: f'A#{octave}/Bb{octave}',
                 2: f'B{octave}'
            }
            name = names[(steps) - (octave - 4) * 12]

            tone = f'{name} {cents_str}'
        else:
            tone = 'off'
        return tone

    @tone.setter
    def tone(self, new_tone):
        if isinstance(new_tone, str):
            try:
                self.__frequency__ = self.tone_parser.parseString(new_tone)[0]
            except pp.ParseException as e:
                self.__errors__ += f'could not parse "{new_tone}" @ col {e.col}; '
                self.__frequency__ = 0.

    @property
    def amplitude(self):
        return self.__amplitude__

    @amplitude.setter
    def amplitude(self, new_amp):
        if isinstance(new_amp, str):
            try:
                self.__amplitude__ = self.amp_parser.parseString(new_amp)[0]
            except pp.ParseException as e:
                self.__errors__ += f'could not parse "{new_amp}" @ col {e.col}; '
                self.__amplitude__ = .5
        elif isinstance(new_amp, (int, float)):
            self.__amplitude__ = new_amp if 0. <= new_amp <= 1. else 0. if new_amp < 0. else 1.


    @property
    def errors(self):
        errors = self.__errors__
        self.__errors__ = ''
        return errors

    def set(self, input):
        if isinstance(input, str):
            try:
                result = self.input_parser.parseString(input).asDict()
                for attribute in result:
                    setattr(self, attribute, result[attribute])
            except pp.ParseException as e:
                self.__errors__ += f'could not parse "{input}" @ col {e.col}; '
                self.__frequency__ = 0.
        else:
            self.__errors__ += f'invalid input type: {type(input).__name__}'


if __name__ == '__main__':
    print('ToneFrequencyConverter - Test')
    converter = ToneFrequencyConverter()

    # print(converter.base_parser.parseString('b440Hz'))

    new_input = ''
    while not new_input == 'quit':
        new_input = input('>> ')
        if not new_input == 'quit':
            converter.set(new_input)
            print(f'frequency: {converter.frequency:5.3f} Hz')
            print(f'tone: {converter.tone}')
            print(f'base: {converter.base_freq:5.3f} Hz')
            print(f'amp: {converter.amplitude * 100:3.0f}%')
            errors = converter.errors
            if errors:
                print(f'errors: {errors}')
    print('terminated.')
