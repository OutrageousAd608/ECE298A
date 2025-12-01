import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
import random

SYSCLK_NS = 20  # 50 MHz

# ----------------------------------------------------------------------
# Helper: Safe integer conversion
# ----------------------------------------------------------------------
def safe_int(sig):
    """Safely convert signal to int, treating X/Z as 0."""
    try:
        return int(sig.value)
    except ValueError:
        return 0

# ----------------------------------------------------------------------
# Helper: Cycle-Aligned Reference Driver
# ----------------------------------------------------------------------
async def drive_ref_cycles(dut, high_cycles, low_cycles, jitter_mode=False):
    """
    Drives ref_in aligned to FallingEdge to avoid GLS X-propagation.
    
    high_cycles: Number of CLK cycles ref is HIGH
    low_cycles:  Number of CLK cycles ref is LOW
    """
    while True:
        # Drive HIGH
        curr_val = safe_int(dut.ui_in.value)
        dut.ui_in.value = curr_val | 1
        
        for _ in range(high_cycles):
            await FallingEdge(dut.clk)
            
        # Drive LOW
        curr_val = safe_int(dut.ui_in.value)
        dut.ui_in.value = curr_val & ~1
        
        # Simple Jitter Injection (skips or adds a wait cycle randomly)
        if jitter_mode and random.randint(0, 10) > 8:
            if random.choice([True, False]):
                await FallingEdge(dut.clk) # Add extra delay
        
        for _ in range(low_cycles):
            await FallingEdge(dut.clk)

# ----------------------------------------------------------------------
# Reset Routine
# ----------------------------------------------------------------------
async def reset_and_start_clock(dut):
    cocotb.start_soon(Clock(dut.clk, SYSCLK_NS, units="ns").start())
    
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    
    await Timer(200, units="ns")
    
    # CRITICAL: Release reset on FallingEdge to prevent Setup violation X's
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    
    for _ in range(10): await RisingEdge(dut.clk)

async def wait_for_lock(dut, timeout_us):
    cycles = int(timeout_us * 1000 // SYSCLK_NS)
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        if safe_int(dut.uo_out.value) & 0x1:
            return True
    return False

# ======================================================================
# TESTS
# ======================================================================

@cocotb.test()
async def test_lock_observation(dut):
    cocotb.log.info("TEST: Observation")
    await reset_and_start_clock(dut)
    
    # 1 MHz = 50 cycles (25 High, 25 Low)
    cocotb.start_soon(drive_ref_cycles(dut, 25, 25))
    
    await Timer(500, units="us")
    cocotb.log.info("Finished Observation")

@cocotb.test()
async def test_basic_lock(dut):
    cocotb.log.info("TEST: Basic Phase Lock at 1 MHz")
    await reset_and_start_clock(dut)
    
    # 1 MHz = 50 cycles (25 High, 25 Low)
    cocotb.start_soon(drive_ref_cycles(dut, 25, 25))
    
    # Increased timeout for GLS settling
    locked = await wait_for_lock(dut, 5000) 
    assert locked, "ADPLL failed to achieve True Phase Lock"
    cocotb.log.info("PASS: Phase Locked")

@cocotb.test()
async def test_jitter_lock(dut):
    cocotb.log.info("TEST: True Lock with Jitter")
    await reset_and_start_clock(dut)
    
    # 1 MHz with occasional cycle skips (Jitter)
    cocotb.start_soon(drive_ref_cycles(dut, 25, 25, jitter_mode=True))
    
    locked = await wait_for_lock(dut, 6000)
    assert locked, "ADPLL failed to lock with jitter"
    cocotb.log.info("PASS: Locked despite jitter")

@cocotb.test()
async def test_freq_step(dut):
    cocotb.log.info("TEST: Frequency Step (Integer Divisors)")
    await reset_and_start_clock(dut)

    # 1. Lock to 1 MHz (50 cycles: 25H/25L)
    ref_task = cocotb.start_soon(drive_ref_cycles(dut, 25, 25))
    await wait_for_lock(dut, 5000)
    
    cocotb.log.info("STEP: Changing to 1.25 MHz (Integer Safe)")
    ref_task.kill()
    
    # Clear input
    dut.ui_in.value = safe_int(dut.ui_in.value) & ~1
    
    # 2. Step to 1.25 MHz
    # 50 MHz / 1.25 MHz = 40 cycles (20 High, 20 Low)
    # This prevents X-propagation by staying grid-aligned
    ref_task = cocotb.start_soon(drive_ref_cycles(dut, 20, 20))

    # Check that lock drops
    await Timer(200, units="us") 
    is_locked_early = safe_int(dut.uo_out.value) & 0x1
    if is_locked_early == 0:
         cocotb.log.info("PASS: Lock correctly dropped.")

    # 3. Wait for Re-lock
    await Timer(7000, units="us")

    # 4. Final Verification
    is_locked = safe_int(dut.uo_out.value) & 0x1
    cocotb.log.info(f"Final Lock State: {is_locked}")
    
    assert is_locked, "Lock bit should be high at steady state"
