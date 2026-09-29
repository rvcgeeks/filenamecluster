"""The Nuitka command for one operating system."""

from __future__ import annotations

import shlex
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field

from build.log import get_logger
from build.paths import ASSETS, PACKAGE, ROOT

log = get_logger(__name__)

# One ``--verbose`` is Nuitka's full trace. The ``--show-*`` flags add the
# C compile commands, memory, included modules, plugin decisions, and progress.
VERBOSE = (
    "--verbose",
    "--show-scons",
    "--show-memory",
    "--show-modules",
    "--show-plugin-usage",
    "--show-progress",
)


@dataclass(frozen=True)
class NuitkaBuild:
    """Compile ``src/filenamecluster`` into ``dist/`` for ``platform``.

    Windows writes ``dist/filenamecluster.exe`` and Linux writes
    ``dist/filenamecluster``, each as one file. Mac writes
    ``dist/filenamecluster.app``. ``keep_analysis`` keeps Nuitka's
    intermediate files.
    """

    platform: str
    keep_analysis: bool = False
    python: str = field(default_factory=lambda: sys.executable)

    def command(self, extra: Sequence[str] = ()) -> list[str]:
        command = [
            self.python,
            "-m",
            "nuitka",
            "--standalone",
            "--assume-yes-for-downloads",
            *VERBOSE,
            "--enable-plugins=tk-inter",
            "--output-dir=dist",
            f"--include-data-dir={ASSETS}=filenamecluster/ui/assets",
        ]
        if self.platform == "darwin":
            command.extend(
                [
                    "--macos-create-app-bundle",
                    "--macos-app-name=filenamecluster",
                    f"--macos-app-icon={ASSETS / 'icon.png'}",
                    "--disable-cache=ccache",
                    "--output-filename=filenamecluster-bin",
                    "--output-folder-name=filenamecluster",
                ]
            )
        else:
            command.extend(["--onefile", "--output-filename=filenamecluster"])
        if self.platform == "win32":
            command.append("--windows-console-mode=disable")
        if not self.keep_analysis:
            command.append("--remove-output")
        command.extend(extra)
        command.extend(["--python-flag=-m", str(PACKAGE)])
        return command

    def run(self, extra: Sequence[str] = ()) -> int:
        """Run Nuitka beside ``pyproject.toml`` and return its exit code.

        Nuitka's own trace is logged a line at a time, so a CI log keeps it
        with the rest of the build.
        """

        command = self.command(extra)
        log.debug("cwd %s", ROOT)
        log.debug("command %s", shlex.join(command))
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        for line in process.stdout:
            log.debug("%s", line.rstrip("\r\n"))
        code = process.wait()
        log.debug("exit %s", code)
        return code
