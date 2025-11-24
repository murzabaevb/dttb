from __future__ import annotations

from dataclasses import dataclass
from math import log, log10, sqrt, pi
from typing import Literal, ClassVar, Tuple, Dict

ReceptionMode = Literal["FX", "PO", "PI", "MO"]
Environment = Literal["urban", "rural"]
Modulation = Literal["QPSK", "16QAM", "64QAM", "256QAM"]
CodeRate = Literal["1/2", "3/5", "2/3", "3/4", "4/5", "5/6"]
ReceiverType = Literal["portable", "handheld"]
HandheldAntennaType = Literal["integrated", "external"]
BuildingClass = Literal["high", "medium", "low"]
BandName = Literal["III", "IV", "V"]


@dataclass
class DVBT2:
    """
    DVB-T2 Minimum Field-Strength and Minimum Median Equivalent Field-Strength Calculator.

    This class implements the complete DVB-T2 planning calculation chain defined in:

        - Rec. ITU-R BT.2033-2
          “Planning criteria, including protection ratios, for second generation
          of digital terrestrial television broadcasting systems in the VHF/UHF bands”

        - Rec. ITU-R BT.2036-5
          “Characteristics of a reference receiving system for frequency planning
          of digital terrestrial television systems”

        - RRC‑06 GE06 Final Acts / Ge06 Agreement (Annex 2):
          – Location probability correction
          – Qi(x) statistical distribution
          – Log-frequency interpolation and extrapolation rules

    The class computes:
        - Required C/N (Table 2, BT.2033‑2)
        - Receiver noise power and minimum receiver input power (Ps_min)
        - Effective antenna aperture (A_a)
        - Minimum power flux-density (Φ_min)
        - Minimum field strength (E_min)
        - Allowances:
            * Man-made noise (Tables 31–32, BT.2033-2)
            * Height loss (Table 3-3, para. 3.2.2.1, Ch.3/Ann.2, GE06)
            * Building entry loss (Table 27, BT.2033-2)
        - Statistical correction:
            * σ_b, σ_m → σ_total
            * µ factor via Qi(1 - p) (GE06 A.2.1.12, Eq. 26a–d)
            * Location correction C_l = µ · σ_total
        - Final minimum median equivalent field strength E_med

    Supported reception modes:
        - "FX" : Fixed rooftop
        - "PO" : Portable outdoor
        - "PI" : Portable indoor
        - "MO" : Mobile

    Bands:
        Band III : 174–230 MHz
        Band IV  : 470–582 MHz
        Band V   : 582–862 MHz

    Antenna gains and losses follow:
        - BT.2036-5 Table 21 (fixed rooftop antennas)
        - BT.2033-2 Table 28 (portable receivers)
        - BT.2033-2 Table 29 (handheld receivers, UHF interpolated with log-frequency rule)
        - BT.2033-2 Table 30 (mobile reception)

    Man-made noise (Pmmn) implemented using:
        - BT.2033-2 Tables 31–32
        - Environment: urban / rural
        - Receiver type: portable / handheld / rooftop / mobile-adapted
        - Band groups: VHF (Band III) and UHF (Bands IV/V)

    Height loss Lh implemented using:
        - Table 3-3 (GE06)
        - Values at 200, 500, 800 MHz
        - Interpolated/extrapolated with log-frequency method (A.2.1.6 GE06)

    Location correction follows GE06 Annex 2:
        - σ_total = sqrt(σ_b² + σ_m²)
        - µ = Qi(1 − p_location)
        - C_l = µ · σ_total
        - Supports arbitrary interpolation of µ over standard location probabilities
          (0.70, 0.90, 0.95, 0.99)

    Parameters
    ----------
    freq_mhz : float
        Operating frequency in MHz.

    reception_mode : Literal["FX", "PO", "PI", "MO"]
        Reception category as defined above.

    environment : Literal["urban", "rural"]
        Environment for man-made noise and height loss.

    modulation : Literal["QPSK", "16QAM", "64QAM", "256QAM"]
        DVB-T2 modulation scheme.

    code_rate : Literal["1/2", "3/5", "2/3", "3/4", "4/5", "5/6"]
        FEC code rate.

    receiver_type : Literal["portable", "handheld"], optional
        For PO/PI modes. Determines antenna gain category and Pmmn category.

    handheld_antenna_type : Literal["integrated", "external"], optional
        Determines MMN category for handheld reception.
        Ignored for FX and MO.

    building_class : Literal["high", "medium", "low"], optional
        For PI (indoor) reception. Determines L_b and σ_b (BT.2033-2 Table 27).

    noise_figure_db : float, optional
        Receiver noise figure in dB. Default: 6 dB.

    noise_bw_hz : float, optional
        Receiver noise bandwidth in Hz (≈7.61 MHz for 8 MHz DVB-T2). Default: 7.61e6.

    feeder_loss_db : float or None
        Override for feeder loss L_f. If None, values from BT.2036-5 are used.

    ant_gain_dbd : float or None
        Override for antenna gain G_d. If None, values from BT.2033-2 / BT.2036-5 are used.

    height_loss_db : float or None
        Override for L_h. If None, log-frequency interpolation is used.

    building_entry_loss_db : float or None
        Override for L_b (indoor only).

    sigma_macro_db : float, optional
        Macro-scale log-normal fade standard deviation. Default: 5.5 dB.

    sigma_building_db : float or None
        Override for σ_b. If None, taken from BT.2033-2 Table 27.

    location_probability : float, optional
        Location probability for coverage planning (70%, 90%, 95%, 99% supported).
        Default: 0.95 (µ = Qi(0.05)).

    Methods
    -------
    cn_required_db()
        Returns the required C/N ratio (dB) from BT.2033-2 Table 2.

    noise_power_dbw()
        Computes receiver noise power Pn (dBW).

    min_receiver_power_dbw()
        Computes Ps_min (dBW) required at receiver input.

    effective_aperture_dbm2()
        Effective antenna aperture (dBm²).

    min_pfd_dbw_per_m2()
        Minimum power flux-density Φ_min (dB(W/m²)).

    Emin_dbuV_per_m()
        Minimum field strength E_min (dBuV/m).

    man_made_noise_db()
        Man-made noise allowance Pmmn (dB).

    location_correction_db()
        GE06 location correction C_l (dB).

    Emed_dbuV_per_m()
        Final minimum median equivalent field strength E_med (dBuV/m).

    summary()
        Returns all computed quantities in a dictionary formatted to match
        ITU-R BT.2033-2 Tables 12 & 13 (for easy verification).

    Class Methods (factory constructors)
    ------------------------------------
    fx(...)
        Preconfigured object for fixed rooftop (FX).

    po_portable(...), po_handheld_integrated(...), po_handheld_external(...)
        Portable outdoor scenarios.

    pi_portable(...), pi_handheld_integrated(...), pi_handheld_external(...)
        Portable indoor scenarios.

    mo(...)
        Mobile reception (vehicle / handheld on the move).

    Notes
    -----
    - All frequency-dependent corrections use the GE06 log-frequency
    interpolation/extrapolation rule, including height loss and
    UHF handheld antenna gain (Table 29).

    - The class is designed so that every computation step corresponds
      exactly to a line item in BT.2033-2 Tables 12 & 13.
    """

    # -------------------------------------------------------------------------
    # CLASS-LEVEL CONSTANT TABLES
    # -------------------------------------------------------------------------

    # Co-channel protection ratios [dB] (Table 2, Rec. ITU-R BT.2033-2)
    # (modulation, code_rate) -> (Gaussian, Ricean, Rayleigh)
    TABLE_CN: ClassVar[Dict[Tuple[str, str], Tuple[float, float, float]]] = {
        # QPSK
        ("QPSK", "1/2"): (2.4, 2.6, 3.4),
        ("QPSK", "3/5"): (3.6, 3.8, 4.9),
        ("QPSK", "2/3"): (4.5, 4.8, 6.3),
        ("QPSK", "3/4"): (5.5, 5.8, 7.6),
        ("QPSK", "4/5"): (6.1, 6.5, 8.5),
        ("QPSK", "5/6"): (6.6, 7.0, 9.3),
        # 16-QAM
        ("16QAM", "1/2"): (7.6, 7.8, 9.1),
        ("16QAM", "3/5"): (9.0, 9.2, 10.7),
        ("16QAM", "2/3"): (10.3, 10.5, 12.2),
        ("16QAM", "3/4"): (11.4, 11.8, 13.9),
        ("16QAM", "4/5"): (12.2, 12.6, 15.1),
        ("16QAM", "5/6"): (12.7, 13.1, 15.9),
        # 64-QAM
        ("64QAM", "1/2"): (11.9, 12.2, 14.0),
        ("64QAM", "3/5"): (13.8, 14.1, 15.8),
        ("64QAM", "2/3"): (15.1, 15.4, 17.2),
        ("64QAM", "3/4"): (16.6, 16.9, 19.3),
        ("64QAM", "4/5"): (17.6, 18.1, 20.9),
        ("64QAM", "5/6"): (18.2, 18.7, 21.8),
        # 256-QAM
        ("256QAM", "1/2"): (15.9, 16.3, 18.3),
        ("256QAM", "3/5"): (18.2, 18.4, 20.5),
        ("256QAM", "2/3"): (19.7, 20.0, 22.1),
        ("256QAM", "3/4"): (21.7, 22.0, 24.6),
        ("256QAM", "4/5"): (23.1, 23.6, 26.6),
        ("256QAM", "5/6"): (23.9, 24.4, 28.0),
    }

    # Man-made noise Pmmn [dB] (Tables 31–32, Rec. ITU-R BT.2033-2)
    # env -> band_group (VHF "III", UHF "IVV") -> category -> Pmmn
    TABLE_MMN: ClassVar[Dict[str, Dict[str, Dict[str, float]]]] = {
        "urban": {
            "III": {"integrated": 0.0, "external": 1.0,
                    "rooftop": 2.0, "adapted": 8.0},
            "IVV": {"integrated": 0.0, "external": 0.0,
                    "rooftop": 0.0, "adapted": 1.0},
        },
        "rural": {
            "III": {"integrated": 0.0, "external": 0.0,
                    "rooftop": 2.0, "adapted": 5.0},
            "IVV": {"integrated": 0.0, "external": 0.0,
                    "rooftop": 0.0, "adapted": 0.0},
        },
    }

    # Building entry loss [dB] (Table 27, Rec. ITU-R BT.2033-2)
    # building class -> (mean Lb, σ_b)
    TABLE_BLD_LOSS: ClassVar[Dict[str, Tuple[float, float]]] = {
        "high": (7.0, 5.0),
        "medium": (11.0, 6.0),
        "low": (15.0, 7.0),
    }

    # -------------------------------------------------------------------------
    # INSTANCE FIELDS
    # -------------------------------------------------------------------------

    # Core configuration
    freq_mhz: float
    reception_mode: ReceptionMode          # "FX", "PO", "PI", "MO"
    environment: Environment               # "urban", "rural"
    modulation: Modulation                 # "QPSK", "16QAM", "64QAM", "256QAM"
    code_rate: CodeRate                    # "1/2", "3/5", "2/3", "3/4", "4/5", "5/6"

    # For PO/PI only: portable vs handheld receiver
    receiver_type: ReceiverType = "portable"  # "portable", "handheld"
    handheld_antenna_type: HandheldAntennaType = "external"  # "integrated", "external"

    # Indoor building class for PI (UHF)
    building_class: BuildingClass = "low"  # "high", "medium", "low"

    # Receiver / RF chain
    noise_figure_db: float = 6.0
    noise_bw_hz: float = 7.61e6           # default for 8 MHz DVB-T2

    # Optional overrides (None → internal defaults)
    feeder_loss_db: float | None = None
    ant_gain_dbd: float | None = None
    height_loss_db: float | None = None
    building_entry_loss_db: float | None = None
    sigma_macro_db: float = 5.5
    sigma_building_db: float | None = None
    location_probability: float = 0.7     # 0.95=95%, 0.9=90% etc.


    # -------------------------------------------------------------------------
    # Post-init validation ("fail early")
    # -------------------------------------------------------------------------

    def __post_init__(self) -> None:
        """
        Basic validation so that out-of-range inputs fail early.
        """
        # This will raise if freq_mhz is outside all DVB bands.
        _ = self.band

        if not (6.6e6 <= self.noise_bw_hz <= 8.0e6):
            raise ValueError(f"noise_bw_hz must be within 6.6E+6...8.0E+6, "
                             f"got {self.noise_bw_hz}")

        if self.noise_figure_db < 0:
            raise ValueError(f"noise_figure_db must be >= 0, got {self.noise_figure_db}")

        if self.sigma_macro_db < 0:
            raise ValueError(f"sigma_macro_db must be >= 0, got {self.sigma_macro_db}")

        if not (0.01 <= self.location_probability <= 0.99):
            raise ValueError(
                f"location_probability must be in [0.01, 0.99], got {self.location_probability}"
            )


    # -------------------------------------------------------------------------
    # Math helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _db10(x: float) -> float:
        return 10.0 * log10(x)


    @staticmethod
    def _log_interp(f: float, f_inf: float, v_inf: float, f_sup: float, v_sup: float) -> float:
        """Log-frequency interpolation/extrapolation.

        Based on the Final Acts RRC-06 (Ge06 Agreement), Annex 2, A.2.1.6).
        v = v_inf + (v_sup − v_inf) * log(f / f_inf) / log(f_sup / f_inf) dB
            where:
            f: frequency for which the dB-value is required (MHz)
            f_inf: lower edge frequency (MHz)
            f_sup: higher edge frequency (MHz)
            v_inf: dB-value for f_inf (dB)
            v_sup: dB-value for f_sup (dB).
        """
        return v_inf + (v_sup - v_inf) * log10(f / f_inf) / log10(f_sup / f_inf)


    @staticmethod
    def _Qi(x: float) -> float:
        """
        Approximation to the inverse complementary cumulative normal
        distribution function Qi(x), valid for 0.01 <= x <= 0.99.

        Based on RRC-06 Final Acts, A.2.1.12, equations (26a–d).
        """
        if not (0.01 <= x <= 0.99):
            raise ValueError(
                f"Qi(x) is defined only for 0.01 <= x <= 0.99; got x={x}"
            )

        # Constants from (26d)
        C0, C1, C2 = 2.515517, 0.802853, 0.010328
        D1, D2, D3 = 1.432788, 0.189269, 0.001308

        def T(z: float) -> float:
            # T(z) = sqrt(-2 ln z)
            return sqrt(-2.0 * log(z))

        def xi(z: float) -> float:
            t = T(z)
            num = C0 + C1 * t + C2 * t * t
            den = 1.0 + D1 * t + D2 * t * t + D3 * t * t * t
            return num / den

        if x <= 0.5:
            # (26a) Qi(x) = T(x) - ξ(x)
            return T(x) - xi(x)
        else:
            # (26b) Qi(x) = -{ T(1 - x) - ξ(1 - x) }
            y = 1.0 - x
            return -(T(y) - xi(y))


    # -------------------------------------------------------------------------
    # Band / Environment helpers
    # -------------------------------------------------------------------------

    @property
    def band(self) -> BandName:
        """
        Return the DVB-T2 band name based on centre frequency:
          Band III : 174–230 MHz
          Band IV  : 470–582 MHz
          Band V   : 582–862 MHz

        Raises ValueError if freq_mhz is outside these ranges.
        """
        f = self.freq_mhz
        if 174.0 <= f <= 230.0:
            return "III"
        elif 470.0 <= f < 582.0:
            return "IV"
        elif 582.0 <= f <= 862.0:
            return "V"
        else:
            raise ValueError(
                f"freq_mhz={f} MHz is outside DVB-T2 bands, "
                f"III (174–230), IV (470–582), V (582–862)"
            )


    @property
    def _is_vhf(self) -> bool:
        """True for Band III."""
        return self.band in ("III",)


    @property
    def _is_uhf(self) -> bool:
        """True for UHF (Bands IV and V)."""
        return self.band in ("IV", "V")


    @property
    def _mmn_band_group(self) -> str:
        """
        Pmmn Band Name (Tables 31–32, Rec. ITU-R BT.2033-2).

        Map bands to:
          - "III" → VHF (Band III)
          - "IVV" → UHF (Bands IV & V)
        """
        return "III" if self._is_vhf else "IVV"


    @property
    def _mmn_category(self) -> str:
        """
        Category for Pmmn lookup:
          FX → "rooftop"
          MO → "adapted"
          PO/PI, receiver_type="handheld":
              handheld_antenna_type → "integrated" or "external"
          PO/PI, receiver_type="portable":
              "integrated"
        """
        if self.reception_mode == "FX":
            return "rooftop"
        if self.reception_mode == "MO":
            return "adapted"

        # PO / PI
        if self.receiver_type == "handheld":
            return "external" if self.handheld_antenna_type == "external" else "integrated"
        else:
            return "integrated"


    # -------------------------------------------------------------------------
    # Required protection ratio (C/N)
    # -------------------------------------------------------------------------

    def _channel_type_for_cn(self) -> str:
        """Ricean for FX, Rayleigh for PO/PI/MO."""
        return "Ricean" if self.reception_mode == "FX" else "Rayleigh"

    def cn_required_db(self) -> float:
        """Return required C/N [dB] from Table 2."""
        key = (self.modulation, self.code_rate)
        try:
            gaussian, ricean, rayleigh = self.TABLE_CN[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported (modulation, code_rate): {key}") from exc

        ch = self._channel_type_for_cn()
        if ch == "Ricean":
            return ricean
        elif ch == "Rayleigh":
            return rayleigh
        else:
            return gaussian

    # -------------------------------------------------------------------------
    # Receiver noise input power (P_n)
    # -------------------------------------------------------------------------

    def noise_power_dbw(self) -> float:
        """Receiver noise power Pn [dBW] = F + 10 log10(k T0 B).

        Ref. Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        k = 1.38e-23
        T0 = 290.0
        thermal_dbw = self._db10(k * T0 * self.noise_bw_hz)
        return self.noise_figure_db + thermal_dbw

    # -------------------------------------------------------------------------
    # Minimum receiver input power (P_smin)
    # -------------------------------------------------------------------------

    def min_receiver_power_dbw(self) -> float:
        """Minimum receiver input power Ps_min [dBW].

        Ref. Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        return self.cn_required_db() + self.noise_power_dbw()

    # -------------------------------------------------------------------------
    # Antenna gain (G) and feeder loss (L_f)
    # -------------------------------------------------------------------------

    def _default_ant_gain_dbd(self) -> float:
        """
        Default receive antenna gain G [dBd].

        FX (Table 26, Rec. ITU-R BT.2036-5):
          Band III:  7 dBd
          Band IV:  10 dBd
          Band V:   12 dBd

        PO/PI portable (Table 28, Rec. ITU-R BT.2033-2):
          Band III:  -2 dBd
          Band IV:    0 dBd
          Band V:     0 dBd

        MO (Table 30, Rec. ITU-R BT.2033-2):
          Band III:  -5 dBd
          Band IV:   -2 dBd
          Band V:    -1 dBd

        PO/PI handheld (Table 29, Rec. ITU-R BT.2033-2):
          474 MHz → -12 dBd
          698 MHz →  -9 dBd
          858 MHz →  -7 dBd
        """

        # --- helper: UHF handheld interpolation (BT.2033 Table 29) --------------
        def handheld_uhf_gain(f_mhz: float) -> float:
            """
            G(f) for handheld UHF.

            Ref. Table 29, Rec. ITU-R BT.2033-2.
              (474 MHz, -12 dBd)
              (698 MHz,  -9 dBd)
              (858 MHz,  -7 dBd)
            Implementation rule:
            - 470–474 MHz  → value at 474 MHz
            - 474–858 MHz  → log-frequency interpolation (Final Acts RRC-06, Annex 2, A.2.1.6)
            - 858–862 MHz  → value at 858 MHz
            """
            if f_mhz < 470.0 or f_mhz > 862.0:
                raise ValueError(
                    f"Handheld UHF antenna gain is defined only for 470–862 MHz; "
                    f"got {f_mhz} MHz."
                )

            # Anchor points
            f1, g1 = 474.0, -12.0
            f2, g2 = 698.0, -9.0
            f3, g3 = 858.0, -7.0

            # Clamping zones
            if f_mhz <= f1:
                return g1
            if f_mhz >= f3:
                return g3

            # Interpolation segments with log-frequency rule
            if f_mhz <= f2:
                # between 474 and 698 MHz
                f_inf, g_inf = f1, g1
                f_sup, g_sup = f2, g2
            else:
                # between 698 and 858 MHz
                f_inf, g_inf = f2, g2
                f_sup, g_sup = f3, g3

            return self._log_interp(f_mhz, f_inf, g_inf, f_sup, g_sup)

        # ---------------- main logic ----------------
        match self.reception_mode:

            # ----------------------------------------------------------
            # FIXED ROOFTOP — Table 26 (Rec. ITU-R BT.2036-5)
            # ----------------------------------------------------------
            case "FX":
                match self.band:
                    case "III":
                        return 7.0
                    case "IV":
                        return 10.0
                    case "V":
                        return 12.0
                    case _:
                        raise ValueError(
                            f"FX antenna gain not defined for freq={self.freq_mhz} MHz "
                            f"in Table 26, Rec. ITU-R BT.2036-5."
                        )

            # ----------------------------------------------------------
            # PORTABLE OUTDOOR / INDOOR — Tables 28, 29 (Rec. ITU-R BT.2033-2)
            # ----------------------------------------------------------
            case "PO" | "PI":
                match self.receiver_type:

                    # -----------------------------------------------
                    # Portable (not handheld) — Table 28 (Rec. ITU-R BT.2033-2)
                    # -----------------------------------------------
                    case "portable":
                        match self.band:
                            case "III":
                                return -2.0
                            case "IV":
                                return 0.0
                            case "V":
                                return 0.0
                            case _:
                                raise ValueError(
                                    f"Portable PO/PI gain undefined for Band {self.band} "
                                    f"in Table 28, BT.2033-2."
                                )

                    # -----------------------------------------------
                    # Handheld — Table 29 (Rec. ITU-R BT.2033-2, with UHF interpolation)
                    # -----------------------------------------------
                    case "handheld":
                        match self.band:
                            case "III":
                                raise ValueError(
                                    "Handheld antenna gain is not defined for Band III "
                                    "in Table 29, Rec. ITU-R BT.2033-2."
                                )
                            case "IV" | "V":
                                return handheld_uhf_gain(self.freq_mhz)
                            case _:
                                raise ValueError(
                                    f"Handheld PO/PI gain undefined for freq={self.freq_mhz} MHz."
                                )

            # ----------------------------------------------------------
            # MOBILE — Table 30 (Rec. ITU-R BT.2033-2)
            # ----------------------------------------------------------
            case "MO":
                match self.band:
                    case "III":
                        return -5.0
                    case "IV":
                        return -2.0
                    case "V":
                        return -1.0
                    case _:
                        raise ValueError(
                            f"MO antenna gain undefined for freq={self.freq_mhz} MHz "
                            f"in Table 30, BT.2033-2."
                        )

            # ----------------------------------------------------------
            # Unknown reception type
            # ----------------------------------------------------------
            case _:
                raise ValueError(f"Unknown reception mode: {self.reception_mode}")


    def _default_feeder_loss_db(self) -> float:
        """
        Default feeder loss Lf [dB].

        FX (Table 27, Rec. ITU-R BT.2036-5):
          Band III:  2 dB
          Band IV:   3 dB
          Band V:    5 dB
        PO/PI/MO (no reference found):
          0 dB
        """
        match self.reception_mode:

            # ----------------------------------------------------------
            # FIXED ROOFTOP — Table 27 (Rec. ITU-R BT.2036-5)
            # ----------------------------------------------------------
            case "FX":
                match self.band:
                    case "III":
                        return 2.0
                    case "IV":
                        return 3.0
                    case "V":
                        return 5.0
                    case _:
                        raise ValueError(
                            f"FX feeder loss not defined for freq={self.freq_mhz} MHz "
                            f"in  Table 27, Rec. ITU-R BT.2036-5."
                        )

            # ----------------------------------------------------------
            # PORTABLE or MOBILE
            # ----------------------------------------------------------
            case "PO" | "PI" | "MO":
                return 0.0

            # ----------------------------------------------------------
            # Unknown reception type
            # ----------------------------------------------------------
            case _:
                raise ValueError(f"Unknown reception mode: {self.reception_mode}")


    @property
    def G_dbd(self) -> float:
        """Antenna gain [dBd]."""
        return self.ant_gain_dbd if self.ant_gain_dbd is not None else self._default_ant_gain_dbd()


    @property
    def Lf_db(self) -> float:
        """Feeder loss [dB]."""
        return self.feeder_loss_db if self.feeder_loss_db is not None else self._default_feeder_loss_db()

    # -------------------------------------------------------------------------
    # Height loss (L_h)
    # -------------------------------------------------------------------------

    def _default_height_loss_db(self) -> float:
        """
        Default height loss Lh [dB] for ~1.5 m receive height.

        Based strictly on Table 3-3, Close 3.2.2.1, Chapter 3 to Annex 2,
        Final Acts of RRC-06 (Ge06 Agreement):

            Frequency (MHz) :  200     500     800
            Height loss (dB):   12      16      18

        Log-frequency interpolation rule (RRC-06, Annex 2, A.2.1.6) applies.
        Valid only in Bands III-V (174-230 MHz /470–862 MHz) and for suburban coverage.
        """

        # FX: no height loss
        if self.reception_mode == "FX":
            return 0.0

        f = self.freq_mhz

        # Allowed DVB height-loss range: Band III–V only
        if f < 174 or f > 862:
            raise ValueError(
                f"Height loss Lh is only defined for Bands III–V (174-230 MHz /470–862 MHz). "
                f"Got freq={f} MHz."
            )

        # Table 3-3 frequency anchor points
        points = [
            (200.0, 12.0),
            (500.0, 16.0),
            (800.0, 18.0),
        ]

        # Pick finf, fsup for interpolation (with extrapolation at edges)
        if f <= 200:
            f_inf, L_inf = points[0]
            f_sup, L_sup = points[1]
        elif f <= 500:
            f_inf, L_inf = points[0]
            f_sup, L_sup = points[1]
        elif f <= 800:
            f_inf, L_inf = points[1]
            f_sup, L_sup = points[2]
        else:
            # f in 800–862 MHz: top extrapolation
            f_inf, L_inf = points[1]
            f_sup, L_sup = points[2]

        # Apply log-frequency interpolation
        return self._log_interp(f, f_inf, L_inf, f_sup, L_sup)


    @property
    def Lh_db(self) -> float:
        """Height loss Lh [dB]."""
        return self.height_loss_db if self.height_loss_db is not None else self._default_height_loss_db()

    # -------------------------------------------------------------------------
    # Building entry loss (L_b) and building-loss standard deviation (σ_b)
    # -------------------------------------------------------------------------

    def _default_building_entry_loss_db(self) -> float:
        """
        Default building entry loss Lb [dB] for PI in UHF.

        Ref. Table 27, Rec. ITU-R BT.2033-2:
          high   : 7 dB
          medium : 11 dB
          low    : 15 dB
        """
        if self.reception_mode == "PI" and self._is_uhf:
            mean_lb, _ = self.TABLE_BLD_LOSS[self.building_class]
            return mean_lb
        return 0.0

    def _default_sigma_building_db(self) -> float:
        """
        Default standard deviation building entry loss σ_b [dB] for PI, UHF.

        Ref. Table 27, Rec. ITU-R BT.2033-2:
          high   : 5 dB
          medium : 6 dB
          low    : 7 dB
        """
        if self.reception_mode == "PI" and self._is_uhf:
            _, sigma = self.TABLE_BLD_LOSS[self.building_class]
            return sigma
        return 0.0

    @property
    def sigma_b_db(self) -> float:
        """Building-related std dev σ_b [dB]."""
        return self.sigma_building_db if self.sigma_building_db is not None else self._default_sigma_building_db()


    # -------------------------------------------------------------------------
    # Location correction factor (C_l)
    # -------------------------------------------------------------------------

    def sigma_total_db(self) -> float:
        """Total std deviation σ_t [dB].

          σ_t [dB] = sqrt(σ_b² + σ_m²)
        Reference: Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2
        """
        return sqrt(self.sigma_b_db ** 2 + self.sigma_macro_db ** 2)


    def mu_factor(self) -> float:
        """µ distribution factor for given location probability.
        User parameter:
          self.location_probability = p (e.g. 0.95 for 95%)

        Below equation is based on section 3.4.5.3 of RRC-06 Final Acts (Ge06 Agreement):
          μ = Qi(1 - x/100)

        Here x is the percentage (100 * p), so:
          μ = Qi(1 - p)
        with 0.01 <= p <= 0.99.
        """
        p = self.location_probability
        x = 1.0 - p  # argument to Qi()
        return self._Qi(x)


    def location_correction_db(self) -> float:
        """Location correction factor C_l [dB].

          C_l = µ · σ_t
        Reference: Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        return self.mu_factor() * self.sigma_total_db()


    # -------------------------------------------------------------------------
    # Man-made noise (P_mmn)
    # -------------------------------------------------------------------------

    def man_made_noise_db(self) -> float:
        """Man-made noise allowance Pmmn [dB] from Tables 31–32, Rec. ITU-R BT.2033-2."""
        env = self.environment
        band_group = self._mmn_band_group
        if env not in self.TABLE_MMN or band_group not in self.TABLE_MMN[env]:
            raise ValueError(f"Pmmn not defined for env={env}, band_group={band_group}")
        cat = self._mmn_category
        try:
            return self.TABLE_MMN[env][band_group][cat]
        except KeyError as exc:
            raise ValueError(
                f"Pmmn not defined for category '{cat}' (env={env}, band_group={band_group})"
            ) from exc


    # -------------------------------------------------------------------------
    # Effective antenna aperture (A_a)
    # -------------------------------------------------------------------------

    def effective_aperture_dbm2(self) -> float:
        """
        Effective antenna aperture Aa [dB(m²)].

          Aa = G + 10 log10(1.64 * λ² / (4π))
        Reference: Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        c = 299_792_458  # light speed in vacuum (m/s)
        freq_hz = self.freq_mhz * 1e6
        wavelength = c / freq_hz
        factor = 1.64 * (wavelength ** 2) / (4.0 * pi)
        return self.G_dbd + self._db10(factor)


    # -------------------------------------------------------------------------
    # Minimum pfd at receiving place (φ_min)
    # -------------------------------------------------------------------------

    def min_pfd_dbw_per_m2(self) -> float:
        """
        Minimum power flux density φ_min [dB(W/m²)].

          φ_min = Ps_min – Aa + Lf
        Reference: Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        return self.min_receiver_power_dbw() - self.effective_aperture_dbm2() + self.Lf_db

    # -------------------------------------------------------------------------
    # Equivalent minimum field strength at receiving place (E_min)
    # -------------------------------------------------------------------------

    def Emin_dbuV_per_m(self) -> float:
        """
        Minimum equivalent field strength Emin [dB(µV/m)].

          Emin = φ_min + 145.8
        Reference: Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        return self.min_pfd_dbw_per_m2() + 145.8


    # -------------------------------------------------------------------------
    # Minimum median equivalent field strength (E_med)
    # -------------------------------------------------------------------------

    def Emed_dbuV_per_m(self) -> float:
        """
        Minimum median equivalent field strength E_med [dB(µV/m)].

          FX:
            E_med = Emin + Pmmn + C_l
          PO / MO:
            E_med = Emin + Pmmn + C_l + L_h
          PI:
            E_med = Emin + Pmmn + C_l + L_h + L_b
        Reference: Attachment 1 to Annex 1, Rec. ITU-R BT.2033-2.
        """
        Emin = self.Emin_dbuV_per_m()

        if self.reception_mode == "FX":
            Pmmn = self.man_made_noise_db()
            Cl = self.location_correction_db()
            return Emin + Pmmn + Cl

        elif self.reception_mode in {"PO", "MO"}:
            Pmmn = self.man_made_noise_db()
            Cl = self.location_correction_db()
            Lh = self.Lh_db
            return Emin + Pmmn + Cl + Lh

        elif self.reception_mode == "PI":
            Pmmn = self.man_made_noise_db()
            Cl = self.location_correction_db()
            Lh = self.Lh_db
            Lb = (
                self.building_entry_loss_db
                if self.building_entry_loss_db is not None
                else self._default_building_entry_loss_db()
            )
            return Emin + Pmmn + Cl + Lh + Lb

        else:
            raise ValueError(f"Unknown reception mode: {self.reception_mode}")


    # =========================================================================
    # Public API (factory constructors and summary)
    # =========================================================================

    @classmethod
    def fx(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        **overrides,
    ) -> "DVBT2":
        """Fixed rooftop reception (FX)."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="FX",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="portable",  # ignored for FX
            handheld_antenna_type="external",  # ignored for FX
            **overrides,
        )

    @classmethod
    def po_portable(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        **overrides,
    ) -> "DVBT2":
        """Portable OUTDOOR reception with portable (non-handheld) receiver."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="PO",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="portable",
            handheld_antenna_type="external",
            **overrides,
        )

    @classmethod
    def po_handheld_integrated(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        **overrides,
    ) -> "DVBT2":
        """Portable OUTDOOR reception with handheld receiver, integrated antenna."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="PO",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="handheld",
            handheld_antenna_type="integrated",
            **overrides,
        )

    @classmethod
    def po_handheld_external(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        **overrides,
    ) -> "DVBT2":
        """Portable OUTDOOR reception with handheld receiver, external antenna."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="PO",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="handheld",
            handheld_antenna_type="external",
            **overrides,
        )

    @classmethod
    def pi_portable(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        building_class: BuildingClass = "medium",
        **overrides,
    ) -> "DVBT2":
        """Portable INDOOR reception with portable (non-handheld) receiver."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="PI",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="portable",
            handheld_antenna_type="integrated",
            building_class=building_class,
            **overrides,
        )

    @classmethod
    def pi_handheld_integrated(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        building_class: BuildingClass = "medium",
        **overrides,
    ) -> "DVBT2":
        """Portable INDOOR reception with handheld receiver, integrated antenna."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="PI",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="handheld",
            handheld_antenna_type="integrated",
            building_class=building_class,
            **overrides,
        )

    @classmethod
    def pi_handheld_external(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        building_class: BuildingClass = "medium",
        **overrides,
    ) -> "DVBT2":
        """Portable INDOOR reception with handheld receiver, external antenna."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="PI",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="handheld",
            handheld_antenna_type="external",
            building_class=building_class,
            **overrides,
        )

    @classmethod
    def mo(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: CodeRate,
        **overrides,
    ) -> "DVBT2":
        """Mobile reception (MO) with adapted portable/mobile antenna."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="MO",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="portable",
            handheld_antenna_type="integrated",
            **overrides,
        )

    # -------------------------------------------------------------------------
    # Summary helper
    # -------------------------------------------------------------------------

    def summary(self) -> dict:
        """
        Return key quantities in (almost) the same order
        as Tables 12 and 13 of Rec. ITU-R BT.2033-2.
        """
        # Effective building loss to use (explicit override or default)
        Lb = (
            self.building_entry_loss_db
            if self.building_entry_loss_db is not None
            else self._default_building_entry_loss_db()
        )

        return {
            # ------------------------------------------------------------------
            # Basic identification / inputs (not explicitly listed in tables,
            # but useful context to put first)
            # ------------------------------------------------------------------
            "freq_mhz": self.freq_mhz,  # Frequency (Freq MHz)
            "band": self.band,  # Band III / IV / V
            "reception_mode": self.reception_mode,  # FX / PO / PI / MO
            "environment": self.environment,  # urban / rural
            "receiver_type": self.receiver_type,  # portable / handheld
            "handheld_antenna_type": self.handheld_antenna_type,
            "building_class": self.building_class,
            "modulation": self.modulation,
            "code_rate": self.code_rate,

            # ------------------------------------------------------------------
            # System performance & receiver noise (C/N, F, B, Pn, Ps_min)
            # ------------------------------------------------------------------
            "C/N_required_dB": self.cn_required_db(),  # Minimum C/N required by system
            "noise_figure_db": self.noise_figure_db,  # F (dB)
            "noise_bw_hz": self.noise_bw_hz,  # B (Hz)
            "Pn_dbw": self.noise_power_dbw(),  # Receiver noise input power Pn (dBW)
            "Ps_min_dbw": self.min_receiver_power_dbw(),
            # Min. receiver signal input power Ps_min (dBW)

            # ------------------------------------------------------------------
            # Antenna & feeder (Lf, Gd, Aa)
            # ------------------------------------------------------------------
            "Lf_db": self.Lf_db,  # Feeder loss Lf (dB)
            "G_dbd": self.G_dbd,  # Antenna gain Gd (dBd, rel. half-dipole)
            "Aa_dbm2": self.effective_aperture_dbm2(),  # Effective antenna aperture Aa (dBm²)

            # ------------------------------------------------------------------
            # Power flux density and field strength (Φmin, Emin)
            # ------------------------------------------------------------------
            "phi_min_dbw_per_m2": self.min_pfd_dbw_per_m2(),  # Φmin (dB(W/m²))
            "Emin_dbuV_per_m": self.Emin_dbuV_per_m(),  # Emin (dB(µV/m))

            # ------------------------------------------------------------------
            # Additional allowances and losses (Pmmn, Lh, Lb)
            # ------------------------------------------------------------------
            "Pmmn_db": self.man_made_noise_db(),  # Allowance for man-made noise Pmmn (dB)
            "Lh_db": self.Lh_db,  # Height loss Lh (dB)
            "Lb_db": Lb,  # Building / vehicle entry loss Lb (dB)

            # ------------------------------------------------------------------
            # Statistical parameters & location correction (σ, µ, Cl)
            # ------------------------------------------------------------------
            "sigma_b_db": self.sigma_b_db,  # σ_b (building)
            "sigma_m_db": self.sigma_macro_db,  # σ_m (macro-scale)
            "sigma_total_db": self.sigma_total_db(),  # σ_t
            "location_probability": self.location_probability,  # 70%, 95%, etc.
            "mu": self.mu_factor(),  # distribution factor µ
            "Cl_db": self.location_correction_db(),  # location correction factor Cl (dB)

            # ------------------------------------------------------------------
            # Final planning value (Emed)
            # ------------------------------------------------------------------
            "Emed_dbuV_per_m": self.Emed_dbuV_per_m(),
            # Minimum median equivalent field strength Emed

            # ------------------------------------------------------------------
            # Extra debug info (not in BT.2033 tables, but useful)
            # ------------------------------------------------------------------
            "mmn_category": self._mmn_category,  # which MMN category was used
        }