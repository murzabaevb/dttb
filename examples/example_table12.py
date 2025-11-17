"""Examples reproducing ITU-R BT.2033-2 Table 12 (Band III, 200 MHz).

These examples assume you have dvbt2.py with the DVBT2 class
in your Python path:

    from dvbt2 import DVBT2
"""

from dvbt2 import DVBT2


def print_case(title: str, inst: DVBT2) -> None:
    print(f"\n=== {title} ===")
    print(f"freq_mhz          = {inst.freq_mhz}")
    print(f"reception_mode    = {inst.reception_mode}")
    print(f"modulation        = {inst.modulation}")
    print(f"code_rate         = {inst.code_rate}")
    print(f"environment       = {inst.environment}")
    print(f"G_dbd             = {inst.G_dbd:.2f} dBd")
    print(f"Lf_db             = {inst.Lf_db:.2f} dB")
    print(f"Pn_dbw            = {inst.noise_power_dbw():.2f} dBW")
    print(f"Ps_min_dbw        = {inst.min_receiver_power_dbw():.2f} dBW")
    print(f"Aa_dbm2           = {inst.effective_aperture_dbm2():.2f} dB(m^2)")
    print(f"phi_min_dbw/m2    = {inst.min_pfd_dbw_per_m2():.2f} dB(W/m^2)")
    print(f"Emin_dBuV/m       = {inst.Emin_dbuV_per_m():.2f} dB(µV/m)")
    for p in (0.70, 0.95):
        inst.location_probability = p
        print(f"Emed({int(p*100)}%)        = {inst.Emed_dbuV_per_m():.2f} dB(µV/m)")


def main() -> None:
    # Common parameters for Table 12 (Band III, 200 MHz)
    freq_mhz = 200.0
    noise_figure_db = 6.0
    noise_bw_hz = 6.66e6  # as used in Rec. ITU-R BT.2033-2 examples

    # 1) Fixed rooftop (Table 12, Band III, Fixed)
    t12_b3_fx = DVBT2(
        freq_mhz=freq_mhz,
        reception_mode="FX",
        environment="urban",
        modulation="256QAM",
        code_rate="2/3",
        noise_figure_db=noise_figure_db,
        noise_bw_hz=noise_bw_hz,
        ant_gain_dbd=7.0,       # Gd
        feeder_loss_db=2.0,     # Lf
        height_loss_db=0.0,
        building_entry_loss_db=0.0,
        sigma_building_db=0.0,
        sigma_macro_db=5.5,
    )
    print_case("Table 12 – Band III, Fixed", t12_b3_fx)

    # 2) Portable outdoor / urban (Table 12, Band III, Portable outdoor)
    t12_b3_po = DVBT2(
        freq_mhz=freq_mhz,
        reception_mode="PO",
        environment="urban",
        modulation="64QAM",
        code_rate="2/3",
        noise_figure_db=noise_figure_db,
        noise_bw_hz=noise_bw_hz,
        ant_gain_dbd=-2.2,      # Gd
        feeder_loss_db=0.0,
        height_loss_db=0.0,     # Band III: no height loss in example
        building_entry_loss_db=0.0,
        sigma_building_db=0.0,
        sigma_macro_db=5.5,
    )
    print_case("Table 12 – Band III, Portable outdoor / urban", t12_b3_po)

    # 3) Portable indoor / urban (Table 12, Band III, Portable indoor)
    t12_b3_pi = DVBT2(
        freq_mhz=freq_mhz,
        reception_mode="PI",
        environment="urban",
        modulation="64QAM",
        code_rate="2/3",
        noise_figure_db=noise_figure_db,
        noise_bw_hz=noise_bw_hz,
        ant_gain_dbd=-2.2,      # Gd
        feeder_loss_db=0.0,
        height_loss_db=0.0,
        building_entry_loss_db=9.0,   # Lb
        sigma_building_db=3.0,        # σ_b
        sigma_macro_db=5.5,
    )
    print_case("Table 12 – Band III, Portable indoor / urban", t12_b3_pi)


if __name__ == "__main__":
    main()
