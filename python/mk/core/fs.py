# -*- coding: utf-8 -*-
# cSpell: words fspath chdir

import os
import abc
import collections.abc
import functools
import shutil
import pathlib
from enum import Enum


from .runner import Runner 
from .to_string_builder import ReprBuilderMixin, ToStringBuilder
from .console import Console
from ._internal import int_die


# @functools.total_ordering
class Path:

    def __init__(self, path):
        # p = self._path_from_object(path);
        # p = os.path.expanduser(p);
        # p = os.path.normpath(p);
        p = os.path.normpath(os.path.expanduser(self._path_from_object(path)))
        if not p:
            raise Exception('Path cannot be empty')
        self._path = str(p)

    # accepting almost everything path-like
    @staticmethod
    def _path_from_object(p):
        
        if p is None:
            return ""

        if isinstance(p, str):
            return p
        
        if isinstance(p, os.PathLike):  # Path is also os.PathLike
            return os.fspath(p)
        
        if isinstance(p, collections.abc.Sequence) and p:
            lst = list(map(Path._path_from_object, p))
            return functools.reduce(Path._join, lst) 

        raise Exception(f"Cannot convert {p} to a path string")

    @staticmethod
    def _join(path1, path2):

        # for convenience, ignore empty or null second path component
        if path2 == "" or path2 is None:
            return os.path.join(path1)

        # prevent os.join wrong behavior on root path processing. Tested on macOS only!
        if os.path.isabs(path2):
            path2 = os.path.splitdrive(path2)[1]
            if path2.startswith(os.sep):
                path2 = path2[len(os.sep):]
        return os.path.join(path1, path2)

    # def __lt__(self, other): # + @functools.total_ordering gives full comparison
    #     return self._path < other._path 

    def __eq__(self, other): 
        return self._path == other._path 

    def __ne__(self, other): 
        return self._path != other._path 

    def __repr__(self):
        return f"[{self._path}]"  # using [ ] enables cmd+click in VS Code while < > not. 

    def __add__(self, other):
        return Path([self._path, other])

    def __iadd__(self, other):
        self._path = Path([self._path, other])._path
        return self

    def __copy__(self):
        return Path(self._path)   

    def __deepcopy__(self, memo):
        return Path(self._path)        

    # os.PathLike implementation
    def __fspath__(self):
        return self._path

    @property
    def fspath(self) -> str:
        return self._path 

    @property
    def exists(self) -> bool:
        return os.path.exists(self.fspath)

    @property
    def exists_as_link(self) -> bool:
        return os.path.islink(self._path)

    @property
    def exists_as_file(self) -> bool:
        return os.path.isfile(self._path)

    @property
    def exists_as_directory(self) -> bool:
        return os.path.isdir(self._path)

    @property
    def is_absolute(self):
        return pathlib.Path(self.fspath).is_absolute() 

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def parent(self):
        p = os.path.dirname(self._path)
        if p == self._path:  # not sure if if fully platform independent
            return None
        return Path(p)
    
    @property
    def base_name(self) -> str:
        """Base path name: filename.ext"""
        return str(os.path.basename(self._path))

    def relative(self, level: int = 0) -> str:
        '''relative path starting base_name and up to [level] levels '''
        components = [self.base_name]
        if level > 0:
            parent = self.parent
            while level > 0 and parent is not None:
                components.insert(0, parent.base_name)
                level -= 1
                parent = parent.parent
        return Path(components)

    @property
    def file_name(self) -> str:
        """File name without extension"""
        return str(os.path.splitext(os.path.basename(self._path))[0])

    @property
    def extension(self) -> str:
        """Extension with dot, if any"""
        return os.path.splitext(self._path)[1]

    def has_extension(self, extension: str) -> bool:
        e = os.path.splitext(self._path)[1]
        return e == extension  # mktodo: case insensitive comparison?

    def ensure_exists(self):
        if not self.exists:
            int_die(f'{self}: does not exist')


