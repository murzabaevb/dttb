
# DVB-T2 Field Strength Calculator — `DVBT2` Python Class

This package provides a **complete, standards-based implementation** of DVB-T2 equivalent 
minimum field strength and minimum median equivalent field strength (planning value) calculations.

It follows the official ITU-R recommendations:
- **Rec. ITU-R BT.2033-2**  
  *“Planning criteria, including protection ratios, for second generation of digital terrestrial 
  television broadcasting systems in the VHF/UHF bands”*
- **Rec. ITU-R BT.2036-5**  
  *“Characteristics of a reference receiving system for frequency planning of digital terrestrial television systems”*
- **RRC‑06 GE06 Final Acts (Ge06 Agreement)**  
  Annex 2: Location correction, interpolation rules, log-frequency rules

The aim of the class is to allow regulators, engineers, and simulation developers to compute 
**Emin** and **Emed** values exactly as defined in BT.2033-2, including C/N thresholds, man-made 
noise, antenna gain, feeder loss, height loss, and building entry loss.

The `DVBT2` class computes:

1. C/N lookup (Table 2, Rec. ITU-R BT.2033‑2)
2. Receiver noise power calculation (P_n)
3. Minimum receiver input power (P_smin)
4. Effective antenna aperture (A_a)
5. Minimum PFD (Φ_min)
6. Minimum field strength (E_min)
7. Allowances:
   - Man-made noise (Tables 31–32, Rec. ITU-R BT.2033-2)
   - Height loss (Table 3-3, para. 3.2.2.1, Ch.3/Ann.2, GE06 Agreement)
   - Building entry loss (Table 27, Rec. ITU-R BT.2033-2)
8. Distribution factor (A.2.1.12, Eq. 26a–d, Ge06 Agreement)
9. Location correction factor 
10. Final minimum median equivalent field strength (E_med)

---

# Features

### ✔ Complete DVB‑T2 field strength chain  
Implements all ITU‑R equations, tables, and interpolation rules.

### ✔ All four reception modes
- **FX** – Fixed rooftop  
- **PO** – Portable outdoor  
- **PI** – Portable indoor  
- **MO** – Mobile  

### ✔ Accurate ITU‑based components:
- C/N values from **Table 2 BT.2033‑2**  
- Antenna gains from **Tables 26/BT.2036-5, 28-30/BT.2033-2**  
- Man‑made noise from **Tables 31–32/BT.2033-2**  
- Building entry loss from **Table 27/BT.2033-2**  
- Height loss via **Tables 3-3, Ch.3/Ann.2, GE06**  
- µ factor using **A.2.1.12, Eq. 26a-d, GE06**  

### ✔ Factory constructors
Simplifies object creation for FX/PO/PI/MO scenarios.

### ✔ Built‑in `summary()` aligned with ITU tables  
Outputs each step in the same order as BT.2033‑2 Table 12/13.

---

# Installation

Place both files:

```
dvbt2.py
dvbt2_cli.py
```

in your project directory.

To install as a console script:

Add to `pyproject.toml`:

```toml
[project.scripts]
dvbt2 = "dvbt2_cli:main"
```

Install:

```bash
pip install .
```
Alternatively, you may install the package directly from GitHub:
```bash
pip install git+https://github.com/murzabaevb/dttb.git
```

Now the command:

```bash
dvbt2 --help
```

is available globally.

---

# Quick Start

### Example: Fixed rooftop (FX) at 650 MHz

```python
from dvbt2 import DVBT2

d = DVBT2.fx(
    freq_mhz=650,
    environment="urban",
    modulation="64QAM",
    code_rate="3/5",
)

print(d.Emed_dbuV_per_m())
```

### Portable indoor handheld with integrated antenna

```python
d = DVBT2.pi_handheld_integrated(
    650, "urban", "16QAM", "1/2"
)

print(d.summary())
```

---

# `summary()` Output

`summary()` produces a dictionary that is similar to **Tables 12 and 13 ITU-R Rec. ITU-R BT.
2033-2** that would help the comparisons.

```python
from pprint import pprint
pprint(d.summary())
```

Gives:

```
freq_mhz                : 650
band                    : V
reception_mode          : PI
environment             : urban
C/N_required_dB         : 14.1
Pn_dbw                  : -108.28
Ps_min_dbw              : -94.18
G_dbd                   : -9.5
Lf_db                   : 0.0
Aa_dbm2                 : -11.5
phi_min_dbw_per_m2      : -82.1
Emin_dbuV_per_m         : 63.7
Pmmn_db                 : 0.0
Lh_db                   : 17.5
Lb_db                   : 11.0
sigma_total_db          : 8.2
mu                      : 1.645
Cl_db                   : 13.5
Emed_dbuV_per_m         : 105.7
```

