"""Fluxonium qubit simulation using scqubits.

This is an effective, lumped-element Fluxonium model. It uses the
scqubits.Fluxonium implementation and does not explicitly diagonalize the
individual junction-array modes or model a fabricated chip layout.

All circuit energies passed to scqubits are expressed as E/h in GHz.
The external flux parameter is expressed in units of Phi_0.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import scqubits as scq
from scipy.constants import elementary_charge, h, hbar


# ---------------------------------------------------------------------------
# Model parameters
# ---------------------------------------------------------------------------
# These are the same reference parameters used in the group's initial
# Fluxonium baseline notebook and in the scqubits documentation example.
EJ_GHZ = 8.9
EC_GHZ = 2.5
EL_GHZ = 0.5
FLUX_BIAS_PHI0 = 0.33
BASIS_CUTOFF = 110
NUMBER_OF_LEVELS = 6

# Numerical studies
FLUX_SWEEP = np.linspace(0.0, 1.0, 101)
PHASE_GRID_MIN = -4.0 * np.pi
PHASE_GRID_MAX = 4.0 * np.pi
PHASE_GRID_POINTS = 501
CUTOFF_VALUES = (80, 90, 100, 110, 120, 130)

# Physical reference design supplied for this project. These values are
# printed as consistency checks; the scqubits Fluxonium object itself uses
# only EJ, EC, EL, flux, and cutoff.
ARRAY_JUNCTION_COUNT = 100
ARRAY_JUNCTION_CRITICAL_CURRENT_A = 100.668e-9
CENTRAL_JUNCTION_CAPACITANCE_F = 0.896e-15
ARRAY_JUNCTION_CAPACITANCE_F = 5.033e-15

DEFAULT_OUTPUT_DIR = Path.home() / "fluxonium_results"


def make_fluxonium(flux_phi0: float) -> scq.Fluxonium:
    """Create a Fluxonium model at the requested external flux bias.

    Args:
        flux_phi0: External magnetic flux in units of Phi_0.

    Returns:
        An scqubits.Fluxonium instance.
    """
    if not np.isfinite(flux_phi0):
        raise ValueError("flux_phi0 must be a finite number")

    return scq.Fluxonium(
        EJ=EJ_GHZ,
        EC=EC_GHZ,
        EL=EL_GHZ,
        flux=float(flux_phi0),
        cutoff=BASIS_CUTOFF,
    )


def physical_parameter_estimates() -> dict[str, float]:
    """Convert the effective scqubits energies to SI circuit estimates.

    scqubits uses GHz for E/h. The resulting capacitance and inductance are
    effective circuit quantities, not a claim that a single physical pad or
    junction has that value.
    """
    phi0_reduced = hbar / (2.0 * elementary_charge)

    EJ_joule = h * EJ_GHZ * 1e9
    EC_joule = h * EC_GHZ * 1e9
    EL_joule = h * EL_GHZ * 1e9

    central_critical_current = EJ_joule / phi0_reduced
    effective_capacitance = elementary_charge**2 / (2.0 * EC_joule)
    superinductance = phi0_reduced**2 / EL_joule

    array_junction_inductance = (
        phi0_reduced / ARRAY_JUNCTION_CRITICAL_CURRENT_A
    )
    array_inductance_from_junctions = (
        ARRAY_JUNCTION_COUNT * array_junction_inductance
    )
    array_junction_EJ_GHz = (
        ARRAY_JUNCTION_CRITICAL_CURRENT_A * phi0_reduced / h / 1e9
    )

    return {
        "reduced_flux_quantum_Wb": phi0_reduced,
        "central_critical_current_A": central_critical_current,
        "effective_capacitance_F": effective_capacitance,
        "superinductance_H": superinductance,
        "array_junction_inductance_H": array_junction_inductance,
        "array_inductance_from_100_junctions_H": array_inductance_from_junctions,
        "array_junction_EJ_GHz": array_junction_EJ_GHz,
    }


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    """Write rows to a CSV file using UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)
        writer.writerows(rows)


def save_figure(fig: plt.Figure, path: Path) -> None:
    """Save a figure at report quality."""
    fig.savefig(path, dpi=250, bbox_inches="tight")


