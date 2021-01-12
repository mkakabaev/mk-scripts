# -*- coding: utf-8 -*-
# cSpell: words iphoneos

import re
import math
from typing import Dict
from enum import Enum
from PIL import Image
from ..core import (
    ReprBuilderMixin,
    Runner,
    die,
    ToStringBuilder,
    Console,
    ConsoleStyle,
    File,
    Path,
    Directory,
)
from .xcode import Xcode, Workspace as XcodeWorkspace


class Project(ReprBuilderMixin):
    def __init__(self, project_dir_path):
        self.path = Path(project_dir_path)
        self._name = "?"
        self._description = "?"
        self._version = "?"

        pubspec = File([project_dir_path, "pubspec.yaml"], must_exist=True).read_all()

        def fetch(tag, regexp, group):
            m = re.search(regexp, pubspec, re.MULTILINE)
            if m is None:
                die(f"{self}: unable to fetch <{tag}> from 'pubspec.yaml'")
            return m.group(group)

        self._name = fetch("name", r"^name:\s+(\S+)", 1)
        self._description = fetch("description", r"^description:\s+(\S.*)\s*$", 1)
        self._version = fetch("version", r"^version:\s+(\S+)", 1)

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.Project"
        sb.add_value(f"{self._name}/{self._version}")

    def make_directory_current(self):
        Directory(self.path).make_current()

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    @property
    def description(self):
        return self._description

    @property
    def xcode_workspace(self) -> XcodeWorkspace:
        return XcodeWorkspace(self.path + "ios/Runner.xcworkspace")

    @property
    def ios_app(self) -> Directory:
        return Directory(self.path + "build/ios/iphoneos/Runner.app")


class BuildMode(Enum):
    DEBUG = {"name": "Debug", "flag": "--debug", "file_name": "debug"}
    RELEASE = {"name": "Release", "flag": "--release", "file_name": "release"}
    PROFILE = {"name": "Profile", "flag": "--profile", "file_name": "profile"}

    def __init__(self, info):
        self.info = info

    @property
    def display_name(self):
        return self.info["name"]

    @property
    def compile_flag(self):
        return self.info["flag"]

    @property
    def file_name(self):
        return self.info["file_name"]


class _FlutterRunner:
    def __init__(self, title):
        self._runner = Runner("flutter")
        self._runner.title = f"Flutter: {title}"
        self._app_name = ["app"]
        self._project = None

    def add_args(self, args):
        self._runner.add_args(args)

    def add_hdr(self, name, param):
        self._runner.add_info(name, param)

    def set_project(self, project: Project,):
        assert isinstance(project, Project)
        self._project = project
        self.add_hdr("Project", project)

    def set_flavor(self, flavor):
        if flavor is not None:
            self._runner.add_args(["--flavor", flavor])
            self._app_name.append(flavor)
            self.add_hdr("Flavor", flavor)

    def set_build_mode(self, build_mode):
        self._runner.add_args(build_mode.compile_flag)
        self._app_name.append(build_mode.file_name)
        self.add_hdr("Build mode", build_mode.display_name)

    def set_analyze_size(self, flag):
        if flag:
            self._runner.add_args("--analyze-size")
            self.add_hdr("Size analysis enabled", True)

    def set_main_module(self, main_module):
        if main_module is not None:
            self._runner.add_args(["-t", main_module])
            self.add_hdr("Main module", main_module)

    def add_environment(self, env: Dict[str, str]):
        if env is not None:
            for name, value in env.items():                
                self._runner.add_args(f"--dart-define={name}={value}")
            self.add_hdr("Environment", env)

    def get_app_name(self, postfix):
        return "-".join(self._app_name) + postfix

    def run(self):
        if self._project is not None:
            self._project.make_directory_current()
        self._runner.run(
            console_output=False, 
            notify_completion=True
        )

