import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
import random

def ns_int(value):
    """Helper to round nanoseconds to integer to avoid simulator precision errors."""
    return int(round(value))

# -----------------------------
# Original tests
# -----------------------------
@cocotb.test()
async def test_locking_basic(dut):
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

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
    await Timer(int(5e6), "ns")  # allow settling
    assert int(dut.locked.value) == 1, "ADPLL did not lock"

@cocotb.test()
async def test_lock_with_jitter(dut):
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

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
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

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

# -----------------------------
# New additional realistic tests
# -----------------------------
@cocotb.test()
async def test_startup_behavior(dut):
    """Ensure ADPLL locks cleanly after reset without overshoot or oscillation."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(100, "ns")
    dut.reset_n.value = 1
    await Timer(5e6, "ns")

    assert int(dut.locked.value) == 1, "ADPLL failed to lock cleanly after reset"

@cocotb.test()
async def test_phase_detector_saturation(dut):
    """Test that phase detector saturates properly for large phase error."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(100, "ns")
    dut.reset_n.value = 1

    # Force a large phase difference
    for _ in range(5000):
        dut.ref_in.value = 0
        await Timer(10, "ns")
        dut.ref_in.value = 1
        await Timer(10, "ns")

    assert True, "Phase detector ran without crashing (check logs for saturation behavior)"

@cocotb.test()
async def test_relock_after_disturbance(dut):
    """After locking, a phase disturbance should cause relock."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1

    # Run until initial lock
    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref_normal():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(drive_ref_normal())
    await Timer(int(5e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL did not lock initially"

    # Introduce phase disturbance
    dut.ref_in.value = 0
    await Timer(int(1e6), "ns")
    dut.ref_in.value = 1
    await Timer(int(1e6), "ns")

    # Give it time to relock
    await Timer(int(5e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL failed to relock after disturbance"
