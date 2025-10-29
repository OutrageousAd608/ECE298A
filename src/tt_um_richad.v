`timescale 1ns/1ps
module tt_um_richad (
    input  wire clk,         // TT system clock
    input  wire ena,         // TT global enable
    input  wire rst_n,       // TT asynchronous active-low reset
    input  wire ref_in,      // PLL reference input
    input  wire [7:0] ui_in, // TinyTapeout user input pins (8 bits)
    output wire dco_out,     // DCO output
    output wire locked,      // Lock indicator
    output wire [7:0] ui_out // TinyTapeout user output pins (8 bits)
);

parameter PHASE_BITS = 16;
parameter CTRL_BITS  = 10;
parameter LOCK_THRESH = 20;

wire signed [31:0] pd_val;
wire [CTRL_BITS-1:0] dco_ctrl;
wire [31:0] lf_out;

// Phase Detector
phase_detector #(.OUT_WIDTH(32)) pd (
    .clk(clk),
    .reset_n(rst_n),
    .ref_in(ref_in),
    .dco_in(dco_out),
    .phase_err(pd_val)
);

// Loop Filter
loop_filter #(.IN_WIDTH(32), .OUT_WIDTH(32), .K_P(8)) lf (
    .clk(clk),
    .reset_n(rst_n),
    .phase_in(pd_val),
    .control_out(lf_out)
);

// DCO
dco #(.CTRL_BITS(CTRL_BITS), .PHASE_BITS(PHASE_BITS)) my_dco (
    .clk(clk),
    .reset_n(rst_n),
    .ctrl_word(lf_out[CTRL_BITS-1:0]),
    .dco_out(dco_out)
);

// Lock Detector
reg [$clog2(LOCK_THRESH+1)-1:0] lock_cnt;
reg lock_reg;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        lock_cnt <= 0;
        lock_reg <= 1'b0;
    end else if (ena) begin
        if ($signed(pd_val) < 32'sd16 && $signed(pd_val) > -32'sd16) begin
            if (lock_cnt < LOCK_THRESH) lock_cnt <= lock_cnt + 1;
        end else begin
            lock_cnt <= 0;
        end
        lock_reg <= (lock_cnt >= (LOCK_THRESH-1));
    end
end

assign locked = lock_reg;
assign ui_out = 8'b0000_0000; // tie unused TT pins to 0

endmodule