class Flutter(ReprBuilderMixin):
    def __init__(self):
        self._version = "?"
        self._channel = "?"
        self._load()

    def _load(self):
        r = Runner("flutter", "--version", title='flutter --version')
        result = r.run_silent()
        self._version = result.search(r"Flutter ([0-9.]+)", 1, tag="version")
        self._channel = result.search(r"channel\s+(\S+)", 1, tag="channel")

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.add_value(f"{self._version}/{self._channel}")
        
    def clean(self, project: Project):
        r = _FlutterRunner(title="Clean")
        r.add_args("clean")        
        r.set_project(project)
        r.run()

    def build_ios(
        self,
        project: Project,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Dict[str, str] = None,
        clean_before: bool = True,
        analyze_size: bool = False,        
        archive_dir=None, # Xcode archive
        scheme: str = None, # Xcode scheme
        ad_hoc_export: bool = False,
        app_store_export: bool = False,
        app_store_upload: bool = False,
        reveal_result: bool = True
    ): # pylint: disable=too-many-locals, too-many-statements 
        # check state and args
        assert isinstance(project, Project)

        # clean flutter
        if clean_before:
            self.clean(project=project)

        # configure and run
        r = _FlutterRunner(title="Build iOS")
        r.add_args(["build", "ios"])
        r.set_project(project)
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(analyze_size)
        r.set_main_module(main_module)
        r.add_environment(environment)
        r.add_hdr('Ad Hoc build', ad_hoc_export)
        r.add_hdr('AppStore build', app_store_export)
        r.add_hdr('Upload to AppStore', app_store_upload)

        # configure xcode stuff
        archive_file = None
        ad_hoc_directory = None
        app_store_directory = None
        app_store_upload_directory = None
        do_archive = False
        do_export_ad_hoc = False
        do_export_app_store = False
        do_upload_app_store = False
        if archive_dir is not None: 
            do_archive = True
            archive_file = File([archive_dir, r.get_app_name(".xcarchive")])
            archive_file.remove()
            if ad_hoc_export:
                do_export_ad_hoc = True
                ad_hoc_directory = Directory([archive_dir, "ad_hoc"])
                ad_hoc_directory.remove()
            if app_store_export:
                do_export_app_store = True
                app_store_directory = Directory([archive_dir, "app_store"])
                app_store_directory.remove()                
            if app_store_upload:
                do_upload_app_store = True
                app_store_upload_directory = Directory([archive_dir, "app_store_upload"])
                app_store_upload_directory.remove()

        # Run flutter. Stop after if no xcode processing is ordered
        r.run()
        if not do_archive:
            if reveal_result:
                Directory(project.ios_app).reveal()
            return

        # archive the project
        workspace = project.xcode_workspace
        if scheme is None:
            scheme = flavor if flavor is not None else "Runner"
        xcode = Xcode()
        xcode.archive(workspace=workspace, scheme=scheme, archive_file=archive_file)

        # do ad-hoc export
        if do_export_ad_hoc:
            xcode.export_ad_hoc(
                archive_file=archive_file,
                output_dir=ad_hoc_directory,
            )

        # do app-store export
        if do_export_app_store:
            xcode.export_app_store( 
                archive_file=archive_file,
                output_dir=app_store_directory,
            )

        # do upload to app store
        if do_upload_app_store:
            xcode.export_app_store(
                archive_file=archive_file,
                output_dir=app_store_upload_directory,
                is_upload=True
            )        

        if reveal_result:
            File(archive_file).reveal()

    def build_apk(
        self,
        project: Project,
        output_dir,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Dict[str, str] = None,
        reveal_result: bool = True,
        clean_before: bool = True,
        # analyze_size: bool = False
    ):

        # check state and args
        assert isinstance(project, Project)

        # clean
        if clean_before:
            self.clean(project=project)

        # configure
        r = _FlutterRunner(title="Build APK")
        r.add_args(["build", "apk"])
        r.set_project(project)
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(False)
        r.set_main_module(main_module)
        r.add_environment(environment)

        app_name = Path(r.get_app_name(".apk"))
        output_d = Directory(output_dir)
        build_f = File([project.path, "build", "app", "outputs", "flutter-apk", app_name])
        output_f = File([output_d.path, app_name])
        r.add_hdr("Build file name", app_name)
        r.add_hdr("Output", output_d.path)

        # Prepare output folders, cd to project, build the project
        output_d.ensure_exists()
        output_f.remove()
        r.run()

        # copy the result
        Console.write_section_header(f"Copying {app_name} to {output_f.path}...")
        build_f.ensure_exists()
        build_f.copy_to(output_f)

        # check the result and reveal
        output_f.ensure_exists()
        if reveal_result:
            output_f.reveal()

    def run(
        self,
        project: Project,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Dict[str, str] = None,
        clean_before: bool = True,
    ):

        # check state and args
        assert isinstance(project, Project)

        # clean
        if clean_before:
            self.clean(project=project)

        # configure
        r = _FlutterRunner(title="Build and run")
        r.add_args(["run"])
        r.add_args(["-d", "all"])
        r.set_project(project)
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(False)
        r.set_main_module(main_module)
        r.add_environment(environment)

        # Run
        r.run()

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
        image = None
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

                        m = re.search(r"\@([0-9.])x[.]\w+$", name)
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
