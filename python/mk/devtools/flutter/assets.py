# -*- coding: utf-8 -*-
# cSpell: words 

import re
import math
from PIL import Image
from ...core import (
    ReprBuilderMixin,
    die,
    ToStringBuilder,
    Console,
    ConsoleStyle,
    File,
    Path,
    Directory,
)


class _ImageSize:
    def __init__(self, w, h):
        self.w = w
        self.h = h

    def __repr__(self) -> str:
        return f"{self.w}x{self.h}"

    def scaled(self, scale):
        return _ImageSize(round(self.w * scale), round(self.h * scale))


class _Image(ReprBuilderMixin):
    def __init__(self, path):
        self.path = Path(path)
        self.name = self.path.base_name
        img = Image.open(self.path.fspath)
        self.size = _ImageSize(img.size[0], img.size[1])
        self.checked = False

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.AssetImage"
        sb.add_value(self.name)
        sb.add_value(self.size)


class _ImageSubFolder(ReprBuilderMixin):
    def __init__(self, name, scale, directory=None) -> None:
        self.name = name
        self.scale = scale
        self.directory = directory
        if directory is not None:
            self.load_directory(directory)
        self.images = {}

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.AssetImageDir"
        sb.add_value(self.name)

    def load_directory(self, directory):
        self.directory = directory
        for fs_entry in directory.list():
            name = fs_entry.path.base_name
            if isinstance(fs_entry, Directory):
                Console.write(
                    f"{self}: unexpected directory {fs_entry} found",
                    style=ConsoleStyle.WARNING,
                )
            elif isinstance(fs_entry, File):
                try:
                    if name.endswith(".png"):
                        self.images[name] = _Image(fs_entry.path)
                    else:
                        raise Exception("Unknown file")
                except Exception as e:
                    Console.write(
                        f"{self}: unable to load {fs_entry}: {e}",
                        style=ConsoleStyle.WARNING,
                    )
            else:
                die(f"{self}: have no idea how to handle {fs_entry}")

    def check(self, parent_image):
        try:
            image = self.images[parent_image.name]
        except KeyError:
            Console.write(
                f"{self}: unable to find {parent_image.name}",
                style=ConsoleStyle.WARNING,
            )
            return False

        image.checked = True
        has_issues = False

        # comparing sizes:
        expected_size = parent_image.size.scaled(self.scale)
        thr = math.ceil(1 * self.scale)
        if (
            image.size.w < expected_size.w - thr
            or image.size.w > expected_size.w + thr
            or image.size.h < expected_size.h - thr
            or image.size.h > expected_size.h + thr
        ):
            Console.write(
                f"{self}: size mismatch for {image}: should be ({self.scale} * {parent_image.size}) ~~> {expected_size} ± {thr}",
                style=ConsoleStyle.WARNING,
            )
            has_issues = True

        return not has_issues

    def detect_unchecked(self):
        has_issues = False
        for image in self.images.values():
            if not image.checked:
                Console.write(
                    f"{self}: extra image {image} found: consider removal",
                    style=ConsoleStyle.WARNING,
                )
                has_issues = True

        return not has_issues


class Assets(ReprBuilderMixin):
    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.Assets"

    def check_images(self, images_dir):  # pylint: disable=too-many-branches
        has_issues = False
        root_dir = Directory(images_dir, must_exist=True, create_if_needed=False)
        Console.write_section_header(f"{self}: Checking images at {root_dir.path}")

        # find folders and libs
        folders = {
            t[0]: _ImageSubFolder(t[0], t[1])
            for t in [
                ("1.5x", 1.5),
                ("2.0x", 2.0),
                ("3.0x", 3.0),
                ("4.0x", 4.0),
            ]
        }

        image_files = {}

        for fs_entry in root_dir.list():
            name = fs_entry.path.base_name

            if isinstance(fs_entry, Directory):
                try:
                    folders[name].load_directory(fs_entry)
                except Exception as _:
                    Console.write(
                        f"{self}: {fs_entry} does not seem to be an image sub-folder",
                        style=ConsoleStyle.WARNING,
                    )
                    has_issues = True
                continue

            if isinstance(fs_entry, File):

                try:
                    if name.endswith(".png"):

                        image = _Image(fs_entry.path)

                        m = re.search(r"@([0-9.])x[.]\w+$", name)
                        if m is not None:
                            Console.write(
                                f"{self}: It seems you forgot to move {image.name} to sub-folder",
                                style=ConsoleStyle.WARNING,
                            )
                            has_issues = True
                            continue

                        image_files[name] = image
                    else:
                        raise Exception("Unknown file")
                except Exception as e:
                    has_issues = True
                    Console.write(
                        f"{self}: unable to load {fs_entry}: {e}",
                        style=ConsoleStyle.WARNING,
                    )
                continue

            has_issues = True
            die(f"{self}: have no idea how to handle {fs_entry}")

        # get existing folders
        existing_folders = []
        for f in folders.values():
            if f.directory is None:
                has_issues = True
                Console.write(
                    f"{self}: {root_dir.path} does not contain {f.name} sub-folder",
                    style=ConsoleStyle.WARNING,
                )
            else:
                existing_folders.append(f)

        # check files
        for name in sorted(image_files.keys()):
            image = image_files[name]
            # Console.write(f"Checking {image}")
            for f in existing_folders:
                if not f.check(image):
                    has_issues = True

        # notify extra images
        for f in existing_folders:
            if not f.detect_unchecked():
                has_issues = True

        if has_issues:
            Console.write("Done (few issues found)", style=ConsoleStyle.WARNING)
        else:
            Console.write("Done (no issues found)")
        return not has_issues
