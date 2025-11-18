`timescale 1ns/1ps
module tt_um_richad (
    input  wire       clk,       // TT system clock
    input  wire       ena,       // TT global enable (can be ignored)
    input  wire       rst_n,     // TT asynchronous active-low reset
    input  wire [7:0] ui_in,     // TinyTapeout user input pins (used for DCO control)
    output wire [7:0] uo_out,    // TinyTapeout dedicated outputs
    input  wire [7:0] uio_in,    // TinyTapeout bidirectional input path (used for DCO control)
    output wire [7:0] uio_out,   // TinyTapeout bidirectional output path
    output wire [7:0] uio_oe     // TinyTapeout bidirectional output enable path
);

    // ===================================================
    // Internal signals (Initialized to avoid 'x' states)
    // ===================================================
    wire [9:0] dco_ctrl_word; // 10-bit control word for DCO
    wire dco_signal;          // Output from the DCO

    // Map the DCO control word from user inputs (10 bits total)
    // dco_ctrl_word[9:0] <= {uio_in[1:0], ui_in[7:0]}
    assign dco_ctrl_word = {uio_in[1:0], ui_in[7:0]};

    // ===================================================
    // Isolated DCO instantiation
    // The PD and LF modules are NOT instantiated or connected for testing.
    // ===================================================

    // Parameters: CTRL_BITS=10, PHASE_BITS=16
    dco #(.CTRL_BITS(10), .PHASE_BITS(16)) my_dco (
        .clk(clk),
        .reset_n(rst_n),
        .ctrl_word(dco_ctrl_word), // Directly driven by user/bidirectional inputs
        .dco_out(dco_signal)
    );

    // ===================================================
    // Map internal signals to TinyTapeout outputs
    // ===================================================
    // uo_out[0] will carry the DCO output signal
    assign uo_out = {7'b0, dco_signal}; 

    // Initialize all unused outputs to '0' to prevent 'X's
    assign uio_out = 8'h00; 
    assign uio_oe  = 8'h00; // Disable bidirectional outputs

    // Initialize remaining inputs/wires if they were used (they are not in this setup)
    // The unused input wires (ena, ui_in[0], uio_in[7:2]) are automatically handled 
    // by cocotb during test.

endmodule
