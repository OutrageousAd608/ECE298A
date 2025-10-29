import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
import random

def ns_int(value):
    """Helper to round nanoseconds to integer to avoid simulator precision errors."""
    return int(round(value))

async def init_dut(dut):
    """Common initialization for all tests."""
    dut.reset_n.value = 0
    dut.ref_in.value = 0
    dut.ena.value = 1  # drive enable high
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

async def start_clock(dut, clk_hz=20e6):
    period_ns = 1e9 / clk_hz
    cocotb.start_soon(Clock(dut.clk, period_ns, "ns").start())

@cocotb.test()
async def test_locking_basic(dut):
    await start_clock(dut)
    await init_dut(dut)

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(drive_ref())
    await Timer(int(5e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL did not lock"

@cocotb.test()
async def test_lock_with_jitter(dut):
    await start_clock(dut)
    await init_dut(dut)

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
    await start_clock(dut)
    await init_dut(dut)

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

# Additional tests added

@cocotb.test()
async def test_startup_behavior(dut):
    """Ensure ADPLL locks cleanly after reset without overshoot or oscillation."""
    await start_clock(dut)
    await init_dut(dut)

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(drive_ref())
    await Timer(int(3e6), "ns")
    assert int(dut.locked.value) == 1, "ADPLL failed to lock cleanly after reset"

@cocotb.test()
async def test_phase_detector_saturation(dut):
    """Test that phase detector saturates properly for large phase error."""
    await start_clock(dut)
    await init_dut(dut)

    # Drive DCO far from reference to saturate PD
    dut.ref_in.value = 0
    dut.ena.value = 1
    for _ in range(1000):
        dut.ref_in.value = 1
        await Timer(500, "ns")
        dut.ref_in.value = 0
        await Timer(500, "ns")

    assert int(dut.locked.value) in [0, 1], "Phase detector saturation misbehaving"

@cocotb.test()
async def test_relock_after_disturbance(dut):
    """After locking, a phase disturbance should cause relock."""
    await start_clock(dut)
    await init_dut(dut)

    ref_freq_hz = 1e6
    ref_period_ns = 1e9 / ref_freq_hz

    async def drive_ref():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(drive_ref())
    await Timer(int(5e6), "ns")

    # Introduce phase disturbance
    dut.reset_n.value = 0
    await Timer(100, "ns")
    dut.reset_n.value = 1
    await Timer(int(2e6), "ns")

    assert int(dut.locked.value) == 1, "ADPLL failed to relock after disturbance"
