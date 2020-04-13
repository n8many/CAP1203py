import smbus2 as smbus
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


def set_bits(register: int, value: Union[int, bool], index: int, length: int = 1) -> int:
    mask = (2**length)-1
    register = register & ~(mask << index)
    register = register | (mask & value) << index
    return register


def get_bits(register: int, index: int, length: int = 1) -> Union[int, bool]:
    result = (register >> index) & (2 ** length - 1)
    if length == 1:
        return result == 1
    return result


class CAP1203(object):

    def __init__(self, bus: smbus.SMBus, address: int=ADDRESS):
        '''
        Initialize CAP1023 Object with i2c bus and address
        TODO: Add documentation on inputs
        '''
        # Only one valid address for this board, but in case that changes
        if address != ADDRESS:
            raise ValueError("Invalid Address: {0:#x}".format(address))
        self.address = address
        if bus is None:
            raise ValueError("Invalid bus, must pass in SMBus object")
        self.bus = bus
        if self.is_connected():
            self.set_sensitivity(Sensitivity.x2)
            self.set_interrupt_setting(True)
            self.clear_interrupt()
        else:
            raise RuntimeError("Cannot connect to CAP1203")

    def is_connected(self):
        for i in range(5):
            try:
                self.bus.read_byte(self.address)  # This will raise OSError if device isn't present
                return True
            except OSError:
                # Device didn't respond, try again
                continue
        return False

    def check_main_control(self):
        reg = self.bus.read_i2c_block_data(self.address, MAIN_CONTROL, 1)[0]
        return

    def check_status(self):
        return

    def set_sensitivity(self, sensitivity: Sensitivity):
        reg = self.bus.read_i2c_block_data(self.address, SENSITIVITY_CONTROL, 1)[0]
        reg = set_bits(reg, sensitivity, 4, 3)
        self.bus.write_i2c_block_data(self.address, SENSITIVITY_CONTROL, [reg])
        return

    def get_sensitivity(self) -> Sensitivity:
        return Sensitivity(get_bits(self.bus.read_i2c_block_data(self.address, SENSITIVITY_CONTROL, 1)[0], 4, 3))

    def set_interrupt_setting(self, enable: Union[bool, Pad]):
        reg = self.bus.read_i2c_block_data(self.address, INTERRUPT_ENABLE, 1)[0]
        if isinstance(enable, Pad):
            # Enable selected pads
            reg = set_bits(reg, enable, 0, 3)
        else:
            reg = set_bits(reg, enable, 0)  # Left
            reg = set_bits(reg, enable, 1)  # Middle
            reg = set_bits(reg, enable, 2)  # Right
        self.bus.write_i2c_block_data(self.address, INTERRUPT_ENABLE, [reg])
        return

    def get_interrupt_setting(self) -> Pad:
        reg = self.bus.read_i2c_block_data(self.address, INTERRUPT_ENABLE, 1)[0]
        return Pad(get_bits(reg, 0, 3))

    def clear_interrupt(self):
        reg = self.bus.read_i2c_block_data(self.address, MAIN_CONTROL, 1)[0]
        reg = set_bits(reg, False, 0)  # Clear flag
        self.bus.write_i2c_block_data(self.address, MAIN_CONTROL, [reg])
        return

    def check_touched(self) -> Pad:
        # Check touch register without clearing interrupt
        reg = self.bus.read_i2c_block_data(self.address, SENSOR_INPUT_STATUS, 1)[0]
        touch_status = Pad(get_bits(reg, 0, 3))
        return touch_status

    def get_touched(self):
        # Get touch register and clear interrupt
        res = self.check_touched()
        if res is not Pad(0):
            self.clear_interrupt()
        return res

    def is_touched(self):
        # Get whether or not a touch is active, and clear interrupt
        reg = self.bus.read_i2c_block_data(self.address, GENERAL_STATUS, 1)[0]
        res = get_bits(reg, 0)
        if res:
            self.clear_interrupt()
            return True
        return False

    def is_left_touched(self):
        # Check left touch bit, and clear interrupt if touched
        res = self.check_touched()
        if Pad.Left in res:
            self.clear_interrupt()
            return True
        return False

    def is_right_touched(self):
        # Check right touch bit, and clear interrupt if touched
        res = self.check_touched()
        if Pad.Right in res:
            self.clear_interrupt()
            return True
        return False

    def is_middle_touched(self):
        # Check middle touch bit, and clear interrupt if touched
        res = self.check_touched()
        if Pad.Middle in res:
            self.clear_interrupt()
            return True
        return False

    def is_right_swipe(self):

        return False

    def is_left_swipe(self):

        return False

    def set_power_button_pad(self, pad: Pad):
        reg = self.bus.read_i2c_block_data(self.address, POWER_BUTTON, 1)[0]
        set_bits(reg, pad, 0, 3)
        self.bus.write_i2c_block_data(self.address, POWER_BUTTON, [reg])
        return

    def get_power_button_pad(self) -> Pad:
        reg = self.bus.read_i2c_block_data(self.address, POWER_BUTTON, 1)[0]
        res = Pad(get_bits(reg, 0, 3))
        return res

    def set_power_button_time(self, time: PowerTime):
        reg = self.bus.read_i2c_block_data(self.address, POWER_BUTTON_CONFIG, 1)[0]
        set_bits(reg, time, 0, 2)
        return

    def get_power_button_time(self) -> PowerTime:
        reg = self.bus.read_i2c_block_data(self.address, POWER_BUTTON_CONFIG, 1)[0]
        return PowerTime(get_bits(reg, 0, 2))

    def set_power_button(self, enabled: bool):
        reg = self.bus.read_i2c_block_data(self.address, POWER_BUTTON_CONFIG, 1)[0]
        reg = set_bits(reg, enabled, 2)
        self.bus.write_i2c_block_data(self.address, POWER_BUTTON_CONFIG, [reg])
        return

    def get_power_button_setting(self) -> bool:
        reg = self.bus.read_i2c_block_data(self.address, POWER_BUTTON_CONFIG, 1)[0]
        res = get_bits(reg, 2)
        return res

    def is_power_button_touched(self):
        # Check Power Button touch bit and clear interrupt
        reg = self.bus.read_i2c_block_data(self.address, GENERAL_STATUS, 1)[0]
        res = get_bits(reg, 4)
        if res:
            self.clear_interrupt()
            return True
        return False
