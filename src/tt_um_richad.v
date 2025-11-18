`timescale 1ns/1ps
module tt_um_richad (
    input  wire       clk,       // TT system clock
    input  wire       ena,       // TT global enable (can be ignored)
    input  wire       rst_n,     // TT asynchronous active-low reset
    input  wire [7:0] ui_in,     // TinyTapeout user input pins
    output wire [7:0] uo_out,    // TinyTapeout dedicated outputs
    input  wire [7:0] uio_in,    // TinyTapeout bidirectional input path
    output wire [7:0] uio_out,   // TinyTapeout bidirectional output path
    output wire [7:0] uio_oe     // TinyTapeout bidirectional output enable path
);

    // ===================================================
    // Internal signals
    // ===================================================
    wire ref_signal;
    wire dco_signal;
    wire locked_signal;

    // Map user input bit 0 as reference input for ADPLL
    assign ref_signal = ui_in[0];

    // ===================================================
    // ADPLL instantiation
    // ===================================================
    wire signed [31:0] pd_val;
    // Removed unused wire dco_ctrl
    wire [31:0] lf_out;

    phase_detector #(.OUT_WIDTH(32)) pd (
        .clk(clk),
        .reset_n(rst_n),
        .ref_in(ref_signal),
        .dco_in(dco_signal),
        .phase_err(pd_val)
    );

    loop_filter #(.IN_WIDTH(32), .OUT_WIDTH(32), .K_P(8)) lf (
        .clk(clk),
        .reset_n(rst_n),
        .phase_in(pd_val),
        .control_out(lf_out)
    );

    dco #(.CTRL_BITS(10), .PHASE_BITS(15)) my_dco ( // FIX: PHASE_BITS set to 15
        .clk(clk),
        .reset_n(rst_n),
        .ctrl_word(lf_out[9:0]),
        .dco_out(dco_signal)
    );

    // ===================================================
    // Lock detection
    // ===================================================
    parameter LOCK_THRESH = 20;
    reg [$clog2(LOCK_THRESH+1)-1:0] lock_cnt;
    reg lock_reg;
    
    parameter LOCK_WINDOW = 32'sd256; 

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            lock_cnt <= 0;
            lock_reg <= 1'b0;
        end else begin
            // Check if phase error is within the acceptable window
            if ($signed(pd_val) < LOCK_WINDOW && $signed(pd_val) > -LOCK_WINDOW) begin
                if (lock_cnt < LOCK_THRESH) lock_cnt <= lock_cnt + 1;
            end else begin
                lock_cnt <= 0;
            end
            lock_reg <= (lock_cnt >= (LOCK_THRESH-1));
        end
    end

    assign locked_signal = lock_reg;

    // ===================================================
    // Map internal signals to TinyTapeout outputs
    // ===================================================
    // uo_out[0] = lock indicator
    // uo_out[1] = DCO output
    assign uo_out = {6'b0, dco_signal, locked_signal};

    // Leave all bidirectional IOs unused for now
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

endmodule
