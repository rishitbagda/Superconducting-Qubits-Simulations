`timescale 1ns/1ps

// Overdamped/underdamped RCSJ Josephson junction, normalized units.
// One integration step of size DT per clock when en=1.
module jj_rcsj #(
    parameter real DT     = 1.0/64.0,  // normalized time step
    parameter real BETA_C = 4.0        // Stewart-McCumber parameter
)(
    input  logic               clk,
    input  logic               rst,
    input  logic               en,
    input  logic signed [31:0] i_bias, // Q8.24, units of Ic
    output logic        [31:0] theta,  // phase in turns, Q0.32 (phi = 2*pi*theta/2^32)
    output logic signed [31:0] v_out   // Q8.24, units of Ic*R  (= dphi/dt)
);

    // Constants (evaluated at elaboration)
    localparam int K_THETA = $rtoi(DT/(2.0*3.14159265358979)*256.0*65536.0); // Q.16
    localparam int G       = $rtoi(DT/BETA_C*65536.0);                        // Q.16

    // Sine LUT: 1024 entries over one full turn, Q8.24
    logic signed [31:0] sin_rom [0:1023];

    initial begin
        for (int k = 0; k < 1024; k++) begin
            sin_rom[k] = $rtoi($sin(2.0*3.14159265358979*k/1024.0) * 16777216.0);
        end
    end

    // Combinational logic variables
    logic signed [31:0] s;
    logic signed [31:0] force1;
    logic signed [63:0] dw_full;
    logic signed [31:0] omega_n;
    logic signed [63:0] dth_full;
    logic signed [31:0] dth;

    // Semi-implicit Euler integration block
    always_comb begin
        s       = sin_rom[theta[31:22]];             // Top 10 bits index the LUT directly
        force1   = i_bias - v_out - s;                
        dw_full = force1 * $signed(G);                // Q16 math extension
        omega_n = v_out + dw_full[47:16];            // Update velocity first
        
        dth_full = omega_n * $signed(K_THETA);       // Use new velocity for position
        dth      = dth_full[47:16];
    end

    // Sequential logic block
    always_ff @(posedge clk) begin
        if (rst) begin
            theta <= '0;
            v_out <= '0;
        end else if (en) begin
            v_out <= omega_n;
            theta <= theta + dth;  // Two's-complement add naturally wraps phase at 2PI
        end
    end

endmodule