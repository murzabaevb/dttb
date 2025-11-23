"""
Command-line interface for the DVBT2 field-strength calculator.

Subcommands
-----------
summary : full ITU-R BT.2033-2 style calculation chain (Tables 12 & 13)
emed    : only final E_med [dB(µV/m)]
debug   : full chain + some extra diagnostic information

Typical usage
-------------
    dvbt2 summary --mode FX --freq 650 --environment urban \
                  --modulation 64QAM --code-rate 3/5

    dvbt2 emed --mode PI --freq 650 --environment urban \
               --modulation 16QAM --code-rate 1/2

    dvbt2 debug --mode PO --freq 650 --environment rural \
                --modulation 64QAM --code-rate 3/4
"""

from __future__ import annotations

import argparse
from pprint import pprint
from typing import Any

from dvbt2 import DVBT2


# ---------------------------------------------------------------------------
# Helpers for argument → DVBT2 mapping
# ---------------------------------------------------------------------------


def _build_overrides_from_args(args: argparse.Namespace) -> dict[str, Any]:
    """
    Collect optional overrides from CLI args into kwargs that can be passed
    to DVBT2 factory methods / constructor.
    """
    overrides: dict[str, Any] = {}

    if args.noise_figure is not None:
        overrides["noise_figure_db"] = args.noise_figure
    if args.noise_bw is not None:
        overrides["noise_bw_hz"] = args.noise_bw
    if args.feeder_loss is not None:
        overrides["feeder_loss_db"] = args.feeder_loss
    if args.ant_gain is not None:
        overrides["ant_gain_dbd"] = args.ant_gain
    if args.height_loss is not None:
        overrides["height_loss_db"] = args.height_loss
    if args.building_loss is not None:
        overrides["building_entry_loss_db"] = args.building_loss
    if args.sigma_macro is not None:
        overrides["sigma_macro_db"] = args.sigma_macro
    if args.sigma_building is not None:
        overrides["sigma_building_db"] = args.sigma_building
    if args.location_probability is not None:
        overrides["location_probability"] = args.location_probability

    return overrides


def _build_dvbt2_from_args(args: argparse.Namespace) -> DVBT2:
    """
    Construct a DVBT2 instance from parsed CLI arguments,
    using the appropriate factory method.
    """
    freq = args.freq
    env = args.environment
    mod = args.modulation
    cr = args.code_rate
    overrides = _build_overrides_from_args(args)

    mode = args.mode.upper()

    if mode == "FX":
        return DVBT2.fx(
            freq_mhz=freq,
            environment=env,
            modulation=mod,
            code_rate=cr,
            **overrides,
        )

    if mode == "PO":
        # Portable OUTDOOR
        if args.receiver_type == "portable":
            return DVBT2.po_portable(
                freq_mhz=freq,
                environment=env,
                modulation=mod,
                code_rate=cr,
                **overrides,
            )
        else:  # handheld
            if args.handheld_antenna == "external":
                return DVBT2.po_handheld_external(
                    freq_mhz=freq,
                    environment=env,
                    modulation=mod,
                    code_rate=cr,
                    **overrides,
                )
            else:
                return DVBT2.po_handheld_integrated(
                    freq_mhz=freq,
                    environment=env,
                    modulation=mod,
                    code_rate=cr,
                    **overrides,
                )

    if mode == "PI":
        # Portable INDOOR
        bclass = args.building_class
        if args.receiver_type == "portable":
            return DVBT2.pi_portable(
                freq_mhz=freq,
                environment=env,
                modulation=mod,
                code_rate=cr,
                building_class=bclass,
                **overrides,
            )
        else:  # handheld
            if args.handheld_antenna == "external":
                return DVBT2.pi_handheld_external(
                    freq_mhz=freq,
                    environment=env,
                    modulation=mod,
                    code_rate=cr,
                    building_class=bclass,
                    **overrides,
                )
            else:
                return DVBT2.pi_handheld_integrated(
                    freq_mhz=freq,
                    environment=env,
                    modulation=mod,
                    code_rate=cr,
                    building_class=bclass,
                    **overrides,
                )

    if mode == "MO":
        # Mobile
        return DVBT2.mo(
            freq_mhz=freq,
            environment=env,
            modulation=mod,
            code_rate=cr,
            **overrides,
        )

    raise ValueError(f"Unsupported reception mode: {mode}")


