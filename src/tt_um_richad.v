`timescale 1ns/1ps

module tt_um_richad (
    input  wire       clk,       // 50 MHz system clock
    input  wire       ena,
    input  wire       rst_n,
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe
);

    // Reference comes in on bit 0
    wire ref_signal = ui_in[0];
    wire dco_signal;

    // Phase detector outputs
    wire signed [15:0] phase_err;
    wire               edge_valid;

    phase_detector #(
        .OUT_WIDTH(16),
        .ERR_STEP(16'sd1)
    ) u_pd (
        .clk        (clk),
        .reset_n    (rst_n),
        .ref_in     (ref_signal),
        .dco_in     (dco_signal),
        .phase_err  (phase_err),
        .edge_valid (edge_valid)
    );

    // Loop filter
    wire signed [23:0] lf_out;

    loop_filter #(
        .IN_WIDTH (16),
        .OUT_WIDTH(24),
        .K_P      (4),
        .I_SHIFT  (4)
    ) u_lf (
        .clk         (clk),
        .reset_n     (rst_n),
        .update_en   (edge_valid & ena),
        .phase_in    (phase_err),
        .control_out (lf_out)
    );

    // ---------------------------------------------------------
    // DCO control mapping (this is already working)
    // ---------------------------------------------------------
    localparam integer CTRL_BITS   = 20;
    localparam integer PHASE_BITS  = 24;
    localparam integer DCO_BASE    = 335544; // about 1 MHz increment

    // Take UPPER bits of loop filter output as signed delta
    // (bits [23:3] → 21 bits total for CTRL_BITS=20)
    wire signed [CTRL_BITS:0] ctrl_delta =
        lf_out[23 -: (CTRL_BITS+1)];

    // Signed sum: base + correction
    wire signed [CTRL_BITS:0] dco_sum =
        $signed(DCO_BASE) + ctrl_delta;

    // Saturate into 0 .. (2^CTRL_BITS - 1)
    wire [CTRL_BITS-1:0] dco_ctrl =
        (dco_sum < 0)                        ? {CTRL_BITS{1'b0}} :
        (dco_sum > ((1<<CTRL_BITS)-1))       ? {CTRL_BITS{1'b1}} :
                                               dco_sum[CTRL_BITS-1:0];

    // DCO instance
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
    // NEW lock detector: based on dco_ctrl staying near DCO_BASE
    // ---------------------------------------------------------
    localparam [CTRL_BITS-1:0] LOCK_WIN    = 20'd64;   // +/- 64 around base
    localparam integer         LOCK_COUNT  = 64;       // edges needed for lock

    wire [CTRL_BITS-1:0] lower_bound = DCO_BASE - LOCK_WIN;
    wire [CTRL_BITS-1:0] upper_bound = DCO_BASE + LOCK_WIN;
    wire                 in_window   = (dco_ctrl >= lower_bound) &&
                                       (dco_ctrl <= upper_bound);

    reg [7:0] lock_cnt;
    reg       lock_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lock_cnt <= 8'd0;
            lock_reg <= 1'b0;
        end else if (edge_valid & ena) begin
            // integrate "good" edges vs "bad"
            if (in_window) begin
                if (lock_cnt != 8'hFF)
                    lock_cnt <= lock_cnt + 8'd1;
            end else begin
                if (lock_cnt != 8'd0)
                    lock_cnt <= lock_cnt - 8'd1;
            end

            lock_reg <= (lock_cnt >= LOCK_COUNT);
        end
    end

    // ---------------------------------------------------------
    // Outputs
    // ---------------------------------------------------------
    // uo_out[0] = locked, uo_out[1] = dco
    assign uo_out = {6'b0, dco_signal, lock_reg};

    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

endmodule
