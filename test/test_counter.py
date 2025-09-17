import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def test_reset_and_count(dut):
    """Test reset and simple counting"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # After reset, counter should be 0
    await RisingEdge(dut.clk)
    assert dut.uo_out.value == 0, f"Expected 0 after reset, got {dut.uo_out.value}"

    # Check normal counting
    for i in range(1, 5):
        await RisingEdge(dut.clk)
        assert dut.uo_out.value == i, f"Expected {i}, got {dut.uo_out.value}"


@cocotb.test()
async def test_load_value(dut):
    """Test synchronous load of counter"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset
    dut.rst_n.value = 0
    dut.ena.value = 1
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # Load a value: 0b10101010 (170)
    dut.ui_in.value = 0b10101010
    dut.uio_in.value = 1  # load enable
    await RisingEdge(dut.clk)  # load happens here
    dut.uio_in.value = 0       # disable load
    await RisingEdge(dut.clk)  # now the counter holds the loaded value

    assert dut.uo_out.value == 0b10101010, f"Load failed, got {dut.uo_out.value}"

    # Check it counts up after load
    await RisingEdge(dut.clk)
    expected = 0b10101010 + 1
    assert dut.uo_out.value == expected, f"Expected {expected}, got {dut.uo_out.value}"


@cocotb.test()
async def test_tristate_output(dut):
    """Test tri-state output when ena=0"""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset and count a bit
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Save the current value
    value_when_enabled = int(dut.uo_out.value)

    # Disable outputs
    dut.ena.value = 0
    await RisingEdge(dut.clk)

    # When ena=0, uo_out should be high-Z
    assert dut.uo_out.value.is_resolvable is False, "Expected tri-state (Z) outputs"

    # Re-enable
    dut.ena.value = 1
    await RisingEdge(dut.clk)
    assert int(dut.uo_out.value) == value_when_enabled + 1, "Counter should keep running internally"
