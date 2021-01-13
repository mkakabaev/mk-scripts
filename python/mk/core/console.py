# -*- coding: utf-8 -*-
# cSpell: words popen bgcolor

from enum import Enum
import rich.console
import rich.style
from .misc import Safe


class ConsoleStyle(Enum):
    SECTION_HEADER = 1
    WARNING = 2
    FATAL_ERROR = 3
    SUCCESS = 4
    # RUN_STATUS = 5


class ConsoleStyleConfig:

    def __init__(
        self, 
        color: str = None, 
        background_color: str = None, 
        bold: bool = False
    ):        
        self._rich_style = None
        self.color = color
        self.background_color = background_color
        self.bold = bold

    def get_rich_style(self): 
        if self._rich_style is None:
            self._rich_style = rich.style.Style(color=self.color, bold=self.bold, bgcolor=self.background_color)
        return self._rich_style


class Console:

    _prev_line_empty = True

    _styles = {
        ConsoleStyle.SECTION_HEADER: ConsoleStyleConfig(bold=True),
        ConsoleStyle.SUCCESS: ConsoleStyleConfig(color="bright_green"),
        ConsoleStyle.WARNING: ConsoleStyleConfig(color="bright_yellow"),
        # ConsoleStyle.FATAL_ERROR: ConsoleStyleConfig(color="bright_white", background_color="bright_red",),
        ConsoleStyle.FATAL_ERROR: ConsoleStyleConfig(color="bright_red"),
        # ConsoleStyle.RUN_STATUS: ConsoleStyleConfig(background_color="grey3", color="bright_white"),        
    }

    _status = None

    _rc = None
    _rcl = None

    @classmethod
    def _init(cls):

        # underlying console processor. https://rich.readthedocs.io/en/latest/index.html
        cls._rcl = rich.console.Console(  # pylint: disable=invalid-name
            highlight=False, 
            markup=False,
            log_path=False,
            record=True,
            width=100
        )
        cls._rc = rich.console.Console(  # pylint: disable=invalid-name
            highlight=False, 
            markup=False,
            log_path=False
        )                

    @classmethod
    def dump_styles(cls):
        for style in cls._styles:
            cls.write(f"{style}", style=style)

    @classmethod
    def _resolve_style(cls, style: ConsoleStyle):  # pylint: disable=unused-argument
        if style is not None:
            try:
                return cls._styles[style]
            except Exception as e:
                cls._rc.print(
                    f"mk.Console: {e} Warning: unable to resolve the console style '{style.name}'",
                    style=rich.style.Style(color="yellow"),
                    highlight=False,
                )
        return None

    @classmethod
    def write_raw(
        cls,
        rich_renderable
    ):
        cls._rc.print(rich_renderable)          
        cls._log(rich_renderable)
        cls._prev_line_empty = False

    @classmethod
    def _log(cls, o):
        with cls._rcl.capture() as _:
            cls._rcl.log(o)            
            log_text = cls._rcl.export_text()
            cls._add_to_history(log_text)

    @classmethod
    def write(
        cls, 
        text, 
        style: ConsoleStyle = None, 
        log_output: bool = True,
        console_output: bool = True,
    ):              
        cls._prev_line_empty = text is None or len(text) == 0 or text.endswith("\n")
    
        if console_output:
            style_config = cls._resolve_style(style)
            cls._rc.print(
                text, 
                style=Safe.conditional(style_config, lambda: style_config.get_rich_style())  # pylint: disable=unnecessary-lambda
            )

        if log_output:
            cls._log(text)
    
    @classmethod
    def stop_status(cls):
        if cls._status is not None:
            cls._status.stop()
            cls._status = None

    @classmethod
    def start_status(cls, title):
        cls.stop_status()
        cls._status = cls._rc.status(title)
        cls._status.start()

    # @classmethod
    # def update_status(cls, title):
    #     if cls._status is not None:
    #         cls._status.update(status=title)

    @classmethod
    def write_empty_line(cls, if_needed_only=True):
        if not if_needed_only or not cls._prev_line_empty:
            cls.write("")

    @classmethod
    def write_section_header(cls, s):
        cls.write_empty_line()
        cls.write("\n".join(Safe.to_list(s)), style=ConsoleStyle.SECTION_HEADER)

    _history = []
    _history_file_path = None
    _history_file = None
    _flush_capacity = 1

    @classmethod
    def set_log_file(cls, log_file_path, flush_capacity: int = None):
        assert log_file_path is not None
        if cls._history_file is not None:
            if cls._history_file_path == log_file_path:
                return
            cls.flush()
            cls._history_file.close()
            cls._history_file = None
            cls._history_file_path = None
        cls._history_file = open(log_file_path, "a")
        cls._history_file_path = log_file_path
        if flush_capacity is not None:
            assert flush_capacity >= 1
            cls._flush_capacity = flush_capacity

    @classmethod
    def _add_to_history(cls, s):
        if cls._history_file is not None:
            cls._history.append(s)
            if len(cls._history) >= cls._flush_capacity:
                cls.flush()

    @classmethod
    def flush(cls):
        if len(cls._history) > 0:
            if cls._history_file is not None:
                # cls._history_file.write("\n".join(cls._history) + "\n")
                cls._history_file.write("".join(cls._history))
                cls._history_file.flush()
            cls._history = []

    @classmethod
    def finalize(cls):
        cls.stop_status()
        cls.flush()


Console._init()  # pylint: disable=protected-access
