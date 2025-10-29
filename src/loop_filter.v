`timescale 1ns/1ps
module loop_filter #(
    parameter IN_WIDTH  = 32,
    parameter OUT_WIDTH = 32,
    parameter K_P = 16,
    parameter K_I = 2
) (
    input  wire clk,
    input  wire reset_n,
    input  wire signed [IN_WIDTH-1:0] phase_in,
    output reg signed [OUT_WIDTH-1:0] control_out
);

reg signed [OUT_WIDTH-1:0] acc;

always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        acc <= 0;
        control_out <= 0;
    end else begin
        acc <= acc + (phase_in >>> K_I);  // small integral action
        control_out <= (phase_in * K_P) + acc;
    end
end

endmodule
