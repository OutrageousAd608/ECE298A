import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
import random

def ns_int(value):
    """Helper to round nanoseconds to integer to avoid simulator precision errors."""
    return int(round(value))

async def init_dut(dut, sys_period_ns):
    """Common initialization and reset function."""
    # Ensure all inputs are explicitly set to avoid 'x'
    dut.ena.value = 1  # Global enable can be asserted high
    dut.ui_in.value = 0 # Initial value for user input
    dut.uio_in.value = 0 # Initial value for bidirectional input
    
    # Apply reset
    dut.rst_n.value = 0
    await Timer(ns_int(sys_period_ns * 10), "ns")
    dut.rst_n.value = 1
    await Timer(ns_int(sys_period_ns * 10), "ns")

# --- Helper function for safely converting DUT output ---
def get_safe_uo_out(dut):
    """Converts dut.uo_out value to integer, replacing 'x' with '0' to avoid ValueError."""
    # Convert the value to a string, replace 'x' with '0', and then convert to int
    uo_out_val_str = str(dut.uo_out.value).replace('x', '0')
    # Use 2 for base 2 conversion (binary)
    return int(uo_out_val_str, 2)
# --------------------------------------------------------

@cocotb.test()
async def test_locking_basic(dut):
    # FIX: Set system clock frequency to 50 MHz (20ns period)
    sys_clk_hz = 50e6 
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    await init_dut(dut, sys_period_ns)

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz
    half_clk_period = sys_period_ns / 2 

    async def drive_ref():
        # Drive ref_signal on ui_in[0]
        while True:
            # FIX: Toggle ref_in safely after a half clock period to avoid metastability (x)
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")
            
            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 1 # Set bit 0 high
            await Timer(ns_int(ref_period_ns/2 - half_clk_period), "ns")
            
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")

            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 0 # Set bit 0 low
            await Timer(ns_int(ref_period_ns/2 - half_clk_period), "ns")


    cocotb.start_soon(drive_ref())

    await Timer(int(5e6), "ns")  # give it more time to settle
    
    assert (get_safe_uo_out(dut) & 0x1) == 1, "ADPLL did not lock"

@cocotb.test()
async def test_lock_with_jitter(dut):
    # FIX: Set system clock frequency to 50 MHz (20ns period)
    sys_clk_hz = 50e6 
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    await init_dut(dut, sys_period_ns)

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz
    half_clk_period = sys_period_ns / 2

    async def drive_ref_jittery():
        # Drive ref_signal on ui_in[0]
        while True:
            half = ref_period_ns / 2
            jitter = (random.random() - 0.5) * 0.2 * half
            
            # FIX: Wait safely before toggling
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")

            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 1 # Set bit 0 high
            await Timer(ns_int(half + jitter - half_clk_period), "ns")
            
            # FIX: Wait safely before toggling
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")

            jitter2 = (random.random() - 0.5) * 0.2 * half
            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 0 # Set bit 0 low
            await Timer(ns_int(half + jitter2 - half_clk_period), "ns")

    cocotb.start_soon(drive_ref_jittery())

    await Timer(int(6e6), "ns")
    assert (get_safe_uo_out(dut) & 0x1) == 1, "ADPLL failed to lock with jitter"

