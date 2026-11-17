#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise target ABI selection and the cross files consumed by Meson."""
import ast
import configparser
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CMAKE = os.environ.get("CMAKE", shutil.which("cmake") or "cmake")


class CrossBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def cmake(self, content, success=True):
        script = self.directory / "check.cmake"
        script.write_text(content)
        result = subprocess.run([CMAKE, "-P", str(script)], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(result.returncode == 0, success, result.stdout)
        return result.stdout

    def test_target_abi_is_not_pointer_size(self):
        for processor, expected in [("x86_64", "x64"), ("AMD64", "x64"),
                                    ("i686", "x86"), ("x86", "x86"),
                                    ("aarch64", "arm64"), ("ARM64", "arm64")]:
            with self.subTest(processor=processor):
                self.cmake(f'''
set(CMAKE_SYSTEM_PROCESSOR "{processor}")
include("{ROOT}/cmake/target-arch.cmake")
if(NOT VENERA_TARGET_ARCH STREQUAL "{expected}")
  message(FATAL_ERROR "Incorrect ABI: ${{VENERA_TARGET_ARCH}}")
endif()
''')

    def test_rejects_conflicting_or_unknown_abi(self):
        output = self.cmake(f'''
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(VENERA_TARGET_ARCH x64)
include("{ROOT}/cmake/target-arch.cmake")
''', success=False)
        self.assertIn("disagrees with toolchain", output)
        output = self.cmake(f'''
set(CMAKE_SYSTEM_PROCESSOR riscv64)
include("{ROOT}/cmake/target-arch.cmake")
''', success=False)
        self.assertIn("Unsupported Windows target", output)

    def test_arm64_meson_uses_the_selected_llvm_toolchain(self):
        output = self.directory / "cross.ini"
        toolchain = self.directory / "llvm mingw"
        self.cmake(f'''
set(VENERA_LLVM_MINGW_ROOT "{toolchain}" CACHE PATH "")
include("{ROOT}/cmake/llvm-mingw-arm64.cmake")
set(VENERA_MESON "${{CMAKE_COMMAND}}")
set(VENERA_NINJA "${{CMAKE_COMMAND}}")
include("{ROOT}/cmake/meson.cmake")
venera_meson_cross_file("{output}")
''')
        cross = configparser.ConfigParser()
        cross.read(output)
        self.assertEqual(ast.literal_eval(cross["host_machine"]["cpu_family"]), "aarch64")
        for key, suffix in [("c", "clang"), ("cpp", "clang++")]:
            self.assertEqual(ast.literal_eval(cross["binaries"][key]),
                             [str(toolchain / "bin" / f"aarch64-w64-mingw32-{suffix}")])
        for key, suffix in [("ar", "ar"), ("strip", "strip"), ("windres", "windres")]:
            self.assertEqual(ast.literal_eval(cross["binaries"][key]),
                             str(toolchain / "bin" / f"aarch64-w64-mingw32-{suffix}"))
        self.assertEqual(ast.literal_eval(cross["built-in options"]["cpp_args"]), [])

    def test_mesa_cross_files_keep_runtimes_per_abi(self):
        env = dict(os.environ,
                   VENERA_LLVM_MINGW_ROOT="/toolchains/llvm-mingw",
                   VENERA_MINGW_MCFG_INCLUDE="/mcfg/x64/include",
                   VENERA_MINGW_MCFG_LIB="/mcfg/x64/lib",
                   VENERA_MINGW32_MCFG_INCLUDE="/mcfg/x86/include",
                   VENERA_MINGW32_MCFG_LIB="/mcfg/x86/lib")
        for arch, cpu in [("x64", "x86_64"), ("x86", "x86"), ("arm64", "aarch64")]:
            with self.subTest(arch=arch):
                output = self.directory / f"{arch}.ini"
                subprocess.run(["sh", str(ROOT / "icd/cross-file.sh"),
                                str(output), arch, "/sdk/shared"], env=env, check=True)
                cross = configparser.ConfigParser()
                cross.read(output)
                self.assertEqual(ast.literal_eval(cross["host_machine"]["cpu_family"]), cpu)
                c_args = ast.literal_eval(cross["built-in options"]["c_args"])
                link_args = ast.literal_eval(cross["built-in options"]["cpp_link_args"])
                self.assertIn("/sdk/shared", c_args)
                if arch == "arm64":
                    self.assertNotIn("-isystem", c_args)
                    self.assertFalse(any("mcfg" in arg for arg in link_args))
                    self.assertIn("aarch64-w64-mingw32-clang", cross["binaries"]["c"])
                else:
                    self.assertIn(f"/mcfg/{arch}/include", c_args)
                    self.assertIn(f"-L/mcfg/{arch}/lib", link_args)

    def test_mesa_rejects_reusing_another_native_abi_directory(self):
        (self.directory / ".target-arch").write_text("x64\n")
        sentinel = self.directory / "existing-driver.dll"
        sentinel.write_bytes(b"preserve existing output")
        result = subprocess.run(["sh", str(ROOT / "icd/build.sh"),
                                 str(self.directory), "arm64"], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("use a separate directory", result.stdout)
        self.assertEqual(sentinel.read_bytes(), b"preserve existing output")

    def test_mesa_rejects_legacy_build_without_abi_metadata(self):
        build = self.directory / "meson"
        build.mkdir()
        sentinel = build / "build.ninja"
        sentinel.write_text("existing compiler configuration\n")
        for arch in ["x64", "arm64"]:
            with self.subTest(arch=arch):
                result = subprocess.run(["sh", str(ROOT / "icd/build.sh"),
                                         str(self.directory), arch], text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("without target ABI metadata", result.stdout)
                self.assertEqual(sentinel.read_text(), "existing compiler configuration\n")
                self.assertFalse((self.directory / ".target-arch").exists())


if __name__ == "__main__":
    unittest.main()
