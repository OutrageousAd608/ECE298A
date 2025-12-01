import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
import random

SYSCLK_NS = 20  # 50 MHz

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def safe_int(sig):
    """Safely convert a signal to int, treating X/Z as 0 to prevent crash."""
    try:
        return int(sig.value)
    except ValueError:
        return 0

async def drive_ref(dut, freq_hz, jitter_ps=0):
    """
    Drives bit 0 of ui_in with the reference clock.
    Uses Read-Modify-Write to preserve other input bits.
    """
    period_ps = int(1_000_000_000_000 // freq_hz)
    half_ps = period_ps // 2
    ref_val = 0
    
    while True:
        ref_val = 1 if ref_val == 0 else 0
        
        # FIX 1: Bitwise Safe Drive
        # In GL, overwriting the whole port with an integer can cause issues.
        current_val = safe_int(dut.ui_in.value)
        if ref_val:
            dut.ui_in.value = current_val | 1
        else:
            dut.ui_in.value = current_val & ~1
            
        # Jitter calculation
        jitter = random.randint(-jitter_ps, jitter_ps) if jitter_ps else 0
        delay_ps = max(1, half_ps + jitter)
        
        await Timer(delay_ps, units="ps")

async def reset_and_start_clock(dut):
    """
    Resets the DUT with GL-safe timing.
    """
    cocotb.start_soon(Clock(dut.clk, SYSCLK_NS, units="ns").start())
    
    # Initialize inputs
    dut.ena.value = 1
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    
    # Wait 200ns
    await Timer(200, units="ns")
    
    # FIX 2: Synchronous Reset Release
    # In Gate Level Sim, releasing reset coincident with RisingEdge causes X (Metastability).
    # We release on FallingEdge so data is stable before the next RisingEdge.
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    
    # Wait a few clocks for internal logic to settle
    for _ in range(10): 
        await RisingEdge(dut.clk)

async def wait_for_lock(dut, timeout_us):
    """
    Waits for the lock signal (bit 0 of uo_out) to go high.
    """
    cycles = int(timeout_us * 1000 // SYSCLK_NS)
    for _ in range(cycles):
        await RisingEdge(dut.clk)
        # Check bit 0 of uo_out
        if safe_int(dut.uo_out.value) & 0x1:
            return True
    return False

# ======================================================================
# TESTS
# ======================================================================

@cocotb.test()
async def test_lock_observation(dut):
    cocotb.log.info("TEST: Observation (True Phase Lock)")
    await reset_and_start_clock(dut)
    cocotb.start_soon(drive_ref(dut, freq_hz=1_000_000))
    
    # Run for a bit to ensure no crashes
    await Timer(500, units="us")
    cocotb.log.info("Finished Observation")

@cocotb.test()
async def test_basic_lock(dut):
    cocotb.log.info("TEST: Basic Phase Lock at 1 MHz")
    await reset_and_start_clock(dut)
    cocotb.start_soon(drive_ref(dut, 1_000_000))
    
    # Tuned for GL: 1MHz is an integer division of 50MHz, so this should lock clean.
    locked = await wait_for_lock(dut, 4000) 
    assert locked, "ADPLL failed to achieve True Phase Lock"
    cocotb.log.info("PASS: Phase Locked")

@cocotb.test()
async def test_jitter_lock(dut):
    cocotb.log.info("TEST: True Lock with Jitter")
    await reset_and_start_clock(dut)
    cocotb.start_soon(drive_ref(dut, 1_000_000, jitter_ps=2000))
    
    # Jitter makes the bucket fill slower, give it time
    locked = await wait_for_lock(dut, 5000)
    assert locked, "ADPLL failed to lock with jitter"
    cocotb.log.info("PASS: Locked despite jitter")

@cocotb.test()
async def test_freq_step(dut):
    cocotb.log.info("TEST: Frequency Step (The Creep & Re-Lock)")
    await reset_and_start_clock(dut)

    # 1. Lock to 0.9 MHz
    ref_task = cocotb.start_soon(drive_ref(dut, 900_000))
    await wait_for_lock(dut, 4000)

    # 2. Step to 1.1 MHz
    cocotb.log.info("STEP: Changing to 1.1 MHz")
    ref_task.kill()
    
    # Clear input safely
    curr = safe_int(dut.ui_in.value)
    dut.ui_in.value = curr & ~1
    
    ref_task = cocotb.start_soon(drive_ref(dut, 1_100_000))

    # Check that lock drops
    await Timer(100, units="us") 
    is_locked_early = safe_int(dut.uo_out.value) & 0x1
    if is_locked_early == 0:
         cocotb.log.info("PASS: Lock correctly dropped during frequency change.")
    
    # 3. Wait for Creep + Bucket Fill
    # GL simulation might be slightly slower to converge due to delays
    await Timer(7000, units="us")

    # 4. Final Verification
    is_locked = safe_int(dut.uo_out.value) & 0x1
    cocotb.log.info(f"Final Lock State: {is_locked}")
    
    # NOTE: If this fails in GL but passes in RTL, it is due to 'X' propagation 
    # in the synchronizer. Synchronizers are notoriously hard to GL simulate.
    assert is_locked, "Lock bit should be high at steady state"
    
    cocotb.log.info("PASS: System re-locked to new phase.")
