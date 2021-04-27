# -*- coding: utf-8 -*-
# cSpell: words xcodebuild xcodeproj unsubscriptable

from typing import Union
from ..core import ReprBuilderMixin, Runner, die, ToStringBuilder, File, Path, Directory

class Workspace(ReprBuilderMixin):
    def __init__(self, path):
        p = Path(path)
        self._path = p
        if p.has_extension(".xcworkspace") and p.exists_as_directory:
            pass
        else:
            die(f"No workspace found at path {p} ")

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "xcode.Workspace"
        sb.add_value(f"{self._path.file_name}")

    @property
    def base_name(self):
        return self._path.base_name

    @property
    def directory(self):
        return Directory(self._path.parent)


class Project(ReprBuilderMixin):
    def __init__(self, path):
        p = Path(path)
        self._path = p
        if p.has_extension(".xcodeproj") and p.exists_as_directory:
            pass
        else:
            die(f"No project found at path {p} ")

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "xcode.Project"
        sb.add_value(f"{self._path.file_name}")

    @property
    def base_name(self):
        return self._path.base_name

    @property
    def directory(self):
        return Directory(self._path.parent)

WorkspaceOrProject = Union[Workspace, Project] # pylint: disable=unsubscriptable-object

class _XcodebuildRunner:
    def __init__(self, title):
        self._runner = Runner("xcodebuild")
        self._runner.title = title
        self._workspace = None
        self._root_dir = None

    def add_args(self, args):
        self._runner.add_args(args)

    def add_arg_pair(self, param, value, header_name):
        if header_name is not None:
            self._runner.add_info(header_name, value)
        self._runner.add_args([param, value])

    def add_hdr(self, name, value):
        self._runner.add_info(name, value)

    def set_workspace(self, workspace: Workspace):
        assert isinstance(workspace, Workspace)
        self._root_dir = workspace.directory
        self.add_arg_pair("-workspace", workspace.base_name, "Workspace")
        self.add_hdr("Directory", self._root_dir.path)

    def set_project(self, project: Project):
        assert isinstance(project, Project)
        self._root_dir = project.directory
        self.add_arg_pair("-project", project.base_name, "Project")
        self.add_hdr("Directory", self._root_dir.path)

    def set_workspace_or_project(self, workspace_or_project:  WorkspaceOrProject): 
        if isinstance(workspace_or_project, Workspace):
            self.set_workspace(workspace_or_project)
        elif isinstance(workspace_or_project, Project):
            self.set_project(workspace_or_project)
        else:
            die("workspace or project is required")

    def set_scheme(self, scheme):
        self.add_arg_pair("-scheme", scheme, "Scheme")

    def run(self):
        if self._root_dir is not None:
            self._root_dir.make_current()
        self._runner.run(display_output=False, notify_completion=True)


