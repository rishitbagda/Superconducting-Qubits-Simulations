# What your friend's project is doing

## 1. The objective visible in the files

The upload contains one computational module (`jj_rcsj.sv`) and one simulation
testbench (`tb_jj.sv`). Together, they implement a fixed-point numerical model of
a single current-biased Josephson junction and measure its current–voltage
characteristic. The chosen capacitance/damping parameter permits hysteresis.
This interpretation comes directly from the equations, input sweep and comments;
the files do not establish any larger intended application such as a qubit,
Josephson computer, neuron or superconducting logic gate.

SystemVerilog describes digital hardware that evolves numbers representing a
junction. Running it on the Nexys FPGA makes a digital emulator. It does not turn
the FPGA into a superconducting device or physically reproduce tunnelling.

## 2. What a Josephson junction is

A Josephson junction couples two superconductors through a weak link, often a
very thin insulating barrier. Below suitable operating temperatures, paired
electrons can carry a supercurrent across it. Each superconductor has a collective
quantum phase; the difference between those phases is phi. Phase is an angular
state variable: adding 2*pi returns to the same position in its periodic
current–phase relationship. It is not simply the phase of an externally applied
sinusoidal source.

The ideal junction supercurrent is

    I_s = I_c sin(phi)

where I_c is its critical current. The voltage is related to the rate of phase
change by

    V = (hbar / 2e) dphi/dt.

Thus a stationary phase permits a supercurrent at zero voltage. A continually
changing phase produces voltage. These two statements explain why the code must
track both phase and voltage rather than implement a fixed resistance V = IR.

For example, with a steady applied current of 0.5 I_c, a stationary phase of
pi/6 can supply that current because sin(pi/6)=0.5. The ideal zero-voltage branch
has a possible equilibrium. For current above I_c, no stationary phase can make
sin(phi) exceed 1, so this stationary balance cannot hold.

## 3. Why there is an R and C in the model

RCSJ means resistively and capacitively shunted junction. The equivalent model has
an ideal Josephson element, a resistor and a capacitor in parallel. Their shared
voltage is V, and the applied current divides among them:

    I_bias = I_c sin(phi) + V/R + C dV/dt.

The first term is the supercurrent, the second dissipates energy, and the third
charges the capacitance. Rearranging this equation tells us how the voltage
changes when the applied current is not balanced by the other two currents.

Capacitance gives the phase dynamics inertia: after the junction enters a running
phase state, it may continue running as the current is reduced below the initial
switching current. Resistance damps that motion. This is the origin of the
hysteresis explored by the testbench. A useful mathematical analogy is a driven,
damped pendulum: phase is angle, voltage is angular velocity, applied current is
drive, sine is restoring force and the resistor gives damping. The analogy
describes the equations, not a physical moving pendulum inside the junction.

## 4. Normalized equations used by this code

Define i = I_bias/I_c, v = V/(I_c R), and normalized time

    tau = (2e I_c R / hbar) t.
    beta_c = 2e I_c R^2 C / hbar.

The equations become

    dphi/dtau = v
    dv/dtau = (i - v - sin(phi)) / beta_c.

The default BETA_C is 4. The corresponding damping coefficient in the alternative
plasma-frequency normalization is 1/sqrt(beta_c)=0.5, an underdamped case.
Do not confuse these two normalizations when comparing equations in papers.

No particular material, temperature, critical current, resistor or capacitor is
specified. The parameter fixes a dimensionless combination, not a unique device.
For example an output v=1.5 means V=1.5 I_c R, not necessarily 1.5 volts.

## 5. How the differential equation becomes a circuit

The code uses a time step DT = 1/64 in normalized time. It updates the voltage
first and uses that new voltage to update phase (semi-implicit Euler):

    v_next   = v + (DT/beta_c) * (i - v - sin(phi))
    phi_next = phi + DT * v_next.

The FPGA has registers that hold current phase and voltage, combinational logic
that calculates the next values, and a clock edge that commits them. Reset clears
both registers. If en is zero, the old state is retained. Each enabled clock edge
advances the numerical model by one DT, regardless of the wall-clock spacing of
those enabled edges.

The original testbench enables every 100 MHz simulation clock edge. The new board
adapter clocks the core at 10 MHz and enables one update in 1000 cycles, giving
10,000 steps per second. This changes the demonstration's wall-clock speed; the
original recurrence and its DT are unchanged. Running at a lower physical clock
also gives the unpipelined arithmetic path more timing margin, but only Vivado
timing analysis can establish closure.

## 6. Fixed-point representation and every arithmetic signal

`i_bias`, `v_out` and sine values are signed 32-bit integers with 24 fractional
bits (Q8.24, counting the sign among the eight upper bits). Decode by dividing
the signed integer by 16,777,216. The representable range is -128 to just below
+128. Thus 1.0 is `0x01000000`, 0.5 is `0x00800000`, and -1.0 is `0xFF000000`.

`theta` is different: it stores phase in unsigned Q0.32 turns. A full turn is
2^32 counts and automatically wraps on overflow. `0x40000000` is one quarter
turn (pi/2 radians), `0x80000000` is half a turn, and `0xC0000000` is three quarters.

