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

// --- Synchronization for Asynchronous Input (ref_in) ---
// Two-flip-flop synchronizer to handle metastability from external ref_in
reg ref_sync_d1;
reg ref_sync_d2;
wire ref_in_synced;
assign ref_in_synced = ref_sync_d2; // The stable, synchronized reference signal

// --- Edge Detection Registers ---
// Ref Path: ref_sync_d2 -> ref_d1 -> ref_d2 (4 cycles total delay before ref_rise pulse)
reg ref_d1, ref_d2; 
// DCO Path: dco_in -> dco_d1 -> dco_d2 -> dco_d3 -> dco_d4 (4 cycles total delay to match Ref)
reg dco_d1, dco_d2, dco_d3; 
reg dco_d4; // Added DFF to match the 4-cycle latency of the Ref path

wire ref_rise;
wire dco_rise;

// Edge detection logic: Detects 0 -> 1 transition
assign ref_rise = (ref_d1 & ~ref_d2); // Uses 2 stages of detection (4-cycle latency total)
assign dco_rise = (dco_d3 & ~dco_d4); // Uses 2 stages of detection on a 4-stage delayed signal

always @(posedge clk or negedge reset_n) begin
    if (!reset_n) begin
        // Reset Synchronizer
        ref_sync_d1 <= 0;
        ref_sync_d2 <= 0;
        
        // Reset Ref Edge Detectors
        ref_d1 <= 0;
        ref_d2 <= 0;
        
        // Reset DCO Edge Detectors
        dco_d1 <= 0;
        dco_d2 <= 0;
        dco_d3 <= 0; 
        dco_d4 <= 0; // Reset for the newly added register
        
        // Reset Output
        phase_err <= 0;
    end else begin
        // 1. Synchronize the external reference input (ref_in)
        ref_sync_d1 <= ref_in;
        ref_sync_d2 <= ref_sync_d1;

        // 2. Perform edge detection on the synchronized signal (ref_in_synced)
        ref_d1 <= ref_in_synced;
        ref_d2 <= ref_d1;
        
        // 3. Perform edge delay and detection on the DCO input
        // Added stage dco_d4 to match the 4-cycle latency of the ref_in path
        dco_d1 <= dco_in;
        dco_d2 <= dco_d1;
        dco_d3 <= dco_d2; 
        dco_d4 <= dco_d3; // New delay stage
        
        // 4. Phase Error Calculation
        if (ref_rise && dco_rise)
            // Explicitly handle simultaneous edges: Phase Error is 0
            phase_err <= 0;
        else if (ref_rise)
            // Reference leads DCO (needs to speed up DCO)
            phase_err <= 32'sd8;
        else if (dco_rise)
            // DCO leads Reference (needs to slow down DCO)
            phase_err <= -32'sd8;
        else begin
            // Leak/drift toward zero when no edges are detected
            if (phase_err > 0)
                phase_err <= phase_err - 1;
            else if (phase_err < 0)
                phase_err <= phase_err + 1;
        end
    end
end

endmodule
