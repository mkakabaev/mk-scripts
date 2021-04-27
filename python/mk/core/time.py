# -*- coding: utf-8 -*-
# cSpell: words dateutil tzlocal

import datetime
import time
from enum import Enum
from dateutil.tz import tzlocal
from .to_string_builder import ReprBuilderMixin, ToStringBuilder


class DateTimeFormat(Enum):
    LOG_FILE_NAME = "%Y.%m.%d_%H.%M"


class DateTime(ReprBuilderMixin):
    def __init__(self):
        self.t = datetime.datetime.now(tzlocal())

    # ReprBuilderMixin overrides
    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.add_value(self.t.strftime("%Y-%m-%d %H:%M:%S %z"))

    def format(self, fmt: DateTimeFormat) -> str:
        return self.t.strftime(fmt.value)
        # return "Date(year: {}, month: {}, day: {}, hour: {}, minute: {})  /* {} */".format(
        #     self.t.year, self.t.month, self.t.day, self.t.hour, self.t.minute, self.t.strftime("%z"))


class DurationFormat(Enum):
    S = 1
    MS = 2


class Duration:
    def __init__(self, ns: int):
        self._ns = ns

    def format(self, fmt: DurationFormat) -> str:
        if fmt == DurationFormat.S:
            return self._format_seconds()
        if fmt == DurationFormat.MS:
            return f"{self._format_seconds()}.{self._format_ms()}"
        raise Exception(f"Unsupported format {fmt}")

    def _format_seconds(self):
        t = self._ns // 1000_000_000
        s = t % 60
        m = (t // 60) % 60
        h = t // 3600
        return f"{h:,}:{m:02}:{s:02}"

    def _format_ms(self):
        t = (self._ns // 1000_000) % 1000
        return f"{t:03}"

    def __repr__(self):
        return f"[{self.format(DurationFormat.MS)}]"


class TimeCounter(ReprBuilderMixin):
    def __init__(self):
        self._start = time.perf_counter_ns()

    # ReprBuilderMixin overrides
    def configure_repr_builder(self, sb: ToStringBuilder):
        sb.add_value(self.elapsed_duration)

    # @property
    # def elapsed_ns(self) -> int:
    #     return time.perf_counter_ns() - self._start

    @property
    def elapsed_duration(self) -> Duration:
        return Duration(ns=time.perf_counter_ns() - self._start)
