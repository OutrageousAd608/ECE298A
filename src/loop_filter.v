`timescale 1ns/1ps

module loop_filter #(
    parameter IN_WIDTH   = 16,
    parameter OUT_WIDTH  = 24,
    parameter integer K_P     = 4,  //proportional gain
    parameter integer I_SHIFT = 4   //integral gain = 1/2^I_SHIFT
)(
    input  wire clk,
    input  wire reset_n,
    input  wire update_en,
    input  wire signed [IN_WIDTH-1:0] phase_in,   //e[k]
    output reg  signed [OUT_WIDTH-1:0] control_out
);
    reg signed [OUT_WIDTH-1:0] acc;  //integrator

    //helper: Sign-extend input to output width for safe arithmetic
    wire signed [OUT_WIDTH-1:0] phase_in_ext = { {OUT_WIDTH-IN_WIDTH{phase_in[IN_WIDTH-1]}}, phase_in };
    
    //helper: Calculate Proportional term separately to handle width (Input * Integer -> 32 bit -> Truncate to OUT_WIDTH)
    wire signed [31:0] prop_mult = phase_in * K_P;
    wire signed [OUT_WIDTH-1:0] prop_term = prop_mult[OUT_WIDTH-1:0];

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            acc         <= 0;
            control_out <= 0;
        end else if (update_en) begin
            //pntegral part: Use the sign-extended input
            acc <= acc + (phase_in_ext >>> I_SHIFT);
            
            //proportional + Integral: Use the explicit widths
            control_out <= acc + prop_term;
        end
        //when update_en=0, hold previous values
    end
endmodule
