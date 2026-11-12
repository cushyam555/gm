"""Exercise the real Tk window and batch worker on the Windows build runner."""
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
import mido
from gm_reset.gui import Application


class GuiTests(unittest.TestCase):
    def test_window_and_batch_failure_isolation(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Display unavailable: {exc}')
        root.withdraw()
        try:
            app = Application(root)
            with tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                bad = folder / 'bad.mid'
                bad.write_bytes(b'broken')
                good = folder / 'good.mid'
                midi = mido.MidiFile()
                midi.tracks.append(mido.MidiTrack([
                    mido.Message('note_on', note=60, velocity=20),
                    mido.Message('note_off', note=60, time=480)]))
                midi.save(good)
                app.add([bad, good, good])
                self.assertEqual(len(app.paths), 2)
                app.process(list(app.paths), folder, 100)
                app.poll()
                self.assertIn('ผิดพลาด', app.table.set('0', 'status'))
                self.assertIn('สำเร็จ', app.table.set('1', 'status'))
                self.assertTrue((folder / 'good_GM1.mid').exists())
                app.process([good], folder, 100)
                self.assertTrue((folder / 'good_GM1_1.mid').exists())
                root.update_idletasks()
        finally:
            root.destroy()
