"""
Python library for the CAP1203 sensor.

"""

from enum import IntEnum, IntFlag
from typing import Union

ADDRESS = 0x28

# Register map
MAIN_CONTROL = 0x00
GENERAL_STATUS = 0x02
SENSOR_INPUT_STATUS = 0x03
NOISE_FLAG_STATUS = 0x0A
SENSOR_INPUT_1_DELTA_COUNT = 0x10
SENSOR_INPUT_2_DELTA_COUNT = 0X11
SENSOR_INPUT_3_DELTA_COUNT = 0X12
SENSITIVITY_CONTROL = 0x1F
CONFIG = 0x20
SENSOR_INPUT_ENABLE = 0x21
SENSOR_INPUT_CONFIG = 0x22
SENSOR_INPUT_CONFIG_2 = 0x23
AVERAGING_AND_SAMPLE_CONFIG = 0x24
CALIBRATION_ACTIVATE_AND_STATUS = 0x26
INTERRUPT_ENABLE = 0x27
REPEAT_RATE_ENABLE = 0x28
MULTIPLE_TOUCH_CONFIG = 0x2A
MULTIPLE_TOUCH_PATTERN_CONFIG = 0x2B
MULTIPLE_TOUCH_PATTERN = 0x2D
BASE_COUNT_OUT = 0x2E
RECALIBRATION_CONFIG = 0x2F
SENSOR_1_INPUT_THRESH = 0x30
SENSOR_2_INPUT_THRESH = 0x31
SENSOR_3_INPUT_THRESH = 0x32
SENSOR_INPUT_NOISE_THRESH = 0x38
STANDBY_CHANNEL = 0x40
STANDBY_CONFIG = 0x41
STANDBY_SENSITIVITY = 0x42
STANDBY_THRESH = 0x43
CONFIG_2 = 0x44
SENSOR_INPUT_1_BASE_COUNT = 0x50
SENSOR_INPUT_2_BASE_COUNT = 0x51
SENSOR_INPUT_3_BASE_COUNT = 0x52
POWER_BUTTON = 0x60
POWER_BUTTON_CONFIG = 0x61
SENSOR_INPUT_1_CALIBRATION = 0xB1
SENSOR_INPUT_2_CALIBRATION = 0xB2
SENSOR_INPUT_3_CALIBRATION = 0xB3
SENSOR_INPUT_CALIBRATION_LSB_1 = 0xB9
PROD_ID = 0xFD
MANUFACTURE_ID = 0xFE
REVISION = 0xFF


class Pad(IntFlag):
    Left = 0x01
    Middle = 0x02
    Right = 0x04


class Sensitivity(IntEnum):
    x128 = 0x00
    x64 = 0x01
    x32 = 0x02
    x16 = 0x03
    x8 = 0x04
    x4 = 0x05
    x2 = 0x06
    x1 = 0x07


class PowerTime(IntEnum):
    t280ms = 0x00  # 280ms
    t560ms = 0x01  # 560ms
    t1120ms = 0x02  # 1.12s
    t2240ms = 0x03  # 2.24s


def set_bits(register, value, index, length=1):
    """
    Set selected bits in register and return new value

    :param register: Input register value
    :type register: int
    :param value: Bits to write to register
    :type value: int
    :param index: Start index (from right)
    :type index: int
    :param length: Number of bits (default 1)
    :type length: int
    :return: Output new register value
    :rtype: int
    """
    mask = (2**length)-1
    register = register & ~(mask << index)
    register = register | (mask & value) << index
    return register


def get_bits(register, index, length=1):
    """
    Get selected bit(s) from register while masking out the rest.
    Returns as boolean if length==1

    :param register: Register value
    :type register: int
    :param index: Start index (from right)
    :type index: int
    :param length: Number of bits (default 1)
    :type length: int
    :return: Selected bit(s)
    :rtype: Union[int, bool]
    """
    result = (register >> index) & (2 ** length - 1)
    if length == 1:
        return result == 1
    return result


