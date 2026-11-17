#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the WDK fetcher's architecture selection with local NuGet packages."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
VERSION = "10.0.26100.6584"
KIT = "10.0.26100.0"


class WinKitsFetchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.output = self.directory / "winkits"
        self.log = self.directory / "requests"
        for arch, directory in (("x64", "x64"), ("arm64", "ARM64")):
            with zipfile.ZipFile(self.directory / f"microsoft.windows.wdk.{arch}.zip", "w") as package:
                package.writestr(f"c/Include/{KIT}/km/ntddk.h", "kernel headers")
                package.writestr(f"c/Lib/{KIT}/km/{directory}/displib.lib", arch)
        with zipfile.ZipFile(self.directory / "microsoft.windows.sdk.cpp.zip", "w") as package:
            package.writestr(f"c/Include/{KIT}/um/Windows.h", "SDK headers")
        # Intercept only network transport. The real script and unzip still select
        # packages, extract the official directory layout and inspect the cache.
        curl = self.directory / "curl"
        curl.write_text("""#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys
args = sys.argv[1:]
url = args[-1]
package = url.split('/')[-3]
with open(os.environ['WINKITS_REQUESTS'], 'a') as log:
    log.write(url + '\\n')
shutil.copyfile(Path(os.environ['WINKITS_PACKAGES']) / (package + '.zip'), args[args.index('-o') + 1])
""")
        curl.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.directory}{os.pathsep}{os.environ['PATH']}",
                        WINKITS_PACKAGES=str(self.directory), WINKITS_REQUESTS=str(self.log))

    def fetch(self, *args):
        return subprocess.run(["sh", str(ROOT / "cmake/fetch-winkits.sh"), str(self.output), *args],
                              env=self.env, text=True, capture_output=True, timeout=20)

    def requests(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_default_is_x64(self):
        result = self.fetch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / f"wdk/c/Lib/{KIT}/km/x64/displib.lib").read_text(), "x64")
        self.assertIn(f"microsoft.windows.wdk.x64/{VERSION}/", self.requests()[0])

    def test_arm64_uses_native_libraries(self):
        result = self.fetch("arm64")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / f"wdk/c/Lib/{KIT}/km/ARM64/displib.lib").read_text(), "arm64")
        self.assertFalse((self.output / f"wdk/c/Lib/{KIT}/km/x64").exists())
        self.assertIn(f"microsoft.windows.wdk.arm64/{VERSION}/", self.requests()[0])

    def test_shared_cache_can_add_arm64_without_redownloading_sdk(self):
        self.assertEqual(self.fetch().returncode, 0)
        result = self.fetch("arm64")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.output / f"wdk/c/Lib/{KIT}/km/x64/displib.lib").is_file())
        self.assertTrue((self.output / f"wdk/c/Lib/{KIT}/km/ARM64/displib.lib").is_file())
        self.assertEqual(len(self.requests()), 3)
        self.assertEqual(self.fetch("arm64").returncode, 0)
        self.assertEqual(len(self.requests()), 3)

    def test_unknown_architecture_does_not_download(self):
        result = self.fetch("arm32")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported architecture", result.stderr)
        self.assertEqual(self.requests(), [])


if __name__ == "__main__":
    unittest.main()
