from ..core import ReprBuilderMixin, Runner, die, ToStringBuilder, File, Path, Directory, Safe

class Dmg(ReprBuilderMixin):
    def __init__(self):
        pass

    def configure_repr_builder(self, sb: ToStringBuilder):
        pass     

    def create(
        self,
        source,  # path to directory. TODO: add a list of directories
        output_path,
        volume_name,
        title=None
    ):
        """
            Create a DMG file. 
        """

        output_path = Path(output_path).ensure_has_extension(".dmg")
        File(output_path).remove();
        
        title = Safe.first_available([title, f"Create volume '{volume_name}'"])

        source_path = Path(source)
        args = [
            "create",
            "-fs",  "HFS+", 
            "-srcfolder", source_path, 
            "-volname", volume_name,
            output_path 
        ]
        r = Runner("hdiutil", args, title=f"{self}: {title}")
        r.add_info('Source', source_path)
        r.add_info('Output', output_path)
        r.run()
