# Josephson junction model — Nexys 4 DDR adapter

This folder adds a board interface to your friend's two-file SystemVerilog project.
**Both original files are byte-for-byte unchanged, including line endings.**
No mathematical fixes, parameter changes, replacement sine tables, or edits to the
original testbench have been made. New RTL is confined to `board/`.

## Status — read this first

- Original model + original testbench: executed using Icarus Verilog 11.0; 82
  measured I–V points produced. The result exhibits hysteresis.
- New UI: simulated successfully for reset, input conversion/clamping, advancing
  state, pausing state, page selection and full-frame display capture.
- Original files: compared directly with the uploaded ZIP and SHA-256 verified.
- Vivado synthesis, placement, routing, timing closure and bitstream generation:
  **not run here** because Vivado is unavailable.
- Physical Nexys 4 DDR: **not tested here**. There is no prebuilt `.bit` file.

This is a board-targeted source project, not a claim of a verified hardware build.
Use the included build script to obtain the bitstream on your Vivado installation.
If synthesis rejects an original construct, retain the log; the source-preservation
requirement takes priority over silently changing your friend's code.

## What is in the folder?

| Path | Purpose |
|---|---|
| `original/jj_rcsj.sv` | Unchanged numerical Josephson junction model |
| `original/tb_jj.sv` | Unchanged current sweep and average-voltage testbench |
| `board/nexys4ddr_top.sv` | 100 MHz input, MMCM/BUFG 10 MHz model clock, physical ports |
| `board/jj_board_ui.sv` | Switch interface, run/pause, snapshots, LEDs and hex display |
| `constraints/nexys4ddr.xdc` | Nexys 4 DDR pin assignments and clock constraints |
| `scripts/create_project.tcl` | Creates the Vivado project for xc7a100tcsg324-1 |
| `scripts/build_bitstream.tcl` | Synthesis, routing, timing reports and bitstream |
| `scripts/run_original_sim.tcl` | Runs the unchanged testbench in Vivado |
| `scripts/run_board_ui_sim.tcl` | Runs the additional UI verification in Vivado |
| `verification/` | Tests, preserved-source hashes, actual simulator log and CSV |
| `docs/EXPLANATION.md` | Physics, equations, fixed-point math, code walkthrough and limitations |
| `docs/original_iv_curve.png` | Plot of the actual original SystemVerilog simulation |

## Create and build in Vivado (Windows or Linux)

1. Extract the whole ZIP, for example to `C:/FPGA/Nexys4DDR_Josephson_Unmodified`.
   Keep the folder structure. Do not run files from inside the ZIP.
2. Open Vivado with Artix-7 device support installed. Close any other open project.
3. Open **Window → Tcl Console**. Run this, using your actual path and forward slashes:

   ```tcl
   source {C:/FPGA/Nexys4DDR_Josephson_Unmodified/scripts/create_project.tcl}
   ```

4. The script creates `build/vivado/jj_nexys4ddr.xpr`. You can open this `.xpr`
   directly on later visits. No Digilent board-file installation is required:
   the project targets the exact FPGA part and uses an XDC.
5. To synthesize, implement and write the programming file, run:

   ```tcl
   source {C:/FPGA/Nexys4DDR_Josephson_Unmodified/scripts/build_bitstream.tcl}
   ```

   Alternatively, from a Vivado command prompt in the extracted root:

   ```text
   vivado -mode batch -source scripts/build_bitstream.tcl
   ```

6. Read the console. The script stops on synthesis/implementation failure or
   negative setup/hold slack. Timing, utilization, clock and DRC reports are in
   `build/reports/`. Successful output is `build/nexys4ddr_jj.bit`.
7. Connect and power the board using its programming USB connection. In Vivado,
   select **Open Hardware Manager → Open Target → Auto Connect → Program Device**.
   Select `build/nexys4ddr_jj.bit`. This loads volatile configuration; after a power
   cycle, program it again. No flash programming is included.

Do not use `tb_jj` as the hardware top: it contains simulation delays, real-number
sweep loops and `$display`, not a physical input/output interface. The hardware
top is `nexys4ddr_top`. The original simulation top is `tb_jj`.

## Board controls

The eight digits show a **32-bit hexadecimal word**, not a decimal voltage.
DP is off. Read left to right, most significant digit first.

