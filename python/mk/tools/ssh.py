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

class SSH(ReprBuilderMixin):
    """
        options: generic list of arguments like ["-o", "option", "-i", "keyfile"] etc
    """
    def __init__(self, user: str, host: str, options: list[str] = []):
        self.user = user
        self.host = host
        self.options = options
        self._load()

    def _load(self):
        pass

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.add_value(self._make_connection_string())

    def _make_connection_string(self):
        components = []
        if self.user:
            components.append(self.user)
        if self.host:
            components.append(self.host)
        return "@".join(components)

    def _make_remote_path(self, path):
        user_host = self._make_connection_string()
        components = []
        if user_host:
            components.append(user_host)
        components.append(Path(path).fspath)
        return ":".join(components)

    def upload(self, local_path, remote_path, title: str | None = None, display_output: bool = True):
        title = Safe.first_available([title, f"Uploading {local_path}"])
        local_path = Path(local_path)
        remote_path = self._make_remote_path(remote_path)
        args = []
        if local_path.exists_as_directory:  # recursive copy
            args += ["-r"]
        args += self.options
        args += [local_path, remote_path]
        r = Runner("scp", args, title=f"{self}: {title}")
        r.run(notify_completion=False, display_output=display_output)

    def download(self, remote_path, local_path, title: str | None = None, display_output: bool = True):
        title = Safe.first_available([title, f"Downloading {remote_path}"])
        local_path = Path(local_path)
        remote_path = self._make_remote_path(remote_path)
        r = Runner("scp", [self.options, remote_path, local_path], title=f"{self}: {title}")
        r.run(notify_completion=False, display_output=display_output)

    def run_script(self, script: str, title: str | None = None, display_output: bool = True):
        """
            Run a multi-line script
        """
        title = Safe.first_available([title, "Executing script"])
        r = Runner(
            "ssh",
            [self._make_connection_string(), self.options, "bash", "-s"],
            title=f"{self}: {title}",
        )
        r.run(notify_completion=True, input_data=script, display_output=display_output)

    def run_command(self, command: str | list[str], title: str | None = None, display_output: bool = True):
        """
            Run a single command
        """
        title = Safe.first_available([title, "Executing command"])
        r = Runner(
            "ssh",
            [self._make_connection_string(), self.options, " ".join(Safe.to_list(command))],
            title=f"{self}: {title}",
        )
        r.run(notify_completion=True, display_output=display_output)
