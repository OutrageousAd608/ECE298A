`timescale 1ns/1ps
module tt_um_richad (
    // TinyTapeout standard ports
    input  wire [7:0] ui_in,    // Dedicated user inputs
    output wire [7:0] uo_out,   // Dedicated user outputs
    input  wire [7:0] uio_in,   // Bidirectional IO inputs
    output wire [7:0] uio_out,  // Bidirectional IO outputs
    output wire [7:0] uio_oe,   // IO output enable (active high)
    input  wire       ena,      // Global enable (can ignore)
    input  wire       clk,      // System clock
    input  wire       rst_n,    // Asynchronous active-low reset

    // PLL-specific ports
    input  wire       ref_in,   // PLL reference input
    output wire       dco_out,  // DCO output
    output wire       locked    // Lock indicator
);

parameter PHASE_BITS = 16;
parameter CTRL_BITS  = 10;
parameter LOCK_THRESH = 20;

// Phase detector
wire signed [31:0] pd_val;

phase_detector #(.OUT_WIDTH(32)) pd (
    .clk(clk),
    .reset_n(rst_n),
    .ref_in(ref_in),
    .dco_in(dco_out),
    .phase_err(pd_val)
);

// Loop filter
wire [31:0] lf_out;

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

// Lock detection
reg [$clog2(LOCK_THRESH+1)-1:0] lock_cnt;
reg lock_reg;
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
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

// Tie off unused TT outputs
assign uo_out  = 8'b0;
assign uio_out = 8'b0;
assign uio_oe  = 8'b0;

endmodule