class CAP1203(object):

    def __init__(self, bus, address=ADDRESS):
        """
        Object for connecting to CAP1023 sensor via i2c.

        :param bus: i2c bus to connect to CAP1203 sensor. Must be compatible with smbus.SMBus object
        :param address: i2c address of CAP1203 sensor
        :type address: int
        """

        # Only one valid address for this board, but in case that changes
        if address != ADDRESS:
            raise ValueError("Invalid Address: {0:#x}".format(address))
        self.address = address

        # Make sure the bus input is valid
        if bus is None:
            raise ValueError("Invalid bus, must pass in SMBus object")
        self.bus = bus

        # Checks to make sure the board is set up properly
        if self.is_connected():
            self.set_sensitivity(Sensitivity.x2)
            self.set_interrupt_setting(True)
            self.clear_interrupt()
        else:
            raise RuntimeError("Cannot connect to CAP1203")

    def is_connected(self):
        """
        Check communication with sensor

        :return: Whether sensor is connected
        :rtype: bool
        """
        for i in range(5):
            try:
                self.bus.read_byte(self.address)  # This will raise OSError if device isn't present
                return True
            except OSError:
                # Device didn't respond, try again
                continue
        return False

    def check_main_control(self):
        """
        Check main control register
        """
        self._read_register(MAIN_CONTROL)
        return

    def check_status(self):
        """
        Check CAP1203 for errors

        :return: Pads with error
        :rtype: Pad
        """
        # Check status registers
        reg = self._read_register(GENERAL_STATUS)
        bc_pad = Pad(self._read_bits_from_register(CALIBRATION_ACTIVATE_AND_STATUS, 0, 3))
        error_pad = Pad(self._read_bits_from_register(BASE_COUNT_OUT, 0, 3))

        # Base Count errors
        if get_bits(reg, 6):
            # Base count out of range for a sensor
            if bc_pad:
                print(f"Base count out of range for pad(s): {bc_pad.__repr__()}")

        # Calibration errors
        if get_bits(reg, 5):
            # Calibration failed for a sensor
            if error_pad:
                print(f"Failed to calibrate pad(s): {error_pad.__repr__()}")

        return bc_pad | error_pad

    def reset(self):
        """
        Reset CAP1203 to manually recalibrate
        """
        self._write_register(CALIBRATION_ACTIVATE_AND_STATUS, 0x07)
        return

    def set_sensitivity(self, sensitivity):
        """
        Set sensitivity of CAP1203

        :param sensitivity: Value to set sensor sensitivity to
        :type sensitivity: Sensitivity
        """
        self._write_bits_to_register(SENSITIVITY_CONTROL, sensitivity, 4, 3)
        return

    def get_sensitivity(self):
        """
        Get sensitivity from CAP1203

        :return: Sensitivity setting
        :rtype: Sensitivity
        """
        return Sensitivity(self._read_bits_from_register(SENSITIVITY_CONTROL, 4, 3))

    def set_interrupt_setting(self, enable):
        """
        Set interrupt setting of CAP1203.

        :param enable: Enable interrupt for some or all pads
        :type enable: Union[bool, Pad]
        """
        if isinstance(enable, Pad):
            # Enable selected pads
            pad = enable
        else:
            pad = Pad(0b111 * enable)  # enable all pads
        self._write_bits_to_register(INTERRUPT_ENABLE, pad, 0, 3)
        return

    def get_interrupt_setting(self):
        """
        Get interrupt setting from CAP1203

        :return: Pads with interrupts enabled
        :rtype: Pad
        """
        return Pad(self._read_bits_from_register(INTERRUPT_ENABLE, 0, 3))

    def clear_interrupt(self):
        """
        Clear interrupt from CAP1203
        """
        self._write_bits_to_register(MAIN_CONTROL, False, 0)

    def check_touched(self):
        """
        Check for touched pads without clearing interrupt

        :return: Touched pad(s) if any
        :rtype: Pad
        """
        return Pad(self._read_bits_from_register(SENSOR_INPUT_STATUS, 0, 3))

    def get_touched(self):
        """
        Get touch register and clear interrupt

        :return: Touched pad(s) if any
        :rtype: Pad
        """
        res = self.check_touched()
        if res is not Pad(0):
            self.clear_interrupt()
        return res

    def is_touched(self):
        """
        Get whether or not a touch is active, and clear interrupt

        :return: Touch status
        :rtype: bool
        """
        res = self._read_bits_from_register(GENERAL_STATUS, 0)
        if res:
            self.clear_interrupt()
            return True
        return False

    def is_left_touched(self):
        """
        Check left touch status, and clear interrupt if touched

        :return: Left touch status
        :rtype: bool
        """
        res = self.check_touched()
        if Pad.Left in res:
            self.clear_interrupt()
            return True
        return False

    def is_right_touched(self):
        """
        Check right touch status, and clear interrupt if touched

        :return: Right touch status
        :rtype: bool
        """
        res = self.check_touched()
        if Pad.Right in res:
            self.clear_interrupt()
            return True
        return False

    def is_middle_touched(self):
        """
        Check middle touch status, and clear interrupt if touched

        :return: Middle touch status
        :rtype: bool
        """
        res = self.check_touched()
        if Pad.Middle in res:
            self.clear_interrupt()
            return True
        return False

    def is_right_swipe(self):
        # TODO: Complete "is_right_swipe"
        print("Warning, is_right_swipe is unimplemented")
        return False

    def is_left_swipe(self):
        # TODO: Complete "is_left_swipe"
        print("Warning, is_left_swipe is unimplemented")
        return False

    def set_power_button_pad(self, pad):
        """
        Set the Pad(s) for which the power button function is enabled.
        See page 16 for more information on the power button function.

        :param pad: Pad(s) to enable the power button on
        :type pad: Pad
        """
        self._write_bits_to_register(POWER_BUTTON, pad, 0, 3)

    def get_power_button_pad(self):
        """
        Get the Pad(s) for which the power button function is enabled.
        See page 16 for more information on the power button function.

        :return: Pad(s) to enable the power button on
        :rtype: Pad
        """
        return Pad(self._read_bits_from_register(POWER_BUTTON, 0, 3))

    def set_power_button_time(self, time):
        """
        Set the time setting for the power button function.
        See page 16 for more information on the power button function.

        :param time: Time setting for power button function
        :type time: PowerTime
        """
        self._write_bits_to_register(POWER_BUTTON_CONFIG, time, 0, 2)

    def get_power_button_time(self):
        """
        Get the time setting for the power button function.
        See page 16 for more information on the power button function.

        :return: Time setting for power button function
        :rtype: PowerTime
        """
        return PowerTime(self._read_bits_from_register(POWER_BUTTON_CONFIG, 0, 2))

    def set_power_button(self, enabled):
        """
        Enable or disable the power button function.
        See page 16 for more information on the power button function.

        :param enabled:
        :type enabled: bool
        """
        self._write_bits_to_register(POWER_BUTTON_CONFIG, enabled, 2)

    def get_power_button_setting(self):
        """
        Get the status of the power button function.
        See page 16 for more information on the power button function.

        :return: Enabled status of power button
        :rtype: bool
        """
        return self._read_bits_from_register(POWER_BUTTON_CONFIG, 2)

    def is_power_button_touched(self):
        """
        Check Power Button touch bit and clear interrupt.
        See page 16 for more information on the power button function.

        :return: Power button touch state
        :rtype: bool
        """
        #
        res = self._read_bits_from_register(GENERAL_STATUS, 4)
        if res:
            self.clear_interrupt()
            return True
        return False

    def _read_bits_from_register(self, register, index, length=1):
        """
        Read value from register on CAP1203

        :param register: Register address to acquire
        :type register: int
        :param index: position to pull bits from
        :type index: int
        :param length: number of bits to grab
        :type length: int
        :return: Bits from register
        :rtype: Union[int, bool]
        """
        return get_bits(self._read_register(register), index, length)

    def _write_bits_to_register(self, register, value, index, length=1):
        """
        Write value to register on CAP1203

        :param register: Address of register you are writing to
        :type register: int
        :param value: Bits to write to register
        :type value: Union[int, bool]
        :param index: position to write bits to
        :type index: int
        :param length: number of bits to grab
        :type length: int
        """
        self._write_register(register, set_bits(self._read_register(register), value, index, length))

    def _read_register(self, register):
        """
        Read value from register on CAP1203

        :param register: Register address to acquire
        :type register: int
        :return: Byte in register
        :rtype: int
        """
        return self.bus.read_i2c_block_data(self.address, register)[0]

    def _write_register(self, register, value):
        """
        Write value to register on CAP1203

        :param register: Address of register you are writing to
        :type register: int
        :param value: Byte to write to register
        :type value: int
        """
        self.bus.write_i2c_block_data(self.address, register, [value])
