"""Examples reproducing ITU-R BT.2033-2 Table 13 (Bands IV/V, 650 MHz).

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
    # Common parameters for Table 13 (Bands IV/V, 650 MHz)
    freq_mhz = 650.0
    noise_figure_db = 6.0
    noise_bw_hz = 7.61e6  # as used in Rec. ITU-R BT.2033-2 examples

    # 1) Fixed rooftop (Table 13, Bands IV/V, Fixed)
    t13_fx = DVBT2(
        freq_mhz=freq_mhz,
        reception_mode="FX",
        environment="urban",
        modulation="256QAM",
        code_rate="2/3",
        noise_figure_db=noise_figure_db,
        noise_bw_hz=noise_bw_hz,
        ant_gain_dbd=11.0,      # Gd
        feeder_loss_db=4.0,     # Lf
        height_loss_db=0.0,
        building_entry_loss_db=0.0,
        sigma_building_db=0.0,
        sigma_macro_db=5.5,
    )
    print_case("Table 13 – Bands IV/V, Fixed", t13_fx)

    # 2) Portable outdoor / urban (Table 13, Bands IV/V, Portable outdoor)
    t13_po = DVBT2(
        freq_mhz=freq_mhz,
        reception_mode="PO",
        environment="urban",
        modulation="64QAM",
        code_rate="2/3",
        noise_figure_db=noise_figure_db,
        noise_bw_hz=noise_bw_hz,
        ant_gain_dbd=0.0,       # Gd
        feeder_loss_db=0.0,
        # In Table 13 examples, height loss at UHF is around mid-20 dB.
        # You can either let DVBT2 compute it or force a specific value:
        # height_loss_db=24.0,
        building_entry_loss_db=0.0,
        sigma_building_db=0.0,
        sigma_macro_db=5.5,
    )
    print_case("Table 13 – Bands IV/V, Portable outdoor / urban", t13_po)

    # 3) Portable indoor / urban (Table 13, Bands IV/V, Portable indoor)
    t13_pi = DVBT2(
        freq_mhz=freq_mhz,
        reception_mode="PI",
        environment="urban",
        modulation="64QAM",
        code_rate="2/3",
        noise_figure_db=noise_figure_db,
        noise_bw_hz=noise_bw_hz,
        ant_gain_dbd=0.0,       # Gd
        feeder_loss_db=0.0,
        # height_loss_db=24.0,   # optionally force Lh
        building_entry_loss_db=11.0,  # Lb
        sigma_building_db=6.0,        # σ_b
        sigma_macro_db=5.5,
    )
    print_case("Table 13 – Bands IV/V, Portable indoor / urban", t13_pi)


if __name__ == "__main__":
    main()
