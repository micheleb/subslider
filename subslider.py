#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# SubSlider - a simple script to apply offsets to subtitles
#
# Copyright (C) 2014 - Michele Bonazza <http://michelebonazza.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
from datetime import datetime
import argparse
import collections
import shutil
import os
import re
import sys


class MyParser(argparse.ArgumentParser):
    """A parser that displays argparse's help message by default."""

    def error(self, message):
        self.print_help()
        sys.exit(1)


class SubSlider:
    """A simple script to apply offsets to subtitles.

    Subtitles can be moved forward or back in time depending on the parameters
    passed."""

    LINES_TO_SHOW = 10
    SUB_TIME_FORMAT = "(\d{2}:\d{2}:\d{2},\d{3}) \-\-> "\
        "(\d{2}:\d{2}:\d{2},\d{3})"
    DEFAULT_START_AT = "same as input; original .srt file will be copied to "\
        "ORIGINAL_SRT_NAME_orig.srt"
    DATE_ZERO = datetime.strptime('2000/1/1', '%Y/%m/%d')

    def __init__(self):
        parser = MyParser(
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("-ds", "--delay_subs",
                           help="""make subtitles appear later.
                        OFFSET format is

                           [mm:]SS[,sss].

                        Examples: "1:23,456" (subs delayed of 1 minute, 23
                        seconds, 456 milliseconds); "100" (subs delayed of 100
                        seconds, or 1 minute, 40 seconds); "12,43" (subs
                        delayed of 12 seconds, 430 milliseconds)""",
                           metavar='OFFSET')

        group.add_argument("-dv", "--delay_video",
                           help="""make subtitles appear sooner.
                        OFFSET format is

                           [mm:]SS[,sss].

                        Examples: "1:23,456" (subs displayed 1 minute,
                        23 seconds, 456 milliseconds sooner); "100" (subs
                        displayed 100 seconds, or 1 minute, 40 seconds sooner);
                        "12,43" (subs are displayed 12 seconds, 430
                        milliseconds sooner)""",
                           metavar='OFFSET')
        group.add_argument("-s", "--start_at",
                           help="""make the first subtitle appear at a specific
                           time. The script will show a list of lines taken
                           from the .srt file to choose what's the first line
                           to be displayed at TIME""",
                           metavar="TIME")

        parser.add_argument("-o", "--output",
                            help="the output .srt subtitles file",
                            default=self.DEFAULT_START_AT)
        parser.add_argument("input_file", type=str,
                            help="the .srt subtitles file")

        args = parser.parse_args()

        parsed = self.check_args(args)

        if not parsed:
            print('')
            parser.error('Bad arguments.')

        (self.input_subs, self.output_subs, self.output_temp,
         minutes, seconds, millis) = parsed

        if self.input_subs == self.output_subs:
            # if input is my_movie.srt copy to my_movie_orig.srt
            original = '%s_orig.srt' % os.path.splitext(self.input_subs)[0]
            shutil.copyfile(self.input_subs, original)

        self.first_valid = 0

        # if start was specified, we need to know what's the first line that
        # the offset needs to be applied to
        subtract_offset = False
        if args.start_at:
            first_starts_at = self.get_offset_from_start_at(args.start_at)
            starting_at = self.get_date(minutes, seconds, millis)
            if first_starts_at > starting_at:
                # subtitles begin later than they should, negative offset
                offset = first_starts_at - starting_at
                subtract_offset = True
            else:
                # subtitles begin sooner than they should, positive offset
                offset = starting_at - first_starts_at
            print('Applying {} as offset'.format(offset))
        else:
            offset = self.get_date(minutes, seconds, millis) - self.DATE_ZERO

        if subtract_offset or args.delay_video:
            def offset_func(start, end): return (start - offset, end - offset)
        else:
            def offset_func(start, end): return (start + offset, end + offset)

        self.parse_subs(offset_func)
        self.fix_file()

        # clean up the temp file
        os.remove(self.output_temp)
        print('Success! Offset subs have been written to {}'
              .format(os.path.abspath(self.output_subs)))

        if self.input_subs == self.output_subs:
            print('The original subs have been copied to {}'.format(original))

    def check_args(self, args):
        """
        Checks that command-line arguments are valid.

        The syntax for parameters is checked by argparse; this method checks
        that the values provided are valid (e.g., file paths point to actual
        files, offsets have been specified following our format, etc.).
        """
        error = None
        input_file = args.input_file
        input_offset = args.start_at or args.delay_subs or args.delay_video
        input_offset = input_offset.strip()

        if not os.path.isfile(input_file):
            print('{} does not exist'.format(input_file))
            error = True
        else:
            if not args.output or args.output == self.DEFAULT_START_AT:
                output_subs = input_file
            else:
                output_subs = args.output
            output_temp = '{}_temp.srt'.format(os.path.splitext(input_file)[0])

        offset_ok = re.match('(\d{1,2}:)?\d+(,\d{1,3})?$', input_offset)

        if not offset_ok:
            print('{} is not a valid offset, format is [MM:]SS[,sss], see help'
                  'dialog for some examples'.format(input_offset))
            error = True
        else:
            offset = re.search('((\d{1,2}):)?(\d+)(,(\d{1,3}))?', input_offset)

            def nsafe(x): return offset.group(x) if offset.group(x) else "0"

            # the ljust call is because we want e.g. '2.5' to be interpreted as
            # 2 seconds, 500 millis
            minutes, seconds, millis = (nsafe(2), nsafe(3),
                                        nsafe(5).ljust(3, '0'))
            if re.match('^\d+(,(\d{1,3}))?$', input_offset):
                # format is seconds(,millis), convert to minutes
                secs = int(seconds)
                minutes = str(secs / 60)
                seconds = str(secs % 60)

        if error:
            return None

        return_me = collections.namedtuple('Params',
                                           ['input', 'output', 'output_tmp',
                                            'mins', 'secs', 'millis'])
        return return_me(input_file, output_subs, output_temp,
                         minutes, seconds, millis)

    def get_offset_from_start_at(self, start_at):
        """
        Shows a prompt to the user for her to choose the reference line that
        should start at the specified time, and returns the time at which the
        chosen line was originally shown.
        """
        lines, times = self.get_first_lines(self.LINES_TO_SHOW)
        # python3 has no "raw_input()"
        try:
            _input = raw_input
        except NameError:
            _input = input
        choices = []
        for idx, val in enumerate(lines):
            choices.append('%d: {%s}\n' % (idx + 1, val[:-1]))

        prompt = "These are the first {0} lines:\n\n{1}\n\nWhich one should "\
            "start at {2}?\nYour choice 1-{0} [1]: "\
            .format(len(choices), '\n'.join(choices), start_at)

        choice = _input(prompt)
        if not choice:
            # default choice is 1, which is at index #0 in the array
            choice = 0
        else:
            try:
                choice = int(choice)
                if choice < 1 or choice > len(choices):
                    print('Expected a number between 1 and {}, but {} was '
                          'entered. Exiting'.format(len(choices), choice))
                    sys.exit(1)
                else:
                    # list is 0-based, choices are 1-based
                    choice -= 1
            except ValueError:
                print('Expected a number between 1 and {}, but "{}" was '
                      'entered. Exiting'.format(len(choices), choice))
                sys.exit(1)

        # parse the string to get the start value
        parsed = re.search(self.SUB_TIME_FORMAT, times[choice])

        # group(1) is start, group(2) is end
        return self.parse_time(parsed.group(1))

    def get_first_lines(self, line_count):
        """
        Parses the input subs file and returns the first 10 entries, together
        with the time at which they're shown.
        """
        found = 0
        lines = []
        times = []
        buf = []
        with open(self.input_subs, 'rt') as _input:
            for line in _input:
                parsed = re.search(self.SUB_TIME_FORMAT, line)
                if parsed:
                    if found:
                        # don't append the UTF header
                        lines.append('\n'.join(buf[:-1]))
                    found += 1
                    times.append(line)
                    buf = []
                else:
                    buf.append(line.strip())
                if found > line_count:
                    return lines, times
        return lines, times

    def parse_subs(self, offset_func):
        """
        Parses the original subs file and applies the offset using the argument
        function, writing the output to a temp file.

        The method sets self.first_valid to the first block in the temp file
        that has a timestamp greater than zero; this is done in case some lines
        in the output subs ended up being displayed at negative time.
        """
        with open(self.input_subs, 'r') as _input:
            with open(self.output_temp, 'w') as output:
                block = 0
                for line in _input:
                    parsed = re.search(self.SUB_TIME_FORMAT, line)
                    if parsed:
                        block += 1
                        start, end = (self.parse_time(parsed.group(1)),
                                      self.parse_time(parsed.group(2)))
                        (start, end) = offset_func(start, end)
                        offset_start, offset_end = (self.format_time(start),
                                                    self.format_time(end))
                        if not self.first_valid:
                            if end >= self.DATE_ZERO:
                                # this line will start at 0, and is going to be
                                # displayed until end
                                self.first_valid = block
                                if start < self.DATE_ZERO:
                                    offset_start = '00:00:00,000'
                        output.write('{} --> {}\n'.format(offset_start,
                                                          offset_end))
                    else:
                        output.write(line)

    def fix_file(self):
        """
        Parses the temp file created by parse_subs and renumbers blocks in case
        lines were dropped because the offset pushed them to negative
        timestamps.
        """
        with open(self.output_temp, 'r') as _input:
            with open(self.output_subs, 'w') as output:
                # we can drop all lines found before the first valid block
                # (set by parse_subs())
                start_output = False
                for line in _input:
                    if re.match('\d+$', line.strip()):
                        block_num = int(line.strip())
                        if block_num >= self.first_valid:
                            # ok, start parsing
                            if not start_output:
                                start_output = True
                            # and renumber blocks so that they start at 1, no
                            # matter what
                            output.write(
                                '{}\r\n'
                                .format(block_num - self.first_valid + 1)
                            )
                    elif start_output:
                        output.write(line)

    @staticmethod
    def format_time(value):
        """
        Parses a date using the format '%H:%M:%S,%f'.
        """
        formatted = datetime.strftime(value, '%H:%M:%S,%f')
        return formatted[:-3]

    @staticmethod
    def get_date(minutes, seconds, millis):
        """
        Returns a date that can be used for comparisons with timestamps in the
        .srt file.
        """
        def nsafe(s): return int(s) if s else 0
        return datetime(2000, 1, 1, 0, nsafe(minutes), nsafe(seconds),
                        nsafe(millis) * 1000)

    @staticmethod
    def parse_time(time):
        """
        Parses a date using the format '%H:%M:%S,%f' and sets the year to 2000
        to avoid trouble.
        """
        parsed = datetime.strptime(time, '%H:%M:%S,%f')
        return parsed.replace(year=2000)

if __name__ == '__main__':
    SubSlider()