| Control | Meaning |
|---|---|
| BTNC, centre button | Reset model and step counter; restarts clock lock |
| SW15 = 0 | Pause; preserve phase, voltage and step count |
| SW15 = 1 | Run at 10,000 numerical steps per real second |
| SW5:0 | Unsigned integer N; current = min(N,32)/16 × Ic |
| SW14:13 = 00 | Instantaneous model voltage, signed Q8.24 |
| SW14:13 = 01 | Phase, unsigned Q0.32 turns |
| SW14:13 = 10 | Applied current, signed Q8.24 |
| SW14:13 = 11 | Number of completed model steps, unsigned hex |
| SW12:6 | Unused |

LED15 indicates run; LED14:13 indicate the selected page; LED12 indicates reset
released; LED11 toggles every 4096 model steps; LED5:0 show the clamped current
code. LED10:6 are off. LED12 is a readiness indication, not a scientific-validity flag.

Examples for SW5:0, written SW5 down to SW0:

| Switch bits | N | Current / Ic | Current-page display |
|---|---:|---:|---|
| 000000 | 0 | 0 | 00000000 |
| 001000 | 8 | 0.5 | 00800000 |
| 010000 | 16 | 1.0 | 01000000 |
| 011000 | 24 | 1.5 | 01800000 |
| 100000 | 32 | 2.0 | 02000000 |

Pause before changing multiple current switches; allow about 0.2 seconds for the
display to update, then resume. The switches are synchronized per bit, not
atomically latched or mechanically debounced. Pause avoids applying intermediate
current codes while your hand changes several switches. Preserve state by pausing,
not resetting, if you want to explore history dependence.

## First board demonstration

1. Start with all switches down; press and release BTNC. LED12 should come on after
   clock lock and reset release. On voltage page the display should be zero.
2. With SW15 down, set SW4=1 and SW3=1 (current code 24 = 1.5 Ic).
3. Set SW14=1, SW13=0 to inspect the input page. Expect `01800000`.
4. Return SW14=0, SW13=0; set SW15=1. Voltage should evolve to nonzero values.
5. Select page 11 (SW14=SW13=1). The numerical step counter should advance.
6. Set SW15=0. After the display refreshes, the counter and computed state should
   stop changing. Pages remain usable while paused.
7. On page 01 inspect phase. Divide its unsigned word by 2^32 to obtain turns.
   On voltage page interpret the word as signed two's complement and divide by
   2^24. For example `01800000` means +1.5 in normalized units.

The board display is an instantaneous sample, updated at about 10 Hz. It does
**not** perform the original testbench's 8000-sample average or automatic 0.05-Ic
sweep. Display flicker is therefore not itself a bug. Use simulation for the
quantitative I–V curve. No analog voltage output, DAC, UART or cryogenic junction
is present. DDR memory is not needed.

## Run the original experiment

After creating/opening the Vivado project, source `scripts/run_original_sim.tcl`.
It runs until `$finish`; expected simulated duration is about 13.12 ms, not the
default short GUI run interval. The Tcl simulator console prints `i_bias,<v>` and
41 upward plus 41 downward points. Inspect `i_bias`, `theta`, `v_out` and internal
`dut.s`, `dut.force1`, `dut.omega_n`, `dut.dth` in the waveform viewer.

Close the active simulation before starting the other testbench. Source
`scripts/run_board_ui_sim.tcl` for the adapter checks. These checks use a faster
enable divider to reduce simulation runtime; the delivered hardware uses 1000.

If Icarus Verilog is installed in PATH, run `python verification/run_checks.py`.
Python is only a test launcher; the project implementation is SystemVerilog.

## Caveats that have deliberately not been fixed

- Original testbench reset and current changes occur at clock edges. These can
  race with the DUT in event-driven simulation; sampling is also before the
  nonblocking update on each edge. Its successful run is not race-free sign-off.
- Original `$sin`/`$rtoi` ROM initialization and real-valued parameters are
  elaboration-time constructs; there is no runtime floating-point sine unit.
  Their exact synthesis treatment must be checked in your Vivado version.
- The model truncates arithmetic, quantizes phase to 1024 sine samples and wraps
  finite-width values; it contains no general overflow/saturation protection.
- No physical Ic, R or C values were supplied. Results are dimensionless;
  absolute amperes, volts and physical junction time cannot be assigned uniquely.
- There is no claim of comparison with measured Josephson-junction data,
  broad numerical convergence verification, or hardware performance advantage.

See `docs/EXPLANATION.md` for the complete interpretation and the actual results.
