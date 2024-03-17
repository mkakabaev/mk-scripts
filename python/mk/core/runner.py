# -*- coding: utf-8 -*-
# cSpell: words Popen bufsize fspath

import collections.abc
import subprocess
import shlex
import os
import re
from rich.table import Table
import rich.box

from .console import Console
from .time_utils import TimeCounter
from ._internal import int_die
from .misc import Safe
from .to_string_builder import ReprBuilderMixin, ToStringBuilder


def _stringify_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, os.PathLike):  # Path and file entries are also os.PathLike
        return str(os.fspath(value))
    return str(value)


class RunnerResult(ReprBuilderMixin):
    def __init__(self, output: str, code: int, runner):
        self.output = output
        self.code = code
        self.runner = runner

    def search(
        self,
        pattern,
        group: int = 0,
        tag: str | None = None,
        message: str | None = None,
    ) -> str:
        m = re.search(pattern, self.output)
        if m is None:
            int_die(
                Safe.first_available(
                    [
                        message,
                        lambda: Safe.conditional(
                            tag,
                            f"{self}: unable to extract the <{tag}> from the output",
                            f"{self}: unable to extract a value from the output",
                        ),
                    ]
                )
            )
        return m.group(group)

    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.add_value(self.runner.title, quoted=True)

class Runner:
    def __init__(self, command, args=None, title: str|None = None):
        self.command = _stringify_value(command)
        self.args = Safe.to_list(args, _stringify_value)
        self.title = title
        self._table = None

    def _full_args(self):
        return [self.command] + list(map(str, self.args))

    def _full_shell_cmd(self):  # for using with shell=True
        return " ".join(map(shlex.quote, self._full_args()))

    # def run_to_get_result_code(self):
    #     p = subprocess.Popen(self.cmd(), stdin=subprocess.PIPE, shell=True)
    #     p.communicate()
    #     return p.returncode

    def add_info(self, name, value):
        table = self._table
        if table is None:
            table = Table(
                # title_justify="left",
                # title="THE TITLE",
                # title_style="bold",
                show_header=False,
                box=rich.box.ROUNDED,
                border_style="dim",
            )
            table.add_column()
            table.add_column()
            self._table = table

        def expand_value(v):
            if isinstance(v, bool):
                return "✓" if v else "-"

            if isinstance(v, collections.abc.Mapping):
                t = Table(
                    show_header=False,
                    box=rich.box.MINIMAL,
                    pad_edge=False,
                    show_edge=False,
                    border_style="dim",
                )
                t.add_column()
                t.add_column()
                for key1, value1 in v.items():
                    t.add_row(f"{key1}", expand_value(value1))
                return t
            if Safe.is_sequence(v):
                t = Table(show_header=False, box=None, padding=0)
                for value1 in v:
                    t.add_row(expand_value(value1))
                return t
            return f"{v}"

        table.add_row(name, expand_value(value))

    def run_silent(self) -> RunnerResult:
        cmd = self._full_shell_cmd()
        outputs = []
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            stdin=subprocess.PIPE,
        )  # bufsize=1, shell=True
        if p.stdout is not None:
            with p.stdout:
                for line_b in iter(p.stdout.readline, b""):
                    line = line_b.decode("utf-8")
                    outputs.append(line)
        result_code = p.wait()
        if result_code:
            int_die(
                f"Executing '{Safe.first_available([self.title, cmd])}' failed with exit code {result_code}."
            )

        return RunnerResult(
            output="".join(outputs).strip(), code=result_code, runner=self
        )

    def run(
        self,
        catch_output: bool = True,
        display_output: bool = True,
        notify_completion: bool = False,
        # the input. Will be converted to UTF8
        input_data: str|None = None,
    ):
        t = TimeCounter()

        # print header
        Console.write_empty_line()
        if self.title is not None:
            Console.write_section_header(f"▸ {self.title}")
        if self._table is not None:
            Console.write_raw(self._table)
        Console.write_empty_line()

        # prepare and output the command line and input
        cmd = self._full_shell_cmd()
        Console.write(f"CMD> {cmd}\n", to_display=display_output)
        if input_data:
            Console.write(f"INPUT> {input_data}\n", to_display=display_output)

        # prepare input
        if input_data:
            input_data_b = input_data.encode("utf-8")
        else:
            input_data_b = None

        # run with output catch
        if catch_output:
            outputs = []

            status = Safe.conditional(self.title, f"{self.title}...", "Running...")
            Console.start_status(status)

            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                stdin=subprocess.PIPE,
            )  # bufsize=1, , shell=True

            if input_data_b:
                p_result = p.communicate(input=input_data_b)
                lines = str(p_result[0].decode("utf-8")).split("\n")
                for line in lines:
                    Console.write(line.strip(), to_display=display_output)
                    outputs.append(line)
                    
            else:
                if p.stdout is not None:
                    with p.stdout:
                        for line_b in iter(p.stdout.readline, b""):
                            line = line_b.decode("utf-8")
                            Console.write(line.strip(), to_display=display_output)
                            outputs.append(line)
                            # Console.update_status(f"{status} {t.elapsed_duration}")

            result_code = p.wait()
            Console.stop_status()
            Console.write_empty_line()
            if result_code:
                int_die(
                    f"Running '{Safe.first_available([self.title, cmd])}' failed with exit code {result_code}."
                )
            if notify_completion:
                Console.write(f"■ Completed. Elapsed time {t.elapsed_duration}")
            Console.write_empty_line()
            return RunnerResult(
                output="".join(outputs).strip(), code=result_code, runner=self
            )

        # run without output catching
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
        p_result = p.communicate(input=input_data_b)
        if p.returncode:
            int_die(
                f"Running {Safe.first_available([self.title, cmd])} failed with exit code {p.returncode}"
            )
        r = str(p_result[0])
        if r is not None:
            r = r.strip()
        Console.write_empty_line()
        return RunnerResult(output=r, code=p.returncode, runner=self)

    # def add_arg_pair(self, param, value):
    #     self.args.append(param)
    #     self.args.append(self.value_to_str(value))

    def add_args(self, args):
        for arg1 in Safe.to_list(args, _stringify_value):
            self.args.append(_stringify_value(arg1))

    def add_arg_pair_eq(self, param, value):
        self.args.append(f"{_stringify_value(param)}={_stringify_value(value)}")
