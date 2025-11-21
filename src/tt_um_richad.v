`timescale 1ns/1ps
module tt_um_richad (
    input  wire       clk,       // TT system clock
    input  wire       ena,       // TT global enable (can be ignored)
    input  wire       rst_n,     // TT asynchronous active-low reset
    input  wire [7:0] ui_in,     // TinyTapeout user input pins
    output wire [7:0] uo_out,    // TinyTapeout dedicated outputs
    input  wire [7:0] uio_in,    // TinyTapeout bidirectional input path (unused)
    output wire [7:0] uio_out,   // TinyTapeout bidirectional output path (used for phase_err)
    output wire [7:0] uio_oe     // TinyTapeout bidirectional output enable path
);

    // ===================================================
    // PHASE DETECTOR ISOLATION FOR TESTING
    //
    // The Loop Filter and DCO are commented out to force
    // isolated testing of the phase_detector module.
    // ===================================================
    
    // Internal signals for Phase Detector (PD)
    wire pd_ref_in;
    wire pd_dco_in;
    wire signed [31:0] pd_val; // Phase error output (signed 32-bit)

    // Map user input bits directly to PD inputs:
    // ui_in[0] -> Reference Input (ref_in)
    // ui_in[1] -> DCO/Feedback Input (dco_in)
    assign pd_ref_in = ui_in[0];
    assign pd_dco_in = ui_in[1];

    // Instantiate ONLY the phase_detector module
    phase_detector #(.OUT_WIDTH(32)) pd (
        .clk(clk),
        .reset_n(rst_n),
        .ref_in(pd_ref_in),
        .dco_in(pd_dco_in),
        .phase_err(pd_val)
    );

    // COMMENTED OUT: Loop Filter and DCO are skipped for isolated PD test.
    /*
    wire [31:0] lf_out;
    loop_filter #(.IN_WIDTH(32), .OUT_WIDTH(32), .K_P(8)) lf (
        .clk(clk),
        .reset_n(rst_n),
        .phase_in(pd_val),
        .control_out(lf_out)
    );

    dco #(.CTRL_BITS(10), .PHASE_BITS(15)) my_dco (
        .clk(clk),
        .reset_n(rst_n),
        .ctrl_word(lf_out[9:0]),
        .dco_out(dco_signal)
    );
    */

    // ===================================================
    // Map internal signals to TinyTapeout outputs
    // We map the 16 LSBs of the 32-bit phase error for observation.
    // ===================================================
    
    // uo_out (Dedicated Outputs): phase_err[7:0] (LSBs)
    assign uo_out = pd_val[7:0];

    // uio_out (Bidirectional Outputs): phase_err[15:8] (Next 8 bits)
    assign uio_out = pd_val[15:8];
    assign uio_oe  = 8'hFF; // Enable all bidirectional outputs

endmodule