def write_summary(
    output_path: Path,
    energies: np.ndarray,
    n_operator: np.ndarray,
    phi_operator: np.ndarray,
    cutoff_rows: list[list[Any]],
) -> None:
    """Write key numerical outputs and modelling assumptions to a text file."""
    physical = physical_parameter_estimates()
    relative_energies = energies - energies[0]
    f01 = float(relative_energies[1])
    f12 = float(energies[2] - energies[1])
    anharmonicity = f12 - f01

    lines = [
        "FLUXONIUM SIMULATION SUMMARY",
        "============================",
        f"scqubits version: {getattr(scq, '__version__', 'not reported')}",
        "",
        "Effective circuit parameters (E/h in GHz):",
        f"  EJ = {EJ_GHZ:.8g} GHz",
        f"  EC = {EC_GHZ:.8g} GHz",
        f"  EL = {EL_GHZ:.8g} GHz",
        f"  External flux = {FLUX_BIAS_PHI0:.8g} Phi_0",
        f"  Harmonic-oscillator basis cutoff = {BASIS_CUTOFF}",
        "",
        "Energy levels:",
    ]

    for state_index, (absolute_energy, relative_energy) in enumerate(
        zip(energies, relative_energies)
    ):
        lines.append(
            f"  E{state_index}/h = {absolute_energy:.12g} GHz; "
            f"(E{state_index}-E0)/h = {relative_energy:.12g} GHz"
        )

    lines.extend(
        [
            "",
            f"  f01 = {f01:.12g} GHz",
            f"  f12 = {f12:.12g} GHz",
            f"  Anharmonicity (f12 - f01) = {anharmonicity:.12g} GHz",
            f"  |<0|n|1>| = {abs(n_operator[0, 1]):.12g}",
            f"  |<0|phi|1>| = {abs(phi_operator[0, 1]):.12g}",
            "",
            "Physical estimates implied by the effective circuit parameters:",
            f"  Central-junction critical current = "
            f"{physical['central_critical_current_A'] * 1e9:.6f} nA",
            f"  Effective circuit capacitance = "
            f"{physical['effective_capacitance_F'] * 1e15:.6f} fF",
            f"  Superinductance from EL = "
            f"{physical['superinductance_H'] * 1e9:.6f} nH",
            f"  Array-junction inductance (reference Ic) = "
            f"{physical['array_junction_inductance_H'] * 1e9:.6f} nH",
            f"  Inductance of {ARRAY_JUNCTION_COUNT} ideal series array junctions = "
            f"{physical['array_inductance_from_100_junctions_H'] * 1e9:.6f} nH",
            f"  Array-junction EJ/h (reference Ic) = "
            f"{physical['array_junction_EJ_GHz']:.6f} GHz",
            f"  Central junction capacitance (reference design) = "
            f"{CENTRAL_JUNCTION_CAPACITANCE_F * 1e15:.6f} fF [not separately modelled]",
            f"  Array junction capacitance (reference design) = "
            f"{ARRAY_JUNCTION_CAPACITANCE_F * 1e15:.6f} fF per junction [not separately modelled]",
            "",
            "Basis-cutoff check (f01 values):",
        ]
    )
    for row in cutoff_rows:
        lines.append(
            f"  cutoff={int(row[0]):3d}: f01={float(row[1]):.12g} GHz; "
            f"f12={float(row[2]):.12g} GHz"
        )

    lines.extend(
        [
            "",
            "MODEL SCOPE",
            "-----------",
            "This is the effective single-mode lumped-element Fluxonium model",
            "provided by scqubits.Fluxonium. The 100-junction array is reduced",
            "to an effective inductive energy EL. Individual array modes,",
            "junction disorder, separate junction capacitances, chip parasitics,",
            "readout resonators, and control lines are not explicitly modelled.",
            "The reference junction capacitances printed above are not added",
            "independently to EC by this script.",
        ]
    )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_simulation(
    show_plots: bool = True,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the baseline Fluxonium analysis and save all outputs.

    Generated files include:
      * energy_levels.csv
      * flux_spectrum.csv
      * matrix_elements.csv
      * cutoff_convergence.csv
      * simulation_summary.txt
      * potential_landscape.png
      * phase_wavefunctions_half_flux.png
      * fluxonium_spectrum.png
      * f01_vs_flux.png
      * matrix_elements.png

    Returns a dictionary containing the qubit, calculated data and output path.
    """
    results_dir = (
        Path(output_dir).expanduser()
        if output_dir is not None
        else DEFAULT_OUTPUT_DIR
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 68)
    print("FLUXONIUM QUBIT SIMULATION")
    print("=" * 68)
    print(f"scqubits version : {getattr(scq, '__version__', 'not reported')}")
    print(f"EJ, EC, EL       : {EJ_GHZ}, {EC_GHZ}, {EL_GHZ} GHz")
    print(f"External flux    : {FLUX_BIAS_PHI0} Phi_0")
    print(f"Basis cutoff     : {BASIS_CUTOFF}")
    print(f"Output directory : {results_dir.resolve()}")

    # 1. Baseline eigensystem at the project's reference flux bias.
    qubit = make_fluxonium(FLUX_BIAS_PHI0)
    energies, eigenvectors = qubit.eigensys(evals_count=NUMBER_OF_LEVELS)
    energies = np.asarray(energies, dtype=float)
    relative_energies = energies - energies[0]

    if len(energies) < 3:
        raise RuntimeError("At least three eigenvalues are required for f01/f12.")
    if not np.all(np.isfinite(energies)) or np.any(np.diff(energies) <= 0.0):
        raise RuntimeError("The calculated eigenvalues are not finite and ordered.")

    f01_GHz = float(energies[1] - energies[0])
    f12_GHz = float(energies[2] - energies[1])
    anharmonicity_GHz = f12_GHz - f01_GHz

    print("\nEnergy levels (absolute, E/h in GHz):")
    for index, energy in enumerate(energies):
        print(
            f"  E{index} = {energy: .9f} GHz; "
            f"E{index}-E0 = {relative_energies[index]: .9f} GHz"
        )
    print(f"\nf01           = {f01_GHz:.9f} GHz")
    print(f"f12           = {f12_GHz:.9f} GHz")
    print(f"Anharmonicity = {anharmonicity_GHz:.9f} GHz")

    energy_eigensystem = (energies, eigenvectors)
    n_operator = np.asarray(
        qubit.n_operator(energy_esys=energy_eigensystem)
    )
    phi_operator = np.asarray(
        qubit.phi_operator(energy_esys=energy_eigensystem)
    )

    print(f"|<0|n|1>|     = {abs(n_operator[0, 1]):.9g}")
    print(f"|<0|phi|1>|   = {abs(phi_operator[0, 1]):.9g}")

    write_csv(
        results_dir / "energy_levels.csv",
        ["state", "energy_E_over_h_GHz", "energy_relative_to_ground_GHz"],
        [
            [index, f"{energies[index]:.12g}", f"{relative_energies[index]:.12g}"]
            for index in range(NUMBER_OF_LEVELS)
        ],
    )

    transition_rows = []
    for lower in range(NUMBER_OF_LEVELS):
        for upper in range(lower + 1, NUMBER_OF_LEVELS):
            transition_rows.append(
                [
                    lower,
                    upper,
                    f"{(energies[upper] - energies[lower]):.12g}",
                ]
            )
    write_csv(
        results_dir / "transition_frequencies.csv",
        ["lower_state", "upper_state", "transition_frequency_GHz"],
        transition_rows,
    )

    matrix_rows = []
    for row_index in range(NUMBER_OF_LEVELS):
        for col_index in range(NUMBER_OF_LEVELS):
            matrix_rows.append(
                [
                    row_index,
                    col_index,
                    f"{abs(n_operator[row_index, col_index]):.12g}",
                    f"{abs(phi_operator[row_index, col_index]):.12g}",
                ]
            )
    write_csv(
        results_dir / "matrix_elements.csv",
        ["state_i", "state_j", "abs_n_ij", "abs_phi_ij"],
        matrix_rows,
    )

    # 2. Convert effective energies into useful physical estimates.
    physical = physical_parameter_estimates()
    print("\nPhysical estimates implied by the effective model:")
    print(
        "  Effective capacitance : "
        f"{physical['effective_capacitance_F'] * 1e15:.6f} fF"
    )
    print(
        "  Central junction Ic   : "
        f"{physical['central_critical_current_A'] * 1e9:.6f} nA"
    )
    print(
        "  Superinductance       : "
        f"{physical['superinductance_H'] * 1e9:.6f} nH"
    )
    print(
        "  100-junction array L  : "
        f"{physical['array_inductance_from_100_junctions_H'] * 1e9:.6f} nH "
        "(using the reference array-junction Ic)"
    )

    # 3. Potential landscapes at zero flux and half a flux quantum.
    # Use scqubits' own potential() method so the plotted convention exactly
    # matches the Hamiltonian convention used internally by the library.
    phase_values = np.linspace(PHASE_GRID_MIN, PHASE_GRID_MAX, 1601)
    qubit_zero_flux = make_fluxonium(0.0)
    qubit_half_flux = make_fluxonium(0.5)
    potential_zero = np.asarray(qubit_zero_flux.potential(phase_values))
    potential_half = np.asarray(qubit_half_flux.potential(phase_values))

    fig_potential, ax_potential = plt.subplots(figsize=(8.5, 5.0))
    ax_potential.plot(
        phase_values,
        potential_zero,
        label=r"$\Phi_{ext}=0$",
        linewidth=1.8,
    )
    ax_potential.plot(
        phase_values,
        potential_half,
        label=r"$\Phi_{ext}=\Phi_0/2$",
        linewidth=1.8,
    )
    ax_potential.set_xlabel(r"Reduced phase $\phi$ (rad)")
    ax_potential.set_ylabel(r"Potential energy $U/h$ (GHz)")
    ax_potential.set_title("Fluxonium potential energy")
    ax_potential.grid(True, alpha=0.3)
    ax_potential.legend()
    fig_potential.tight_layout()
    save_figure(fig_potential, results_dir / "potential_landscape.png")

    # 4. Phase-basis wavefunctions around half a flux quantum.
    half_flux_eigensystem = qubit_half_flux.eigensys(evals_count=4)
    phase_grid = scq.Grid1d(
        min_val=PHASE_GRID_MIN,
        max_val=PHASE_GRID_MAX,
        pt_count=PHASE_GRID_POINTS,
    )
    fig_wavefunctions, ax_wavefunctions = qubit_half_flux.plot_wavefunction(
        which=[0, 1, 2, 3],
        mode="real",
        esys=half_flux_eigensystem,
        phi_grid=phase_grid,
    )
    ax_wavefunctions.set_title(
        r"Fluxonium phase-basis wavefunctions at $\Phi_{ext}=\Phi_0/2$"
    )
    fig_wavefunctions.tight_layout()
    save_figure(
        fig_wavefunctions,
        results_dir / "phase_wavefunctions_half_flux.png",
    )

    # 5. Energy spectrum as external flux is swept from 0 to Phi_0.
    # The repo's tunable-transmon notebook uses this same scqubits
    # get_spectrum_vs_paramvals / energy_table workflow.
    spectrum = qubit.get_spectrum_vs_paramvals(
        param_name="flux",
        param_vals=FLUX_SWEEP,
        evals_count=NUMBER_OF_LEVELS,
        subtract_ground=True,
        get_eigenstates=False,
        num_cpus=1,
    )
    spectrum_energies = np.asarray(spectrum.energy_table, dtype=float)
    if spectrum_energies.shape != (len(FLUX_SWEEP), NUMBER_OF_LEVELS):
        raise RuntimeError(
            "Unexpected spectrum array shape: "
            f"{spectrum_energies.shape}; expected "
            f"({len(FLUX_SWEEP)}, {NUMBER_OF_LEVELS})."
        )
    transition_01_sweep = spectrum_energies[:, 1] - spectrum_energies[:, 0]

    spectrum_header = ["external_flux_over_Phi0"] + [
        f"E{index}_relative_to_E0_GHz" for index in range(NUMBER_OF_LEVELS)
    ] + ["f01_GHz"]
    spectrum_rows = []
    for flux_value, level_values, f01_value in zip(
        FLUX_SWEEP, spectrum_energies, transition_01_sweep
    ):
        spectrum_rows.append(
            [f"{flux_value:.12g}"]
            + [f"{value:.12g}" for value in level_values]
            + [f"{f01_value:.12g}"]
        )
    write_csv(results_dir / "flux_spectrum.csv", spectrum_header, spectrum_rows)

    fig_spectrum, ax_spectrum = plt.subplots(figsize=(8.5, 5.0))
    for level_index in range(1, NUMBER_OF_LEVELS):
        ax_spectrum.plot(
            FLUX_SWEEP,
            spectrum_energies[:, level_index],
            label=fr"$E_{level_index}-E_0$",
            linewidth=1.6,
        )
    ax_spectrum.set_xlabel(r"External flux $\Phi_{ext}/\Phi_0$")
    ax_spectrum.set_ylabel("Transition energy (GHz)")
    ax_spectrum.set_title("Fluxonium energy spectrum")
    ax_spectrum.grid(True, alpha=0.3)
    ax_spectrum.legend(ncol=2)
    fig_spectrum.tight_layout()
    save_figure(fig_spectrum, results_dir / "fluxonium_spectrum.png")

    fig_f01, ax_f01 = plt.subplots(figsize=(8.5, 5.0))
    ax_f01.plot(FLUX_SWEEP, transition_01_sweep, linewidth=1.8)
    ax_f01.axvline(0.5, color="0.4", linestyle="--", linewidth=1.0)
    ax_f01.set_xlabel(r"External flux $\Phi_{ext}/\Phi_0$")
    ax_f01.set_ylabel(r"$f_{01}$ (GHz)")
    ax_f01.set_title(r"Fluxonium $0\rightarrow1$ transition versus flux")
    ax_f01.grid(True, alpha=0.3)
    fig_f01.tight_layout()
    save_figure(fig_f01, results_dir / "f01_vs_flux.png")

    # 6. Charge and phase matrix-element magnitudes in the energy basis.
    fig_matrix, axes_matrix = plt.subplots(1, 2, figsize=(10.0, 4.5))
    state_labels = [str(index) for index in range(NUMBER_OF_LEVELS)]
    for axis, matrix, title, colorbar_label in [
        (axes_matrix[0], np.abs(n_operator), r"$|n_{ij}|$", r"$|n_{ij}|$"),
        (axes_matrix[1], np.abs(phi_operator), r"$|\phi_{ij}|$", r"$|\phi_{ij}|$"),
    ]:
        image = axis.imshow(matrix, origin="lower", aspect="equal")
        axis.set_title(title)
        axis.set_xlabel("State j")
        axis.set_ylabel("State i")
        axis.set_xticks(range(NUMBER_OF_LEVELS), state_labels)
        axis.set_yticks(range(NUMBER_OF_LEVELS), state_labels)
        fig_matrix.colorbar(image, ax=axis, label=colorbar_label, fraction=0.046)
    fig_matrix.suptitle(
        fr"Operator matrix elements at $\Phi_{{ext}}={FLUX_BIAS_PHI0}\Phi_0$"
    )
    fig_matrix.tight_layout()
    save_figure(fig_matrix, results_dir / "matrix_elements.png")

    # 7. Check convergence with respect to the harmonic-oscillator basis cutoff.
    cutoff_rows: list[list[Any]] = []
    print("\nBasis-cutoff check:")
    print("  cutoff       f01 (GHz)       f12 (GHz)       |delta f01| (GHz)")
    previous_f01: float | None = None
    for cutoff in CUTOFF_VALUES:
        cutoff_qubit = scq.Fluxonium(
            EJ=EJ_GHZ,
            EC=EC_GHZ,
            EL=EL_GHZ,
            flux=FLUX_BIAS_PHI0,
            cutoff=int(cutoff),
        )
        cutoff_energies = np.asarray(
            cutoff_qubit.eigenvals(evals_count=3), dtype=float
        )
        cutoff_f01 = float(cutoff_energies[1] - cutoff_energies[0])
        cutoff_f12 = float(cutoff_energies[2] - cutoff_energies[1])
        delta_f01 = (
            float("nan")
            if previous_f01 is None
            else abs(cutoff_f01 - previous_f01)
        )
        cutoff_rows.append(
            [
                int(cutoff),
                f"{cutoff_f01:.12g}",
                f"{cutoff_f12:.12g}",
                "" if previous_f01 is None else f"{delta_f01:.12g}",
            ]
        )
        delta_display = "---" if previous_f01 is None else f"{delta_f01:.6e}"
        print(
            f"  {cutoff:6d}  {cutoff_f01:14.9f}  "
            f"{cutoff_f12:14.9f}  {delta_display:>18s}"
        )
        previous_f01 = cutoff_f01

    write_csv(
        results_dir / "cutoff_convergence.csv",
        ["basis_cutoff", "f01_GHz", "f12_GHz", "abs_change_in_f01_from_previous_GHz"],
        cutoff_rows,
    )

    write_summary(
        results_dir / "simulation_summary.txt",
        energies,
        n_operator,
        phi_operator,
        cutoff_rows,
    )

    print("\nSaved results:")
    for file_path in sorted(results_dir.iterdir()):
        if file_path.is_file():
            print(f"  {file_path.name}")
    print("\nSimulation completed.")

    if show_plots:
        plt.show()
    else:
        plt.close("all")

    return {
        "qubit": qubit,
        "energies_GHz": energies,
        "relative_energies_GHz": relative_energies,
        "f01_GHz": f01_GHz,
        "f12_GHz": f12_GHz,
        "anharmonicity_GHz": anharmonicity_GHz,
        "flux_values": FLUX_SWEEP.copy(),
        "spectrum_GHz": spectrum_energies,
        "f01_vs_flux_GHz": transition_01_sweep,
        "n_operator": n_operator,
        "phi_operator": phi_operator,
        "physical_parameters": physical,
        "output_dir": results_dir,
    }


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Simulate a Fluxonium qubit using scqubits."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory in which CSV files, plots and summary are saved.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Save plots without opening interactive Matplotlib windows.",
    )
    args = parser.parse_args()
    run_simulation(show_plots=not args.no_show, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
