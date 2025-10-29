`timescale 1ns/1ps
module dco #(
    parameter CTRL_BITS = 10,
    parameter PHASE_BITS = 16
) (
    input  wire clk,
    input  wire reset_n,
    input  wire [CTRL_BITS-1:0] ctrl_word,
    output reg dco_out
);

reg [PHASE_BITS-1:0] phase_acc;
reg [PHASE_BITS-1:0] incr;

always @(*) begin
    incr = {ctrl_word, {PHASE_BITS-CTRL_BITS{1'b0}}};
end

always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        phase_acc <= 0;
        dco_out <= 0;
    end else begin
        phase_acc <= phase_acc + incr;
        dco_out <= phase_acc[PHASE_BITS-1];
    end
end

endmodule
