`timescale 1ns/1ps

/* verilator lint_off TIMESCALEMOD */
module tt_um_richad (
    input  wire       clk,
    input  wire       ena,
    input  wire       rst_n,
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe
);
    
    wire ref_signal = ui_in[0];
    wire dco_signal;

    wire signed [15:0] phase_err;
    wire               edge_valid;

    // ---------------------------------------------------------
    // Phase-Frequency Detector
    // ---------------------------------------------------------
    phase_detector #(
        .OUT_WIDTH(16),
        .ERR_STEP(16'sd256)
    ) u_pd (
        .clk        (clk),
        .reset_n    (rst_n),
        .ref_in     (ref_signal),
        .dco_in     (dco_signal),
        .phase_err  (phase_err),
        .edge_valid (edge_valid)
    );

    // ---------------------------------------------------------
    // Loop Filter
    // ---------------------------------------------------------
    wire signed [23:0] lf_out;
    
    loop_filter #(
        .IN_WIDTH (16),
        .OUT_WIDTH(24),
        .K_P      (4),
        .I_SHIFT  (3)
    ) u_lf (
        .clk         (clk),
        .reset_n     (rst_n),
        .update_en   (edge_valid & ena),
        .phase_in    (phase_err),
        .control_out (lf_out)
    );

    // ---------------------------------------------------------
    // DCO Control
    // ---------------------------------------------------------
    localparam integer CTRL_BITS   = 20;
    localparam integer PHASE_BITS  = 24;
    // Explicitly size the constant to match the addition width (21 bits: 20 bits + sign)
    localparam signed [CTRL_BITS:0] DCO_BASE = 21'sd335544;

    wire signed [CTRL_BITS:0] ctrl_delta = lf_out[23 -: (CTRL_BITS+1)];
    
    // Both operands are now 21 bits
    wire signed [CTRL_BITS:0] dco_sum = DCO_BASE + ctrl_delta;

    wire [CTRL_BITS-1:0] dco_ctrl =
        (dco_sum < 0)                        ? {CTRL_BITS{1'b0}} :
        (dco_sum > ((1<<CTRL_BITS)-1))       ? {CTRL_BITS{1'b1}} :
                                               dco_sum[CTRL_BITS-1:0];

    dco #(
        .CTRL_BITS (CTRL_BITS),
        .PHASE_BITS(PHASE_BITS)
    ) u_dco (
        .clk       (clk),
        .reset_n   (rst_n),
        .ctrl_word (dco_ctrl),
        .dco_out   (dco_signal)
    );

    // ---------------------------------------------------------
    // TRUE LOCK DETECTOR (Leaky Bucket)
    // ---------------------------------------------------------
    reg [10:0] lock_bucket;
    reg        lock_reg;

    // Explicitly size constants to match the 11-bit bucket
    localparam [10:0] BUCKET_MAX    = 11'd2000;
    localparam [10:0] LOCK_THRESH   = 11'd1500;
    localparam [10:0] UNLOCK_THRESH = 11'd1000;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lock_bucket <= 0;
            lock_reg    <= 0;
        end else if (ena) begin
            if (!edge_valid) begin
                // No Error: Fill bucket (+1)
                if (lock_bucket < BUCKET_MAX)
                    lock_bucket <= lock_bucket + 1'b1;
            end else begin
                // Error Detected: Drain bucket (-4)
                if (lock_bucket >= 11'd4)
                    lock_bucket <= lock_bucket - 11'd4;
                else
                    lock_bucket <= 0;
            end

            // Schmitt Trigger
            if (lock_bucket > LOCK_THRESH)
                lock_reg <= 1'b1;
            else if (lock_bucket < UNLOCK_THRESH)
                lock_reg <= 1'b0;
        end
    end

    assign uo_out = {6'b0, dco_signal, lock_reg};
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

    // MOVED: Keep this at the end so all signals are defined before use
    wire _unused = &{ui_in[7:1], uio_in, lf_out[2:0]};

endmodule
