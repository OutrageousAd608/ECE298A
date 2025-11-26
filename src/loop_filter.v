`timescale 1ns/1ps

module loop_filter #(
    parameter IN_WIDTH   = 16,
    parameter OUT_WIDTH  = 24,
    parameter integer K_P     = 4,  // proportional gain
    parameter integer I_SHIFT = 4   // integral gain = 1/2^I_SHIFT
)(
    input  wire clk,
    input  wire reset_n,
    input  wire update_en,
    input  wire signed [IN_WIDTH-1:0] phase_in,   // e[k]
    output reg  signed [OUT_WIDTH-1:0] control_out
);
    reg signed [OUT_WIDTH-1:0] acc;  // integrator

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            acc         <= 0;
            control_out <= 0;
        end else if (update_en) begin
            // Integral part
            acc <= acc + (phase_in >>> I_SHIFT);
            // Proportional + Integral
            control_out <= acc + (phase_in * K_P);
        end
        // when update_en=0, hold previous values
    end
endmodule