class FSEntry(ReprBuilderMixin, metaclass=abc.ABCMeta):
    
    def __init__(self, path):        
        self._path = Path(path)

    # ReprBuilderMixin overrides    
    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.add('path', self._path.fspath)

    # os.PathLike implementation
    def __fspath__(self):
        return self._path.fspath

    @property
    def path(self) -> Path:
        return self._path             

    def reveal(self):
        runner = Runner("open", ["-R", self])
        runner.title = f"Reveal {self}..."
        runner.run(display_output = False)

    @property
    @abc.abstractmethod
    def is_system(self):
        pass

    def remove(self, missing_ok=True):
        
        p = self.path
        if not p.exists:
            if missing_ok:
                return
            int_die(f"{self}: unable to remove (does not exist")

        if p.exists_as_file or p.exists_as_link:
            try:
                os.unlink(p.fspath)
                return
            except Exception as e:
                int_die(f"{self}: unable to remove: {e}")

        if p.exists_as_directory:
            try:
                shutil.rmtree(p.fspath)
                return
            except Exception as e:
                int_die(f"{self}: unable to remove: {e}")

        int_die(f"{self}: unable to remove: not a file, link or directory")


class FileMode(Enum):
    READ = 1
    WRITE = 2
    APPEND = 3


class File(FSEntry):

    def __init__(self, path, must_exist=False):
        self._mode = None
        self._file = None
        super().__init__(path=path)
        if must_exist:
            self.ensure_exists()

    # ReprBuilderMixin overrides    
    def configure_repr_builder(self, sb: ToStringBuilder):    
        super().configure_repr_builder(sb)    
        sb.add('mode', self._mode)

    def read_all(self):
        f = open(self.path.fspath, "r") or int_die(f"{self}: Unable to open file for reading")
        result = f.read()
        f.close()
        return result

    def open_for_writing(self):
        try:
            if self._mode != FileMode.WRITE: 
                self.close()            
                self._file = open(self.path.fspath, "w")
                self._mode = FileMode.WRITE
        except Exception as e:    
            int_die(f"{self}: Unable to open file for writing: {e}")        

    def open_for_appending(self):
        try:
            if self._mode != FileMode.APPEND: 
                self.close()            
                self._file = open(self.path.fspath, "a")
                self._mode = FileMode.APPEND
        except Exception as e:    
            int_die(f"{self}: Unable to open file for appending: {e}")        

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None
            self._mode = None

    def write(self, s):
        assert self._mode == FileMode.WRITE or self._mode == FileMode.APPEND, f"{self}: unable to write to, the file is not opened for writing"
        self._file.write(s)

    def ensure_exists(self):
        if self.path.exists:
            if self.path.exists_as_file:
                return
            int_die(f'{self}: the entry exists in file system but it is not a file')
        int_die(f'{self}: does not exist')

    def copy_to(self, destination: os.PathLike, log: bool = False):
        try:
            if log:
                Console.write(f"{self}: copying to {destination}")
            shutil.copy(self.path.fspath, destination)
        except Exception as e:
            int_die(f"{self}: Unable to copy myself to {destination}: {e}")

    def move_to(self, destination: os.PathLike, log: bool = False):
        try:
            if log:
                Console.write(f"{self}: moving to {destination}")
            shutil.move(self.path.fspath, destination)
        except Exception as e:
            int_die(f"{self}: Unable to move myself to {destination}: {e}")

    @property
    def is_system(self):
        name = self.path.base_name.lower()
        return name in [".ds_store"]


class Directory(FSEntry):

    def __init__(self, path, must_exist: bool = False, create_if_needed: bool = True):
        super().__init__(path=path)
        if must_exist:
            self.ensure_exists(create_if_needed=create_if_needed)

    # ReprBuilderMixin overrides    
    # def configure_repr_builder(self, sb: ToStringBuilder):
    #     super().configure_repr_builder(sb) 

    def make_current(self):
        try:
            os.chdir(self.path.fspath)
        except Exception as e:
            int_die(f"{self}: Unable to make myself the current directory: {e}")

    def ensure_exists(self, create_if_needed: bool = True):        
        if self.path.exists:
            if self.path.exists_as_directory:
                return
            int_die(f'{self}: the entry exists in file system but it is not a directory')
        if create_if_needed:
            try:
                os.makedirs(self.path.fspath)            
                return           
            except Exception as e:
                int_die(f'{self}: unable to create directory: {e}')
        int_die(f'{self}: does not exist')

    @property
    def is_system(self):
        return False

    def list(self, skip_system_objects=True, sort=False):
        try:
            result = []
            for (_, dirnames, filenames) in os.walk(self.path):
                if sort:
                    dirnames = sorted(dirnames)
                for d in dirnames:
                    result.append(Directory([self.path, d]))
                if sort:
                    filenames = sorted(filenames)
                for f in filenames:
                    file = File([self.path, f])
                    if not skip_system_objects or not file.is_system:
                        result.append(file)
                return result # no recurse yet
        except Exception as e:
            int_die(f'{self}: unable to list the directory: {e}')