The top ten phase bits select one of 1024 precomputed sine samples. For example,
at a quarter turn the index is 256 and the sine is approximately +1. This avoids
calculating a transcendental function every cycle. The `initial` loop asks the
tool to calculate the table's constants before the model starts.

| Signal | Calculation / meaning |
|---|---|
| `s` | Sine-table value at the current phase |
| `force1` | Applied current minus resistive current minus supercurrent |
| `G` | Integer representation of DT/beta_c with 16 fractional bits |
| `dw_full` | 64-bit product of force1 and G |
| `omega_n` | Current voltage plus the rescaled voltage increment |
| `K_THETA` | Conversion from Q8.24 voltage to Q0.32 phase increment, with 16 extra fractional bits |
| `dth_full` | 64-bit product of new voltage and K_THETA |
| `dth` | Rescaled phase increment |
| `theta` | Accumulated phase, wrapped modulo one turn |

Why is there a factor 256 in K_THETA? The voltage integer scales with 2^24 but
the phase integer scales with 2^32. Their ratio is 2^8 = 256. Converting radians
to turns also requires division by 2*pi. Therefore

    delta_theta_integer = v_integer * DT * 256 / (2*pi).

The code stores that coefficient multiplied by 65536, multiplies it by the
voltage, then selects product bits [47:16] to remove those extra 16 fractional
bits. The same rescaling technique is used in the voltage update.

With the defaults, G=256 and K_THETA=41721 (truncated). Truncation and table
quantization introduce approximation error. Phase wrapping is intentional;
voltage overflow would not represent a physical junction correctly.

## 7. What the original testbench does

It starts from zero state, applies current values 0, 0.05, 0.10, ..., 2.0 I_c,
and for each current waits 8000 steps before averaging voltage for 8000 further
steps. It then sweeps back from 2.0 to 0 in the same increments. It deliberately
keeps the model state between current points and between sweep directions.

The waiting interval is intended to reduce transient influence. The average is
useful because the voltage can oscillate while its long-term mean is nonzero.
The resulting table is an I–V curve: applied current on the horizontal axis,
mean voltage on the vertical axis. Retaining state lets the descending branch
differ from the ascending branch, revealing hysteresis.

## 8. Actual result from the uploaded, unchanged SV

The included log was produced by Icarus Verilog 11.0, not by a replacement Python
model. The CSV is extracted from that log; the PNG is a plot of the CSV values.

| Current / Ic | Mean voltage on upward sweep / IcR | Mean voltage on downward sweep / IcR |
|---:|---:|---:|
| 0.50 | 0.00000 | -0.00000 |
| 0.60 | 0.00000 | 0.29917 |
| 0.80 | -0.00000 | 0.74094 |
| 1.00 | 0.00003 | 0.96720 |
| 1.05 | 1.02594 | 1.02648 |
| 1.50 | 1.49139 | 1.49236 |
| 2.00 | 1.99549 | 1.99645 |

On the sampled upward sweep the running-voltage state appears at 1.05 Ic; on the
downward sweep it persists at 0.60 Ic and is approximately zero at 0.55 Ic.
These are sampled observations, not precise estimates of switching/retrapping
thresholds. The step size is 0.05 Ic, integration is approximate, and the averaging
window is finite. Tiny values printed as negative zero are rounding artefacts.

At 0.8 Ic the same input yields two different average outputs because the
junction arrived there with a different state. That is the central result.

## 9. What this project demonstrates and what remains

It is a meaningful implementation of a nonlinear dynamical model: the FPGA can
calculate a junction's response by updating its state rather than looking up a
final answer for each bias current. Intermediate sine, force, voltage increment
and phase increment are visible in simulation. The new board step counter and
state pages expose basic operation directly.

However, an I–V hysteresis curve alone does not validate all physical regimes,
prove speed/resource advantages over other implementations, or establish a qubit
or superconducting logic system. Such claims require additional specifications,
comparisons, convergence tests and, for device accuracy, physical data.

The preserved testbench has event-ordering concerns: reset and bias can change
on the same rising edge that the DUT samples them, and the average is accumulated
before the edge's nonblocking assignments commit. Those should be reviewed in a
future revision. No change was made here. Finite-width overflow, parameter
validity, numerical stability and synthesis of the elaboration-time ROM are
also review items; their existence does not mean the successful sweep failed.

## Sources for background and board mapping

The code-specific explanation and reported numbers come from the uploaded files
and the included actual simulation log. External sources are supporting context:

- Digilent Nexys 4 DDR manual (FPGA part and 100 MHz clock):
  https://digilent.com/reference/_media/nexys4-ddr%3Anexys4ddr_rm.pdf
- Digilent master XDC (pin locations, including 1.8 V SW8 and SW9):
  https://github.com/Digilent/digilent-xdc/blob/master/Nexys-4-DDR-Master.xdc
- AMD MMCME2_BASE documentation (clock-manager primitive):
  https://docs.amd.com/r/en-US/ug953-vivado-7series-libraries/MMCME2_BASE
- SCE Futures, Josephson Junctions (Josephson relations and RCSJ background):
  https://adiabatic-machines.github.io/sce-futures/notebooks/03_josephson_junctions/
- Research example using the RCSJ current decomposition:
  https://www.nature.com/articles/s41467-025-60569-9
