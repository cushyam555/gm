"""Reset performance controls while preserving event positions in MIDI ticks."""
from pathlib import Path
import os
import tempfile
import mido

# Preserve pedals that affect note duration only via explicit note events; remove
# all original controllers so RPN/NRPN, bank changes and later resets cannot undo us.
DEFAULTS = {0: 0, 32: 0, 7: 100, 10: 64, 11: 127, 64: 0, 91: 0, 93: 0}


def reset_midi(source: mido.MidiFile, velocity: int = 100) -> mido.MidiFile:
    if not 1 <= velocity <= 127:
        raise ValueError("Velocity ต้องอยู่ระหว่าง 1 ถึง 127")
    if source.type not in (0, 1):
        raise ValueError("รองรับ MIDI Type 0 และ 1 เท่านั้น (Type 2 เป็นเพลงอิสระหลายชุด)")
    result = mido.MidiFile(type=source.type, ticks_per_beat=source.ticks_per_beat,
                           charset=source.charset)
    channels = sorted({msg.channel for track in source.tracks for msg in track
                       if hasattr(msg, "channel")})
    setup = [mido.Message("sysex", data=[0x7E, 0x7F, 0x09, 0x01], time=0)]
    for channel in channels:
        setup.extend(mido.Message("control_change", channel=channel, control=cc,
                                  value=value, time=0) for cc, value in DEFAULTS.items())
        setup.extend([mido.Message("program_change", channel=channel, program=0, time=0),
                      mido.Message("pitchwheel", channel=channel, pitch=0, time=0)])
    for index, track in enumerate(source.tracks):
        output = mido.MidiTrack(setup if index == 0 else [])
        pending = 0
        for msg in track:
            pending += msg.time
            if msg.type in {"sysex", "control_change", "pitchwheel", "aftertouch", "polytouch"}:
                continue
            # GM1 percussion has one standard kit on channel 10.
            if msg.type == "program_change" and msg.channel == 9:
                continue
            changes = {"time": pending}
            if msg.type == "note_on" and msg.velocity > 0:
                changes["velocity"] = velocity
            output.append(msg.copy(**changes))
            pending = 0
        if pending:
            output.append(mido.MetaMessage("end_of_track", time=pending))
        result.tracks.append(output)
    if not result.tracks:
        result.tracks.append(mido.MidiTrack(setup + [mido.MetaMessage("end_of_track")]))
    return result


def convert_file(source: Path, destination: Path, velocity: int = 100) -> Path:
    """Write a complete new file exclusively; never replace an existing file."""
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("ไม่สามารถเขียนทับไฟล์ต้นฉบับได้")
    converted = reset_midi(mido.MidiFile(source), velocity)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Serialize before publishing so failures do not leave a partial MIDI file.
    with tempfile.TemporaryFile() as temp:
        converted.save(file=temp)
        temp.seek(0)
        created = False
        try:
            with destination.open("xb") as output:
                created = True
                output.write(temp.read())
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise
    return destination
