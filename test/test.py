import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.handle import Force

async def generate_clock(dut):
    """Generate clock signal with 10ns period (100MHz)."""
    # NOTE: TinyTapeout clock is 50MHz, so 10ns period is correct for this simulation.
    dut.clk.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

async def reset_dut(dut):
    """Apply and release asynchronous reset."""
    dut.rst_n.value = 0
    dut.ui_in.value = 0 # Ensure inputs are low during reset
    await Timer(50, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_phase_detector(dut):
    """Test the phase detector by creating different phase differences."""
    
    # Expected pulse amplitudes based on your Verilog logic
    EXPECTED_POS_ERR = 8
    EXPECTED_NEG_ERR = -8
    LATENCY_CYCLES = 4 # The delay from input edge to output error pulse
    
    # Start the clock
    await generate_clock(dut)
    
    # Reset and initial wait
    cocotb.log.info("Starting reset sequence...")
    await reset_dut(dut)
    
    # Get handles to the inputs and phase_err output
    ref_in = dut.ui_in[0]
    dco_in = dut.ui_in[1]
    # We access the internal signal of the phase_detector module for the true 32-bit value
    # The instance name 'pd' is defined in tt_um_richad.v
    phase_err = dut.pd.phase_err 
    
    await RisingEdge(dut.clk)
    assert phase_err.value.signed_integer == 0, f"Error: Expected initial phase_err to be 0, got {phase_err.value.signed_integer}"

    # =========================================================================
    # --- Test 1: Reference (Ref) leads DCO (Positive Error: +8) ---
    # =========================================================================
    cocotb.log.info("--- Test 1: Ref leads DCO (Expect +8) ---")
    
    # T0: Ref goes high
    ref_in.value = 1
    dco_in.value = 0
    await Timer(1, units="ns") 
    
    # Wait for the pulse to propagate (Latency)
    for _ in range(LATENCY_CYCLES):
        await RisingEdge(dut.clk)
    
    # T4: Peak Value
    await Timer(1, units="ns") 
    assert phase_err.value.signed_integer == EXPECTED_POS_ERR, \
        f"Test 1 Error T4: Expected {EXPECTED_POS_ERR} (Ref Lead), got {phase_err.value.signed_integer}. Check timing."

    # T4.001ns: Shut off inputs
    dco_in.value = 0 
    ref_in.value = 0
    
    await RisingEdge(dut.clk) # T5: Hold cycle (still 8)
    assert phase_err.value.signed_integer == EXPECTED_POS_ERR, \
        f"Test 1 Hold Error T5: Expected {EXPECTED_POS_ERR}, got {phase_err.value.signed_integer}."

    # T6: Leakage starts (8 -> 7)
    await RisingEdge(dut.clk) 
    
    # Check continued leakage
    cocotb.log.info("Test 1: Checking positive leakage to 0...")
    assert phase_err.value.signed_integer == EXPECTED_POS_ERR - 1, \
        f"Test 1 Leak Error T6 Start: Expected {EXPECTED_POS_ERR - 1}, got {phase_err.value.signed_integer}"

    # Loop for 6 more steps (from +7 down to +1)
    for i in range(2, EXPECTED_POS_ERR): 
        expected = EXPECTED_POS_ERR - i
        await RisingEdge(dut.clk)
        assert phase_err.value.signed_integer == expected, \
            f"Test 1 Leak Error: Expected {expected}, got {phase_err.value.signed_integer}"
    
    # T(6+7): Check final leakage to 0
    await RisingEdge(dut.clk)
    assert phase_err.value.signed_integer == 0, \
        f"Test 1 Leak Error Final: Expected 0, got {phase_err.value.signed_integer}"


    # =========================================================================
    # --- Test 2: DCO leads Ref (Negative Error: -8) ---
    # =========================================================================
    cocotb.log.info("--- Test 2: DCO leads Ref (Expect -8) ---")
    
    # T0: DCO goes high
    ref_in.value = 0
    dco_in.value = 1
    await Timer(1, units="ns")
    
    # Wait for the pulse to propagate (Latency)
    for _ in range(LATENCY_CYCLES):
        await RisingEdge(dut.clk)
    
    # T4: Peak Value
    await Timer(1, units="ns")
    assert phase_err.value.signed_integer == EXPECTED_NEG_ERR, \
        f"Test 2 Error T4: Expected {EXPECTED_NEG_ERR} (DCO Lead), got {phase_err.value.signed_integer}"

    # T4.001ns: Shut off inputs
    ref_in.value = 0 
    dco_in.value = 0
    
    await RisingEdge(dut.clk) # T5: Hold cycle (still -8)
    assert phase_err.value.signed_integer == EXPECTED_NEG_ERR, \
        f"Test 2 Hold Error T5: Expected {EXPECTED_NEG_ERR}, got {phase_err.value.signed_integer}."
    
    # T6: Leakage starts (-8 -> -7)
    await RisingEdge(dut.clk) 
    
    # Check continued leakage
    cocotb.log.info("Test 2: Checking negative leakage to 0...")
    assert phase_err.value.signed_integer == EXPECTED_NEG_ERR + 1, \
        f"Test 2 Leak Error T6 Start: Expected {EXPECTED_NEG_ERR + 1}, got {phase_err.value.signed_integer}"

    # Loop for 6 more steps (from -7 up to -1)
    for i in range(2, abs(EXPECTED_NEG_ERR)): 
        expected = EXPECTED_NEG_ERR + i
        await RisingEdge(dut.clk)
        assert phase_err.value.signed_integer == expected, \
            f"Test 2 Leak Error: Expected {expected}, got {phase_err.value.signed_integer}"

    # T(6+7): Check final leakage to 0
    await RisingEdge(dut.clk)
    assert phase_err.value.signed_integer == 0, \
        f"Test 2 Leak Error Final: Expected 0, got {phase_err.value.signed_integer}"


    # =========================================================================
    # --- Test 3: Simultaneous Edges (Expect 0) ---
    # =========================================================================
    cocotb.log.info("--- Test 3: Simultaneous Edges (Expect 0) ---")
    
    # Ensure inputs are low before starting this test
    ref_in.value = 0 
    dco_in.value = 0
    await RisingEdge(dut.clk) 

    # T0: Both go high simultaneously
    ref_in.value = 1
    dco_in.value = 1
    await Timer(1, units="ns")
    
    # Wait for the pulse to propagate (Latency)
    for _ in range(LATENCY_CYCLES):
        await RisingEdge(dut.clk)
    
    # T4: Assert point for stable value (should be 0)
    await Timer(1, units="ns") 

    assert phase_err.value.signed_integer == 0, \
        f"Test 3 Simultaneous Error T4: Expected 0, got {phase_err.value.signed_integer}"
    
    # Clean up inputs
    ref_in.value = 0
    dco_in.value = 0
    await RisingEdge(dut.clk) 
    
    
    # =========================================================================
    # --- Test 4: Ref Leads DCO (Sustained Input) ---
    # Ensures the module only reacts to the *rising edge* even if input is held high.
    # =========================================================================
    cocotb.log.info("--- Test 4: Ref Leads DCO (Sustained Input) ---")
    
    # T0: Ref goes high and stays high
    ref_in.value = 1
    dco_in.value = 0
    await Timer(1, units="ns") 
    
    # T1-T4: Wait for the pulse to propagate (Latency)
    for _ in range(LATENCY_CYCLES):
        await RisingEdge(dut.clk)
    
    # T4: Peak Value
    await Timer(1, units="ns") 
    assert phase_err.value.signed_integer == EXPECTED_POS_ERR, \
        f"Test 4 Error T4: Expected {EXPECTED_POS_ERR} (Ref Lead), got {phase_err.value.signed_integer}."

    # T5: Hold cycle. ref_in is STILL high (sustained input). The error should still HOLD.
    await RisingEdge(dut.clk) 
    assert phase_err.value.signed_integer == EXPECTED_POS_ERR, \
        f"Test 4 Hold Error T5: Expected {EXPECTED_POS_ERR}, got {phase_err.value.signed_integer}."
        
    # T5.001ns: Pull ref_in low
    ref_in.value = 0 
    
    # T6: Leakage starts (8 -> 7). This confirms it was a single pulse regardless of input duration.
    await RisingEdge(dut.clk) 
    assert phase_err.value.signed_integer == EXPECTED_POS_ERR - 1, \
        f"Test 4 Leak Error T6 Start: Expected {EXPECTED_POS_ERR - 1}, got {phase_err.value.signed_integer}"
    
    # Finish decay
    cocotb.log.info("Test 4: Finishing positive leakage to 0...")
    for _ in range(EXPECTED_POS_ERR - 2): # decay from 6 down to 1
        await RisingEdge(dut.clk)
    await RisingEdge(dut.clk) # Check final leakage to 0
    assert phase_err.value.signed_integer == 0, \
        f"Test 4 Leak Error Final: Expected 0, got {phase_err.value.signed_integer}"


    # =========================================================================
    # --- Test 5: Opposite Edge During Decay (Decay Override) ---
    # Tests that a new pulse immediately overrides a decaying value.
    # =========================================================================
    cocotb.log.info("--- Test 5: Opposite Edge During Decay ---")
    
    # 1. Trigger Initial Ref Lead (+8)
    ref_in.value = 1
    dco_in.value = 0
    await Timer(1, units="ns") 
    
    # T1-T4: Wait for the pulse to propagate (Latency)
    for _ in range(LATENCY_CYCLES):
        await RisingEdge(dut.clk)

    # T4: Peak Value (+8)
    await Timer(1, units="ns") 
    ref_in.value = 0 # End the ref pulse
    
    await RisingEdge(dut.clk) # T5: Hold cycle (+8)
    
    await RisingEdge(dut.clk) # T6: Decay 1 (+7)
    assert phase_err.value.signed_integer == 7, f"Test 5: Decay Error 1 Failed, got {phase_err.value.signed_integer}"
    
    await RisingEdge(dut.clk) # T7: Decay 2 (+6)
    assert phase_err.value.signed_integer == 6, f"Test 5: Decay Error 2 Failed, got {phase_err.value.signed_integer}"
    
    # 2. Trigger Opposite DCO Lead Pulse during decay (at T7.001ns)
    cocotb.log.info("Test 5: Triggering DCO lead at T7 (Decay value is 6)...")
    ref_in.value = 0
    dco_in.value = 1
    await Timer(1, units="ns")
    
    # T8-T11: Wait for the DCO pulse to propagate (4 cycles)
    for _ in range(LATENCY_CYCLES):
        await RisingEdge(dut.clk)
    
    # T11: DCO Peak Value (-8)
    # The DCO pulse should override the decaying Ref pulse (+6)
    await Timer(1, units="ns")
    assert phase_err.value.signed_integer == EXPECTED_NEG_ERR, \
        f"Test 5 Override Error T11: Expected {EXPECTED_NEG_ERR}, got {phase_err.value.signed_integer}"

    # T11.001ns: Shut off inputs
    dco_in.value = 0
    
    await RisingEdge(dut.clk) # T12: Hold cycle (still -8)
    await RisingEdge(dut.clk) # T13: Leakage starts (-8 -> -7)
    assert phase_err.value.signed_integer == EXPECTED_NEG_ERR + 1, \
        f"Test 5 Leak Error T13 Start: Expected {EXPECTED_NEG_ERR + 1}, got {phase_err.value.signed_integer}"
    
    # Finish negative decay
    cocotb.log.info("Test 5: Checking negative leakage to 0...")
    for _ in range(abs(EXPECTED_NEG_ERR) - 1): 
        await RisingEdge(dut.clk)
    assert phase_err.value.signed_integer == 0, \
        f"Test 5 Leak Error Final: Expected 0, got {phase_err.value.signed_integer}"
    
    cocotb.log.info("All Phase Detector tests passed successfully!")