Formatted line‑by‑line like ITU‑R BT.2033‑2.

---

# Optional Overrides

All inputs can be overridden:

```python
d = DVBT2.fx(
    650, "urban", "16QAM", "3/5",
    ant_gain_dbd=8,
    noise_figure_db=7,
    building_entry_loss_db=12,
    sigma_macro_db=6,
)
```

---

# Factory Constructors

Each reception mode has pre-configured constructors:

### Fixed rooftop:
```python
DVBT2.fx(...)
```

### Portable outdoor:
```python
DVBT2.po_portable(...)
DVBT2.po_handheld_integrated(...)
DVBT2.po_handheld_external(...)
```

### Portable indoor:
```python
DVBT2.pi_portable(...)
DVBT2.pi_handheld_integrated(...)
DVBT2.pi_handheld_external(...)
```

### Mobile:
```python
DVBT2.mo(...)
```

These automatically configure the relevant antenna gains, feeder losses, and other mode-specific parameters.

---

# Command‑Line Interface (CLI)

The CLI provides:

### **Three subcommands**

| Subcommand | Description |
|-----------|-------------|
| `dvbt2 summary` | Full ITU calculation chain (Tables 12 & 13). |
| `dvbt2 emed` | Outputs **E_med only**. |
| `dvbt2 debug` | Summary + diagnostic details. |

---

## CLI Usage

### Full Summary

```
dvbt2 summary --mode FX --freq 650 --environment urban --modulation 64QAM --code-rate 3/5
```

### E_med Only

```
dvbt2 emed --mode PI --freq 650 --environment urban --modulation 16QAM --code-rate 1/2
```

### Debug Mode

```
dvbt2 debug --mode PO --freq 650 --environment rural --modulation 64QAM --code-rate 3/4
```

Debug prints:

- Band detection  
- MMN category  
- Interpolated antenna gain  
- Interpolated height loss  
- σ_b, σ_m, σ_total  
- µ factor  
- Location correction  
- Full summary  

---

## Common CLI Arguments

### Required

```
--mode {FX,PO,PI,MO}
--freq <MHz>
--environment {urban,rural}
--modulation {QPSK,16QAM,64QAM,256QAM}
--code-rate {1/2,3/5,2/3,3/4,4/5,5/6}
```

### Receiver options (PO/PI)

```
--receiver-type {portable,handheld}
--handheld-antenna {integrated,external}
--building-class {high,medium,low}
```

### Overrides

```
--noise-figure
--noise-bw
--feeder-loss
--ant-gain
--height-loss
--building-loss
--sigma-macro
--sigma-building
--location-probability
```

---

## Example CLI Scenarios

### Fixed configuration in Table 13, Rec. ITU-R BT.2033-2

With default or recommended parameters:
```
dvbt2 summary --mode FX --freq 650 --environment rural \
              --modulation 256QAM --code-rate 2/3              
```

With override parameters as shown in the table:
```
dvbt2 summary --mode FX --freq 650 --environment rural \
              --modulation 256QAM --code-rate 2/3 \
              --noise-bw 7.77e6 --feeder-loss 4 --ant-gain 11 \
              --location-probability 0.7
```

### Portable outdoor/urban configuration in Table 13, Rec. ITU-R BT.2033-2

With default or recommended parameters:
```
dvbt2 summary --mode PO --freq 650 --environment rural \
              --modulation 64QAM --code-rate 2/3              
```

With override parameters as shown in the table:
```
dvbt2 summary --mode PO --freq 650 --environment urban \
              --modulation 64QAM --code-rate 2/3 --noise-bw 7.77e6 \
              --receiver-type portable --handheld-antenna integrated \
              --location-probability 0.7
```

### Portable indoor/urban configuration in Table 13, Rec. ITU-R BT.2033-2

With default or recommended parameters:
```
dvbt2 summary --mode PI --freq 650 --environment urban \
              --modulation 64QAM --code-rate 2/3              
```

With override parameters as shown in the table:
```
dvbt2 summary --mode PI --freq 650 --environment urban \
              --modulation 64QAM --code-rate 2/3 --noise-bw 7.77e6 \
              --receiver-type portable --handheld-antenna integrated \
              --location-probability 0.7
```

---

# License

This project is licensed under the GNU General Public License. See the LICENSE.txt file for details.
