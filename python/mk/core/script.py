# -*- coding: utf-8 -*-
# cSpell: words atexit getpid runpy

import signal
import sys
import atexit
import os
import time
import re
import importlib.util
from runpy import run_path
from rich.rule import Rule
from .console import Console, ConsoleStyle
from .notification import NotificationConfig, NotificationSound, show_notification
from .fs import Path, Directory
from .time import TimeCounter
from .assets import Assets

# core folder: os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
# import inspect
# print(inspect.currentframe())
# print(inspect.getfile(inspect.currentframe()))
# print(f"---{sys.argv}---") 

class _SignalHandler:
    def __init__(self, signal_no, handler):
        def do_handle(s_no, stack_frame):
            self.new_handler()
            if callable(self.old_handler):
                self.old_handler(s_no, stack_frame)
            elif self.old_handler == signal.SIG_DFL:
                signal.signal(s_no, signal.SIG_DFL)
                os.kill(os.getpid(), s_no)  # Rethrow signal

        self.new_handler = handler
        self.old_handler = signal.getsignal(signal_no)
        signal.signal(signal_no, do_handle)


class ExitActionConfig:
    def __init__(
        self, 
        notification_config: NotificationConfig = None, 
        console_style: ConsoleStyle = None
    ):
        self.notification_config = notification_config
        self.console_style = console_style


class _StackItem:
    def __init__(self, path):
        self.path = Path(path)
        self.directory = Directory(self.path.parent)
        self.time_counter = TimeCounter()
    
    @property
    def name(self):
        return re.sub( r"[.]py$", "", self.path.base_name).upper()

class _Stack:
    def __init__(self):
        self.items = []

    def push(self, path):
        self.items.append(_StackItem(path))

    def pop(self):
        del self.items[-1]

    def _get_name(self):
        return " >> ".join(map(lambda i: i.name, self.items))

    @property
    def display_path(self):
        return f"[{self._get_name()}]" 

    @property
    def display_name_ntf(self):
        return f"{self._get_name()}"  # no braces. notification utility does not like it :(

    @property
    def current(self) -> _StackItem:
        return self.items[-1]

    @property
    def is_nested(self) -> bool:
        return len(self.items) > 1
        

