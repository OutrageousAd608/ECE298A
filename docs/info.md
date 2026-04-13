<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

# How it works

This project implements an All-Digital Phase-Locked Loop (ADPLL) that consists of four primary functional blocks. The Phase-Frequency Detector uses a state-machine architecture to compare the rising edges of the reference input and the DCO feedback signal to generate a 16-bit signed error value. This error is processed by a Loop Filter, which functions as a Proportional-Integral controller with a proportional gain of 4 and an integral shift of 3. The resulting control signal adjusts the frequency of a 24-bit phase-accumulator Digitally Controlled Oscillator. Finally, a "Leaky Bucket" lock detector monitors the phase error and uses a Schmitt trigger with thresholds of 1500 and 1000 to determine if the system has achieved a stable lock.

# How to test

Testing the ADPLL requires providing a system clock and a reference signal on pin ui_in[0]. After ensuring the enable signal is high and the reset is released, the user should monitor uo_out[1] for the DCO output clock and uo_out[0] for the lock status. By sweeping the frequency of the reference input, you can verify that the DCO tracks the input frequency and that the lock bit transitions to high once the "Leaky Bucket" counter exceeds the lock threshold.

# External hardware

The design interfaces with external equipment through the Tiny Tapeout GPIO pins. A function generator or secondary microcontroller is required to provide the reference square wave to input ui_in[0]. An oscilloscope or logic analyzer should be connected to the output pins to observe the generated DCO signal and the digital lock indicator. The system's timing and resolution are determined by the external clock provided to the main clk input.
