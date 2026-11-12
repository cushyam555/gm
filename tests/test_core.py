import tempfile
import unittest
from pathlib import Path
import mido
from gm_reset.core import reset_midi, convert_file, DEFAULTS


def positions(track, types):
    tick = 0
    events = []
    for msg in track:
        tick += msg.time
        if msg.type in types:
            events.append((tick, msg.type, getattr(msg, 'note', None)))
    return events


class ResetTests(unittest.TestCase):
    def fixture(self, midi_type=1):
        midi = mido.MidiFile(type=midi_type, ticks_per_beat=960)
        midi.tracks.append(mido.MidiTrack([
            mido.MetaMessage('set_tempo', tempo=600000),
            mido.Message('program_change', channel=0, program=40),
            mido.Message('control_change', control=10, value=0, time=20),
            mido.Message('note_on', note=60, velocity=42, time=30),
            mido.Message('sysex', data=[0x43, 0x10], time=15),
            mido.Message('pitchwheel', pitch=2000, time=15),
            mido.Message('note_on', note=60, velocity=0, time=120),
            mido.Message('note_on', note=62, velocity=127, time=20),
            mido.Message('note_off', note=62, velocity=36, time=240),
            mido.Message('control_change', control=121, value=0, time=40),
            mido.MetaMessage('end_of_track', time=60),
        ]))
        return midi

    def test_timing_notes_and_metadata(self):
        original = self.fixture()
        result = reset_midi(original)
        self.assertEqual(positions(original.tracks[0], {'note_on', 'note_off', 'end_of_track', 'set_tempo'}),
                         positions(result.tracks[0], {'note_on', 'note_off', 'end_of_track', 'set_tempo'}))
        self.assertEqual([m.velocity for m in result.tracks[0] if m.type == 'note_on'], [100, 0, 100])
        self.assertEqual(result.ticks_per_beat, 960)
        self.assertEqual([m.program for m in result.tracks[0] if m.type == 'program_change'], [0, 40])
        self.assertEqual(original.tracks[0][3].velocity, 42)

    def test_no_later_controls_and_standard_kit(self):
        original = self.fixture()
        original.tracks.append(mido.MidiTrack([
            mido.Message('program_change', channel=9, program=32, time=50),
            mido.Message('note_on', channel=9, note=38, velocity=10, time=50),
            mido.Message('note_off', channel=9, note=38, time=30)]))
        result = reset_midi(original, 90)
        for track in result.tracks:
            tick = 0
            for msg in track:
                tick += msg.time
                if msg.type in {'control_change', 'sysex', 'pitchwheel'}:
                    self.assertEqual(tick, 0)
        self.assertEqual([m.program for t in result.tracks for m in t if m.type == 'program_change' and m.channel == 9], [0])
        self.assertEqual({m.control: m.value for m in result.tracks[0] if m.type == 'control_change' and m.channel == 0}, DEFAULTS)
        self.assertEqual(positions(original.tracks[1], {'note_on', 'note_off'}), positions(result.tracks[1], {'note_on', 'note_off'}))

    def test_roundtrip_no_overwrite_and_bad_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'เพลง.mid'
            target = Path(folder) / 'เพลง_GM1.mid'
            self.fixture(0).save(source)
            before = source.read_bytes()
            convert_file(source, target)
            self.assertEqual(mido.MidiFile(target).type, 0)
            with self.assertRaises(FileExistsError):
                convert_file(source, target)
            with self.assertRaises(ValueError):
                convert_file(source, source)
            self.assertEqual(source.read_bytes(), before)
            source.write_bytes(b'not midi')
            with self.assertRaises((OSError, EOFError)):
                convert_file(source, Path(folder) / 'bad.mid')
            self.assertFalse((Path(folder) / 'bad.mid').exists())

    def test_invalid_options(self):
        for value in (0, 128):
            with self.assertRaises(ValueError):
                reset_midi(self.fixture(), value)
        with self.assertRaises(ValueError):
            reset_midi(mido.MidiFile(type=2))


if __name__ == '__main__':
    unittest.main()
