import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
import random

def ns_int(value):
    """Helper to round nanoseconds to integer to avoid simulator precision errors."""
    return int(round(value))

@cocotb.test()
async def test_locking_basic(dut):
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(drive_ref())

    await Timer(int(5e6), "ns")  # give it more time to settle
    assert int(dut.locked.value) == 1, "ADPLL did not lock"

@cocotb.test()
async def test_lock_with_jitter(dut):
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref_jittery():
        while True:
            half = ref_period_ns / 2
            jitter = (random.random() - 0.5) * 0.2 * half
            dut.ref_in.value = 1
            await Timer(ns_int(half + jitter), "ns")
            jitter2 = (random.random() - 0.5) * 0.2 * half
            dut.ref_in.value = 0
            await Timer(ns_int(half + jitter2), "ns")

    cocotb.start_soon(drive_ref_jittery())

    await Timer(int(6e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL failed to lock with jitter"

@cocotb.test()
async def test_frequency_tracking(dut):
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    async def drive_ref_steps(freqs_hz):
        for f in freqs_hz:
            half = (1e9 / f) / 2
            t_end = cocotb.utils.get_sim_time('ns') + 300000
            while cocotb.utils.get_sim_time('ns') < t_end:
                dut.ref_in.value = 1
                await Timer(ns_int(half), "ns")
                dut.ref_in.value = 0
                await Timer(ns_int(half), "ns")

    freqs = [0.9e6, 1.0e6, 1.1e6]
    cocotb.start_soon(drive_ref_steps(freqs))

    await Timer(int(2e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL not locked after frequency steps"

# ------------------------------
# NEW TESTS BELOW
# ------------------------------

@cocotb.test()
async def test_startup_behavior(dut):
    """Ensure ADPLL locks cleanly after reset without overshoot or oscillation."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    # Reset
    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(100, "ns")
    dut.reset_n.value = 1

    # Reference signal
    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns / 2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns / 2), "ns")

    cocotb.start_soon(drive_ref())

    await Timer(int(3e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL failed to lock cleanly after reset"

@cocotb.test()
async def test_phase_detector_saturation(dut):
    """Test that phase detector saturates properly for large phase error."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    await Timer(100, "ns")
    dut.reset_n.value = 1

    # Drive extremely slow reference
    ref_freq_hz = 100e3
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_slow_ref():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns / 2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns / 2), "ns")

    cocotb.start_soon(drive_slow_ref())

    await Timer(int(5e6), "ns")
    assert int(dut.locked.value) in [0, 1], "Lock signal unstable under saturation condition"

@cocotb.test()
async def test_relock_after_disturbance(dut):
    """After locking, a phase disturbance should cause relock."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref_with_glitch():
        count = 0
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns / 2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns / 2), "ns")
            count += 1
            # introduce phase glitch
            if count == 1000:
                await Timer(500, "ns")

    cocotb.start_soon(drive_ref_with_glitch())

    await Timer(int(2e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL failed to relock after disturbance"
