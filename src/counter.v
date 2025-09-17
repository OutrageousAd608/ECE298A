/*
    * 8-bit Programmable Counter with Synchronous Load and Tri-State Outputs
    * Richard Dong, 2025
*/

`default_nettype none

module tt_um_counter (
    input  wire [7:0] ui_in,    // Dedicated inputs (load value)
    output wire [7:0] uo_out,   // Dedicated outputs (counter value, tri-stated when !ena)
    input  wire [7:0] uio_in,   // IOs: Input path (uio_in[0] used for load enable)
    output wire [7:0] uio_out,  // IOs: Output path (unused)
    output wire [7:0] uio_oe,   // IOs: Enable path (unused)
    input  wire       ena,      // Global enable from TinyTapeout
    input  wire       clk,      // Clock
    input  wire       rst_n     // Reset (active low)
);

    // Internal counter register
    reg [7:0] count;

    // Load logic
    wire [7:0] load_value;
    wire       load_enable;

    assign load_value  = ui_in;
    assign load_enable = uio_in[0];

    // Counter logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 8'b0;
        end else if (load_enable) begin
            count <= load_value;
        end else if (ena) begin
            count <= count + 1;
        end
    end

    // Tri-state output logic
    assign uo_out  = ena ? count : 8'bz;

    // Unused outputs set to zero
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

endmodule
