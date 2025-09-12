import os
import subprocess

user = os.getenv("USER")

subprocess.run(
    [
        "flatpak",
        "build",
        "--with-appdir",
        "--allow=devel",
        "--die-with-parent",
        "--nofilesystem=host",
        "--env=PATH=/app/bin:/usr/bin",
        "--talk-name=org.freedesktop.portal.*",
        "--filesystem=~/.local:ro",
        f"--bind-mount=/run/host/font-dirs.xml=/home/{user}/.cache/font-dirs.xml",
        "--bind-mount=/run/host/local-fonts=/usr/local/share/fonts",
        "--bind-mount=/run/host/fonts=/usr/share/fonts",
        "--talk-name=org.a11y.Bus",
        "--bind-mount=/run/flatpak/at-spi-bus=/run/user/1000/at-spi/bus",
        "--env=AT_SPI_BUS_ADDRESS=unix:path=/run/flatpak/at-spi-bus",
        "build-dir",
        "pyrose",
    ]
)
