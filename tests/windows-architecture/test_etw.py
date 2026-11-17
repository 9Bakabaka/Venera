# SPDX-License-Identifier: MIT
"""Record real ETW events and verify the raw timestamps use the advertised clock.

Requires elevation, like venera-trace. No Venera driver or GPU is required.
"""
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as tmp:
    subprocess.run([sys.argv[1], 'record', '0.1', tmp], check=True)
    events = [json.loads(line) for line in (Path(tmp) / 'events.jsonl').read_text().splitlines()]
    meta = next(event for event in events if event['k'] == 'meta')
    # The runner's Python may itself run under emulation. Inspect the recorder's
    # PE target rather than inferring its clock from the Python process.
    pe = Path(sys.argv[1]).read_bytes()
    offset = struct.unpack_from('<I', pe, 60)[0]
    machine = struct.unpack_from('<H', pe, offset + 4)[0]
    assert machine in (0xaa64, 0x8664), hex(machine)
    expected = 'qpc' if machine == 0xaa64 else 'tsc'
    assert meta['clock'] == expected, meta
    assert meta['clock_hz'] > 0, meta
    syncs = [event for event in events if event.get('name') == 'venera-trace.sync']
    assert len(syncs) == 2, syncs
    for event in syncs:
        # EventWrite follows the sampled clock, in the same raw tick units.
        assert 0 <= event['t'] - event['v'] < meta['clock_hz'] * 0.1, event
    assert syncs[1]['t'] > syncs[0]['t'], syncs
    assert not meta['events_lost'] and not meta['buffers_lost'], meta
