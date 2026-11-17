#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check kernel target selection before compiler checks create a subproject."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CMAKE = os.environ.get("CMAKE", shutil.which("cmake") or "cmake")


class KernelToolchainTests(unittest.TestCase):
    def configure(self, architecture=None):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "toolchain.cmake"
            selection = f'set(VENERA_TARGET_ARCH "{architecture}")' if architecture else ""
            script.write_text(f'''
cmake_minimum_required(VERSION 3.24)
{selection}
include("{ROOT}/cmake/clang-cl-kmd.cmake")
file(WRITE "{directory}/target.txt"
  "${{VENERA_TARGET_ARCH}};${{CMAKE_SYSTEM_PROCESSOR}};${{CMAKE_C_COMPILER_TARGET}};${{CMAKE_CXX_COMPILER_TARGET}};${{CMAKE_TRY_COMPILE_TARGET_TYPE}};${{CMAKE_TRY_COMPILE_PLATFORM_VARIABLES}}")
''')
            result = subprocess.run([CMAKE, "-P", str(script)], text=True,
                                    capture_output=True, timeout=20)
            output = Path(directory) / "target.txt"
            return result, output.read_text().split(";") if output.exists() else []

    def test_default_target_preserves_x64_abi(self):
        result, values = self.configure()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values[:4], ["x64", "AMD64", "x86_64-pc-windows-msvc", "x86_64-pc-windows-msvc"])
        self.assertEqual(values[4], "STATIC_LIBRARY")

    def test_arm64_target_uses_native_kernel_abi(self):
        result, values = self.configure("arm64")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(values[:4], ["arm64", "ARM64", "aarch64-pc-windows-msvc", "aarch64-pc-windows-msvc"])
        self.assertEqual(values[4], "STATIC_LIBRARY")
        self.assertIn("VENERA_TARGET_ARCH", values[5:])

    def test_rejects_unsupported_kernel_target(self):
        result, values = self.configure("x86")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported VENERA_TARGET_ARCH", result.stderr)
        self.assertEqual(values, [])


if __name__ == "__main__":
    unittest.main()
