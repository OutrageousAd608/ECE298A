`timescale 1ns/1ps
module adpll_top (
    input  wire sys_clk,
    input  wire reset_n,
    input  wire ref_in,
    output wire dco_out,
    output wire locked
);

parameter PHASE_BITS = 16;
parameter CTRL_BITS  = 10;
parameter LOCK_THRESH = 20;

wire signed [31:0] pd_val;
wire [CTRL_BITS-1:0] dco_ctrl;
wire [31:0] lf_out;

phase_detector #(.OUT_WIDTH(32)) pd (
    .clk(sys_clk),
    .reset_n(reset_n),
    .ref_in(ref_in),
    .dco_in(dco_out),
    .phase_err(pd_val)
);

loop_filter #(.IN_WIDTH(32), .OUT_WIDTH(32), .K_P(8)) lf (
    .clk(sys_clk),
    .reset_n(reset_n),
    .phase_in(pd_val),
    .control_out(lf_out)
);

dco #(.CTRL_BITS(CTRL_BITS), .PHASE_BITS(PHASE_BITS)) my_dco (
    .clk(sys_clk),
    .reset_n(reset_n),
    .ctrl_word(lf_out[CTRL_BITS-1:0]),
    .dco_out(dco_out)
);

reg [$clog2(LOCK_THRESH+1)-1:0] lock_cnt;
reg lock_reg;
always @(posedge sys_clk or negedge reset_n) begin
    if (!reset_n) begin
        lock_cnt <= 0;
        lock_reg <= 1'b0;
    end else begin
        if ($signed(pd_val) < 32'sd16 && $signed(pd_val) > -32'sd16) begin
            if (lock_cnt < LOCK_THRESH) lock_cnt <= lock_cnt + 1;
        end else begin
            lock_cnt <= 0;
        end
        lock_reg <= (lock_cnt >= (LOCK_THRESH-1));
    end
end
assign locked = lock_reg;

endmodule
