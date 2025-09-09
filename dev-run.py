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
        "--filesystem=~/.local/share/flatpak:ro",
        f"--bind-mount=/run/host/font-dirs.xml=/home/{user}/.cache/font-dirs.xml",
        "--bind-mount=/run/host/local-fonts=/usr/local/share/fonts",
        "--bind-mount=/run/host/fonts=/usr/share/fonts",
        "build-dir",
        "pyrose",
    ]
)
