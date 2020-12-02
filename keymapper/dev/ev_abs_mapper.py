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


"""Keeps mapping joystick to mouse movements."""


import asyncio
import time

import evdev
from evdev.ecodes import EV_ABS, EV_REL

from keymapper.logger import logger
from keymapper.config import config


# other events for ABS include buttons
JOYSTICK = [
    evdev.ecodes.ABS_X,
    evdev.ecodes.ABS_Y,
    evdev.ecodes.ABS_RX,
    evdev.ecodes.ABS_RY,
]


def _write(device, ev_type, keycode, value):
    """Inject."""
    device.write(ev_type, keycode, value)
    device.syn()


async def ev_abs_mapper(abs_state, input_device, keymapper_device):
    """Keep writing mouse movements based on the gamepad stick position.

    Parameters
    ----------
    abs_state : [int, int]
        array to read the current abs values from. Like a pointer.
    input_device : evdev.InputDevice
    keymapper_device : evdev.UInput
    """
    # events only take ints, so a movement of 0.3 needs to add
    # up to 1.2 to affect the cursor.
    pending_x_rel = 0
    pending_y_rel = 0

    logger.info('Mapping gamepad to mouse movements')
    max_value = input_device.absinfo(EV_ABS).max
    max_speed = ((max_value ** 2) * 2) ** 0.5

    pointer_speed = config.get('gamepad.joystick.pointer_speed')
    non_linearity = config.get('gamepad.joystick.non_linearity')

    while True:
        start = time.time()
        abs_x, abs_y = abs_state

        if non_linearity != 1:
            # to make small movements smaller for more precision
            speed = (abs_x ** 2 + abs_y ** 2) ** 0.5
            factor = (speed / max_speed) ** non_linearity
        else:
            factor = 1

        rel_x = abs_x * factor * pointer_speed / max_value
        rel_y = abs_y * factor * pointer_speed / max_value

        pending_x_rel += rel_x
        pending_y_rel += rel_y
        rel_x = int(pending_x_rel)
        rel_y = int(pending_y_rel)
        pending_x_rel -= rel_x
        pending_y_rel -= rel_y

        if rel_y != 0:
            _write(
                keymapper_device,
                EV_REL,
                evdev.ecodes.ABS_Y,
                rel_y
            )

        if rel_x != 0:
            _write(
                keymapper_device,
                EV_REL,
                evdev.ecodes.ABS_X,
                rel_x
            )

        # try to do this as close to 60hz as possible
        time_taken = time.time() - start
        await asyncio.sleep(max(0.0, (1 / 60) - time_taken))