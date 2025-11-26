`timescale 1ns/1ps

module phase_detector #(
    parameter OUT_WIDTH = 16,
    parameter signed [OUT_WIDTH-1:0] ERR_STEP = 16'sd1
)(
    input  wire clk,
    input  wire reset_n,

    input  wire ref_in,
    input  wire dco_in,

    output reg  signed [OUT_WIDTH-1:0] phase_err,
    output reg  edge_valid
);
    // Synchronize reference to clk
    reg ref_ff1, ref_ff2, ref_prev;
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            ref_ff1  <= 0;
            ref_ff2  <= 0;
            ref_prev <= 0;
        end else begin
            ref_ff1  <= ref_in;
            ref_ff2  <= ref_ff1;
            ref_prev <= ref_ff2;
        end
    end
    wire ref_sync = ref_ff2;

    // Register DCO
    reg dco_ff, dco_prev;
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            dco_ff   <= 0;
            dco_prev <= 0;
        end else begin
            dco_prev <= dco_ff;
            dco_ff   <= dco_in;
        end
    end

    // Edge detection
    wire ref_rise = ref_sync & ~ref_prev;
    wire dco_rise = dco_ff   & ~dco_prev;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            phase_err  <= 0;
            edge_valid <= 0;
        end else begin
            edge_valid <= (ref_rise | dco_rise);

            if (ref_rise && !dco_rise)
                phase_err <=  ERR_STEP;   // ref leads → speed up DCO
            else if (dco_rise && !ref_rise)
                phase_err <= -ERR_STEP;   // DCO leads → slow down DCO
            else
                phase_err <= 0;           // no edge or simultaneous
        end
    end
endmodule