class Script:
    @classmethod
    def _init(cls):        
        cls._stack = _Stack()
        cls._stack.push(sys.argv[0])
        # cls.directory = Directory(cls.path.parent)
        # cls._exit_handlers = []
        cls._on_exit_called = False
        # _SignalHandler(signal.SIGINT, lambda: cls._call_exit_handler(ExitReason.SIG_INT)) # will use exception hook for KeyboardInterrupt instead
        _SignalHandler(signal.SIGTERM, cls._on_sig_term)
        atexit.register(cls._on_default_exit)
        cls._original_except_hook = sys.excepthook
        sys.excepthook = cls._except_hook        

    # not needed yet
    # @classmethod
    # def register_exit_handler(cls, handler):
    #     assert handler is not None
    #     cls._exit_handlers.append(handler)

    _stack = None

    _original_except_hook = None

    exception_exit_action_config = ExitActionConfig(
        notification_config=NotificationConfig(
            sound=NotificationSound.ERROR,
            icon=Assets.get_icon('error_icon')
        ),
        console_style=ConsoleStyle.FATAL_ERROR     
    )

    term_exit_action_config = ExitActionConfig(
        notification_config=NotificationConfig(
            sound=NotificationSound.ERROR,
            icon=Assets.get_icon('error_icon')
        ),
        console_style=ConsoleStyle.FATAL_ERROR     
    )

    die_exit_action_config = ExitActionConfig(
        notification_config=NotificationConfig(
            sound=NotificationSound.ERROR,
            icon=Assets.get_icon('error_icon')
        ),
        console_style=ConsoleStyle.FATAL_ERROR     
    )

    success_exit_action_config = ExitActionConfig(
        notification_config=NotificationConfig(
            sound=NotificationSound.SUCCESS,
            icon=Assets.get_icon('success_icon')
        ),
        console_style=ConsoleStyle.SUCCESS     
    )

    default_exit_action_config = ExitActionConfig(
        # notification_config=NotificationConfig(
        #     sound=NotificationSound.SUCCESS,
        # ),
        # console_style=ConsoleStyle.SUCCESS      
    )

    @classmethod
    def _on_exit2(
        cls,
        config: ExitActionConfig,
        message: str,
        details: str = None,
        do_show_notification: bool = True
    ):
        # must be called only once
        if cls._on_exit_called:  
            return
        cls._on_exit_called = True

        # Flush console
        Console.flush()

        # call exit handlers
        # for handler in cls._exit_handlers:
        #     handler(reason)

        elapsed_duration = cls._stack.current.time_counter.elapsed_duration   

        # print the final message and flush again 
        if config.console_style is not None:            
            Console.write_empty_line()

            name = cls._stack.display_path
            s = f"{name} {message}. Execution time {elapsed_duration}"
            if details is not None:
                s = f"{s}, Details: {details}" 
            Console.write(s, style=config.console_style)
            Console.write_empty_line()

        Console.finalize()

        if do_show_notification and config.notification_config is not None:
            show_notification(
                f"Execution time {elapsed_duration}",
                title=f"{cls._stack.display_name_ntf} {message}",
                subtitle=details,
                config=config.notification_config,
            )

    @classmethod    
    @property
    def path(cls) -> Path:
        return cls._stack.current.path

    @classmethod
    def _on_default_exit(cls):
        cls._on_exit2(cls.default_exit_action_config, "finished")

    @classmethod
    def _on_sig_term(cls):
        cls._on_exit2(cls.term_exit_action_config, "terminated")

    @classmethod
    def _except_hook(cls, exc_type, value, traceback):        
        if exc_type == KeyboardInterrupt:        
            message = "is interrupted by user"
            details = None
        else:
            message = "is interrupted by uncaught exception"
            details = f"{exc_type.__name__}({value})"
        cls._on_exit2(cls.exception_exit_action_config, message, details)
        if cls._original_except_hook is not None:
            cls._original_except_hook(exc_type, value, traceback)  #pylint: disable=not-callable

    @classmethod
    def die(cls, message):
        cls._on_exit2(cls.term_exit_action_config, "died", message)
        cls.exit(1)

    @classmethod
    def success(cls, message: str = None):
        full_effects = not cls._stack.is_nested
        cls._on_exit2(cls.success_exit_action_config, "completed", message, do_show_notification=full_effects)
        if full_effects:
            cls.exit(0)

    @classmethod
    def exit(cls, code: int):
        sys.exit(code)

    @classmethod
    def sleep(cls, interval: float):
        time.sleep(interval)

    @classmethod
    def run_subscript(cls, path):
        try:
            p = Path(path)
            if not p.is_absolute:
                p = Path([cls._stack.current.directory, path])
            if not p.exists_as_file:
                raise Exception(f"{p} does not exist")
            Console.write_empty_line()
            Console.write_raw(Rule(title=f"Entering {p}..."))
            Console.write_empty_line()
            try:
                cls._stack.push(p.fspath)
                run_path(p.fspath)

            finally:
                cls._on_exit_called = False
                cls._stack.pop()                
                Console.write_empty_line()
                Console.write_raw(Rule(title=f"Exiting {p}..."))    
                Console.write_empty_line()

        except Exception as e:
            cls.die(f"Unable to run subscript [{path}]: {e}")

    @classmethod
    def import_module(cls, name, path):
        try:
            p = Path(path)
            if not p.is_absolute:
                p = Path([cls._stack.current.directory, path])
            if p.exists_as_directory:
                p += "__init__.py"
                if not p.exists_as_file:
                    raise Exception(f"{path} refers to a module directory but {p} does not exist")
            else:
                if not p.exists_as_file:
                    raise Exception(f"{p} does not exist")

            spec = importlib.util.spec_from_file_location(name, p.fspath)
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module 
            spec.loader.exec_module(module) 
            return module

        except Exception as e:
            cls.die(f"Unable to import module [{path}]: {e}")


Script._init()  # pylint: disable=protected-access
# Script.register_exit_handler(lambda reason: Console.flush())


def die(message: str = None):
    Script.die(message)


def success(message: str = None):
    Script.success(message=message)
