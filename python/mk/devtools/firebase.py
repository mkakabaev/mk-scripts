# -*- coding: utf-8 -*-
# cspell:ignore appdistribution

import json
from typing import List
from ..core import (
    ReprBuilderMixin,
    Runner,
    die,
    ToStringBuilder,
    File,
    Path,
    Directory,
    Safe,
)


class Firebase(ReprBuilderMixin):
    def __init__(self, token: str | None = None):
        self.token = token
        self._load()

    def _load(self):
        pass

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "Firebase"
        pass

    def _authorize_runner(self, runner: Runner):
        if self.token is not None:
            runner.add_dash2_arg_pair("token", self.token)
            runner.add_info("Authorization", "Token")

    def app_distribution_upload(
        self,
        path: Path,
        app_id: str,
        display_output=False,
        title: str | None = None,
        release_notes: str | None = None,
        release_notes_file: Path | None = None,
        tester_emails: list[str] | None = None,
        tester_emails_file: Path | None = None,
        tester_groups: list[str] | None = None,
        tester_groups_file: Path | None = None,
    ):
        """
        Uploads a release binary to Firebase App Distribution.

        Parameters:
        - path (Path): The path to the release binary file to be distributed.
        - app_id (str): The ID of the Firebase app to which the binary should be distributed.
        - display_output (bool, optional): Whether to display the command execution output. Defaults to False.
        - title (str, optional): Title for the operation. Defaults to "Distribute Application".
        - release_notes (str, optional): Release notes to include in the distribution. Defaults to None.
        - release_notes_file (Path, optional): Path to a file containing release notes. Defaults to None.
        - tester_emails (List[str], optional): List of tester email addresses. Defaults to None.
        - tester_emails_file (Path, optional): Path to a file containing a comma-separated list of tester email addresses. Defaults to None.
        - tester_groups (List[str], optional): List of group aliases to distribute to. Defaults to None.
        - tester_groups_file (Path, optional): Path to a file containing a comma-separated list of group aliases to distribute to. Defaults to None.

        Returns:
        None
        """
        if title is None:
            title = f"Distribute Application"

        r = Runner("firebase", ["appdistribution:distribute", path], title=title)

        def _make_csv_arg(args: List[str] | None):
            l = Safe.to_string_list(args)
            if len(l) > 0:
                return ",".join(l)
            return None

        r.add_dash2_arg_pair("app", app_id)
        r.add_dash2_arg_pair("release-notes", release_notes)
        r.add_dash2_arg_pair("release-notes-file", release_notes_file)
        r.add_dash2_arg_pair("testers", _make_csv_arg(tester_emails))
        r.add_dash2_arg_pair("testers-file", tester_emails_file)
        r.add_dash2_arg_pair("groups", _make_csv_arg(tester_groups))
        r.add_dash2_arg_pair("groups-file", tester_groups_file)
        r.add_info("AppId", app_id)
        r.add_info("File", path)
        r.add_info("Groups", _make_csv_arg(tester_groups))
        r.add_info("Groups File", tester_groups_file)
        r.add_info("Testers", _make_csv_arg(tester_emails))
        r.add_info("Testers File", tester_emails_file)
        r.add_info("Release Notes", release_notes_file)
        
        self._authorize_runner(r)

        r.run(display_output=display_output)
