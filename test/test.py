# File: test.py (Final attempt with simple indexing)
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles

@cocotb.test()
async def adpll_lock_test(dut):
    """Test the ADPLL lock functionality for a specific frequency multiplication."""

    # --- 1. Initialization and Reset ---
    
    # 1.1 Set initial inputs
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.ena.value = 1
    
    cocotb.log.info("Starting up and asserting reset")
    dut.rst_n.value = 0 

    # 1.2 Start the two clocks
    # clk_sys (dut.clk): 100MHz system clock (10 ns period)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start()) 
    
    # A 5MHz reference clock (200 ns period)
    # FIX 1: Use the simple Python indexer to get the single-bit handle
    ref_clk_handle = dut.ui_in[0] 
    cocotb.start_soon(Clock(ref_clk_handle, 200, unit="ns").start())

    # Wait for a few clock cycles before deasserting reset
    await ClockCycles(dut.clk, 10)
    
    # 1.3 Set the N-Divider ratio (e.g., N=4)
    N_RATIO = 4
    # Set the whole value (we can still use the integer assignment here)
    dut.ui_in.value = (N_RATIO << 1) | 0
    
    # Deassert reset
    dut.rst_n.value = 1
    cocotb.log.info(f"PLL configured for N={N_RATIO} and reset released.")

    # --- 2. Wait for Lock ---
    
    # 2.1 Allow time for the PLL to lock 
    REF_CYCLES_TO_WAIT = 1000
    cocotb.log.info(f"Waiting for {REF_CYCLES_TO_WAIT} reference cycles (approx. 200us) to acquire lock...")
    await ClockCycles(ref_clk_handle, REF_CYCLES_TO_WAIT)
    
    # uo_out[1] is the locked signal (pll_locked)
    # Use slicing for reading the value's content (safe method)
    locked_signal = dut.uo_out.value[1:1]
    
    # uo_out[7:2] is the debug_out
    debug_val = dut.uo_out.value[7:2]
    
    cocotb.log.info(f"Final Lock Status: {locked_signal}")
    cocotb.log.info(f"DCO Code (debug_out): {debug_val}")

    # --- 3. Verification ---
    
    # 3.1 Check if the locked flag is high
    assert locked_signal.integer == 1, f"PLL failed to assert 'locked' signal. Final debug: {debug_val}"
    
    # 3.2 Check the frequency of clk_out (uo_out[0])
    expected_period = 200.0 / N_RATIO # 50.0 ns
    
    # FIX 2: Get the handle for the DCO output clock (uo_out[0])
    dco_clk_handle = dut.uo_out[0] # Use simple Python indexer
    
    # Measure 5 cycles of the DCO output clock
    MEASURE_CYCLES = 5
    start_time = cocotb.time()
    for _ in range(MEASURE_CYCLES):
        await RisingEdge(dco_clk_handle) 
    
    end_time = cocotb.time()
    measured_period = (end_time - start_time) / MEASURE_CYCLES

    cocotb.log.info(f"Measured DCO period over {MEASURE_CYCLES} cycles: {measured_period:.2f} ns")
    
    # Check tolerance
    TOLERANCE = 0.1
    if not (abs(measured_period - expected_period) / expected_period < TOLERANCE):
         cocotb.log.warning(f"Period check failed! Measured: {measured_period:.2f} ns, Expected: {expected_period:.2f} ns")
    
    cocotb.log.info("ADPLL test completed successfully.")
