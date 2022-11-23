import json
from ..core import ReprBuilderMixin, Runner, die, ToStringBuilder, File, Path, Directory, Safe


class Project(ReprBuilderMixin):
    def __init__(self, dir_path):
        dir_path = Path(dir_path)
        self._dir_path = dir_path
        if not dir_path.exists_as_directory:
            die(f"No project found at path {dir_path}: not a directory")

        self.package_json_path = Path([dir_path, "package.json"])
        if not self.package_json_path.exists_as_file:
            die(f"No package.json found at path {self.package_json_path}")

        with open(self.package_json_path, "rt", encoding="utf-8") as f:
            d = json.load(f)
            self._name = d["name"]
            self._version = d["version"]

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.typename = "NodeJS.Project"
        sb.add_value(f"{self._dir_path}")
        sb.add_value(f"{self._name}/{self._version}")

    @property
    def directory(self):
        return Directory(self._dir_path)


class NodeJS(ReprBuilderMixin):
    def __init__(self):
        self._load()

    def _load(self):
        pass

    def configure_repr_builder(self, sb: ToStringBuilder):
        pass

    def npm_run(
        self, 
        project: Project, 
        args=None, 
        display_output=False,
        title: str="Running npm script"
    ):  # pylint: disable=no-self-use
        args = Safe.to_list(args)

        project.directory.make_current()

        r = Runner("npm", args=["run"] + args, title=f"Node.JS: {title}")
        r.add_info("Project", project)
        r.add_info("Script", args)
        r.run(display_output=display_output, notify_completion=True)

    def npx_run(
        self, 
        args, 
        display_output=False,
        title: str="Running npm script"
    ):  # pylint: disable=no-self-use
        args = Safe.to_list(args)

        r = Runner("npx", args, title=f"Node.JS: {title}")
        r.add_info("Command", " ".join(args))
        r.run(display_output=display_output, notify_completion=True)
