# -*- coding: utf-8 -*-
# cSpell: words

import collections.abc
from enum import Enum


class ToStringBuilderValueFmt(Enum):
    ANY = 1
    TIMESTAMP = 2
    RAW = 3


class ToStringBuilder:
    def __init__(self, typename):
        self._entries = []
        self.typename = typename

    def add(
        self, name: str, value, format_type=ToStringBuilderValueFmt.ANY, quoted=False
    ):
        if name is not None and value is not None:
            self._entries.append(
                f"{name}={self._format_value(value, format_type, quoted = quoted)}"
            )
        return self

    def add_value(self, value, format_type=ToStringBuilderValueFmt.ANY, quoted=False):
        if value is not None:
            self._entries.append(self._format_value(value, format_type, quoted))
        return self

    # addDict(dict: Record<string, any>, formatType = ToStringBuilderValueFormat.any): ToStringBuilder {
    #     Object.entries(dict).forEach(
    #         ([key, value]) => this.add(key, value, formatType)
    #     );
    #     return this;
    # }

    # addBool(name: string, value?: boolean): ToStringBuilder {
    #     if (name != null && value) {
    #         this.addRawValue(name);
    #     }
    #     return this;
    # }

    # addRaw(name: string, value: any): ToStringBuilder  {
    #     return this.add(name, value, ToStringBuilderValueFormat.raw)
    # }

    # addRawValue(value: any): ToStringBuilder {
    #     return this.addValue(value, ToStringBuilderValueFormat.raw)
    # }

    # addTag(tag: string): ToStringBuilder {
    #     return this.addValue(tag, ToStringBuilderValueFormat.raw)
    # }

    # addTimestampValue(value: any): ToStringBuilder {
    #     return this.addValue(value, ToStringBuilderValueFormat.timestamp)
    # }

    def _format_value(
        self, value, format_type: ToStringBuilderValueFmt, quoted: bool
    ) -> str:

        is_string = isinstance(value, str)

        if isinstance(value, collections.abc.Sequence) and not is_string:
            m = map(
                lambda v1: self._format_value(v1, format_type, quoted=quoted), value
            )
            return f'[{", ".join(list(m))}]'

        if format_type == ToStringBuilderValueFmt.TIMESTAMP:
            # // trying to interpret number as a Unix milliseconds time
            # if ('number' == typeof value) {
            #     value = new Date(value);
            # }

            # // regular date
            # if (value instanceof Date) {
            #     const m  = moment(value);
            #     const year = value.getFullYear()
            #     if (year != _currentYear) {
            #         return m.format('YYYY-MMM-DD HH:mm:ss.SSS');
            #     }
            #     return m.format('MMM-DD HH:mm:ss.SSS'); //  Z');
            # }
            # break;
            raise Exception("Not implemented yet")

        if format_type == ToStringBuilderValueFmt.RAW:
            return f"{value}"

        if format_type == ToStringBuilderValueFmt.ANY:
            pass

        # common data processing

        # if (value instanceof Date) {
        #     return value.toLocaleDateString('en-US');
        # }

        if is_string:
            if quoted:
                return f'"{value}"'
            return f"{value}"

        return f"{value}"

    def __str__(self):
        t_name = self.typename
        if t_name is None:
            return ", ".join(self._entries)
        return f'{t_name}({", ".join(self._entries)})'


class ReprBuilderMixin:
    def __repr__(self):
        sb = ToStringBuilder(typename=self.__class__.__name__)
        self.configure_repr_builder(sb)
        return sb.__str__()

    def configure_repr_builder(self, sb: ToStringBuilder):
        pass
