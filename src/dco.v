`timescale 1ns/1ps

module dco #(
    parameter CTRL_BITS  = 20,
    parameter PHASE_BITS = 24
)(
    input  wire clk,
    input  wire reset_n,
    input  wire [CTRL_BITS-1:0] ctrl_word,
    output reg  dco_out
);
    reg [PHASE_BITS-1:0] phase;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            phase   <= 0;
            dco_out <= 0;
        end else begin
            // Explicitly pad the 20-bit control word to 24 bits
            phase   <= phase + { {PHASE_BITS-CTRL_BITS{1'b0}}, ctrl_word };
            dco_out <= phase[PHASE_BITS-1];
        end
    end
endmodule
