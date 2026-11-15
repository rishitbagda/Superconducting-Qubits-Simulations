`timescale 1ns/1ps
// New board adapter only. original/jj_rcsj.sv is used without modification.
module nexys4ddr_top(
    input wire CLK100MHZ, input wire BTNC,
    input wire [15:0] SW,
    output wire [15:0] LED, output wire [6:0] SEG,
    output wire DP, output wire [7:0] AN
);
    wire clk_in, clk_fb, clk_fb_buf, clk_10_raw, clk_10, locked;
    IBUF input_buffer(.I(CLK100MHZ), .O(clk_in));
    MMCME2_BASE #(
        .CLKIN1_PERIOD(10.0), .CLKFBOUT_MULT_F(10.0),
        .DIVCLK_DIVIDE(1), .CLKOUT0_DIVIDE_F(100.0),
        .STARTUP_WAIT("FALSE")
    ) clock_manager (
        .CLKIN1(clk_in), .CLKFBIN(clk_fb_buf), .CLKFBOUT(clk_fb),
        .CLKOUT0(clk_10_raw), .LOCKED(locked), .PWRDWN(1'b0), .RST(BTNC),
        .CLKFBOUTB(), .CLKOUT0B(), .CLKOUT1(), .CLKOUT1B(),
        .CLKOUT2(), .CLKOUT2B(), .CLKOUT3(), .CLKOUT3B(),
        .CLKOUT4(), .CLKOUT5(), .CLKOUT6()
    );
    BUFG feedback_buffer(.I(clk_fb), .O(clk_fb_buf));
    BUFG model_clock_buffer(.I(clk_10_raw), .O(clk_10));
    jj_board_ui ui(.clk(clk_10), .reset_async(BTNC | ~locked),
                   .sw(SW), .led(LED), .seg(SEG), .dp(DP), .an(AN));
endmodule
