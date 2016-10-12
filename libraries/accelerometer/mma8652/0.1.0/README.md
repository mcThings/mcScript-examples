MMA8652FC Digital Accelerometer

> The 3-axis, 12-bit accelerometer found on the mc-Module 110

[Datasheet](http://cache.freescale.com/files/sensors/doc/data_sheet/MMA8652FC.pdf)

## Usage

1. `git clone https://github.com/mcThings/mcScript.git`
-  Make a new project in mc-Studio
-  Go to File > Open and select _mcScript/libraries/accelerometer/MMA8652.mcscript_ from cloned git repo
-  Add the following code to the main project file

```vbscript
Class MMA8652_Test
    Shared accel As MMA8652

    Shared Event Boot()
        accel = New MMA8652()

        If accel.online Then
            accel.Setup(MMA8652_ACTIVE_ODR._50HZ, MMA8652_MODS.NORMAL)
            accel.ConfigureShockInterrupt(1.2, 20.0)
        Else
            LedRed = True
        End If

    End Event

    Shared Event AccelerometerInt1()
        Dim intType As ListOfString = accel.GetIntSource()

        For Each interrupt In intType
            Select interrupt
                Case "shock"
                    accel.Shock() // Must read shock data to clear interrupt

                    LedGreen = Not LedGreen
            End Select
        Next
    End Event

    Shared Event ReadAccelData() RaiseEvent Every 1 Seconds
        Dim data As ListOfFloat

        If (accel.online) Then
            data = accel.Accel()
            LedGreen = Not LedGreen
        Else
            LedRed = True
        End If

    End Event

End Class

```

## Caveats

There is no support for FIFO, and some opinionated decisions have been made when setting some of the more obscure configuration bits on the device in an effort to make a simple interface.

## API

### New MMA8652([enableHighPassFilter, outputDataFormat])

Returns an instance of the MMA8652 accelerometer class. Checks that the device has the MMA8652FC chip. Device is reset, so any other instances of the MMA8652 will no longer be configured for interrupts.

If the optional parameters are used, it allows configuring the high pass filter and scale of the output data for calling the Accel() function.

enableHighPassFilter [Boolean] (default: False)  
outputDataFormat [[MMA8652_SCALES](#mma8652_scales)] (default: \_2G)  

### Instance Members

#### online [Boolean]

True if I2C bus is active, the chip is onboard, and the device was reset.

#### Accel() -> ListOfFloat

Returns a list of length 3; 0th is x, 1st is y, 2nd is z. This represents the gravitational force along each direction, accounting for negative direction. Poll this function at your own frequency using a shared event thread in your main process.

#### Autosleep() -> String

Gets the current operating mode of the accelerometer. Returns "standby", "active", or "sleep".

#### ConfigureFreefallInterrupt(threshold, duration [, axis, setPin2]) -> Boolean

Enables the freefall interrupt. Returns True if successful.

_threshold_ [Float] - Amount of gravitational force to trigger threshold (0.0 Gs - 8.0 Gs in 0.063mG steps)  
_duration_ [Byte] - Count for threshold to be present before interrupt  
_axis_ [Byte] (default: 0x38) - Optionally set the axis on which to enable freefall detection. Bit 0x20 is z-axis, bit 0x10 is y-axis, and bit 0x08 is x-axis. 0 or more bits may be set.  
_setPin2_ [Boolean] (default: False) - Optionally route the interrupt to pin 2

#### ConfigureOrientationInterrupt(duration, bfAngle, zlockAngle, thsAngle, hysAngle [, setPin2]) -> Boolean

Enables the orientation interrupt, which triggers on portrait/landscape changes and up/down changes. Also interrupts once immediately after configuring. Returns True if successful.

_duration_ [Float] - Time for angle to be present before interrupt in ms. Adheres to [long table](#long)  
_bfAngle_ [[MMA8652_BF_ANGLE](#mma8652_bf_angle)] - Angle for transitioning between back/front orientation  
_zlockAngle_ [Float] - Angle which determines z-axis dead zone  
_thsAngle_ [[MMA8652_THS_ANGLE](#mma8652_ths_angle)] - Angle which determins portrait to landscape transition  
_hysAngle_ [[MMA8652_HYS_ANGLE](#mma8652_hys_angle)] - Angle for widening the thsAngle  
_setPin2_ [Boolean] (default: False) - Optionally route the interrupt to pin 2

#### ConfigurePulseInterrupt(threshold, duration, latency, window [, abortDoublePulse, enableLowPassFilter [, axis, setPin2]]) -> Boolean

Enables the pulse interrupt, which triggers when a pulse at the specified level begins and ends within the specified duration. Returns True if successful.

The Pulse behavior is like a knock; A sudden force that does not last for a long time.

_threshold_ [Float] - Amount of gravitational force to trigger threshold (0.0 Gs - 8.0 Gs in 0.063mG steps)  
_duration_ [Float] - Duration in which the threshold must be reached, but not maintained. Adheres to [short table](#short) by default, but if enableLowPassFilter is True, then use the [long table](#long).  
_latency_ [Float] - Time to wait after pulse before interpreting further pulses as a new pulse. Adheres to [medium table](#medium) by default, but if enableLowPassFilter is True, then use the [xlong table](#xlong).  
_window_ [Float] - Time after latency period to interpret another pulse as a double pulse. Adheres to [medium table](#medium) by default, but if enableLowPassFilter is True, then use the [xlong table](#xlong).  
_abortDoublePulse_ [Boolean] (default: False) - Optionally suspend the double tap detection if the start of a pulse is detected during the time period specified by latency, and the pulse ends before the end of the time period specified by latency  
_enableLowPassFilter_ [Boolean] (default: False) - Optionally enable the low pass filter for pulse processing. Note that this changes the max time tables for the duration, latency, and window parameters.  
_axis_ [Byte] (default: 0x3f) - Optionally set the axis on which to enable pulse detection. For double pulse: Bit 0x20 is z-axis, bit 0x08 is y-axis, and bit 0x02 is x-axis. For single pulse: Bit 0x10 is z-axis, bit 0x04 is y-axis, and bit 0x01 is x-axis. 0 or more bits may be set.  
_setPin2_ [Boolean] (default: False) - Optionally route the interrupt to pin 2

#### ConfigureShockInterrupt(threshold, duration [, axis, setPin2]) -> Boolean

Enables the shock interrupt, which triggers when any transient forces occur at the specified level for the specified duration. Returns True if successful.

_threshold_ [Float] - Amount of gravitational force to trigger threshold (0.0 Gs - 8.0 Gs in 0.063mG steps)  
_duration_ [Float] - Duration for threshold to be present before interrupt in ms. Adheres to [long table](#long)  
_axis_ [Byte] (default: 0x0e) - Optionally set the axis on which to enable shock detection. Bit 0x08 is z-axis, bit 0x04 is y-axis, and bit 0x02 is x-axis. 0 or more bits may be set.  
_setPin2_ [Boolean] (default: False) - Optionally route the interrupt to pin 2

#### DisableSleepMode() -> Boolean

Will disable the sleep mode function of the accelerometer. Returns True if successful.

#### EnableSleepMode(duration [, setPin2]) -> Boolean

Will enable the sleep mode function of the accelerometer. Returns True if successful.

_duration_ [Float] - Time in milliseconds that will pass before device transitions from active to sleep mode. If the output data rate is set to 1.56Hz, the max time is 162,000ms. Otherwise, the max time is 81,000ms.  
_setPin2_ [Boolean] - Optionally route the interrupt to pin 2

#### Freefall() -> ListOfString

Returns a list of length 2. The 0th item is x, y, or z. The 1st item is "neg" (for negative direction) or "pos" (for positive direction).

#### GetIntSource() -> ListOfString

Returns all of the interrupts that are set. The recommended way to use this function is with a For-Each statement to handle all active interrupts. Interrupt names are "autosleep", "freefall", "orientation", "pulse", and "shock". Call their respective functions to get information on their status'.

#### GetVersion() -> String

Returns the driver version. The recommended use is for ensuring the correct driver library is included in the project.

#### Orientation() -> ListOfString

Returns a list of length 2. The 0th item is "portrait up", "portrait down", "landscape right", or "landscape left". The 1st item is "back" or "front".

#### Pulse() -> String

Returns "double" or "single"

#### Reset() -> Boolean

Resets the MMA8652FC accelerometer, which may take some time. Returns True if successful.

#### Setup(activeHz, activePowerScheme [, sleepHz, sleepPowerScheme]) -> Boolean

Allows overriding the default output data rates and oversampling modes for active and sleep modes. Lower frequencies use less power, but lose sensitivity for interrupts.

_activeHz_ [[MMA8652_ACTIVE_ODR](#mma8652_active_odr)] (default: MMA8652_ACTIVE_ODR.\_800HZ)  
_activePowerScheme_ [[MMA8652_MODS](#mma8652_mods)] (default: MMA8652_MODS.NORMAL)  
_sleepHz_ [[MMA8652_SLEEP_ODR](#mma8652_sleep_odr)] (default: MMA8652_SLEEP_ODR.\_50HZ)  
_sleepPowerScheme_ [[MMA8652_SMODS](#mma8652_smods)] (default: MMA8652_SMODS.NORMAL)  

#### Shock() ->

Returns a list of length 2. The 0th item is x, y, or z. The 1st item is "neg" (for negative direction) or "pos" (for positive direction).

### Static Enumerations

#### MMA8652_ACTIVE_ODR

Active Output Data Rates

\_800HZ - 800Hz  
\_400HZ - 400Hz  
\_200HZ - 200Hz  
\_100HZ - 100Hz  
\_50HZ - 50Hz  
\_12_5HZ - 12.5Hz  
\_6_25HZ - 6.25Hz  
\_1_56HZ - 1.56Hz  

#### MMA8652_MODS

Active Modes

NORMAL  
LOW_POWER_LOW_NOISE  
HIGH_RES  
LOW_POWER  

#### MMA8652_SLEEP_ODR

Sleep Output Data Rates

\_50HZ - 50Hz  
\_12_5HZ - 12.5Hz  
\_6_25HZ - 6.25Hz  
\_1_56HZ - 1.56Hz  

#### MMA8652_SMODS

Sleep Modes

NORMAL  
LOW_POWER_LOW_NOISE  
HIGH_RES  
LOW_POWER  

#### MMA8652_BF_ANGLE

Back/Front Trigger Angles

\_80 - 80°  
\_75 - 75°  
\_70 - 70°  
\_65 - 65°  

#### MMA8652_THS_ANGLE

Portrait/Landscape Threshold Angles

\_15 - 15°  
\_20 - 20°  
\_30 - 30°  
\_35 - 35°  
\_40 - 40°  
\_45 - 45°  
\_55 - 55°  
\_60 - 60°  
\_70 - 70°  
\_75 - 75°  

#### MMA8652_HYS_ANGLE

Portrait/Landscape Hysteresis Angles

\_0 - 0°  
\_4 - 4°  
\_7 - 7°  
\_11 - 11°  
\_14 - 14°  
\_17 - 17°  
\_21 - 21°

#### MMA8652_SCALES

\_2G  
\_4G  
\_8G  

### Output Data Rate by Oversampling Mode Tables

#### short

<table>
    <tr>
        <th rowspan="2">ODR (Hz)</th>
        <th colspan="4" style="text-align:center;">Max Time (ms)</th>
    </tr>
    <tr>
        <td>Normal</td>
        <td>Low Power Low Noise</td>
        <td>High Resolution</td>
        <td>Low Power</td>
    </tr>
    <tr>
        <td>800</td>
        <td>159</td>
        <td>159</td>
        <td>159</td>
        <td>159</td>
    </tr>
    <tr>
        <td>400</td>
        <td>159</td>
        <td>159</td>
        <td>159</td>
        <td>319</td>
    </tr>
    <tr>
        <td>200</td>
        <td>319</td>
        <td>319</td>
        <td>159</td>
        <td>638</td>
    </tr>
    <tr>
        <td>100</td>
        <td>638</td>
        <td>638</td>
        <td>159</td>
        <td>1280</td>
    </tr>
    <tr>
        <td>50</td>
        <td>1280</td>
        <td>1280</td>
        <td>159</td>
        <td>2550</td>
    </tr>
    <tr>
        <td>12.5</td>
        <td>1280</td>
        <td>5100</td>
        <td>159</td>
        <td>10200</td>
    </tr>
    <tr>
        <td>6.25</td>
        <td>1280</td>
        <td>5100</td>
        <td>159</td>
        <td>10200</td>
    </tr>
    <tr>
        <td>1.56</td>
        <td>1280</td>
        <td>5100</td>
        <td>159</td>
        <td>10200</td>
    </tr>
</table>

#### medium

<table>
    <tr>
        <th rowspan="2">ODR (Hz)</th>
        <th colspan="4" style="text-align:center;">Max Time (ms)</th>
    </tr>
    <tr>
        <td>Normal</td>
        <td>Low Power Low Noise</td>
        <td>High Resolution</td>
        <td>Low Power</td>
    </tr>
    <tr>
        <td>800</td>
        <td>318</td>
        <td>318</td>
        <td>318</td>
        <td>318</td>
    </tr>
    <tr>
        <td>318</td>
        <td>318</td>
        <td>318</td>
        <td>318</td>
        <td>638</td>
    </tr>
    <tr>
        <td>200</td>
        <td>638</td>
        <td>638</td>
        <td>318</td>
        <td>1276</td>
    </tr>
    <tr>
        <td>100</td>
        <td>1276</td>
        <td>1276</td>
        <td>318</td>
        <td>2560</td>
    </tr>
    <tr>
        <td>50</td>
        <td>2560</td>
        <td>2560</td>
        <td>318</td>
        <td>5100</td>
    </tr>
    <tr>
        <td>12.5</td>
        <td>2560</td>
        <td>10200</td>
        <td>318</td>
        <td>20400</td>
    </tr>
    <tr>
        <td>6.25</td>
        <td>2560</td>
        <td>10200</td>
        <td>318</td>
        <td>20400</td>
    </tr>
    <tr>
        <td>1.56</td>
        <td>2560</td>
        <td>10200</td>
        <td>318</td>
        <td>20400</td>
    </tr>
</table>

#### long

<table>
    <tr>
        <th rowspan="2">ODR (Hz)</th>
        <th colspan="4" style="text-align:center;">Max Time (ms)</th>
    </tr>
    <tr>
        <td>Normal</td>
        <td>Low Power Low Noise</td>
        <td>High Resolution</td>
        <td>Low Power</td>
    </tr>
    <tr>
        <td>800</td>
        <td>319</td>
        <td>319</td>
        <td>319</td>
        <td>319</td>
    </tr>
    <tr>
        <td>400</td>
        <td>638</td>
        <td>638</td>
        <td>638</td>
        <td>638</td>
    </tr>
    <tr>
        <td>200</td>
        <td>1280</td>
        <td>1280</td>
        <td>638</td>
        <td>1280</td>
    </tr>
    <tr>
        <td>100</td>
        <td>2550</td>
        <td>2550</td>
        <td>638</td>
        <td>2550</td>
    </tr>
    <tr>
        <td>50</td>
        <td>5100</td>
        <td>5100</td>
        <td>638</td>
        <td>5100</td>
    </tr>
    <tr>
        <td>12.5</td>
        <td>5100</td>
        <td>20400</td>
        <td>638</td>
        <td>20400</td>
    </tr>
    <tr>
        <td>6.25</td>
        <td>5100</td>
        <td>20400</td>
        <td>638</td>
        <td>40800</td>
    </tr>
    <tr>
        <td>1.56</td>
        <td>5100</td>
        <td>20400</td>
        <td>638</td>
        <td>40800</td>
    </tr>
</table>

#### xlong

<table>
    <tr>
        <th rowspan="2">ODR (Hz)</th>
        <th colspan="4" style="text-align:center;">Max Time (ms)</th>
    </tr>
    <tr>
        <td>Normal</td>
        <td>Low Power Low Noise</td>
        <td>High Resolution</td>
        <td>Low Power</td>
    </tr>
    <tr>
        <td>800</td>
        <td>638</td>
        <td>638</td>
        <td>638</td>
        <td>638</td>
    </tr>
    <tr>
        <td>400</td>
        <td>1276</td>
        <td>1276</td>
        <td>1276</td>
        <td>1276</td>
    </tr>
    <tr>
        <td>200</td>
        <td>2560</td>
        <td>2560</td>
        <td>1276</td>
        <td>2560</td>
    </tr>
    <tr>
        <td>100</td>
        <td>5100</td>
        <td>5100</td>
        <td>1276</td>
        <td>5100</td>
    </tr>
    <tr>
        <td>50</td>
        <td>10200</td>
        <td>10200</td>
        <td>1276</td>
        <td>10200</td>
    </tr>
    <tr>
        <td>12.5</td>
        <td>10200</td>
        <td>40800</td>
        <td>1276</td>
        <td>40800</td>
    </tr>
    <tr>
        <td>6.25</td>
        <td>10200</td>
        <td>40800</td>
        <td>1276</td>
        <td>81600</td>
    </tr>
    <tr>
        <td>1.56</td>
        <td>10200</td>
        <td>40800</td>
        <td>1276</td>
        <td>81600</td>
    </tr>
</table>

## License

MIT License
