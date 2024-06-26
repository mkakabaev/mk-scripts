# -*- coding: utf-8 -*-
# cSpell: words unsubscriptable appbundle
# pylint: disable=too-many-statements, too-many-locals

from typing import Dict, Optional
from enum import Enum
from .assets import *
from .project import Project
from ...core import Runner
from ..xcode import Xcode

__all__ = ["Assets", "Project"]


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


class _AppNamer:
    def __init__(self) -> None:
        self.prefix = "app"
        self.flavor = None
        self.build_mode = None
        self.project_version: Optional[str]

    def get(self, postfix="", include_version=False):
        components = []
        components.append(self.prefix)
        if self.flavor:
            components.append(self.flavor)
        if self.build_mode:
            components.append(self.build_mode)
        if include_version and self.project_version:
            components.append(self.project_version)
        return "-".join(components) + postfix

    @property
    def flutter_app_bundle_folder(self):
        components = []
        if self.flavor:
            components.append(self.flavor)
        if self.build_mode:
            components.append(self.build_mode.capitalize())
        return "".join(components)


class FlutterSDK(ReprBuilderMixin):
    def __init__(self):
        self.version = "?"
        self.channel = "?"
        self.fvm_version = None
        self.command = "flutter"
        self._load()

    def _load(self):
        fvm_r = Runner("fvm", "--version").run_silent(die_on_error=False)
        if fvm_r.code == 0:
            self.fvm_version = fvm_r.search(r"([0-9.]+)", 1, tag="version")
            self.command = ["fvm", "flutter"]
        r = Runner(self.command, "--version", title=f"{self.command} --version")
        result = r.run_silent()
        self.version = result.search(r"Flutter ([0-9.]+)", 1, tag="version")
        self.channel = result.search(r"channel\s+(\S+)", 1, tag="channel")

    @property
    def has_vfm(self):
        return self.fvm_version is not None

class _FlutterProjectRunner:
    def __init__(self, title: str, project: Project):
        self._runner = Runner("<_unknown_flutter_>", title=f"Flutter: {title}")
        self._project = None
        self.namer = _AppNamer()
        self.set_project(project)
        self._sdk_info_added = False

    def add_args(self, args):
        self._runner.add_args(args)

    def add_hdr(self, name, param):
        self._runner.add_info(name, param)

    def set_project(
        self,
        project: Project,
    ):
        assert isinstance(project, Project)
        self._project = project
        self.add_hdr("Project", project)
        self.add_hdr("Project Path", project.path)
        self.add_hdr("Project FVM Version", project.fvm_version)
        self.namer.project_version = project.version

    def set_flavor(self, flavor):
        if flavor is not None:
            self._runner.add_args(["--flavor", flavor])
            self.namer.flavor = flavor
            self.add_hdr("Flavor", flavor)

    def set_build_mode(self, build_mode):
        self._runner.add_args(build_mode.compile_flag)
        self.namer.build_mode = build_mode.file_name
        self.add_hdr("Build mode", build_mode.display_name)

    def set_analyze_size(self, flag):
        if flag:
            self._runner.add_args("--analyze-size")
            self.add_hdr("Size analysis enabled", True)

    def set_main_module(self, main_module):
        if main_module is not None:
            self._runner.add_args(["-t", main_module])
            self.add_hdr("Main module", main_module)

    def add_environment(
        self, env: Optional[Dict[str, str]]
    ):  # pylint: disable=unsubscriptable-object
        if env is not None and len(env) > 0:
            for name, value in env.items():
                self._runner.add_args(f"--dart-define={name}={value}")
            self.add_hdr("Environment", env)

    def run(self):
        
        if self._project is not None:
            self._project.make_directory_current()
        
        # get the SDK info, display it, configure command. Do it here because it depends on folder 
        flutter_sdk = FlutterSDK()
        self._runner.set_command(flutter_sdk.command)
        
        if self._project is not None:
            p_ver = self._project.fvm_version
            if p_ver is not None:
                if p_ver != flutter_sdk.version:
                    die(f"Flutter version mismatch: Project required {p_ver}, SDK is {flutter_sdk.version}")  
            
        # add SDK info to the runner
        if not self._sdk_info_added:
            self._sdk_info_added = True
            s = f"{flutter_sdk.version}/{flutter_sdk.channel}"
            if flutter_sdk.has_vfm:
                s += f" FVM({flutter_sdk.fvm_version})"
            self.add_hdr("Flutter SDK", s)

        self._runner.run(display_output=False, notify_completion=True)


