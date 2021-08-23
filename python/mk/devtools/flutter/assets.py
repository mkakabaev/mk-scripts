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
        self.checked = False
        self.path = Path(path)
        img = Image.open(self.path.fspath)
        self.size = _ImageSize(img.size[0], img.size[1])
        self.name = self.path.base_name
        m = re.search(r"(.+)@([1234][.]?[05]?x)$", self.path.file_name)
        if m is not None:
            self.scale_postfix = m.group(2)
            self.base_name = m.group(1)
        else:
            self.scale_postfix = ""
            self.base_name = self.path.file_name
                
    @property
    def has_scale_postfix(self):
        return self.scale_postfix != ""

    @property
    def rel_path(self):
        return self.path.relative()

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.AssetImage"
        sb.add_value(self.name, quoted=True)
        sb.add_value(self.size)


class _ImageSubFolder(ReprBuilderMixin):
    def __init__(self, name, scale) -> None:
        self.name = name
        self.scale = scale
        self.images = {}
        self.directory = None

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = None
        sb.add_value(Path(self.name)) # let it be formatted as a relative path

    def load(self, directory, issues):
        self.directory = directory
        for fs_entry in directory.list():
            name = fs_entry.path.base_name
            p_name = fs_entry.path.relative()

            # Nested directoriesare no allowed
            if isinstance(fs_entry, Directory):
                issues.add(f"{self}: Unexpected directory {p_name} found")
                continue

            # Image files
            if isinstance(fs_entry, File):
                try:
                    image = _Image(fs_entry.path)
                    if image.has_scale_postfix:
                        issues.add(f"{self}: {p_name} contains scale postfix in the name")
                    else:
                        self.images[name] = image
                except Exception as e:
                    issues.add(f"{self}: Unable to load image {p_name}: {e}")
                continue

            # all the rest 
            issues.add(f"have no idea how to handle {fs_entry}")

    def check(self, parent_image, issues):

        try:
            image = self.images[parent_image.name]
        except KeyError:
            issues.add(f"{self}: Missed {parent_image.rel_path}")
            return

        image.checked = True

        # comparing sizes:
        expected_size = parent_image.size.scaled(self.scale)
        thr = math.ceil(1.5 * self.scale)
        if (
            image.size.w < expected_size.w - thr
            or image.size.w > expected_size.w + thr
            or image.size.h < expected_size.h - thr
            or image.size.h > expected_size.h + thr
        ):
            issues.add(f"{self}: Size mismatch for {image}: should be ({self.scale} * {parent_image.size}) ~~> {expected_size} ± {thr}")

    def detect_unchecked(self, issues):
        for image in self.images.values():
            if not image.checked:
                issues.add(f"{self}: extra image {image} found: consider removal")


class _Issues:
    '''Simplest way to simplify issues handling code. As of now it just print issues as they are'''
    def __init__(self, owner):
        self.is_empty = True
        self.owner = owner

    def add(self, issue):
        Console.write(f"{self.owner}: {issue}", style=ConsoleStyle.WARNING)
        self.is_empty = False


class Assets(ReprBuilderMixin):

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.Assets"

    def check_images(self, images_dir):  # pylint: disable=too-many-branches
        root_dir = Directory(images_dir, must_exist=True, create_if_needed=False)
        Console.write_section_header(f"{self}: Checking images at {root_dir.path}")
        issues = _Issues(self)

        # find folders and libs
        folders = {
            t[0]: _ImageSubFolder(name=t[0], scale=t[1]) for t in [
                ("1.5x", 1.5),
                ("2.0x", 2.0),
                ("3.0x", 3.0),
                ("4.0x", 4.0),
            ]
        }

        image_files = {}

        for fs_entry in root_dir.list(sort=True):
            name = fs_entry.path.base_name
            p_name = fs_entry.path.relative()

            # handle directories
            if isinstance(fs_entry, Directory):
                if name in folders:
                    try:
                        folders[name].load(fs_entry, issues)
                    except Exception as e:
                        issues.add(f"Unable to load {fs_entry}: {e}")
                else:
                    issues.add(f"Directory {p_name} does not seem to be an image sub-folder")
                continue

            # handle plain files 
            if isinstance(fs_entry, File):
                try:
                    image = _Image(fs_entry.path)
                    if image.has_scale_postfix:
                        issues.add(f"It seems you forgot to move {p_name} to sub-folder '{image.scale_postfix}'")
                    else:
                        image_files[name] = image
                except Exception as e:
                    issues.add(f"Unable to load image {p_name}: {e}")
                continue

            # all the rest 
            issues.add(f"have no idea how to handle {fs_entry}")

        # get existing folders
        existing_folders = []
        for f in folders.values():
            if f.directory is None:
                issues.add(f"{root_dir.path} does not contain {f.name} sub-folder")
            else:
                existing_folders.append(f)

        # check files
        for name in sorted(image_files.keys()):
            image = image_files[name]
            # Console.write(f"Checking {image}")
            for f in existing_folders:
                f.check(image, issues)

        # notify extra images
        for f in existing_folders:
            f.detect_unchecked(issues)

        if issues.is_empty:
            Console.write("Done (no issues found)")
            return True

        Console.write("Done (few issues found)", style=ConsoleStyle.WARNING)
        return False

    def distribute_images(self, images_dir): 
        '''Put all name@Y.Zx.ext images in Y.Zx/name.ext'''
        root_dir = Directory(images_dir, must_exist=True, create_if_needed=False)
        Console.write_section_header(f"{self}: Distributing images at {root_dir.path}")
        issues = _Issues(self)  

        # fixing typical errors
        typo_fixes = {
            '4x': "4.0x",
            '2x': "2.0x",
            '3x': "3.0x",
            '1.5x': "1.5x",
            '1,5x': "1.5x",
            '15x': "1.5x",
            '15': "1.5x",
        }

        for fs_entry in root_dir.list():
            p_name = fs_entry.path.relative()

            # handle plain files 
            if isinstance(fs_entry, File):
                try:
                    image = _Image(fs_entry.path)
                except Exception as e:
                    issues.add(f"Unable to load image {p_name}: {e}")
                    continue                    

                if not image.has_scale_postfix: 
                    continue


                # finding a destination
                dest_path = root_dir.path + typo_fixes.get(image.scale_postfix, image.scale_postfix)
                if not dest_path.exists_as_directory:
                    issues.add(f"No destination sub-folder found for {image}")
                    continue
                full_dest_path = dest_path + f"{image.base_name}{image.path.extension}"

                # Moving
                if full_dest_path.exists:
                    Console.write(f'{self}: Overwriting {p_name} in {full_dest_path.relative(1)}')
                else:
                    Console.write(f'{self}: Moving {p_name} to {full_dest_path.relative(1)}')
                fs_entry.move_to(full_dest_path)


        if issues.is_empty:
            Console.write("Done (no issues found)")
            return True

        Console.write("Done (few issues found)", style=ConsoleStyle.WARNING)
        return False

