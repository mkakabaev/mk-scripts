from ..core import ReprBuilderMixin, Runner, die, ToStringBuilder, File, Path, Directory, Safe


class SSH(ReprBuilderMixin):
    def __init__(self, user: str, host: str):
        self.user = user
        self.host = host
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

    def upload(self, local_path, remote_path, title=None):
        title = Safe.first_available([title, f"Uploading {local_path}"])
        local_path = Path(local_path)
        remote_path = self._make_remote_path(remote_path)        
        r = Runner("scp", [ local_path, remote_path], title=f"{self}: {title}")
        r.run(notify_completion=False, display_output=True)

    def download(self, remote_path, local_path, title=None) :
        title = Safe.first_available([title, f"Downloading {remote_path}"])
        local_path = Path(local_path)
        remote_path = self._make_remote_path(remote_path)        
        r = Runner("scp", [ remote_path, local_path], title=f"{self}: {title}")
        r.run(notify_completion=False, display_output=True)

    def run_script(self, script: str, title: str = None):
        title = Safe.first_available([title, "Executing script"])
        r = Runner( "ssh", [ self._make_connection_string(), 'bash', "-s"], title=f"{self}: {title}")
        r.run(notify_completion=True, input_data=script, display_output=False)
