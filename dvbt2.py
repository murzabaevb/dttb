from __future__ import annotations

from dataclasses import dataclass, field
from math import log10, sqrt
from typing import Literal, Tuple, Dict


ReceptionMode = Literal["FX", "PO", "PI", "MO"]
Environment = Literal["urban", "rural"]
Modulation = Literal["QPSK", "16QAM", "64QAM", "256QAM"]
ReceiverType = Literal["portable", "handheld"]
HandheldAntennaType = Literal["integrated", "external"]
BuildingClass = Literal["high", "medium", "low"]


@dataclass
class DVBT2:
    """
    DVB-T2 field-strength and C/N calculator following Rec. ITU-R BT.2033-2.

    Main features
    -------------
    • C/N from Table 2 (Ricean for FX, Rayleigh for PO/PI/MO).
    • Man-made noise Pmmn from Tables 31–32.
    • Height loss Lh and building entry loss Lb from Annex 4 (UHF).
    • Full Attachment-1 chain: Pn, Ps_min, Aa, φ_min, Emin, Cl, Emed.
    """

    # Core configuration
    freq_mhz: float
    reception_mode: ReceptionMode          # "FX", "PO", "PI", "MO"
    environment: Environment               # "urban", "rural"
    modulation: Modulation                 # "QPSK", "16QAM", "64QAM", "256QAM"
    code_rate: str                         # "1/2", "3/5", "2/3", "3/4", "4/5", "5/6"

    # For PO/PI only: portable vs handheld receiver
    receiver_type: ReceiverType = "portable"
    handheld_antenna_type: HandheldAntennaType = "integrated"

    # Indoor building class for PI (UHF)
    building_class: BuildingClass = "medium"

    # Receiver / RF chain
    noise_figure_db: float = 6.0
    noise_bw_hz: float = 7.61e6           # for 8 MHz DVB-T2

    # Optional overrides (None → internal defaults)
    feeder_loss_db: float | None = None
    ant_gain_dbd: float | None = None
    height_loss_db: float | None = None
    building_entry_loss_db: float | None = None
    sigma_macro_db: float = 5.5
    sigma_building_db: float | None = None
    location_probability: float = 0.95     # for C_l

    # -------------------------------------------------------------------------
    # Static tables: C/N (Table 2), Pmmn (Tables 31–32), µ, Lb (Table 27)
    # -------------------------------------------------------------------------

    # (modulation, code_rate) -> (Gaussian, Ricean, Rayleigh)
    TABLE2_CN: Dict[Tuple[str, str], Tuple[float, float, float]] = field(
        init=False,
        default_factory=lambda: {
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
        },
    )

    # Man-made noise Pmmn [dB] from Tables 31–32
    # env -> band -> category -> Pmmn
    MMN_DB: Dict[str, Dict[str, Dict[str, float]]] = field(
        init=False,
        default_factory=lambda: {
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
        },
    )

    # µ factors for location correction C_l
    MU_BY_PROB: Dict[float, float] = field(
        init=False,
        default_factory=lambda: {
            0.70: 0.52,
            0.90: 1.28,
            0.95: 1.64,
            0.99: 2.33,
        },
    )

    # Table 27: mean Lb, σ_b (UHF) by building class
    TABLE27_LB: Dict[BuildingClass, Tuple[float, float]] = field(
        init=False,
        default_factory=lambda: {
            "high":   (7.0, 5.0),
            "medium": (11.0, 6.0),
            "low":    (15.0, 7.0),
        },
    )

    # -------------------------------------------------------------------------
    # Basic helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _db10(x: float) -> float:
        return 10.0 * log10(x)

    @property
    def band(self) -> str:
        """Return 'III' for VHF Band III, 'IVV' for UHF Bands IV/V."""
        return "III" if self.freq_mhz < 300.0 else "IVV"

    # -------------------------------------------------------------------------
    # C/N (Table 2)
    # -------------------------------------------------------------------------

    def _channel_type_for_cn(self) -> str:
        """Ricean for FX, Rayleigh for PO/PI/MO."""
        return "Ricean" if self.reception_mode == "FX" else "Rayleigh"

    def cn_required_db(self) -> float:
        """Return required C/N [dB] from Table 2."""
        key = (self.modulation, self.code_rate)
        try:
            gaussian, ricean, rayleigh = self.TABLE2_CN[key]
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
    # Noise and receiver input power
    # -------------------------------------------------------------------------

    def noise_power_dbw(self) -> float:
        """Receiver noise power Pn [dBW] = F + 10 log10(k T0 B)."""
        k = 1.38e-23
        T0 = 290.0
        thermal_dbw = self._db10(k * T0 * self.noise_bw_hz)
        return self.noise_figure_db + thermal_dbw

    def min_receiver_power_dbw(self) -> float:
        """Minimum receiver input power Ps_min [dBW]."""
        return self.cn_required_db() + self.noise_power_dbw()

    # -------------------------------------------------------------------------
    # Antenna gain and feeder loss
    # -------------------------------------------------------------------------

    def _default_ant_gain_dbd(self) -> float:
        """
        Default receive antenna gain G [dBd].

        FX:
          Band III:  ~7 dBd
          UHF:      ~11 dBd
        PO/PI, receiver_type='portable':
          Band III:  -2.2 dBd
          UHF:        0 dBd
        PO/PI, receiver_type='handheld':
          (placeholder, usually lower than portable)
          Band III:  -4 dBd
          UHF:       -2 dBd
        MO:
          Band III:  -5 dBd
          UHF:       -2 dBd
        """
        if self.reception_mode == "FX":
            return 7.0 if self.band == "III" else 11.0

        if self.reception_mode in {"PO", "PI"}:
            if self.receiver_type == "handheld":
                return -4.0 if self.band == "III" else -2.0
            else:
                return -2.2 if self.band == "III" else 0.0

        # MO
        return -5.0 if self.band == "III" else -2.0

    def _default_feeder_loss_db(self) -> float:
        """
        Default feeder loss Lf [dB].

        FX:
          Band III:  2 dB
          UHF:       4 dB
        PO/PI/MO:
          0 dB
        """
        if self.reception_mode == "FX":
            return 2.0 if self.band == "III" else 4.0
        return 0.0

    @property
    def G_dbd(self) -> float:
        """Effective receive antenna gain [dBd]."""
        return self.ant_gain_dbd if self.ant_gain_dbd is not None else self._default_ant_gain_dbd()

    @property
    def Lf_db(self) -> float:
        """Receive feeder loss [dB]."""
        return self.feeder_loss_db if self.feeder_loss_db is not None else self._default_feeder_loss_db()

    # -------------------------------------------------------------------------
    # Height loss Lh
    # -------------------------------------------------------------------------

    def _default_height_loss_db(self) -> float:
        """
        Default height loss Lh [dB] for ~1.5 m receive height (PO/PI/MO, UHF).

        UHF (≈500–800 MHz, interpolated):
          rural: 16–18 dB
          urban: 23–25 dB
        VHF: 0 dB by default.
        """
        if self.reception_mode == "FX":
            return 0.0

        if self.band == "IVV":
            f = max(500.0, min(800.0, self.freq_mhz))
            if self.environment == "urban":
                return 23.0 + (25.0 - 23.0) * (f - 500.0) / 300.0
            else:
                return 16.0 + (18.0 - 16.0) * (f - 500.0) / 300.0

        return 0.0

    @property
    def Lh_db(self) -> float:
        """Height loss Lh [dB]."""
        return self.height_loss_db if self.height_loss_db is not None else self._default_height_loss_db()

    # -------------------------------------------------------------------------
    # Building entry loss Lb and σ_b
    # -------------------------------------------------------------------------

    def _default_building_entry_loss_db(self) -> float:
        """
        Default building entry loss Lb [dB] for PI, UHF.

        From Table 27:
          high   : 7 dB
          medium : 11 dB
          low    : 15 dB
        """
        if self.reception_mode == "PI" and self.band == "IVV":
            mean_lb, _ = self.TABLE27_LB[self.building_class]
            return mean_lb
        return 0.0

    def _default_sigma_building_db(self) -> float:
        """
        Default σ_b [dB] for PI, UHF (Table 27):

          high   : 5 dB
          medium : 6 dB
          low    : 7 dB
        """
        if self.reception_mode == "PI" and self.band == "IVV":
            _, sigma = self.TABLE27_LB[self.building_class]
            return sigma
        return 0.0

    @property
    def sigma_b_db(self) -> float:
        """Building-related std dev σ_b [dB]."""
        return self.sigma_building_db if self.sigma_building_db is not None else self._default_sigma_building_db()

    # -------------------------------------------------------------------------
    # Man-made noise Pmmn
    # -------------------------------------------------------------------------

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

    def man_made_noise_db(self) -> float:
        """Man-made noise allowance Pmmn [dB] from Tables 31–32."""
        env = self.environment
        band = self.band
        if env not in self.MMN_DB or band not in self.MMN_DB[env]:
            raise ValueError(f"Pmmn not defined for env={env}, band={band}")
        cat = self._mmn_category
        try:
            return self.MMN_DB[env][band][cat]
        except KeyError as exc:
            raise ValueError(f"Pmmn not defined for category '{cat}' (env={env}, band={band})") from exc

    # -------------------------------------------------------------------------
    # Antenna aperture, φ_min, Emin
    # -------------------------------------------------------------------------

    def effective_aperture_dbm2(self) -> float:
        """
        Effective antenna aperture Aa [dBm²]:

          Aa = G + 10 log10(1.64 * λ² / (4π))
        """
        c = 3.0e8
        freq_hz = self.freq_mhz * 1e6
        wavelength = c / freq_hz
        factor = 1.64 * (wavelength ** 2) / (4.0 * 3.141592653589793)
        return self.G_dbd + self._db10(factor)

    def min_pfd_dbw_per_m2(self) -> float:
        """
        Minimum power flux density φ_min [dB(W/m²)]:

          φ_min = Ps_min – Aa + Lf
        """
        return self.min_receiver_power_dbw() - self.effective_aperture_dbm2() + self.Lf_db

    def Emin_dbuV_per_m(self) -> float:
        """
        Minimum equivalent field strength Emin [dB(µV/m)]:

          Emin = φ_min + 145.8
        """
        return self.min_pfd_dbw_per_m2() + 145.8

    # -------------------------------------------------------------------------
    # Location correction C_l
    # -------------------------------------------------------------------------

    def sigma_total_db(self) -> float:
        """Total std dev σ_t [dB] = sqrt(σ_b² + σ_m²)."""
        return sqrt(self.sigma_b_db ** 2 + self.sigma_macro_db ** 2)

    def mu_factor(self) -> float:
        """µ factor for given location probability (linear interpolation)."""
        p = self.location_probability
        if p in self.MU_BY_PROB:
            return self.MU_BY_PROB[p]

        probs = sorted(self.MU_BY_PROB.keys())
        if p <= probs[0]:
            return self.MU_BY_PROB[probs[0]]
        if p >= probs[-1]:
            return self.MU_BY_PROB[probs[-1]]

        for lo, hi in zip(probs[:-1], probs[1:]):
            if lo <= p <= hi:
                mu_lo, mu_hi = self.MU_BY_PROB[lo], self.MU_BY_PROB[hi]
                t = (p - lo) / (hi - lo)
                return mu_lo + t * (mu_hi - mu_lo)

        return self.MU_BY_PROB[0.95]

    def location_correction_db(self) -> float:
        """Location correction C_l [dB] = µ · σ_t."""
        return self.mu_factor() * self.sigma_total_db()

    # -------------------------------------------------------------------------
    # E_med
    # -------------------------------------------------------------------------

    def Emed_dbuV_per_m(self) -> float:
        """
        Minimum median equivalent field strength E_med [dB(µV/m)]:

          FX:
            E_med = Emin + Pmmn + C_l
          PO / MO:
            E_med = Emin + Pmmn + C_l + L_h
          PI:
            E_med = Emin + Pmmn + C_l + L_h + L_b
        """
        Emin = self.Emin_dbuV_per_m()
        Pmmn = self.man_made_noise_db()
        Cl = self.location_correction_db()
        Lh = self.Lh_db
        Lb = (
            self.building_entry_loss_db
            if self.building_entry_loss_db is not None
            else self._default_building_entry_loss_db()
        )

        if self.reception_mode == "FX":
            return Emin + Pmmn + Cl
        elif self.reception_mode in {"PO", "MO"}:
            return Emin + Pmmn + Cl + Lh
        elif self.reception_mode == "PI":
            return Emin + Pmmn + Cl + Lh + Lb
        else:
            raise ValueError(f"Unknown reception mode: {self.reception_mode}")

    # -------------------------------------------------------------------------
    # Factory helpers for typical scenarios
    # -------------------------------------------------------------------------

    @classmethod
    def fx(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: str,
        **overrides,
    ) -> "DVBT2":
        """Fixed rooftop reception (FX)."""
        return cls(
            freq_mhz=freq_mhz,
            reception_mode="FX",
            environment=environment,
            modulation=modulation,
            code_rate=code_rate,
            receiver_type="portable",
            handheld_antenna_type="integrated",
            **overrides,
        )

    @classmethod
    def po_portable(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: str,
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
            handheld_antenna_type="integrated",
            **overrides,
        )

    @classmethod
    def po_handheld_integrated(
        cls,
        freq_mhz: float,
        environment: Environment,
        modulation: Modulation,
        code_rate: str,
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
        code_rate: str,
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
        code_rate: str,
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
        code_rate: str,
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
        code_rate: str,
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
        code_rate: str,
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
        """Return key quantities for inspection or debugging."""
        Lb = (
            self.building_entry_loss_db
            if self.building_entry_loss_db is not None
            else self._default_building_entry_loss_db()
        )

        return {
            "freq_mhz": self.freq_mhz,
            "band": self.band,
            "reception_mode": self.reception_mode,
            "receiver_type": self.receiver_type,
            "handheld_antenna_type": self.handheld_antenna_type,
            "environment": self.environment,
            "modulation": self.modulation,
            "code_rate": self.code_rate,
            "mmn_category": self._mmn_category,
            "building_class": self.building_class,
            "C/N_required_dB": self.cn_required_db(),
            "Pn_dbw": self.noise_power_dbw(),
            "Ps_min_dbw": self.min_receiver_power_dbw(),
            "G_dbd": self.G_dbd,
            "Lf_db": self.Lf_db,
            "Aa_dbm2": self.effective_aperture_dbm2(),
            "phi_min_dbw_per_m2": self.min_pfd_dbw_per_m2(),
            "Emin_dbuV_per_m": self.Emin_dbuV_per_m(),
            "Pmmn_db": self.man_made_noise_db(),
            "Lh_db": self.Lh_db,
            "Lb_db": Lb,
            "sigma_b_db": self.sigma_b_db,
            "sigma_m_db": self.sigma_macro_db,
            "sigma_total_db": self.sigma_total_db(),
            "mu": self.mu_factor(),
            "Cl_db": self.location_correction_db(),
            "Emed_dbuV_per_m": self.Emed_dbuV_per_m(),
        }