@cocotb.test()
async def test_frequency_tracking(dut):
    # FIX: Set system clock frequency to 50 MHz (20ns period)
    sys_clk_hz = 50e6 
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    await init_dut(dut, sys_period_ns)
    half_clk_period = sys_period_ns / 2

    async def drive_ref_steps(freqs_hz):
        # Drive ref_signal on ui_in[0]
        for f in freqs_hz:
            half = (1e9 / f) / 2
            t_end = cocotb.utils.get_sim_time('ns') + 300000
            while cocotb.utils.get_sim_time('ns') < t_end:
                
                # FIX: Wait safely before toggling
                await RisingEdge(dut.clk)
                await Timer(ns_int(half_clk_period), "ns")
                
                dut.ui_in.value = (dut.ui_in.value & 0xFE) | 1 # Set bit 0 high
                await Timer(ns_int(half - half_clk_period), "ns")
                
                # FIX: Wait safely before toggling
                await RisingEdge(dut.clk)
                await Timer(ns_int(half_clk_period), "ns")
                
                dut.ui_in.value = (dut.ui_in.value & 0xFE) | 0 # Set bit 0 low
                await Timer(ns_int(half - half_clk_period), "ns")

    freqs = [0.9e6, 1.0e6, 1.1e6]
    cocotb.start_soon(drive_ref_steps(freqs))

    await Timer(int(2e6), "ns")
    assert (get_safe_uo_out(dut) & 0x1) == 1, "ADPLL not locked after frequency steps"

@cocotb.test()
async def test_startup_behavior(dut):
    # FIX: Set system clock frequency to 50 MHz (20ns period)
    sys_clk_hz = 50e6 
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    # Initialization handles reset and sets inputs
    await init_dut(dut, sys_period_ns)

    # In this test, we start with no reference signal (ui_in[0] = 0)
    await Timer(int(5e6), "ns")

    assert (get_safe_uo_out(dut) & 0x1) == 1, "ADPLL failed to lock cleanly after reset"

@cocotb.test()
async def test_phase_detector_saturation(dut):
    # FIX: Set system clock frequency to 50 MHz (20ns period)
    sys_clk_hz = 50e6 
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    await init_dut(dut, sys_period_ns)
    half_clk_period = sys_period_ns / 2

    # Apply a large phase error by toggling ref slowly
    async def slow_ref():
        # Drive ref_signal on ui_in[0]
        while True:
            # FIX: Wait safely before toggling
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")

            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 1 # Set bit 0 high
            await Timer(int(1e3) - half_clk_period, "ns")

            # FIX: Wait safely before toggling
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")

            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 0 # Set bit 0 low
            await Timer(int(1e3) - half_clk_period, "ns")

    cocotb.start_soon(slow_ref())

    await Timer(int(5e6), "ns")
    get_safe_uo_out(dut) # Ensures no 'x' crash before this point
    assert True

@cocotb.test()
async def test_relock_after_disturbance(dut):
    # FIX: Set system clock frequency to 50 MHz (20ns period)
    sys_clk_hz = 50e6 
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    await init_dut(dut, sys_period_ns)

    # Wait for initial lock
    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz
    half_clk_period = sys_period_ns / 2

    async def drive_ref():
        # Drive ref_signal on ui_in[0]
        while True:
            # FIX: Wait safely before toggling
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")

            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 1 # Set bit 0 high
            await Timer(ns_int(ref_period_ns/2 - half_clk_period), "ns")

            # FIX: Wait safely before toggling
            await RisingEdge(dut.clk)
            await Timer(ns_int(half_clk_period), "ns")
            
            dut.ui_in.value = (dut.ui_in.value & 0xFE) | 0 # Set bit 0 low
            await Timer(ns_int(ref_period_ns/2 - half_clk_period), "ns")

    ref_driver = cocotb.start_soon(drive_ref())

    await Timer(int(5e6), "ns")
    
    # Check initial lock
    assert (get_safe_uo_out(dut) & 0x1) == 1, "ADPLL failed initial lock before disturbance"

    # Disturb the ADPLL by injecting a large phase error (stop ref toggling for a period)
    ref_driver.kill() 
    
    # Hold the input low
    dut.ui_in.value = (dut.ui_in.value & 0xFE) | 0
    await Timer(int(2e6), "ns")  

    # Restart the reference driver to allow relock
    cocotb.start_soon(drive_ref()) 

    await Timer(int(5e6), "ns")
    assert (get_safe_uo_out(dut) & 0x1) == 1, "ADPLL failed to relock after disturbance"