class Xcode(ReprBuilderMixin):
    def __init__(self):
        self._load()

    def _load(self):
        pass

    def configure_repr_builder(self, sb: ToStringBuilder):
        pass

    def clean(self, workspace_or_project:  WorkspaceOrProject, scheme: str):  
        r = _XcodebuildRunner(title=f"{self}: Cleaning")
        r.set_workspace_or_project(workspace_or_project)
        r.set_scheme(scheme)
        r.add_args("clean")
        r.run()

    def archive(
        self,
        workspace_or_project:  WorkspaceOrProject, 
        scheme: str,
        archive_file,
        clean_first: bool = True,
    ):
        if clean_first:
            self.clean(workspace_or_project, scheme=scheme)

        archive_path = Path(archive_file)
        Directory(archive_path.parent).ensure_exists()

        r = _XcodebuildRunner(title=f"{self}: Archive")
        r.set_workspace_or_project(workspace_or_project)
        r.set_scheme(scheme)
        r.add_arg_pair("-archivePath", archive_path, "Result archive")
        r.add_args("archive")
        r.run()

    def make_export_options_file(  # pylint: disable=no-self-use
        self,
        output_path,
        team_id: str = None,
        method: str = None,
        signing_style: str = "automatic",
        destination: str = None
    ):
        content = []

        def add_key_value(key, value):
            if value is not None:
                content.append(f"<key>{key}</key>")
                content.append(f"<string>{value}</string>")

        # see all available keys using `xcodebuild -h`
        add_key_value("method", method)
        add_key_value("signingStyle", signing_style)
        add_key_value("teamID", team_id)
        add_key_value("destination", destination)

        options_file = File(output_path)
        options_file.open_for_writing()
        options_file.write(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n<dict>\n\t' + "\n\t".join(content) + "\n</dict>\n</plist>"
        )
        options_file.close()

    def export_ad_hoc(
        self,
        archive_file,
        output_dir,
    ):
        archive_path = Path(archive_file)
        output_dir_path = Path(output_dir)

        # create output dir
        out_dir = Directory(output_dir_path)
        out_dir.ensure_exists()

        # Create options file
        plist_path = Path([output_dir_path, "ExportOptions.plist"])
        self.make_export_options_file(output_path=plist_path, method="ad-hoc")

        # export
        r = _XcodebuildRunner(title=f"{self}: Export AdHoc")
        r.add_args("-exportArchive")
        r.add_arg_pair("-archivePath", archive_path, "Source archive")
        r.add_arg_pair("-exportOptionsPlist", plist_path, "Options")
        r.add_arg_pair("-exportPath", output_dir_path, "Output")
        r.add_args("-allowProvisioningUpdates") # to enable automatic signing and getting fresh profiles
        r.run()

    def export_app_store(
        self,
        archive_file,
        output_dir,
        is_upload: bool = False
    ):
        archive_path = Path(archive_file)
        output_dir_path = Path(output_dir)

        # create output dir
        out_dir = Directory(output_dir_path)
        out_dir.ensure_exists()

        # Create options file
        plist_path = Path([output_dir_path, "ExportOptions.plist"])
        self.make_export_options_file(
            output_path=plist_path, 
            method="app-store",
            destination="upload" if is_upload else None
        )

        # export
        if is_upload:
            r = _XcodebuildRunner(title=f"{self}: Uploading to AppStore")
        else:
            r = _XcodebuildRunner(title=f"{self}: Exporting AppStore's IPA")
            r.add_arg_pair("-exportPath", output_dir_path, "Output")
        r.add_args("-exportArchive")
        r.add_arg_pair("-archivePath", archive_path, "Source archive")
        r.add_arg_pair("-exportOptionsPlist", plist_path, "Options")
        r.add_args("-allowProvisioningUpdates") # to enable automatic signing and getting fresh profiles
        r.run()

# cSpell: disable
# class XCode:

#     IsRunning = False
#     SourceRoot = ""
#     ProjectDir = ""
#     InfoPListPath = ""
#     @classmethod
#     def check_is_running(cls):
#         if not cls.IsRunning:
#             fatal_error("Script is intended to be invoked by XCode building process")

#     @classmethod
#     def all_sources(cls):
#         cls.check_is_running()

#         result = []

#         def is_wrong_folder(signature):
#             if subdir.endswith(signature): return True
#             if (signature + "/") in subdir: return True
#             return False

#         for subdir, _, files in os.walk(cls.SourceRoot):
#             if is_wrong_folder("Tests"): continue
#             if is_wrong_folder(".framework"): continue
#             if is_wrong_folder(".idea"): continue
#             if is_wrong_folder(".xcodeproj"): continue
#             if is_wrong_folder(".xcassets"): continue
#             if is_wrong_folder("3rdparty"): continue
#             if is_wrong_folder(".lproj"): continue

#             for file in files:
#                 path = os.path.join(subdir, file)
#                 if path.endswith(".swift"):
#                     result.append(path)

#         return result

#     @classmethod
#     def load(cls):
#         if "XCODE_PRODUCT_BUILD_VERSION" in os.environ:
#             cls.SourceRoot = os.environ["SOURCE_ROOT"]
#             cls.ProjectDir = os.environ["PROJECT_DIR"]
#             cls.InfoPListPath = os.environ["PRODUCT_SETTINGS_PATH"]
#             cls.IsRunning = True

# class VersionBuilder:
#     def __init__(self, env):
#         self.env = env
#         self.load()

#     def load(self):
#         self.version = None
#         self.build = None

#         self.build_number = Runner(self.env, "xcrun", ["agvtool", "what-version", "-terse"]).run("Getting build number")
#         build_version = Runner(self.env, "xcrun", ["agvtool", "what-marketing-version", "-terse"]).run("Getting build version")
#         m = re.search('=(.+)$', build_version)
#         if m is None:
#             die("Unable extract project version from {}".format(build_version))
#         self.build_version = m.group(1).strip()

#     def increment(self):
#         Runner(self.env, "xcrun", ["agvtool", "next-version", "-all"]).run("Incrementing build version")
#         self.load()

#     def __str__(self):
#         return "{}.{}".format(self.build_version, self.build_number)
