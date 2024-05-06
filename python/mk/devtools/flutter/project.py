# -*- coding: utf-8 -*-
# cSpell: words iphoneos pubspec

import re
from ...core import (
    ReprBuilderMixin,
    die,
    ToStringBuilder,
    File,
    Path,
    Directory,
)
from ..xcode import Workspace as XcodeWorkspace


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
            else:
                return m.group(group)

        self._name = fetch("name", r"^name:\s+(\S+)", 1)
        self._description = fetch("description", r"^description:\s+(\S.*)\s*$", 1)
        self._version = fetch("version", r"^version:\s*(\S+)", 1)

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "flutter.Project"
        sb.add_value(f"{self._name}/{self._version}")

    def make_directory_current(self):
        Directory(self.path).make_current()

    @property
    def name(self):
        return self._name

    @property
    def version_xyz(self):
        """Returns the version of the project in X.Y.Z"""
        version = self._version
        if version is None:
            version = ""
        result = version.split("+")[0]
        if result is None or result.strip() == "":
            raise Exception("Version is not set")
        return result.strip()

    @property
    def build_number(self):
        version = self._version
        if version is None:
            version = ""
        result = version.split("+", 1)[1]
        if result is None or result.strip() == "":
            raise Exception("Build number is not set")
        return result.strip()

    @property
    def version(self):
        """Returns the version of the project in X.Y.Z+Build"""
        return self._version

    @property
    def description(self):
        return self._description

    @property
    def xcode_ios_workspace(self) -> XcodeWorkspace:
        return XcodeWorkspace(self.path + "ios/Runner.xcworkspace")

    @property
    def ios_app(self) -> Directory:
        return Directory(self.path + "build/ios/iphoneos/Runner.app")

    @property
    def xcode_macos_workspace(self) -> XcodeWorkspace:
        return XcodeWorkspace(self.path + "macos/Runner.xcworkspace")

    # @property
    # def mac_app(self) -> Directory:
    #     return Directory(self.path + "build/ios/iphoneos/Runner.app")
