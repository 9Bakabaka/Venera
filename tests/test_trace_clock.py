# SPDX-License-Identifier: MIT
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('vtrace', Path(__file__).parent / 'perf/vtrace.py')
vtrace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vtrace)


class TraceClockTests(unittest.TestCase):
    def load(self, meta, host=False):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name)
        events = [dict(k='meta', **meta),
                  dict(k='instant', t=1000, pid=1, tid=1, name='venera-trace.sync', id=0, v=1000),
                  dict(k='instant', t=2000, pid=1, tid=1, name='venera-trace.sync', id=0, v=2000)]
        (path / 'events.jsonl').write_text('\n'.join(map(json.dumps, events)))
        if host:
            (path / 'host.txt').touch()
        return vtrace.Run(path)

    def test_qpc_trace_uses_recorded_frequency(self):
        run = self.load(dict(clock='qpc', clock_hz=10_000_000))
        self.assertEqual(run.clock, 'qpc')
        self.assertEqual(run.ms(10_000), 1)
        self.assertEqual(run.sync_error_us, 0)
        self.assertTrue(vtrace.write_perfetto(run).exists())

    def test_existing_tsc_traces_remain_readable(self):
        run = self.load(dict(tsc_hz=2_000_000_000))
        self.assertEqual(run.clock, 'tsc')
        self.assertEqual(run.ms(2_000_000), 1)

    def test_qpc_cannot_be_correlated_as_host_tsc(self):
        with self.assertRaisesRegex(SystemExit, 'host correlation requires TSC'):
            self.load(dict(clock='qpc', clock_hz=10_000_000), host=True)

    def test_invalid_clocks_are_rejected(self):
        for meta in (dict(clock='invalid', clock_hz=1), dict(clock='qpc', clock_hz=0),
                     dict(clock='qpc', clock_hz=-1), dict(clock='qpc', clock_hz=float('nan')),
                     dict(clock='qpc', clock_hz=float('inf')), dict(clock='qpc')):
            with self.subTest(meta=meta), self.assertRaises(SystemExit):
                self.load(meta)


if __name__ == '__main__':
    unittest.main()
