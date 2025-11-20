import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.result import TestFailure
from cocotb.utils import get_sim_time 

# Constants based on dco.v parameters
DCO_CTRL_BITS = 10
DCO_PHASE_BITS = 16
CLOCK_PERIOD_NS = 20 # 20ns period = 50MHz clock (Adjusted for typical TT clock speed)

async def measure_frequency(dut, ctrl_value, num_cycles):
    """
    Applies a control word and measures the period of the DCO output.
    """
    # 1. Apply Control Word
    dut._log.info(f"Applying control word C={ctrl_value} ({hex(ctrl_value)})")
    
    # TinyTapeout control word mapping: {uio_in[1:0], ui_in[7:0]}
    ui_in_val = ctrl_value & 0xFF
    uio_in_val = (ctrl_value >> 8) & 0x3
    
    dut.ui_in.value = ui_in_val
    dut.uio_in.value = uio_in_val
    
    # Wait for the control word to propagate
    await Timer(CLOCK_PERIOD_NS * 5, units='ns')
    
    # 2. Measure DCO Period
    start_time = get_sim_time()
    
    # Find the first rising edge
    await RisingEdge(dut.dco_signal) 
    
    # Find the next NUM_CYCLES edges to measure the average period
    for _ in range(num_cycles):
        await RisingEdge(dut.dco_signal)

    end_time = get_sim_time()
    
    # Calculate measured period and frequency
    # get_sim_time returns ps (int). Divide by 1000.0 to convert to ns (float).
    total_time_ps = end_time - start_time
    total_time_ns = total_time_ps / 1000.0 
    
    measured_period_ns = total_time_ns / num_cycles
    
    if measured_period_ns == 0:
        return 0, 0 # Avoid division by zero if output is stuck
        
    measured_freq_mhz = 1000.0 / measured_period_ns
    
    return measured_period_ns, measured_freq_mhz

def calculate_expected_freq(ctrl_value):
    """
    Calculates the theoretical DCO frequency in MHz based on the
    scaled increment value in the Verilog module (dco.v).
    
    f_dco = (C / 2^CTRL_BITS) * f_clk
    """
    f_clk_mhz = 1000.0 / CLOCK_PERIOD_NS # 50 MHz
    
    # Use DCO_CTRL_BITS (10) as the effective denominator resolution.
    expected_freq_mhz = (ctrl_value / (2**DCO_CTRL_BITS)) * f_clk_mhz
    return expected_freq_mhz

@cocotb.test()
async def dco_frequency_test(dut):
    """
    Tests the DCO's frequency output for various control words across the 10-bit range.
    """
    # 1. Setup Clock and Reset
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, units="ns").start())
    
    # Initialize inputs to avoid 'X'
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.ena.value = 1
    
    # Apply reset
    dut._log.info("Starting DCO test. Applying reset... (40ns)")
    dut.rst_n.value = 0
    await Timer(CLOCK_PERIOD_NS * 2, units='ns')
    dut.rst_n.value = 1
    dut._log.info("Reset released.")

    # 2. Define Test Cases (Ctrl Word C)
    # NOTE: The maximum reliable, 50%-duty-cycle frequency for this DCO design is
    # f_clk / 2 (25 MHz when f_clk=50MHz), corresponding to C=512.
    test_ctrl_words = {
        0: 0,       # C=0: Min frequency (should be 0 Hz).
        1: 200,     # C=1: Smallest non-zero (Very slow, measure many cycles).
        3: 200,     # C=3: Odd number, not a power of 2 (Slow, measure many cycles).
        100: 50,    # C=100: General low frequency.
        256: 50,    # C=256: 1/4 of full scale (12.5 MHz).
        400: 50,    # C=400: Arbitrary mid-low frequency.
        512: 50,    # C=512: 1/2 of full scale (25 MHz, highest unambiguous test).
    }
    
    tolerance_percent = 5.0 # Allowed error margin

    # 3. Execute Tests
    for ctrl_word, cycles_to_measure in test_ctrl_words.items():
        if ctrl_word == 0:
            # Special case: C=0 must result in 0 Hz (stuck low)
            dut._log.info("Testing C=0: DCO must be stuck low.")
            dut.ui_in.value = 0
            dut.uio_in.value = 0
            await RisingEdge(dut.clk)
            await Timer(CLOCK_PERIOD_NS * 10, units='ns')
            
            # Check the output signal value
            val = dut.dco_signal.value
            ival = int(val)
            assert ival == 0, f"DCO output should be 0 for C=0, but measured {ival}"

            continue # Skip frequency measurement for C=0
            
        
        # Measure and compare
        measured_period, measured_freq = await measure_frequency(dut, ctrl_word, num_cycles=cycles_to_measure)
        expected_freq = calculate_expected_freq(ctrl_word)
        
        # Guard against zero expected frequency
        if expected_freq == 0:
             continue

        error = abs(measured_freq - expected_freq)
        error_percent = (error / expected_freq) * 100
        
        dut._log.info(f"--- Control Word C={ctrl_word} ---")
        dut._log.info(f"Expected Freq: {expected_freq:.4f} MHz")
        dut._log.info(f"Measured Freq: {measured_freq:.4f} MHz (Period: {measured_period:.4f} ns)")
        dut.dco_signal._log.info(f"Measurement based on {cycles_to_measure} cycles.")
        dut._log.info(f"Error: {error_percent:.2f}% (Tolerance: {tolerance_percent}%)")

        # Use assert statement
        assert error_percent <= tolerance_percent, (
            f"DCO failed for C={ctrl_word}. Expected {expected_freq:.4f} MHz, "
            f"but measured {measured_freq:.4f} MHz. Error: {error_percent:.2f}%"
        )
        
    dut._log.info("All DCO frequency tests passed successfully.")
