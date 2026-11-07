#!/usr/bin/env python3
"""Run PyRose from build-dir, built with:

flatpak-builder --force-clean build-dir io.github.vanillajonathan.pyrose.json
"""

import os
import subprocess
from pathlib import Path

home = Path.home()
runtime_dir = os.getenv("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

subprocess.run(
    [
        "flatpak",
        "build",
        "--with-appdir",
        "--allow=devel",
        "--die-with-parent",
        "--nofilesystem=host",
        # Same as finish-args in the manifest
        "--share=ipc",
        "--device=dri",
        "--socket=fallback-x11",
        "--socket=wayland",
        "--filesystem=~/.local/bin:ro",
        "--env=PATH=/app/bin:/usr/bin",
        "--talk-name=org.freedesktop.portal.*",
        f"--bind-mount=/run/host/font-dirs.xml={home}/.cache/font-dirs.xml",
        "--bind-mount=/run/host/local-fonts=/usr/local/share/fonts",
        "--bind-mount=/run/host/fonts=/usr/share/fonts",
        "--talk-name=org.a11y.Bus",
        f"--bind-mount=/run/flatpak/at-spi-bus={runtime_dir}/at-spi/bus",
        "--env=AT_SPI_BUS_ADDRESS=unix:path=/run/flatpak/at-spi-bus",
        "build-dir",
        "pyrose",
    ],
    check=False,
)
