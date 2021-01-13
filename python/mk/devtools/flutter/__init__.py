# -*- coding: utf-8 -*-
# cSpell: words 

from typing import Dict
from enum import Enum
from .assets import *
from .project import Project
from ...core import Runner
from ..xcode import Xcode

__all__ = [
    "Assets",
    "Project"
]


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
        
    def clean(self, project: Project):  # pylint: disable=no-self-use
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
        archive_dir=None,  # Xcode archive
        scheme: str = None,  # Xcode scheme
        ad_hoc_export: bool = False,
        app_store_export: bool = False,
        app_store_upload: bool = False,
        reveal_result: bool = True
    ):  # pylint: disable=too-many-locals, too-many-statements
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
