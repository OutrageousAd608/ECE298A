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

    reg ref_ff1, ref_ff2, ref_prev;
    reg dco_ff, dco_prev;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            ref_ff1 <= 0; ref_ff2 <= 0; ref_prev <= 0;
            dco_ff  <= 0; dco_prev <= 0;
        end else begin
            ref_ff1 <= ref_in;
            ref_ff2 <= ref_ff1;
            ref_prev<= ref_ff2;
            dco_ff  <= dco_in;
            dco_prev<= dco_ff;
        end
    end

    wire ref_rise = ref_ff2 & ~ref_prev;
    wire dco_rise = dco_ff  & ~dco_prev;

    localparam [1:0] S_IDLE = 2'b00, S_UP = 2'b01, S_DN = 2'b10;
    reg [1:0] state;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) state <= S_IDLE;
        else case (state)
            S_IDLE: if (ref_rise && !dco_rise) state <= S_UP;
                    else if (dco_rise && !ref_rise) state <= S_DN;
            S_UP:   if (dco_rise) state <= S_IDLE;
            S_DN:   if (ref_rise) state <= S_IDLE;
            default: state <= S_IDLE;
        endcase
    end

    always @(*) begin
        case (state)
            S_UP: begin phase_err = ERR_STEP;  edge_valid = 1'b1; end
            S_DN: begin phase_err = -ERR_STEP; edge_valid = 1'b1; end
            default: begin phase_err = 0;      edge_valid = 1'b0; end
        endcase
    end
endmodule