# ---------------------------------------------------------------------------
# Argument definitions
# ---------------------------------------------------------------------------


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add common DVB-T2 planning parameters to a parser or parent parser.
    This is shared by all subcommands.
    """
    parser.add_argument(
        "--mode",
        required=True,
        choices=["FX", "PO", "PI", "MO"],
        help="Reception mode: FX (fixed rooftop), PO (portable outdoor), "
             "PI (portable indoor), MO (mobile).",
    )
    parser.add_argument(
        "--freq",
        type=float,
        required=True,
        help="Frequency in MHz (within Bands III, IV or V).",
    )
    parser.add_argument(
        "--environment",
        dest="environment",
        choices=["urban", "rural"],
        required=True,
        help="Environment: urban or rural.",
    )
    parser.add_argument(
        "--modulation",
        dest="modulation",
        choices=["QPSK", "16QAM", "64QAM", "256QAM"],
        required=True,
        help="DVB-T2 modulation scheme.",
    )
    parser.add_argument(
        "--code-rate",
        dest="code_rate",
        choices=["1/2", "3/5", "2/3", "3/4", "4/5", "5/6"],
        required=True,
        help="FEC code rate.",
    )

    # Receiver / antenna type for PO / PI
    parser.add_argument(
        "--receiver-type",
        choices=["portable", "handheld"],
        default="portable",
        help="Receiver type (for PO/PI): portable (default) or handheld.",
    )
    parser.add_argument(
        "--handheld-antenna",
        choices=["integrated", "external"],
        default="integrated",
        help="Handheld antenna type (for PO/PI): integrated (default) or external.",
    )
    parser.add_argument(
        "--building-class",
        choices=["high", "medium", "low"],
        default="medium",
        help="Building class for PI: high / medium / low (BT.2033-2 Table 27).",
    )

    # Optional overrides
    parser.add_argument(
        "--noise-figure",
        type=float,
        help="Override receiver noise figure F (dB). Default is 6 dB.",
    )
    parser.add_argument(
        "--noise-bw",
        type=float,
        help="Override receiver noise bandwidth B (Hz). "
             "Default is about 7.61e6 for 8 MHz DVB-T2.",
    )
    parser.add_argument(
        "--feeder-loss",
        type=float,
        help="Override feeder loss Lf (dB). If not set, mode-specific defaults are used.",
    )
    parser.add_argument(
        "--ant-gain",
        type=float,
        help="Override antenna gain Gd (dBd). If not set, table defaults are used.",
    )
    parser.add_argument(
        "--height-loss",
        type=float,
        help="Override height loss Lh (dB). If not set, GE06 log-frequency model is used.",
    )
    parser.add_argument(
        "--building-loss",
        type=float,
        help="Override building entry loss Lb (dB). If not set, "
             "BT.2033-2 Table 27 defaults are used for PI.",
    )
    parser.add_argument(
        "--sigma-macro",
        type=float,
        help="Override macro-scale σ_m (dB). Default is 5.5 dB.",
    )
    parser.add_argument(
        "--sigma-building",
        type=float,
        help="Override building σ_b (dB). If not set, table defaults are used.",
    )
    parser.add_argument(
        "--location-probability",
        type=float,
        help="Location probability (0.01–0.99). Default is 0.95 (95%%).",
    )


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def _cmd_summary(args: argparse.Namespace) -> None:
    """Handle the `summary` subcommand: full BT.2033-2 style table."""
    dvbt2 = _build_dvbt2_from_args(args)
    summary = dvbt2.summary()

    # Print in the order provided by summary() (which mirrors Tables 12 & 13)
    for key, value in summary.items():
        print(f"{key:25s}: {value}")


def _cmd_emed(args: argparse.Namespace) -> None:
    """Handle the `emed` subcommand: only final E_med."""
    dvbt2 = _build_dvbt2_from_args(args)
    emed = dvbt2.Emed_dbuV_per_m()
    print(f"{emed:.2f}  # E_med [dB(µV/m)]")


def _cmd_debug(args: argparse.Namespace) -> None:
    """
    Handle the `debug` subcommand: summary + some internal diagnostic info.
    """
    dvbt2 = _build_dvbt2_from_args(args)

    print("=== INPUT CONFIGURATION ===")
    print(f"mode                : {dvbt2.reception_mode}")
    print(f"freq_mhz            : {dvbt2.freq_mhz}")
    print(f"band                : {dvbt2.band}")
    print(f"environment         : {dvbt2.environment}")
    print(f"receiver_type       : {dvbt2.receiver_type}")
    print(f"handheld_antenna    : {dvbt2.handheld_antenna_type}")
    print(f"building_class      : {dvbt2.building_class}")
    print()

    print("=== SUMMARY (BT.2033-2 TABLE STYLE) ===")
    summary = dvbt2.summary()
    for key, value in summary.items():
        print(f"{key:25s}: {value}")
    print()

    # Additional internal details (especially interpolation / categorisation)
    print("=== INTERNAL DETAILS ===")
    print(f"mmn_category        : {dvbt2._mmn_category}")
    print(f"location_probability: {dvbt2.location_probability}")
    print(f"sigma_total_db      : {dvbt2.sigma_total_db():.3f}")
    print(f"mu_factor           : {dvbt2.mu_factor():.3f}")
    print(f"location_correction : {dvbt2.location_correction_db():.3f} dB")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """
    CLI entry point for the dvbt2 tool.

    Subcommands
    -----------
    summary : Full ITU-R BT.2033-2 style calculation chain.
    emed    : Only final E_med [dB(µV/m)].
    debug   : Summary + extra diagnostic information.
    """
    parser = argparse.ArgumentParser(
        prog="dvbt2",
        description=(
            "DVB-T2 field-strength and E_med calculator based on "
            "ITU-R BT.2033-2 / BT.2036-5 / GE06."
        ),
    )

    # Parent parser for shared arguments (no help to avoid duplication)
    common_parent = argparse.ArgumentParser(add_help=False)
    _add_common_arguments(common_parent)

    subparsers = parser.add_subparsers(dest="command", required=True)

    # summary
    p_summary = subparsers.add_parser(
        "summary",
        parents=[common_parent],
        help="Compute full BT.2033-2 style summary (Tables 12 & 13).",
    )
    p_summary.set_defaults(func=_cmd_summary)

    # emed
    p_emed = subparsers.add_parser(
        "emed",
        parents=[common_parent],
        help="Compute only E_med [dB(µV/m)].",
    )
    p_emed.set_defaults(func=_cmd_emed)

    # debug
    p_debug = subparsers.add_parser(
        "debug",
        parents=[common_parent],
        help="Compute summary and show extra diagnostic information.",
    )
    p_debug.set_defaults(func=_cmd_debug)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
