#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the packaging architecture contract without requiring a Windows guest."""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CMAKE = os.environ.get("CMAKE", "cmake")


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def run_cmake(self, arch, body):
        script = self.directory / "check.cmake"
        script.write_text(f'set(VENERA_TARGET_ARCH "{arch}")\n'
                          f'include("{ROOT / "setup/package.cmake"}")\n' + body)
        return subprocess.run([CMAKE, "-P", str(script)], capture_output=True, text=True)

    def pe(self, machine, offset=128):
        data = bytearray(256)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, offset)
        if 64 <= offset <= len(data) - 6:
            data[offset:offset + 4] = b"PE\0\0"
            struct.pack_into("<H", data, offset + 4, machine)
        return data

    def validate(self, data, expected):
        file = self.directory / "driver.dll"
        file.write_bytes(data)
        return self.run_cmake("arm64", f'venera_check_pe("{file}" "{expected}")\n')

    def test_native_and_wow_binary_machines(self):
        for machine, expected in [(0xaa64, "aa64"), (0x8664, "8664"), (0x014c, "014c")]:
            result = self.validate(self.pe(machine), expected)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_foreign_machine_rejected(self):
        for machine, expected in [(0x8664, "aa64"), (0xaa64, "8664"), (0xaa64, "014c")]:
            result = self.validate(self.pe(machine), expected)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("PE machine", result.stderr)

    def test_payload_requires_native_binaries_and_x86_wow(self):
        for arch, native_machine in [("arm64", 0xaa64), ("x64", 0x8664)]:
            native = self.directory / "venera_d3d11.dll"
            wow = self.directory / "venera_d3d11_32.dll"
            console = self.directory / "venera-panel.com"
            manifest = self.directory / "venera_vulkan_virtio.json"
            native.write_bytes(self.pe(native_machine))
            wow.write_bytes(self.pe(0x014c))
            console.write_bytes(self.pe(native_machine))
            manifest.write_text("{}")
            check = f'venera_validate_payload("{native}" "{wow}" "{console}" "{manifest}")\n'
            result = self.run_cmake(arch, check)
            self.assertEqual(result.returncode, 0, result.stderr)
            wow.write_bytes(self.pe(native_machine))
            result = self.run_cmake(arch, check)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expected 014c", result.stderr)
            wow.write_bytes(self.pe(0x014c))
            console.write_bytes(self.pe(0x014c))
            result = self.run_cmake(arch, check)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("venera-panel.com", result.stderr)

    def test_malformed_pe_rejected(self):
        malformed = [b"MZ", bytes(256), self.pe(0xaa64, 0xffffffff), self.pe(0xaa64, 8)]
        invalid_signature = self.pe(0xaa64)
        invalid_signature[128] = 0
        malformed.append(invalid_signature)
        for data in malformed:
            self.assertNotEqual(self.validate(data, "aa64").returncode, 0)

    def test_inf_targets_only_native_architecture(self):
        for arch, decoration, foreign in [("x64", "amd64", "arm64"), ("arm64", "arm64", "amd64")]:
            out = self.directory / "venera.inf"
            result = self.run_cmake(arch,
                f'venera_configure_inf("{ROOT / "pkg/venera.inf"}" inf)\n'
                f'file(WRITE "{out}" "${{inf}}")\n')
            self.assertEqual(result.returncode, 0, result.stderr)
            inf = out.read_text()
            self.assertIn(f"[VENERA.NT{decoration}.10.0...22000]", inf)
            self.assertNotIn(f"NT{foreign}", inf)
            self.assertNotIn("@VENERA_", inf)
            self.assertIn("UserModeDriverNameWow", inf)
            self.assertIn("venera_d3d11_32.dll", inf)
            self.assertRegex(inf, r"OpenGLFlagsWow,\s+%REG_DWORD%, 3")
            self.assertRegex(inf, r"OpenGLVersionWow,\s+%REG_DWORD%, 4096")

    def test_unsupported_package_architecture_rejected(self):
        for arch in ["x86", "arm", "ARM64", ""]:
            result = self.run_cmake(arch, "")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("VENERA_TARGET_ARCH=x64 or arm64", result.stderr)


if __name__ == "__main__":
    unittest.main()