class FlutterResult(ReprBuilderMixin):
    def __init__(self):
        self.project_version: str | None = None
        self.archive_file: File | None = None
        self.archive_dir: Directory | None = None
        self.mac_app_output_dir: Directory | None = None
        self.mac_app_development_output_dir: Directory | None = None
        self.ad_hoc_directory: Directory | None = None
        self.app_store_directory: Directory | None = None
        self.app_store_upload_directory: Directory | None = None
        self.apk_file: File | None = None

    @property
    def ad_hoc_ipa_file(self) -> File | None:
        files = Directory(self.ad_hoc_directory, must_exist=True).list()
        for file in files:
            if isinstance(file, File) and file.path.fspath.endswith(".ipa"):
                return file
        return None

    def configure_repr_builder(self, sb: ToStringBuilder):
        pass


class Flutter(ReprBuilderMixin):
    def __init__(self):
        # self._version = "?"
        # self._channel = "?"
        # self._load()
        pass

    def _load(self):
        # fvm_r = Runner("fvm", "--version").run_silent(die_on_error=False)
        # if fvm_r.code == 0:
        #     self._fvm_version = fvm_r.search(r"([0-9.]+)", 1, tag="version")
        # else:
        #     self._fvm_version = None
        # r = Runner("flutter", "--version", title="flutter --version")
        # result = r.run_silent()
        # self._version = result.search(r"Flutter ([0-9.]+)", 1, tag="version")
        # self._channel = result.search(r"channel\s+(\S+)", 1, tag="channel")
        pass

    def configure_repr_builder(self, sb: ToStringBuilder):
        # sb.add_value(f"{self._version}/{self._channel}")
        pass

    def clean(self, project: Project):  # pylint: disable=no-self-use
        r = _FlutterProjectRunner(title="Clean", project=project)
        r.add_args("clean")
        r.run()

    def build_ios(
        self,
        project: Project,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Optional[Dict[str, str]] = None,
        clean_before: bool = True,
        analyze_size: bool = False,
        archive_dir=None,  # Xcode archive
        scheme: Optional[str] = None,  # Xcode scheme
        ad_hoc_export: bool = False,
        app_store_export: bool = False,
        app_store_upload: bool = False,
        reveal_result: bool = True,
    ) -> FlutterResult:
        # check state and args
        assert isinstance(project, Project)

        # clean flutter
        if clean_before:
            self.clean(project=project)

        # starting collecting result data
        result = FlutterResult()
        result.project_version = project.version

        # configure and run
        r = _FlutterProjectRunner(title="Build iOS", project=project)
        r.add_args(["build", "ios"])
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(analyze_size)
        r.set_main_module(main_module)
        r.add_environment(environment)
        r.add_hdr("Ad Hoc build", ad_hoc_export)
        r.add_hdr("AppStore build", app_store_export)
        r.add_hdr("Upload to AppStore", app_store_upload)

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
            archive_file = File(
                [archive_dir, r.namer.get(postfix=".xcarchive", include_version=True)]
            )
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
                app_store_upload_directory = Directory(
                    [archive_dir, "app_store_upload"]
                )
                app_store_upload_directory.remove()

        # Run flutter. On completion stop unless archiving is ordered
        r.run()
        if not do_archive:
            if reveal_result:
                Directory(project.ios_app).reveal()
            return result

        result.archive_file = archive_file
        result.archive_dir = archive_dir
        result.ad_hoc_directory = ad_hoc_directory
        result.app_store_directory = app_store_directory
        result.app_store_upload_directory = app_store_upload_directory

        # archive the project
        workspace = project.xcode_ios_workspace
        if scheme is None:
            scheme = flavor if flavor is not None else "Runner"
        xcode = Xcode()
        xcode.set_destination_ios()
        xcode.archive(workspace, scheme=scheme, archive_file=archive_file)  # type: ignore

        # do ad-hoc export
        if do_export_ad_hoc:
            xcode.export_ad_hoc(
                archive_file=archive_file,
                output_dir=ad_hoc_directory,
                display_output=False,
            )

        # do app-store export
        if do_export_app_store:
            xcode.export_app_store(
                archive_file=archive_file,
                output_dir=app_store_directory,
                display_output=False,
            )

        # do upload to app store
        if do_upload_app_store:
            xcode.export_app_store(
                archive_file=archive_file,
                output_dir=app_store_upload_directory,
                is_upload=True,
                display_output=False,
            )

        if reveal_result:
            File(archive_file).reveal()

        return result

    def build_macos(
        self,
        project: Project,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Optional[Dict[str, str]] = None,
        clean_before: bool = True,
        analyze_size: bool = False,
        archive_dir=None,  # Xcode archive, optional, but required for any exporting
        scheme: Optional[str] = None,  # Xcode scheme
        app_export: bool = False,
        development_app_export: bool = False,
        # app_store_export: bool = False,
        # app_store_upload: bool = False,
        reveal_result: bool = True,
    ) -> FlutterResult:

        # check state and args
        assert isinstance(project, Project)

        # clean flutter
        if clean_before:
            self.clean(project=project)

        # starting collecting result data
        result = FlutterResult()
        result.project_version = project.version

        # configure and run
        r = _FlutterProjectRunner(title="Build macOS", project=project)
        r.add_args(["build", "macos"])
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(analyze_size)
        r.set_main_module(main_module)
        r.add_environment(environment)
        r.add_hdr("Export App from archive", app_export)
        r.add_hdr(
            "Export App from archive as Development build", development_app_export
        )

        # r.add_hdr('AppStore build', app_store_export)
        # r.add_hdr('Upload to AppStore', app_store_upload)

        # configure xcode stuff
        archive_file = None
        path_to_reveal = None
        # app_store_directory = None
        # app_store_upload_directory = None
        # do_export_app_store = False
        # do_upload_app_store = False

        do_archive = False
        if archive_dir is not None:
            do_archive = True
            archive_file = File(
                [archive_dir, r.namer.get(postfix=".xcarchive", include_version=True)]
            )
            archive_file.remove()
            path_to_reveal = archive_file
            result.archive_file = archive_file
            result.archive_dir = archive_dir

        if app_export or development_app_export:
            if not do_archive:
                die("<archive_dir> is required for <app_export> option")

        app_directory = None
        if app_export:
            app_directory = Directory([archive_dir, "app"])
            app_directory.remove()
            path_to_reveal = app_directory
            result.mac_app_output_dir = app_directory

        dev_app_directory = None
        if development_app_export:
            dev_app_directory = Directory([archive_dir, "app_development"])
            dev_app_directory.remove()
            path_to_reveal = dev_app_directory
            result.mac_app_development_output_dir = dev_app_directory

        # Not implemented yet
        # if app_store_export:
        #     do_export_app_store = True
        #     app_store_directory = Directory([archive_dir, "app_store"])
        #     app_store_directory.remove()
        # if app_store_upload:
        #     do_upload_app_store = True
        #     app_store_upload_directory = Directory([archive_dir, "app_store_upload"])
        #     app_store_upload_directory.remove()

        # Run flutter. On completion stop unless archiving is ordered
        r.run()
        if not do_archive:
            return result

        # archive the project
        workspace = project.xcode_macos_workspace
        if scheme is None:
            scheme = flavor if flavor is not None else "Runner"
        xcode = Xcode()
        xcode.set_destination_macos()
        xcode.archive(workspace, scheme=scheme, archive_file=archive_file)

        # do app export
        if app_export:
            xcode.export_mac_application(
                archive_file=archive_file,
                output_dir=app_directory,
            )

        # do development export
        if development_app_export:
            xcode.export_mac_application_development(
                archive_file=archive_file,
                output_dir=dev_app_directory,
            )

        # Not implemented yet

        # # do app-store export
        # if do_export_app_store:
        #     xcode.export_app_store(
        #         archive_file=archive_file,
        #         output_dir=app_store_directory,
        #     )

        # # do upload to app store
        # if do_upload_app_store:
        #     xcode.export_app_store(
        #         archive_file=archive_file,
        #         output_dir=app_store_upload_directory,
        #         is_upload=True
        #     )

        if reveal_result:
            File(path_to_reveal).reveal()

        return result

    def build_apk(
        self,
        project: Project,
        output_dir,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Optional[Dict[str, str]] = None,
        reveal_result: bool = True,
        clean_before: bool = True,
        # analyze_size: bool = False
    ) -> FlutterResult:

        # check state and args
        assert isinstance(project, Project)

        # clean
        if clean_before:
            self.clean(project=project)

        # starting collecting result data
        result = FlutterResult()
        result.project_version = project.version

        # configure
        r = _FlutterProjectRunner(title="Build Android APK", project=project)
        r.add_args(["build", "apk"])
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(False)
        r.set_main_module(main_module)
        r.add_environment(environment)

        src_app_name = r.namer.get(".apk")
        dst_app_name = r.namer.get(".apk", include_version=True)
        output_d = Directory(output_dir)
        build_f = File(
            [project.path, "build", "app", "outputs", "flutter-apk", src_app_name]
        )
        output_f = File([output_d.path, dst_app_name])
        r.add_hdr("Build file name", dst_app_name)
        r.add_hdr("Output", output_d.path)

        # Prepare output folders, cd to project, build the project
        output_d.ensure_exists()
        output_f.remove()
        r.run()

        # copy the result
        Console.write_section_header(f"Copying {src_app_name} to {output_f.path}...")
        build_f.ensure_exists()
        build_f.copy_to(output_f)

        # check the result and reveal
        output_f.ensure_exists()
        if reveal_result:
            output_f.reveal()

        result.apk_file = output_f
        return result

    def build_app_bundle(
        self,
        project: Project,
        output_dir,
        flavor=None,
        build_mode: BuildMode = BuildMode.RELEASE,
        main_module=None,
        environment: Optional[Dict[str, str]] = None,
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
        r = _FlutterProjectRunner(title="Build Android app bundle (AAB)", project=project)
        r.add_args(["build", "appbundle"])
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(False)
        r.set_main_module(main_module)
        r.add_environment(environment)

        # No --build-number XXX, --build-name=X.Y.Z yet. Values are taken from project version string
        src_app_name = r.namer.get(".aab")
        dst_app_name = r.namer.get(".aab", include_version=True)
        output_d = Directory(output_dir)
        build_f = File(
            [
                project.path,
                "build",
                "app",
                "outputs",
                "bundle",
                r.namer.flutter_app_bundle_folder,
                src_app_name,
            ]
        )
        output_f = File([output_d.path, dst_app_name])
        r.add_hdr("Build file name", dst_app_name)
        r.add_hdr("Output", output_d.path)

        # flutter build appbundle -d all --flavor prod --build-number XXX --release "lib/main_prod.dart"

        # Prepare output folders, cd to project, build the project
        output_d.ensure_exists()
        output_f.remove()
        r.run()

        # copy the result
        Console.write_section_header(f"Copying {src_app_name} to {output_f.path}...")
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
        environment: Optional[Dict[str, str]] = None,
        clean_before: bool = True,
    ):

        # check state and args
        assert isinstance(project, Project)

        # clean
        if clean_before:
            self.clean(project=project)

        # configure
        r = _FlutterProjectRunner(title="Build and run", project=project)
        r.add_args(["run"])
        r.add_args(["-d", "all"])
        r.set_flavor(flavor)
        r.set_build_mode(build_mode)
        r.set_analyze_size(False)
        r.set_main_module(main_module)
        r.add_environment(environment)

        # Run
        r.run()
