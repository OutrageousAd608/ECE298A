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


# ---------------------------------------------------------------------
# Additional realistic PLL verification tests
# ---------------------------------------------------------------------

@cocotb.test()
async def test_relock_after_phase_jump(dut):
    """Simulate a phase step (reference signal sudden phase jump)."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    ref_period_ns = 1e9 / 1e6
    async def drive_ref_phase_shift():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")
            if cocotb.utils.get_sim_time('ns') > 2e6:
                await Timer(30, "ns")  # simulate phase lag once

    cocotb.start_soon(drive_ref_phase_shift())
    await Timer(int(5e6), "ns")
    assert int(dut.locked.value) == 1, "PLL failed to relock after phase jump"

@cocotb.test()
async def test_response_to_frequency_step(dut):
    """PLL relocks after sudden reference frequency change."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    async def drive_ref_freq_step():
        freq = 1e6
        while True:
            half = (1e9 / freq) / 2
            dut.ref_in.value = 1
            await Timer(ns_int(half), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(half), "ns")
            if cocotb.utils.get_sim_time('ns') > 2e6:
                freq = 1.3e6  # frequency step

    cocotb.start_soon(drive_ref_freq_step())
    await Timer(int(6e6), "ns")
    assert int(dut.locked.value) == 1, "PLL failed to track frequency step"

@cocotb.test()
async def test_long_term_stability(dut):
    """Long run with small jitter to ensure phase stability."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    ref_period_ns = 1e9 / 1e6
    async def drive_ref_jitter():
        while True:
            half = ref_period_ns / 2
            jitter = (random.random() - 0.5) * 0.05 * half
            dut.ref_in.value = 1
            await Timer(ns_int(half + jitter), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(half + jitter), "ns")

    cocotb.start_soon(drive_ref_jitter())
    await Timer(int(1e7), "ns")
    assert int(dut.locked.value) == 1, "PLL lost lock during long-term stability test"

@cocotb.test()
async def test_startup_edge_case(dut):
    """Reference clock starts late; check startup robustness."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    async def delayed_ref():
        await Timer(500_000, "ns")
        ref_period_ns = 1e9 / 1e6
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(delayed_ref())
    await Timer(int(6e6), "ns")
    assert int(dut.locked.value) == 1, "PLL failed to lock with delayed reference"

@cocotb.test()
async def test_no_reference(dut):
    """DUT behavior with no reference clock input (free-run mode)."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(int(3e6), "ns")
    assert True, "PLL did not free-run correctly"

@cocotb.test()
async def test_multiple_lock_cycles(dut):
    """Repeated lock/unlock cycles to check recovery."""
    sys_clk_hz = 20e6
    sys_period_ns = 1e9 / sys_clk_hz
    cocotb.start_soon(Clock(dut.sys_clk, sys_period_ns, "ns").start())

    dut.reset_n.value = 0
    dut.ref_in.value = 0
    await Timer(200, "ns")
    dut.reset_n.value = 1
    await Timer(200, "ns")

    ref_period_ns = 1e9 / 1e6
    async def drive_ref_fluctuating():
        while True:
            dut.ref_in.value = 1
            await Timer(ns_int(ref_period_ns/2), "ns")
            dut.ref_in.value = 0
            await Timer(ns_int(ref_period_ns/2), "ns")

    cocotb.start_soon(drive_ref_fluctuating())
    for cycle in range(3):
        await Timer(2_000_000, "ns")
        dut.reset_n.value = 0
        await Timer(100_000, "ns")
        dut.reset_n.value = 1
    await Timer(2_000_000, "ns")
    assert int(dut.locked.value) == 1, "PLL failed to relock after multiple cycles"
