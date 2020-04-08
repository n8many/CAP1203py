# CAP1203py
Python library for reading CAP1203 Touch Slider sensor from Sparkfun. https://www.sparkfun.com/products/15344

Written for the Raspberry Pi, but should work on other Linux based computers so long as they have an i2c bus you can connect to.

## Installation
1. Enable I2C on your computer
2. Install the smbus library (via pip)
2. Add this library to your project. You can either...
    * Clone this repo to your project via:

       ```git clone https://github.com/n8many/CAP1203py.git```

   * Or download "cap1203.py" to have the code in your project base directory.

## Usage

If you cloned the repo to your project, add the CAP1203 object via:

```from CAP1203.cap1203 import CAP1203```

If you added the file directly to your project, then use:

```from cap1203 import CAP1203```

Initializing a sensor can be as easy as:

```cap = CAP1203()```

## History

4/07/20 - Creation

## Credits
Most of this code is being translated from the original Sparkfun library here: https://github.com/sparkfun/Qwiic_Capacitive_Touch_Slider_Arduino_Library

License
This is under the MIT License
