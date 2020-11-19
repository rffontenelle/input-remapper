#!/usr/bin/python3
# -*- coding: utf-8 -*-
# key-mapper - GUI for device specific keyboard mappings
# Copyright (C) 2020 sezanzeb <proxima@hip70890b.de>
#
# This file is part of key-mapper.
#
# key-mapper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# key-mapper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with key-mapper.  If not, see <https://www.gnu.org/licenses/>.


import unittest

import evdev

from keymapper.injector import _start_injecting_worker, \
    is_numlock_on, toggle_numlock, ensure_numlock
from keymapper.getdevices import get_devices
from keymapper.state import custom_mapping, system_mapping

from test import uinput_write_history, Event, pending_events


class TestInjector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.injector = None

    def tearDown(self):
        if self.injector is not None:
            self.injector.stop_injecting()
            self.injector = None

    def test_numlock(self):
        before = is_numlock_on()

        toggle_numlock()  # should change
        self.assertEqual(not before, is_numlock_on())

        @ensure_numlock
        def wrapped():
            toggle_numlock()
            return 1234

        wrapped()  # should not change
        self.assertEqual(not before, is_numlock_on())

        # toggle one more time to restore the previous configuration
        toggle_numlock()
        self.assertEqual(before, is_numlock_on())

    def test_injector(self):
        device = get_devices()['device 2']

        custom_mapping.change(9, 'a')
        # one mapping that is unknown in the system_mapping on purpose
        custom_mapping.change(10, 'b')

        system_mapping.empty()
        system_mapping.change(100, 'a')

        # the second arg of those event objects is 8 lower than the
        # keycode used in X and in the mappings
        pending_events['device 2'] = [
            Event(evdev.events.EV_KEY, 1, 0),
            Event(evdev.events.EV_KEY, 1, 1),
            # ignored because unknown to the system
            Event(evdev.events.EV_KEY, 2, 0),
            Event(evdev.events.EV_KEY, 2, 1),
            # just pass those over without modifying
            Event(3124, 3564, 6542),
        ]

        class FakePipe:
            def send(self, message):
                pass

        _start_injecting_worker(
            path=device['paths'][0],
            pipe=FakePipe()
        )

        self.assertEqual(uinput_write_history[0].type, evdev.events.EV_KEY)
        self.assertEqual(uinput_write_history[0].code, 92)
        self.assertEqual(uinput_write_history[0].value, 0)

        self.assertEqual(uinput_write_history[1].type, evdev.events.EV_KEY)
        self.assertEqual(uinput_write_history[1].code, 92)
        self.assertEqual(uinput_write_history[1].value, 1)

        self.assertEqual(uinput_write_history[2].type, 3124)
        self.assertEqual(uinput_write_history[2].code, 3564)
        self.assertEqual(uinput_write_history[2].value, 6542)


if __name__ == "__main__":
    unittest.main()
