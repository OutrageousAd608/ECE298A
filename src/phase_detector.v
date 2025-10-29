`timescale 1ns/1ps
module phase_detector #(
    parameter OUT_WIDTH = 32
) (
    input  wire clk,
    input  wire reset_n,
    input  wire ref_in,
    input  wire dco_in,
    output reg signed [OUT_WIDTH-1:0] phase_err
);

reg ref_d1, ref_d2;
reg dco_d1, dco_d2;
wire ref_rise;
wire dco_rise;

assign ref_rise = (ref_d1 & ~ref_d2);
assign dco_rise = (dco_d1 & ~dco_d2);

always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        ref_d1 <= 0;
        ref_d2 <= 0;
        dco_d1 <= 0;
        dco_d2 <= 0;
        phase_err <= 0;
    end else begin
        ref_d1 <= ref_in;
        ref_d2 <= ref_d1;
        dco_d1 <= dco_in;
        dco_d2 <= dco_d1;

        if (ref_rise && !dco_rise)
            phase_err <= 32'sd8;
        else if (dco_rise && !ref_rise)
            phase_err <= -32'sd8;
        else begin
            if (phase_err > 0)
                phase_err <= phase_err - 1;
            else if (phase_err < 0)
                phase_err <= phase_err + 1;
        end
    end
end

endmodule
