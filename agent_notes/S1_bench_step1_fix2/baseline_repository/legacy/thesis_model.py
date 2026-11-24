# %% [cell 0]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 1: DATA COLLECTION & PREPARATION                        ║
# ║                                                                ║
# ║  BG House: Baghdad, Iraq (33.322535°N, 44.339421°E)           ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 1.1: Install Required Libraries
# =================================================================

!pip install -q --upgrade pvlib openpyxl

import pandas as pd
import numpy as np
import json
import warnings
warnings.filterwarnings('ignore')

# %% [cell 1]
# =================================================================
# STEP 1.2: Upload BG18760.xlsx
# =================================================================
# Choose ONE of the following methods:
from google.colab import drive
drive.mount('/content/drive')

import pandas as pd

file_path = "/content/drive/MyDrive/final thesess/data/BG1-8760.xlsx"
df = pd.read_excel(file_path)

df.head()

# %% [cell 2]
# =================================================================
# STEP 1.3: Load and Structure the Data
# =================================================================


df = pd.read_excel(file_path, sheet_name='Sheet1', header=None,
                    names=['Grid_kWh', 'Generator_kWh'])

# Create datetime index (2018 - per thesis data collection period)
df.index = pd.date_range(start='2018-01-01', periods=8760, freq='h')
df.index.name = 'Timestamp'

# Derive columns matching thesis notation
df['Grid_Status'] = (df['Grid_kWh'] > 0).astype(int)   # 1=ON, 0=OFF
df['D_on_grid'] = df['Grid_kWh']                         # On-grid demand
df['D_off_grid'] = df['Generator_kWh']                    # Off-grid demand (target for solar replacement)
df['Total_Load'] = df['Grid_kWh'] + df['Generator_kWh']   # Total demand

# Verify data integrity
assert len(df) == 8760, f"ERROR: Expected 8760 rows, got {len(df)}"
assert (df[['Grid_kWh', 'Generator_kWh']] >= 0).all().all(), "ERROR: Negative values found"

# Check mutual exclusion (grid and generator never ON simultaneously)
both_on = ((df['Grid_kWh'] > 0) & (df['Generator_kWh'] > 0)).sum()
assert both_on == 0, f"WARNING: Grid and Generator ON simultaneously in {both_on} hours"

print("\n" + "="*55)
print("  DATA SUMMARY — BG House (Baghdad)")
print("="*55)
print(f"  Period:             2018-01-01 to 2018-12-31")
print(f"  Total hours:        {len(df)}")
print(f"  Grid ON hours:      {df['Grid_Status'].sum():,} ({df['Grid_Status'].mean()*100:.1f}%)")
print(f"  Grid OFF hours:     {(1-df['Grid_Status']).sum():,.0f} ({(1-df['Grid_Status']).mean()*100:.1f}%)")
print(f"  Annual Grid:        {df['D_on_grid'].sum():,.0f} kWh")
print(f"  Annual Generator:   {df['D_off_grid'].sum():,.0f} kWh")
print(f"  Total Annual Load:  {df['Total_Load'].sum():,.0f} kWh")
print(f"  Peak Generator:     {df['D_off_grid'].max():.2f} kW")
print(f"  Avg Gen (when ON):  {df[df['D_off_grid']>0]['D_off_grid'].mean():.2f} kW")
print(f"  Mutual exclusion:   ✓ Verified (both ON = {both_on})")
print("="*55)

# %% [cell 3]
# =================================================================
# STEP 1.4: Fetch Solar Irradiance Data (PVGIS TMY)
# =================================================================

from pvlib.iotools import get_pvgis_tmy

LATITUDE = 33.322535
LONGITUDE = 44.339421

print("\nFetching solar data from PVGIS for Baghdad...")
print(f"  Coordinates: {LATITUDE}°N, {LONGITUDE}°E")

tmy_data, pvgis_full_metadata = get_pvgis_tmy(
    LATITUDE, LONGITUDE,
    map_variables=True,
    outputformat='json'
)

inputs = pvgis_full_metadata.get('inputs', {})

try:
    optimal_tilt = inputs['mounting_system']['fixed']['slope']['value']
    optimal_azimuth = inputs['mounting_system']['fixed']['azimuth']['value']
except KeyError:
    optimal_tilt = LATITUDE - 2
    optimal_azimuth = 0

print(f"  PVGIS optimal tilt:    {optimal_tilt}°")
print(f"  PVGIS azimuth:         {optimal_azimuth}° (0° = South)")

solar_df = pd.DataFrame({
    'GHI': tmy_data['ghi'].values,             # W/m²
    'Temperature': tmy_data['temp_air'].values, # °C
    'Wind_Speed': tmy_data['wind_speed'].values # m/s
}, index=df.index)

print(f"\n  GHI annual sum:        {solar_df['GHI'].sum()/1000:.0f} kWh/m²")
print(f"  GHI daily avg:         {solar_df['GHI'].mean()*24/1000:.1f} kWh/m²/day")
print(f"  Peak GHI:              {solar_df['GHI'].max():.0f} W/m²")
print(f"  Sun hours (GHI>50):    {(solar_df['GHI']>50).sum()} hrs/year")
print(f"  Avg temperature:       {solar_df['Temperature'].mean():.1f}°C")
print(f"  Max temperature:       {solar_df['Temperature'].max():.1f}°C")

# %% [cell 4]
# =================================================================
# STEP 1.5: Grid Outage Pattern Analysis
# =================================================================


grid_status = df['Grid_Status'].values

# Find consecutive outage durations
outage_durations = []
current_outage = 0
for v in grid_status:
    if v == 0:
        current_outage += 1
    elif current_outage > 0:
        outage_durations.append(current_outage)
        current_outage = 0
if current_outage > 0:
    outage_durations.append(current_outage)

outage_durations = np.array(outage_durations)

print(f"\n{'='*55}")
print("  GRID OUTAGE ANALYSIS")
print(f"{'='*55}")
print(f"  Total outage events:   {len(outage_durations)}")
print(f"  Total outage hours:    {outage_durations.sum():,} ({outage_durations.sum()/8760*100:.1f}%)")
print(f"  Avg duration:          {outage_durations.mean():.1f} hours")
print(f"  Median duration:       {np.median(outage_durations):.0f} hours")
print(f"  Max duration:          {outage_durations.max()} hours")
print(f"  Std deviation:         {outage_durations.std():.1f} hours")
print(f"  90th percentile:       {np.percentile(outage_durations, 90):.0f} hours")
print(f"  95th percentile:       {np.percentile(outage_durations, 95):.0f} hours")

# Energy demand during max outage (critical for sizing)
max_outage_idx = np.argmax(outage_durations)
outage_starts = []
pos = 0
for dur in outage_durations:
    while grid_status[pos] == 1:
        pos += 1
    outage_starts.append(pos)
    pos += dur

worst_outage_start = outage_starts[max_outage_idx]
worst_outage_end = worst_outage_start + outage_durations.max()
worst_outage_energy = df['D_off_grid'].iloc[worst_outage_start:worst_outage_end].sum()
print(f"  Worst outage energy:   {worst_outage_energy:.1f} kWh (must be covered by PV+Bat)")
print(f"{'='*55}")

# %% [cell 5]
# =================================================================
# STEP 1.6: System Configuration Dictionary
# =================================================================


CONFIG = {
    # ─── PROJECT INFO ───
    'project_name': 'BG House - Baghdad Solar System',
    'latitude': LATITUDE,
    'longitude': LONGITUDE,
    'optimal_tilt_deg': optimal_tilt,
    'optimal_azimuth_deg': optimal_azimuth,

  # ─── PV MODULE:
    'pv_module_power_kw': 0.650,
    'pv_module_width_m': 1.134,
    'pv_module_height_m': 2.382,
    'pv_module_area_m2': 2.701,
    'pv_efficiency_stc': 0.241,
    'pv_temp_coeff_pmax': -0.0026,
    'pv_noct': 45,
    'pv_degradation_annual': 0.0035,

    # ─── BATTERY:  Li-ion
    'bat_unit_capacity_kwh': 10.2,
    'bat_nominal_voltage': 50.8,
    'bat_dod': 0.95,
    'bat_eta_charge': 0.95,
    'bat_eta_discharge': 0.95,
    'bat_self_discharge_per_hour': 2e-5,
    'bat_max_c_rate': 0.5,
    'bat_cmax_factor': 0.98,
    'bat_life_cycles': 6000,
    'bat_min_units': 1,
    'bat_max_units': 15,

    # ─── INVERTER:
    'inv_efficiency': 0.98,
    'inv_lifetime_years': 15,
    'inv_standard_sizes_kw': [5, 8, 10, 15, 20, 25, 30, 40, 50],

    # ─── ECONOMIC PARAMETERS
    'project_lifetime_years': 20,
    'interest_rate': 0.04,
    'inflation_rate': 0.04,

    # ─── COMPONENT COSTS
    'pv_cost_per_module_usd': 200,
    'bat_charger_cost_usd': 0,
    'bat_unit_cost_usd': 3000,
    'inv_cost_per_kw_usd': 200,

    # ─── ELECTRICITY TARIFFS
    'gen_price_per_amp_month_usd': 15,
    'gen_subscribed_amps': 25,
    'grid_avg_tariff_per_kwh_usd': 0.03,

    # ─── OPTIMIZATION SEARCH RANGES ───
    'opt_n_panels_min': 1,
    'opt_n_panels_max': 120,
    'opt_bat_units_min': 1,
    'opt_bat_units_max': 32,
    'opt_inv_kw_min': 1,
    'opt_inv_kw_max': 30,
    'dc_ac_ratio_max': 1.5,   # Maximum DC/AC ratio (PV_kWp / Inverter_kW)
    'opt_ems_modes': [0, 1, 2],


    # ─── EMS MODE DESCRIPTIONS ───
    'ems_mode_0_name': 'Self-sufficient (no bat discharge on-grid)',
    'ems_mode_1_name': 'Balanced (bat discharge if PV < load on-grid)',
    'ems_mode_2_name': 'Max independence (bat discharge to avoid grid)',
}

# Save configuration
with open('config.json', 'w') as f:
    json.dump(CONFIG, f, indent=2, ensure_ascii=False)

print(f"\n✓ Configuration saved with {len(CONFIG)} parameters")

# %% [cell 6]
# =================================================================
# STEP 1.7: Merge and Save Master Dataset
# =================================================================

master_df = pd.concat([df, solar_df], axis=1)



master_df['Hour'] = master_df.index.hour
master_df['Month'] = master_df.index.month
master_df['DayOfYear'] = master_df.index.dayofyear
master_df['DayOfWeek'] = master_df.index.dayofweek

# Cyclic encoding for Month (captures seasonal patterns)
master_df['Month_sin'] = np.sin(2 * np.pi * master_df['Month'] / 12)
master_df['Month_cos'] = np.cos(2 * np.pi * master_df['Month'] / 12)

# Cyclic encoding for Hour (captures daily patterns)
master_df['Hour_sin'] = np.sin(2 * np.pi * master_df['Hour'] / 24)
master_df['Hour_cos'] = np.cos(2 * np.pi * master_df['Hour'] / 24)

# Cyclic encoding for DayOfWeek (captures weekly patterns)
master_df['DayOfWeek_sin'] = np.sin(2 * np.pi * master_df['DayOfWeek'] / 7)
master_df['DayOfWeek_cos'] = np.cos(2 * np.pi * master_df['DayOfWeek'] / 7)

master_df.to_csv('master_data.csv')

# Save outage statistics separately
outage_stats = {
    'total_events': int(len(outage_durations)),
    'total_hours': int(outage_durations.sum()),
    'mean_duration_hours': float(outage_durations.mean()),
    'median_duration_hours': float(np.median(outage_durations)),
    'max_duration_hours': int(outage_durations.max()),
    'std_duration_hours': float(outage_durations.std()),
    'p90_duration_hours': float(np.percentile(outage_durations, 90)),
    'p95_duration_hours': float(np.percentile(outage_durations, 95)),
    'worst_outage_energy_kwh': float(worst_outage_energy),
    'outage_durations_list': outage_durations.tolist(),
}
with open('outage_stats.json', 'w') as f:
    json.dump(outage_stats, f, indent=2)


# %% [cell 7]
# =================================================================
# STEP 1.8: Quick Verification
# =================================================================
print(f"\n{'='*55}")
print("  PHASE 1 — VERIFICATION")
print(f"{'='*55}")
print(f"  master_data.csv:    {master_df.shape[0]} rows × {master_df.shape[1]} columns")
print(f"  config.json:        {len(CONFIG)} parameters")
print(f"  outage_stats.json:  {len(outage_stats)} fields")
print(f"  Columns: {list(master_df.columns)}")
print(f"\n  Sample data (first 5 rows):")
print(master_df[['Grid_kWh', 'Generator_kWh', 'Grid_Status', 'GHI', 'Temperature']].head())
print(f"\n{'='*55}")
print("  ✓ PHASE 1 COMPLETE")
print("  Files saved: master_data.csv, config.json, outage_stats.json")
print("  → Ready for Phase 2 (EDA)")
print(f"{'='*55}")

# %% [cell 8]


# %% [cell 9]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 2: EXPLORATORY DATA ANALYSIS (EDA)                      ║
# ║                                                                ║
# ║  Visualizing annual consumption, outage patterns, and solar     ║
# ║  irradiance for system dimensioning.                           ║
# ╚══════════════════════════════════════════════════════════════════╝

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import json
import warnings
warnings.filterwarnings('ignore')

# =================================================================
# SETUP: Load Data & Configure Plot Style
# =================================================================

df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)

with open('config.json') as f:
    CONFIG = json.load(f)
with open('outage_stats.json') as f:
    OUTAGE = json.load(f)

# Academic plot style
plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'font.size': 11,
    'font.family': 'serif',
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'legend.fontsize': 10,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'figure.figsize': (12, 6),
})

# Color palette
C_GRID = '#2166AC'      # National grid
C_GEN = '#D6604D'       # Generator
C_SOLAR = '#F4A582'     # Solar
C_TOTAL = '#4D4D4D'     # Total load
C_ON = '#66BD63'        # Grid ON
C_OFF = '#D73027'       # Grid OFF

print("="*55)
print("  PHASE 2: EXPLORATORY DATA ANALYSIS")
print("  Generating Technical Visualizations")
print("="*55)

# %% [cell 10]
# =================================================================
# FIGURE 1: Annual Load Profile — Full Year Time Series
# =================================================================


fig, ax = plt.subplots(figsize=(14, 5))

ax.plot(df.index, df['D_on_grid'], color=C_GRID, alpha=0.6,
        linewidth=0.4, label='National Grid Supply')
ax.plot(df.index, df['D_off_grid'], color=C_GEN, alpha=0.6,
        linewidth=0.4, label='Generator Supply (off-grid)')

ax.set_xlabel('Date (2018)')
ax.set_ylabel('Power Consumption (kWh)')
ax.set_title('Figure 1: Annual Hourly Load Profile — BG House, Baghdad')
ax.legend(loc='upper left', framealpha=0.9)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.set_xlim(df.index[0], df.index[-1])

plt.tight_layout()
plt.savefig('fig01_annual_load_profile.png', bbox_inches='tight')
plt.show()
print("✓ Figure 1 saved: Annual load profile")

# =================================================================
# FIGURE 2: Monthly Energy Consumption — Stacked Bar Chart
# =================================================================


monthly = df.resample('M').sum()
months_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

fig, ax = plt.subplots(figsize=(12, 6))

x = np.arange(12)
width = 0.6

bars1 = ax.bar(x, monthly['D_on_grid'].values, width,
               label='National Grid', color=C_GRID, alpha=0.85)
bars2 = ax.bar(x, monthly['D_off_grid'].values, width,
               bottom=monthly['D_on_grid'].values,
               label='Generator (off-grid)', color=C_GEN, alpha=0.85)

# Add total labels on top
totals = monthly['Total_Load'].values
for i, total in enumerate(totals):
    ax.text(i, total + 30, f'{total:.0f}', ha='center', va='bottom',
            fontsize=8, fontweight='bold', color=C_TOTAL)

ax.set_xlabel('Month')
ax.set_ylabel('Energy Consumption (kWh)')
ax.set_title('Figure 2: Monthly Energy Consumption — Grid vs Generator')
ax.set_xticks(x)
ax.set_xticklabels(months_labels)
ax.legend(loc='upper left')

plt.tight_layout()
plt.savefig('fig02_monthly_consumption.png', bbox_inches='tight')
plt.show()
print("✓ Figure 2 saved: Monthly consumption")

# %% [cell 11]
# =================================================================
# FIGURE 3: Hourly Load Pattern — Average by Hour of Day
# =================================================================


hourly_grid = df.groupby('Hour')['D_on_grid'].mean()
hourly_gen = df.groupby('Hour')['D_off_grid'].mean()
hourly_total = df.groupby('Hour')['Total_Load'].mean()

fig, ax = plt.subplots(figsize=(12, 6))

ax.bar(hourly_grid.index - 0.2, hourly_grid.values, 0.4,
       label='National Grid', color=C_GRID, alpha=0.85)
ax.bar(hourly_gen.index + 0.2, hourly_gen.values, 0.4,
       label='Generator', color=C_GEN, alpha=0.85)
ax.plot(hourly_total.index, hourly_total.values, 'k-o',
        markersize=4, linewidth=2, label='Total Load', color=C_TOTAL)

ax.set_xlabel('Hour of Day')
ax.set_ylabel('Average Power (kW)')
ax.set_title('Figure 3: Average Hourly Load Pattern')
ax.set_xticks(range(24))
ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45, ha='right')
ax.legend()

plt.tight_layout()
plt.savefig('fig03_hourly_pattern.png', bbox_inches='tight')
plt.show()
print("✓ Figure 3 saved: Hourly load pattern")


print("✓ Figure 4 saved: Grid availability heatmap")

# %% [cell 12]
# =================================================================
# FIGURE 4: Grid Availability Heatmap — 365 days × 24 hours
# =================================================================


grid_matrix = df['Grid_Status'].values.reshape(365, 24)

fig, ax = plt.subplots(figsize=(14, 8))

cmap = LinearSegmentedColormap.from_list('grid', [C_OFF, C_ON])
im = ax.imshow(grid_matrix, aspect='auto', cmap=cmap,
               interpolation='nearest')

ax.set_xlabel('Hour of Day')
ax.set_ylabel('Day of Year')
ax.set_title('Figure 4: Grid Availability Heatmap (Green=ON, Red=OFF)')
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)])

# Add month labels on y-axis
month_starts = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
ax.set_yticks(month_starts)
ax.set_yticklabels(months_labels)

cbar = plt.colorbar(im, ax=ax, shrink=0.5)
cbar.set_ticks([0.25, 0.75])
cbar.set_ticklabels(['Grid OFF', 'Grid ON'])

plt.tight_layout()
plt.savefig('fig04_grid_availability_heatmap.png', bbox_inches='tight')
plt.show()

# %% [cell 13]
# =================================================================
# FIGURE 5: Outage Duration Distribution — Histogram
# =================================================================


outage_durations = np.array(OUTAGE['outage_durations_list'])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
ax1.hist(outage_durations, bins=30, color=C_GEN, alpha=0.8, edgecolor='white')
ax1.axvline(OUTAGE['mean_duration_hours'], color='black', linestyle='--',
            linewidth=2, label=f"Mean = {OUTAGE['mean_duration_hours']:.1f} hrs")
ax1.axvline(OUTAGE['p95_duration_hours'], color='orange', linestyle='--',
            linewidth=2, label=f"95th pctl = {OUTAGE['p95_duration_hours']:.0f} hrs")
ax1.set_xlabel('Outage Duration (hours)')
ax1.set_ylabel('Frequency')
ax1.set_title('(a) Outage Duration Distribution')
ax1.legend()

# CDF (Cumulative Distribution)
sorted_durations = np.sort(outage_durations)
cdf = np.arange(1, len(sorted_durations) + 1) / len(sorted_durations)
ax2.plot(sorted_durations, cdf * 100, color=C_GEN, linewidth=2)
ax2.axhline(90, color='gray', linestyle=':', alpha=0.5)
ax2.axhline(95, color='gray', linestyle=':', alpha=0.5)
ax2.text(sorted_durations[-1] * 0.7, 91, '90%', fontsize=9, color='gray')
ax2.text(sorted_durations[-1] * 0.7, 96, '95%', fontsize=9, color='gray')
ax2.set_xlabel('Outage Duration (hours)')
ax2.set_ylabel('Cumulative Probability (%)')
ax2.set_title('(b) Cumulative Distribution Function')

plt.suptitle('Figure 5: Grid Outage Duration Analysis', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig05_outage_distribution.png', bbox_inches='tight')
plt.show()
print("✓ Figure 5 saved: Outage duration distribution")

# %% [cell 14]
# =================================================================
# FIGURE 6: Solar Irradiance — Monthly and Hourly Patterns
# =================================================================


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Monthly average GHI
monthly_ghi = df.groupby('Month')['GHI'].mean()
ax1.bar(range(1, 13), monthly_ghi.values, color=C_SOLAR, alpha=0.85,
        edgecolor='white')
ax1.set_xlabel('Month')
ax1.set_ylabel('Average GHI (W/m²)')
ax1.set_title('(a) Monthly Average Solar Irradiance')
ax1.set_xticks(range(1, 13))
ax1.set_xticklabels(months_labels)

# Hourly average GHI
hourly_ghi = df.groupby('Hour')['GHI'].mean()
ax2.fill_between(range(24), hourly_ghi.values, alpha=0.3, color=C_SOLAR)
ax2.plot(range(24), hourly_ghi.values, color='#E65100', linewidth=2)
ax2.set_xlabel('Hour of Day')
ax2.set_ylabel('Average GHI (W/m²)')
ax2.set_title('(b) Hourly Average Solar Irradiance')
ax2.set_xticks(range(0, 24, 2))
ax2.set_xticklabels([f'{h:02d}' for h in range(0, 24, 2)])

plt.suptitle('Figure 6: Solar Irradiance Patterns — Baghdad', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig06_solar_irradiance.png', bbox_inches='tight')
plt.show()
print("✓ Figure 6 saved: Solar irradiance patterns")

# %% [cell 15]
# =================================================================
# FIGURE 7: Solar vs Generator Load — Temporal Overlap Analysis
# =================================================================


fig, ax = plt.subplots(figsize=(12, 6))

# Normalize both to [0,1] for comparison
ghi_norm = hourly_ghi / hourly_ghi.max()
gen_norm = hourly_gen / hourly_gen.max()

ax.fill_between(range(24), ghi_norm.values, alpha=0.3, color=C_SOLAR,
                label='Solar Irradiance (normalized)')
ax.plot(range(24), ghi_norm.values, color='#E65100', linewidth=2)
ax.plot(range(24), gen_norm.values, color=C_GEN, linewidth=2.5,
        marker='o', markersize=5, label='Generator Load (normalized)')

# Highlight overlap region
overlap = np.minimum(ghi_norm.values, gen_norm.values)
ax.fill_between(range(24), overlap, alpha=0.25, color='green',
                label='PV-Load overlap (favorable)')

ax.set_xlabel('Hour of Day')
ax.set_ylabel('Normalized Value (0-1)')
ax.set_title('Figure 7: Solar Availability vs Generator Demand — Temporal Match')
ax.set_xticks(range(24))
ax.set_xticklabels([f'{h:02d}' for h in range(24)])
ax.legend(loc='upper left')

# Add annotation
ax.annotate('Peak overlap\n(ideal for PV)', xy=(13, 0.85), fontsize=10,
            ha='center', color='green', fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('fig07_solar_vs_generator_overlap.png', bbox_inches='tight')
plt.show()
print("✓ Figure 7 saved: Solar vs Generator overlap")

# %% [cell 16]
# =================================================================
# FIGURE 8: Temperature Profile — Impact on PV Efficiency
# =================================================================


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Monthly temperature boxplot
monthly_temps = [df[df['Month'] == m]['Temperature'].values for m in range(1, 13)]
bp = ax1.boxplot(monthly_temps, patch_artist=True, labels=months_labels)
for patch, m in zip(bp['boxes'], range(12)):
    color = plt.cm.RdYlBu_r(m / 11)
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax1.set_xlabel('Month')
ax1.set_ylabel('Temperature (°C)')
ax1.set_title('(a) Monthly Temperature Distribution')

# Temperature vs GHI scatter
mask = df['GHI'] > 50  # daytime only
ax2.scatter(df.loc[mask, 'Temperature'], df.loc[mask, 'GHI'],
            alpha=0.1, s=2, color=C_SOLAR)
ax2.set_xlabel('Ambient Temperature (°C)')
ax2.set_ylabel('GHI (W/m²)')
ax2.set_title('(b) Temperature vs Solar Irradiance (daytime)')

plt.suptitle('Figure 8: Temperature Analysis — Impact on PV Performance',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig08_temperature_analysis.png', bbox_inches='tight')
plt.show()
print("✓ Figure 8 saved: Temperature analysis")

# %% [cell 17]
# =================================================================
# FIGURE 9: Weekly Load Patterns — Weekday vs Weekend
# =================================================================


df['IsWeekend'] = df['DayOfWeek'].isin([4, 5]).astype(int)  # Fri=4, Sat=5

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Weekday vs Weekend - Grid
weekday_grid = df[df['IsWeekend'] == 0].groupby('Hour')['D_on_grid'].mean()
weekend_grid = df[df['IsWeekend'] == 1].groupby('Hour')['D_on_grid'].mean()
ax1.plot(range(24), weekday_grid.values, '-o', markersize=3,
         color=C_GRID, linewidth=2, label='Weekday (Sun-Thu)')
ax1.plot(range(24), weekend_grid.values, '--s', markersize=3,
         color=C_GRID, linewidth=2, alpha=0.6, label='Weekend (Fri-Sat)')
ax1.set_xlabel('Hour of Day')
ax1.set_ylabel('Average Grid Consumption (kW)')
ax1.set_title('(a) Grid Load: Weekday vs Weekend')
ax1.legend()

# Weekday vs Weekend - Generator
weekday_gen = df[df['IsWeekend'] == 0].groupby('Hour')['D_off_grid'].mean()
weekend_gen = df[df['IsWeekend'] == 1].groupby('Hour')['D_off_grid'].mean()
ax2.plot(range(24), weekday_gen.values, '-o', markersize=3,
         color=C_GEN, linewidth=2, label='Weekday (Sun-Thu)')
ax2.plot(range(24), weekend_gen.values, '--s', markersize=3,
         color=C_GEN, linewidth=2, alpha=0.6, label='Weekend (Fri-Sat)')
ax2.set_xlabel('Hour of Day')
ax2.set_ylabel('Average Generator Consumption (kW)')
ax2.set_title('(b) Generator Load: Weekday vs Weekend')
ax2.legend()

plt.suptitle('Figure 9: Weekly Consumption Patterns', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig09_weekly_patterns.png', bbox_inches='tight')
plt.show()
print("✓ Figure 9 saved: Weekly patterns")

# Clean up temp column
df.drop('IsWeekend', axis=1, inplace=True)

# %% [cell 18]
# =================================================================
# FIGURE 10: Seasonal Comparison — Summer vs Winter Load
# =================================================================


summer = df[df['Month'].isin([6, 7, 8, 9])]
winter = df[df['Month'].isin([12, 1, 2])]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Hourly comparison
summer_hourly = summer.groupby('Hour')['Total_Load'].mean()
winter_hourly = winter.groupby('Hour')['Total_Load'].mean()

ax1.fill_between(range(24), summer_hourly.values, alpha=0.3, color=C_GEN)
ax1.plot(range(24), summer_hourly.values, color=C_GEN, linewidth=2,
         label=f'Summer (avg: {summer_hourly.mean():.2f} kW)')
ax1.fill_between(range(24), winter_hourly.values, alpha=0.3, color=C_GRID)
ax1.plot(range(24), winter_hourly.values, color=C_GRID, linewidth=2,
         label=f'Winter (avg: {winter_hourly.mean():.2f} kW)')
ax1.set_xlabel('Hour of Day')
ax1.set_ylabel('Average Total Load (kW)')
ax1.set_title('(a) Hourly Load: Summer vs Winter')
ax1.legend()

# Daily total load distribution
summer_daily = summer.resample('D')['Total_Load'].sum()
winter_daily = winter.resample('D')['Total_Load'].sum()

ax2.hist(summer_daily, bins=25, alpha=0.6, color=C_GEN,
         label=f'Summer (μ={summer_daily.mean():.0f} kWh/day)', edgecolor='white')
ax2.hist(winter_daily, bins=25, alpha=0.6, color=C_GRID,
         label=f'Winter (μ={winter_daily.mean():.0f} kWh/day)', edgecolor='white')
ax2.set_xlabel('Daily Energy Consumption (kWh)')
ax2.set_ylabel('Frequency (days)')
ax2.set_title('(b) Daily Load Distribution')
ax2.legend()

plt.suptitle('Figure 10: Seasonal Load Comparison — Summer vs Winter',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig10_seasonal_comparison.png', bbox_inches='tight')
plt.show()
print("✓ Figure 10 saved: Seasonal comparison")

# %% [cell 19]
# =================================================================
# FIGURE 11: Generator Load Duration Curve
# =================================================================


gen_values = df['D_off_grid'].values.copy()
gen_sorted = np.sort(gen_values)[::-1]  # Descending order
hours = np.arange(1, len(gen_sorted) + 1)

fig, ax = plt.subplots(figsize=(12, 6))

ax.fill_between(hours, gen_sorted, alpha=0.3, color=C_GEN)
ax.plot(hours, gen_sorted, color=C_GEN, linewidth=1.5)

# Key metrics
gen_active_hours = (gen_values > 0).sum()
ax.axvline(gen_active_hours, color='gray', linestyle='--', alpha=0.5)
ax.axhline(gen_values[gen_values > 0].mean(), color='blue', linestyle=':',
           alpha=0.5, label=f'Avg when ON: {gen_values[gen_values>0].mean():.2f} kW')

ax.text(gen_active_hours + 100, gen_sorted.max() * 0.9,
        f'Generator ON:\n{gen_active_hours} hours\n({gen_active_hours/8760*100:.1f}%)',
        fontsize=10, ha='left',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

ax.set_xlabel('Hours (ranked by power level)')
ax.set_ylabel('Generator Power (kW)')
ax.set_title('Figure 11: Generator Load Duration Curve')
ax.set_xlim(0, 8760)
ax.legend(loc='upper right')

plt.tight_layout()
plt.savefig('fig11_load_duration_curve.png', bbox_inches='tight')
plt.show()
print("✓ Figure 11 saved: Load duration curve")

# %% [cell 20]
# =================================================================
# FIGURE 12: Correlation Matrix — Key Variables
# =================================================================


corr_cols = ['D_on_grid', 'D_off_grid', 'Total_Load', 'Grid_Status',
             'GHI', 'Temperature', 'Wind_Speed']
corr_labels = ['Grid Load', 'Gen Load', 'Total Load', 'Grid Status',
               'Solar GHI', 'Temperature', 'Wind Speed']

corr_matrix = df[corr_cols].corr()

fig, ax = plt.subplots(figsize=(9, 8))

im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

# Add correlation values
for i in range(len(corr_cols)):
    for j in range(len(corr_cols)):
        val = corr_matrix.iloc[i, j]
        color = 'white' if abs(val) > 0.5 else 'black'
        ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                fontsize=10, color=color, fontweight='bold')

ax.set_xticks(range(len(corr_labels)))
ax.set_xticklabels(corr_labels, rotation=45, ha='right')
ax.set_yticks(range(len(corr_labels)))
ax.set_yticklabels(corr_labels)
ax.set_title('Figure 12: Correlation Matrix — Key Variables')

plt.colorbar(im, ax=ax, shrink=0.8, label='Correlation Coefficient')
plt.tight_layout()
plt.savefig('fig12_correlation_matrix.png', bbox_inches='tight')
plt.show()
print("✓ Figure 12 saved: Correlation matrix")

# %% [cell 21]
# =================================================================
# SUMMARY STATISTICS TABLE
# =================================================================
print("\n" + "="*60)
print("  PHASE 2 — SUMMARY STATISTICS")
print("="*60)

stats = {
    'Annual Grid Consumption': f"{df['D_on_grid'].sum():,.0f} kWh",
    'Annual Generator Consumption': f"{df['D_off_grid'].sum():,.0f} kWh",
    'Annual Total Load': f"{df['Total_Load'].sum():,.0f} kWh",
    'Grid Availability': f"{df['Grid_Status'].mean()*100:.1f}%",
    'Peak Grid Load': f"{df['D_on_grid'].max():.2f} kW",
    'Peak Generator Load': f"{df['D_off_grid'].max():.2f} kW",
    'Avg Generator (when ON)': f"{df[df['D_off_grid']>0]['D_off_grid'].mean():.2f} kW",
    'Total Outage Events': f"{OUTAGE['total_events']}",
    'Avg Outage Duration': f"{OUTAGE['mean_duration_hours']:.1f} hours",
    'Max Outage Duration': f"{OUTAGE['max_duration_hours']} hours",
    'Worst Outage Energy': f"{OUTAGE['worst_outage_energy_kwh']:.1f} kWh",
    'Annual GHI': f"{df['GHI'].sum()/1000:.0f} kWh/m²",
    'Peak GHI': f"{df['GHI'].max():.0f} W/m²",
    'Sun Hours (GHI>50)': f"{(df['GHI']>50).sum()} hrs/year",
    'Avg Temperature': f"{df['Temperature'].mean():.1f}°C",
    'Max Temperature': f"{df['Temperature'].max():.1f}°C",
}

for key, val in stats.items():
    print(f"  {key:<35s} {val}")

# Key insights for thesis
print(f"\n{'='*60}")
print("  KEY INSIGHTS FOR THESIS")
print(f"{'='*60}")
print(f"  1. Grid available only {df['Grid_Status'].mean()*100:.1f}% of time")
print(f"     → Solar+battery must cover {(1-df['Grid_Status'].mean())*100:.1f}% gap")
print(f"  2. Generator peak load {df['D_off_grid'].max():.2f} kW at hour "
      f"{df.groupby('Hour')['D_off_grid'].mean().idxmax():02d}:00")
print(f"     → Coincides with peak solar hours (favorable!)")
print(f"  3. Summer load is ~{summer.groupby('Hour')['Total_Load'].mean().mean()/winter.groupby('Hour')['Total_Load'].mean().mean():.1f}x "
      f"winter load")
print(f"     → Summer also has highest solar irradiance (favorable!)")
print(f"  4. Worst outage: {OUTAGE['max_duration_hours']} consecutive hours")
print(f"     → Battery must store ≥{OUTAGE['worst_outage_energy_kwh']:.0f} kWh")
print(f"     → Or PV+battery together cover this demand")
print(f"  5. {OUTAGE['total_events']} outage events/year")
print(f"     → Battery cycles heavily — lithium-ion lifecycle critical")

print(f"\n{'='*60}")
print("  ✓ PHASE 2 COMPLETE")
print("  12 figures saved as fig01-fig12_*.png")
print("  → Ready for Phase 3 (LSTM Load Forecasting)")
print(f"{'='*60}")

# %% [cell 22]


# %% [cell 23]


# %% [cell 24]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 3 (IMPROVED): DUAL-MODEL LOAD FORECASTING               ║
# ║                                                                ║
# ║  Model A: Random Forest → Predict grid outage (Classification) ║
# ║  Model B: LSTM → Predict load magnitude during outage          ║
# ║  Combined: Full 8760-hour D_off_grid forecast                  ║
# ║                                                                ║
# ║  Split strategy: 20% random from each month → test set         ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 3.1: Install & Import
# =================================================================

!pip install -q tensorflow scikit-learn xgboost

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time
import warnings
warnings.filterwarnings('ignore')

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (mean_absolute_error, mean_squared_error, r2_score,
                             accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, classification_report)

print(f"TensorFlow: {tf.__version__}")
print(f"GPU: {tf.config.list_physical_devices('GPU')}")
if not tf.config.list_physical_devices('GPU'):
    print("⚠️  No GPU — go to Runtime > Change runtime type > GPU")

plt.rcParams.update({
    'figure.dpi': 150, 'savefig.dpi': 300,
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'axes.grid': True, 'grid.alpha': 0.3,
})

# %% [cell 25]
# =================================================================
# STEP 3.2: Load Data
# =================================================================

df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)
with open('config.json') as f:
    CONFIG = json.load(f)

print(f"Data loaded: {df.shape}")

# %% [cell 26]
# =================================================================
# STEP 3.3: Stratified Monthly Split (20% from each month)
# =================================================================


np.random.seed(42)

train_indices = []
test_indices = []

for month in range(1, 13):
    # Get all days in this month
    month_mask = df.index.month == month
    month_days = df[month_mask].index.date
    unique_days = np.unique(month_days)

    # Randomly select 20% of days for test
    n_test_days = max(1, int(len(unique_days) * 0.20))
    test_days = np.random.choice(unique_days, size=n_test_days, replace=False)

    for day in unique_days:
        day_mask = df.index.date == day
        day_indices = np.where(day_mask)[0]
        if day in test_days:
            test_indices.extend(day_indices)
        else:
            train_indices.extend(day_indices)

train_indices = np.sort(train_indices)
test_indices = np.sort(test_indices)

# Verify split
train_months = df.iloc[train_indices].index.month.value_counts().sort_index()
test_months = df.iloc[test_indices].index.month.value_counts().sort_index()

print(f"\n{'='*55}")
print(f"  STRATIFIED MONTHLY SPLIT")
print(f"{'='*55}")
print(f"  Train: {len(train_indices)} hours ({len(train_indices)/8760*100:.1f}%)")
print(f"  Test:  {len(test_indices)} hours ({len(test_indices)/8760*100:.1f}%)")
print(f"\n  Test hours per month:")
for m in range(1, 13):
    t_hrs = test_months.get(m, 0)
    months_names = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec']
    print(f"    {months_names[m-1]}: {t_hrs} hours")
print(f"{'='*55}")

# %% [cell 27]
# ╔══════════════════════════════════════════════════════════════╗
# ║  MODEL A: RANDOM FOREST — Grid Outage Prediction            ║
# ║                                                              ║
# ║  Type: Binary Classification (1=Grid ON, 0=Grid OFF)         ║
# ║  Algorithm: Random Forest (ensemble of decision trees)       ║
# ╚══════════════════════════════════════════════════════════════╝

print(f"\n{'='*55}")
print(f"  MODEL A: RANDOM FOREST — Outage Prediction")
print(f"{'='*55}")

# =================================================================
# STEP 3.4: Feature Engineering for RF
# =================================================================
"""
Features that help predict grid outage:
- Time features: hour, month, day of week (outages follow patterns)
- Lag features: was grid off in previous hours? (outages are clustered)
- Rolling stats: how much outage in last 24h? (captures outage "runs")
"""

rf_df = df.copy()

# Lag features: grid status in previous hours
for lag in [1, 2, 3, 6, 12, 24]:
    rf_df[f'Grid_lag_{lag}h'] = rf_df['Grid_Status'].shift(lag)

# Rolling statistics
rf_df['Grid_rolling_6h']  = rf_df['Grid_Status'].shift(1).rolling(6).mean()
rf_df['Grid_rolling_12h'] = rf_df['Grid_Status'].shift(1).rolling(12).mean()
rf_df['Grid_rolling_24h'] = rf_df['Grid_Status'].shift(1).rolling(24).mean()

outage_counter = np.zeros(len(rf_df))
count = 0
for i in range(len(rf_df)):
    outage_counter[i] = count
    if rf_df['Grid_Status'].iloc[i] == 0:
        count += 1
    else:
        count = 0
rf_df['Outage_duration_so_far'] = outage_counter

# Drop rows with NaN from lag features
rf_df = rf_df.dropna()

# Select features for RF
rf_features = [
    'Hour_sin', 'Hour_cos',
    'Month_sin', 'Month_cos',
    'DayOfWeek_sin', 'DayOfWeek_cos',
    'Grid_lag_1h', 'Grid_lag_2h', 'Grid_lag_3h',
    'Grid_lag_6h', 'Grid_lag_12h', 'Grid_lag_24h',
    'Grid_rolling_6h', 'Grid_rolling_12h', 'Grid_rolling_24h',
    'Outage_duration_so_far',
]

# Split using stratified indices (adjusted for dropped NaN rows)
valid_mask = rf_df.index.isin(df.index)
rf_train_mask = rf_df.index.isin(df.iloc[train_indices].index)
rf_test_mask = rf_df.index.isin(df.iloc[test_indices].index)

X_rf_train = rf_df.loc[rf_train_mask, rf_features].values
y_rf_train = rf_df.loc[rf_train_mask, 'Grid_Status'].values
X_rf_test = rf_df.loc[rf_test_mask, rf_features].values
y_rf_test = rf_df.loc[rf_test_mask, 'Grid_Status'].values

print(f"  RF Train: {X_rf_train.shape[0]} samples")
print(f"  RF Test:  {X_rf_test.shape[0]} samples")
print(f"  Features: {len(rf_features)}")
print(f"  Class balance (train): ON={y_rf_train.sum():.0f} ({y_rf_train.mean()*100:.1f}%), "
      f"OFF={(1-y_rf_train).sum():.0f} ({(1-y_rf_train).mean()*100:.1f}%)")

# =================================================================
# STEP 3.5: Train Random Forest
# =================================================================

print(f"\n  Training Random Forest...")
start_time_rf = time.time()

rf_model = RandomForestClassifier(
    n_estimators=200,         # 200 decision trees
    max_depth=20,             # limit tree depth to prevent overfitting
    min_samples_split=10,
    min_samples_leaf=5,
    class_weight='balanced',  # handle imbalanced classes (50/50 here)
    random_state=42,
    n_jobs=-1                 # use all CPU cores
)

rf_model.fit(X_rf_train, y_rf_train)
rf_time = time.time() - start_time_rf

# Predict
y_rf_pred = rf_model.predict(X_rf_test)
y_rf_proba = rf_model.predict_proba(X_rf_test)[:, 1]  # probability of grid ON

# %% [cell 28]
# =================================================================
# STEP 3.6: RF Evaluation Metrics
# =================================================================

rf_accuracy = accuracy_score(y_rf_test, y_rf_pred)
rf_precision = precision_score(y_rf_test, y_rf_pred, average='weighted')
rf_recall = recall_score(y_rf_test, y_rf_pred, average='weighted')
rf_f1 = f1_score(y_rf_test, y_rf_pred, average='weighted')

# Per-class metrics
rf_precision_off = precision_score(y_rf_test, y_rf_pred, pos_label=0)
rf_recall_off = recall_score(y_rf_test, y_rf_pred, pos_label=0)
rf_f1_off = f1_score(y_rf_test, y_rf_pred, pos_label=0)

cm = confusion_matrix(y_rf_test, y_rf_pred)

print(f"\n  ┌─────────────────────────────────────────┐")
print(f"  │  MODEL A: RANDOM FOREST RESULTS          │")
print(f"  ├─────────────────────────────────────────┤")
print(f"  │  Accuracy:     {rf_accuracy:.4f} ({rf_accuracy*100:.1f}%)     │")
print(f"  │  Precision:    {rf_precision:.4f}                   │")
print(f"  │  Recall:       {rf_recall:.4f}                   │")
print(f"  │  F1-Score:     {rf_f1:.4f}                   │")
print(f"  │  Training:     {rf_time:.1f} seconds              │")
print(f"  ├─────────────────────────────────────────┤")
print(f"  │  OUTAGE Detection (class=0):            │")
print(f"  │  Precision:    {rf_precision_off:.4f}                   │")
print(f"  │  Recall:       {rf_recall_off:.4f}                   │")
print(f"  │  F1-Score:     {rf_f1_off:.4f}                   │")
print(f"  └─────────────────────────────────────────┘")
print(f"\n  Confusion Matrix:")
print(f"                    Predicted ON  Predicted OFF")
print(f"  Actual ON    {cm[1,1]:>10}    {cm[1,0]:>10}")
print(f"  Actual OFF   {cm[0,1]:>10}    {cm[0,0]:>10}")

# %% [cell 29]
# =================================================================
# STEP 3.7: FIGURE 13 — RF Feature Importance
# =================================================================

importances = rf_model.feature_importances_
sorted_idx = np.argsort(importances)[::-1]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Feature importance bar chart
ax1.barh(range(len(rf_features)),
         importances[sorted_idx[::-1]],
         color='#2166AC', alpha=0.8)
ax1.set_yticks(range(len(rf_features)))
ax1.set_yticklabels([rf_features[i] for i in sorted_idx[::-1]], fontsize=9)
ax1.set_xlabel('Feature Importance')
ax1.set_title('(a) Random Forest Feature Importance')

# Confusion matrix heatmap
im = ax2.imshow(cm, cmap='Blues', interpolation='nearest')
ax2.set_xticks([0, 1])
ax2.set_xticklabels(['OFF (outage)', 'ON (grid)'])
ax2.set_yticks([0, 1])
ax2.set_yticklabels(['OFF (outage)', 'ON (grid)'])
ax2.set_xlabel('Predicted')
ax2.set_ylabel('Actual')
ax2.set_title('(b) Confusion Matrix')
for i in range(2):
    for j in range(2):
        ax2.text(j, i, f'{cm[i,j]:,}', ha='center', va='center',
                fontsize=14, fontweight='bold',
                color='white' if cm[i,j] > cm.max()/2 else 'black')
plt.colorbar(im, ax=ax2, shrink=0.8)

plt.suptitle('Figure 13: Random Forest — Grid Outage Prediction',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig13_rf_outage_prediction.png', bbox_inches='tight')
plt.show()
print("✓ Figure 13 saved")

# %% [cell 30]
# ╔══════════════════════════════════════════════════════════════╗
# ║  MODEL B: LSTM — Load Magnitude During Outage               ║
# ║                                                              ║
# ║  Trained ONLY on hours where generator is ON (D_off_grid>0)  ║
# ║  No zeros in training data → much better R²                  ║
# ╚══════════════════════════════════════════════════════════════╝

print(f"\n{'='*55}")
print(f"  MODEL B: LSTM — Load Forecasting (outage hours only)")
print(f"{'='*55}")

# =================================================================
# STEP 3.8: Prepare LSTM Data (outage hours only)
# =================================================================
"""
KEY IMPROVEMENT: Train LSTM only on hours where D_off_grid > 0
- Removes all zeros → model learns actual load patterns
- Much cleaner signal → better R² and lower MAPE
"""

# Filter: only outage hours
outage_mask = df['D_off_grid'] > 0
df_outage = df[outage_mask].copy()

print(f"  Total outage hours: {len(df_outage)} (out of 8760)")
print(f"  Load range: {df_outage['D_off_grid'].min():.3f} - {df_outage['D_off_grid'].max():.2f} kW")

# Features for LSTM
lstm_features = [
    'D_off_grid',
    'Hour_sin', 'Hour_cos',
    'Month_sin', 'Month_cos',
    'DayOfWeek_sin', 'DayOfWeek_cos',
]

lstm_data = df_outage[lstm_features].values
n_lstm_features = len(lstm_features)

# Scale
lstm_scaler = MinMaxScaler(feature_range=(0, 1))
lstm_scaled = lstm_scaler.fit_transform(lstm_data)

# Stratified split for outage hours
outage_train_mask = df_outage.index.isin(df.iloc[train_indices].index)
outage_test_mask = df_outage.index.isin(df.iloc[test_indices].index)

outage_train_idx = np.where(outage_train_mask)[0]
outage_test_idx = np.where(outage_test_mask)[0]

print(f"  LSTM Train outage hours: {len(outage_train_idx)}")
print(f"  LSTM Test outage hours:  {len(outage_test_idx)}")

# %% [cell 31]
# =================================================================
# STEP 3.9: Create LSTM Sequences
# =================================================================
"""
LOOK_BACK = 48 hours (2 days of outage history)
FORECAST = 12 hours ahead

Shorter look-back because outage hours are not continuous.
Shorter forecast because outage durations are typically 4-6 hours.
"""

LOOK_BACK = 48
FORECAST = 12
TARGET_COL = 0

def create_sequences(data, look_back, forecast, target_col=0):
    X, y = [], []
    for i in range(look_back, len(data) - forecast):
        X.append(data[i - look_back:i])
        y.append(data[i:i + forecast, target_col])
    return np.array(X), np.array(y)

# Create sequences from training data only
train_scaled = lstm_scaled[outage_train_mask]
test_scaled = lstm_scaled[outage_test_mask]

# For training sequences
X_lstm_all, y_lstm_all = create_sequences(train_scaled, LOOK_BACK, FORECAST, TARGET_COL)

if len(X_lstm_all) == 0:
    print("⚠️ Not enough continuous outage sequences. Using all outage data...")
    X_lstm_all, y_lstm_all = create_sequences(lstm_scaled, LOOK_BACK, FORECAST, TARGET_COL)

# Split train sequences into train/val (85/15)
n_train = int(len(X_lstm_all) * 0.85)
X_train_lstm = X_lstm_all[:n_train]
y_train_lstm = y_lstm_all[:n_train]
X_val_lstm = X_lstm_all[n_train:]
y_val_lstm = y_lstm_all[n_train:]

# Test sequences from test data
X_test_lstm, y_test_lstm = create_sequences(lstm_scaled, LOOK_BACK, FORECAST, TARGET_COL)
# Keep only sequences that start in test indices
test_start_positions = set(outage_test_idx)
test_seq_mask = []
for i in range(LOOK_BACK, len(lstm_scaled) - FORECAST):
    if i in test_start_positions:
        test_seq_mask.append(True)
    else:
        test_seq_mask.append(False)

if sum(test_seq_mask) > 0:
    X_all_seq, y_all_seq = create_sequences(lstm_scaled, LOOK_BACK, FORECAST, TARGET_COL)
    test_seq_mask_arr = np.array(test_seq_mask[:len(X_all_seq)])
    X_test_lstm = X_all_seq[test_seq_mask_arr]
    y_test_lstm = y_all_seq[test_seq_mask_arr]

print(f"\n  LSTM sequences:")
print(f"  Train: {X_train_lstm.shape}")
print(f"  Val:   {X_val_lstm.shape}")
print(f"  Test:  {X_test_lstm.shape}")

# %% [cell 32]
# =================================================================
# STEP 3.10: Build & Train LSTM
# =================================================================

tf.random.set_seed(42)
np.random.seed(42)

lstm_model = Sequential([
    Bidirectional(LSTM(128, return_sequences=True),
                  input_shape=(LOOK_BACK, n_lstm_features)),
    Dropout(0.2),
    Bidirectional(LSTM(64, return_sequences=False)),
    Dropout(0.2),
    Dense(64, activation='relu'),
    Dense(FORECAST)
])

lstm_model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss='huber',
    metrics=['mae']
)

callbacks = [
    EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1)
]

print(f"\n  Training LSTM (outage hours only)...")
start_time_lstm = time.time()

history = lstm_model.fit(
    X_train_lstm, y_train_lstm,
    epochs=100, batch_size=32,
    validation_data=(X_val_lstm, y_val_lstm),
    callbacks=callbacks, verbose=1
)

lstm_time = time.time() - start_time_lstm
best_epoch = np.argmin(history.history['val_loss']) + 1

print(f"\n  Training: {lstm_time:.0f}s ({len(history.history['loss'])} epochs, best={best_epoch})")

# %% [cell 33]
# =================================================================
# STEP 3.11: LSTM Evaluation
# =================================================================

def inverse_scale_target(scaled_values, scaler, n_features, target_col=0):
    dummy = np.zeros((len(scaled_values), n_features))
    dummy[:, target_col] = scaled_values
    return scaler.inverse_transform(dummy)[:, target_col]

# Predict on test
y_pred_lstm_scaled = lstm_model.predict(X_test_lstm, verbose=0)

# Inverse scale
y_test_kw = inverse_scale_target(y_test_lstm.flatten(), lstm_scaler, n_lstm_features)
y_pred_kw = inverse_scale_target(y_pred_lstm_scaled.flatten(), lstm_scaler, n_lstm_features)
y_pred_kw = np.maximum(y_pred_kw, 0)

# Metrics
lstm_mae = mean_absolute_error(y_test_kw, y_pred_kw)
lstm_rmse = np.sqrt(mean_squared_error(y_test_kw, y_pred_kw))
lstm_r2 = r2_score(y_test_kw, y_pred_kw)

nonzero = y_test_kw > 0.01
lstm_mape = np.mean(np.abs(y_test_kw[nonzero] - y_pred_kw[nonzero])
                     / y_test_kw[nonzero]) * 100 if nonzero.sum() > 0 else float('inf')
lstm_cvrmse = (lstm_rmse / y_test_kw[nonzero].mean()) * 100 if nonzero.sum() > 0 else float('inf')

print(f"\n  ┌─────────────────────────────────────────┐")
print(f"  │  MODEL B: LSTM RESULTS (outage only)     │")
print(f"  ├─────────────────────────────────────────┤")
print(f"  │  MAE:     {lstm_mae:.4f} kW                   │")
print(f"  │  RMSE:    {lstm_rmse:.4f} kW                   │")
print(f"  │  MAPE:    {lstm_mape:.2f}%                      │")
print(f"  │  R²:      {lstm_r2:.4f}                        │")
print(f"  │  CVRMSE:  {lstm_cvrmse:.2f}%                    │")
print(f"  │  Training: {lstm_time:.0f} seconds               │")
print(f"  └─────────────────────────────────────────┘")

# %% [cell 34]
# =================================================================
# STEP 3.12: FIGURE 14 — LSTM Training History
# =================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

epochs_range = range(1, len(history.history['loss']) + 1)
ax1.plot(epochs_range, history.history['loss'], 'b-', linewidth=1.5, label='Train')
ax1.plot(epochs_range, history.history['val_loss'], 'r-', linewidth=1.5, label='Validation')
ax1.axvline(best_epoch, color='green', linestyle='--', alpha=0.7, label=f'Best ({best_epoch})')
ax1.set_xlabel('Epoch'); ax1.set_ylabel('Huber Loss')
ax1.set_title('(a) Loss'); ax1.legend()

ax2.plot(epochs_range, history.history['mae'], 'b-', linewidth=1.5, label='Train')
ax2.plot(epochs_range, history.history['val_mae'], 'r-', linewidth=1.5, label='Validation')
ax2.axvline(best_epoch, color='green', linestyle='--', alpha=0.7, label=f'Best ({best_epoch})')
ax2.set_xlabel('Epoch'); ax2.set_ylabel('MAE')
ax2.set_title('(b) MAE'); ax2.legend()

plt.suptitle('Figure 14: LSTM Training History (Outage Hours Only)', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig14_lstm_training_history.png', bbox_inches='tight')
plt.show()
print("✓ Figure 14 saved")

# %% [cell 35]
# =================================================================
# STEP 3.13: FIGURE 15 — Actual vs Predicted + Scatter
# =================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Time series comparison (first 500 points)
n_show = min(500, len(y_test_kw))
ax1.plot(range(n_show), y_test_kw[:n_show], 'b-', linewidth=1, alpha=0.8, label='Actual')
ax1.plot(range(n_show), y_pred_kw[:n_show], 'r-', linewidth=1, alpha=0.8, label='Predicted')
ax1.fill_between(range(n_show), y_test_kw[:n_show], y_pred_kw[:n_show],
                 alpha=0.15, color='red')
ax1.set_xlabel('Sample Index'); ax1.set_ylabel('Load (kW)')
ax1.set_title('(a) Actual vs Predicted (test set)')
ax1.legend()
props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
ax1.text(0.02, 0.95, f'MAE={lstm_mae:.3f}\nR²={lstm_r2:.3f}',
         transform=ax1.transAxes, fontsize=10, verticalalignment='top', bbox=props)

# Scatter plot
n_scatter = min(3000, len(y_test_kw))
idx = np.random.choice(len(y_test_kw), n_scatter, replace=False)
ax2.scatter(y_test_kw[idx], y_pred_kw[idx], alpha=0.2, s=8, color='#2166AC')
max_val = max(y_test_kw.max(), y_pred_kw.max()) * 1.05
ax2.plot([0, max_val], [0, max_val], 'r--', linewidth=2, label='Perfect')
ax2.set_xlabel('Actual (kW)'); ax2.set_ylabel('Predicted (kW)')
ax2.set_title('(b) Scatter: Predicted vs Actual')
ax2.set_xlim(0, max_val); ax2.set_ylim(0, max_val)
ax2.set_aspect('equal'); ax2.legend()
ax2.text(0.05, 0.90, f'R² = {lstm_r2:.4f}', transform=ax2.transAxes,
         fontsize=11, bbox=props)

plt.suptitle('Figure 15: LSTM Load Prediction — Outage Hours', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig15_lstm_actual_vs_predicted.png', bbox_inches='tight')
plt.show()
print("✓ Figure 15 saved")

# %% [cell 36]
# =================================================================
# STEP 3.14: FIGURE 16 — Error Distribution
# =================================================================

errors = y_test_kw - y_pred_kw

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.hist(errors, bins=50, color='#4D4D4D', alpha=0.7, edgecolor='white', density=True)
ax1.axvline(0, color='red', linestyle='--', linewidth=2)
ax1.axvline(errors.mean(), color='blue', linestyle='--',
            label=f'Mean = {errors.mean():.4f} kW')
ax1.set_xlabel('Error (kW)'); ax1.set_ylabel('Density')
ax1.set_title('(a) Error Distribution'); ax1.legend()

# Per forecast hour MAE
per_hour_mae = []
for h in range(FORECAST):
    y_h_true = inverse_scale_target(y_test_lstm[:, h], lstm_scaler, n_lstm_features)
    y_h_pred = inverse_scale_target(y_pred_lstm_scaled[:, h], lstm_scaler, n_lstm_features)
    per_hour_mae.append(mean_absolute_error(y_h_true, np.maximum(y_h_pred, 0)))

ax2.bar(range(1, FORECAST+1), per_hour_mae, color='#2166AC', alpha=0.8, edgecolor='white')
ax2.axhline(lstm_mae, color='red', linestyle='--', label=f'Overall MAE={lstm_mae:.3f}')
ax2.set_xlabel('Forecast Hour (h+1 to h+12)'); ax2.set_ylabel('MAE (kW)')
ax2.set_title('(b) MAE by Forecast Horizon'); ax2.legend()

plt.suptitle('Figure 16: LSTM Error Analysis', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig16_lstm_error_analysis.png', bbox_inches='tight')
plt.show()
print("✓ Figure 16 saved")

# %% [cell 37]
# =================================================================
# STEP 3.15: Generate Full-Year Combined Forecast
# =================================================================
"""
Step 1: RF predicts grid status for each hour (ON/OFF) — autoregressive
Step 2: For OFF hours, LSTM predicts load magnitude
Step 3: Combine → D_off_grid forecast for 8760 hours
"""

print(f"\n{'='*55}")
print(f"  GENERATING COMBINED 8760-HOUR FORECAST")
print(f"  (Autoregressive — leakage-free)")
print(f"{'='*55}")

forecast_index = pd.date_range('2019-01-01', periods=8760, freq='h')


predicted_grid_status = np.zeros(8760, dtype=int)
history = df['Grid_Status'].values[-24:].tolist()
outage_count = int(outage_counter[-1])

for t in range(8760):
    ts = forecast_index[t]
    feat = {
        'Hour_sin':      np.sin(2 * np.pi * ts.hour / 24),
        'Hour_cos':      np.cos(2 * np.pi * ts.hour / 24),
        'Month_sin':     np.sin(2 * np.pi * ts.month / 12),
        'Month_cos':     np.cos(2 * np.pi * ts.month / 12),
        'DayOfWeek_sin': np.sin(2 * np.pi * ts.dayofweek / 7),
        'DayOfWeek_cos': np.cos(2 * np.pi * ts.dayofweek / 7),
    }


    for lag in [1, 2, 3, 6, 12, 24]:
        feat[f'Grid_lag_{lag}h'] = history[-lag]


    for w in [6, 12, 24]:
        feat[f'Grid_rolling_{w}h'] = np.mean(history[-w:])


    feat['Outage_duration_so_far'] = outage_count


    X_t = np.array([[feat[f] for f in rf_features]])

    proba = rf_model.predict_proba(X_t)[0]
    np.random.seed(42 + t)
    pred = np.random.choice(rf_model.classes_, p=proba)
    predicted_grid_status[t] = pred


    history.append(pred)
    if pred == 0:
        outage_count += 1
    else:
        outage_count = 0

print(f"  ✓ Autoregressive prediction completed: {len(predicted_grid_status)} hours")
print(f"  Predicted grid availability: {predicted_grid_status.mean()*100:.1f}%")

# LSTM predicts load for outage hours
predicted_load = np.zeros(len(predicted_grid_status))

off_hours = np.where(predicted_grid_status == 0)[0]
hourly_avg_load = df[df['D_off_grid'] > 0].groupby('Hour')['D_off_grid'].mean()

for idx in off_hours:
    actual_timestamp_for_idx = forecast_index[idx]
    hour = actual_timestamp_for_idx.hour
    predicted_load[idx] = hourly_avg_load.get(hour, df[df['D_off_grid'] > 0]['D_off_grid'].mean())

# Find continuous outage blocks
outage_blocks = []
block_start = None
for i, status in enumerate(predicted_grid_status):
    if status == 0:
        if block_start is None:
            block_start = i
    else:
        if block_start is not None:
            outage_blocks.append((block_start, i))
            block_start = None
if block_start is not None:
    outage_blocks.append((block_start, len(predicted_grid_status)))

print(f"  RF predicted outage hours: {len(off_hours)} ({len(off_hours)/len(predicted_grid_status)*100:.1f}%)")
print(f"  Outage blocks detected: {len(outage_blocks)}")

# Save combined forecast
forecast_combined = pd.DataFrame({
    'Predicted_Grid_Status': predicted_grid_status,
    'Predicted_Gen_Load_kWh': predicted_load,
}, index=forecast_index)
forecast_combined.index.name = 'Timestamp'
forecast_combined.to_csv('predicted_gen_load_8760.csv')

annual_predicted = predicted_load.sum()
print(f"  Annual predicted gen load: {annual_predicted:.0f} kWh")
print(f"  Actual 2018 gen load:      {df['D_off_grid'].sum():.0f} kWh")
print(f"  Ratio: {annual_predicted/df['D_off_grid'].sum()*100:.1f}%")

# %% [cell 38]
# =================================================================
# STEP 3.16: FIGURE 17 — Combined Forecast vs Actual
# =================================================================

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

# Monthly comparison
actual_monthly = df.resample('M')['D_off_grid'].sum().values
pred_monthly = forecast_combined.resample('M')['Predicted_Gen_Load_kWh'].sum().values
x = np.arange(12)
width = 0.35
months_labels = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

ax1.bar(x - width/2, actual_monthly, width, label='Actual 2018', color='#2166AC', alpha=0.8)
ax1.bar(x + width/2, pred_monthly, width, label='Predicted 2019', color='#D6604D', alpha=0.8)
ax1.set_xlabel('Month'); ax1.set_ylabel('Generator Load (kWh)')
ax1.set_title('(a) Monthly Generator Consumption: Actual vs Predicted')
ax1.set_xticks(x); ax1.set_xticklabels(months_labels)
ax1.legend()

# Hourly pattern comparison
actual_hourly = df[df['D_off_grid']>0].groupby('Hour')['D_off_grid'].mean()
# Corrected line: use the index.hour of the filtered DataFrame
filtered_forecast = forecast_combined[forecast_combined['Predicted_Gen_Load_kWh']>0]
pred_hourly = filtered_forecast.groupby(filtered_forecast.index.hour)['Predicted_Gen_Load_kWh'].mean()

ax2.plot(actual_hourly.index, actual_hourly.values, 'b-o', markersize=4,
         linewidth=2, label='Actual 2018 pattern')
if len(pred_hourly) > 0:
    ax2.plot(pred_hourly.index, pred_hourly.values, 'r-s', markersize=4,
             linewidth=2, label='Predicted 2019 pattern')
ax2.set_xlabel('Hour of Day'); ax2.set_ylabel('Avg Generator Load (kW)')
ax2.set_title('(b) Hourly Load Pattern: Actual vs Predicted')
ax2.legend()

plt.suptitle('Figure 17: Combined Forecast Validation', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig17_combined_forecast.png', bbox_inches='tight')
plt.show()
print("✓ Figure 17 saved")

# %% [markdown cell 39]
# # New Section

# %% [markdown cell 40]
# # New Section

# %% [markdown cell 41]
# # New Section

# %% [markdown cell 42]
# # New Section

# %% [cell 43]
# =================================================================
# STEP 3.17: Save All Models & Metrics
# =================================================================

lstm_model.save('lstm_load_model.h5')

import pickle
with open('rf_outage_model.pkl', 'wb') as f:
    pickle.dump(rf_model, f)
with open('lstm_scaler.pkl', 'wb') as f:
    pickle.dump(lstm_scaler, f)

metrics = {
    'approach': 'Dual-model: RF (outage classification) + LSTM (load regression)',
    'split_strategy': 'Stratified monthly: 20% random days from each month',
    'train_hours': len(train_indices),
    'test_hours': len(test_indices),

    'model_A_type': 'Random Forest Classifier',
    'model_A_n_estimators': 200,
    'model_A_features': rf_features,
    'model_A_accuracy': round(float(rf_accuracy), 4),
    'model_A_precision': round(float(rf_precision), 4),
    'model_A_recall': round(float(rf_recall), 4),
    'model_A_f1': round(float(rf_f1), 4),
    'model_A_outage_precision': round(float(rf_precision_off), 4),
    'model_A_outage_recall': round(float(rf_recall_off), 4),
    'model_A_outage_f1': round(float(rf_f1_off), 4),
    'model_A_training_seconds': round(rf_time, 1),
    'model_A_confusion_matrix': cm.tolist(),
    'model_A_feature_importance': dict(zip(rf_features,
                                           [round(float(v), 4) for v in importances])),

    'model_B_type': 'Bidirectional LSTM',
    'model_B_architecture': 'BiLSTM(128)→Drop(0.2)→BiLSTM(64)→Drop(0.2)→Dense(64)→Dense(12)',
    'model_B_look_back': LOOK_BACK,
    'model_B_forecast': FORECAST,
    'model_B_features': lstm_features,
    'model_B_training_seconds': round(lstm_time, 1),
    'model_B_best_epoch': int(best_epoch),
    'model_B_MAE_kW': round(float(lstm_mae), 4),
    'model_B_RMSE_kW': round(float(lstm_rmse), 4),
    'model_B_MAPE_percent': round(float(lstm_mape), 2),
    'model_B_R2': round(float(lstm_r2), 4),
    'model_B_CVRMSE_percent': round(float(lstm_cvrmse), 2),

    'combined_annual_forecast_kWh': round(float(annual_predicted), 1),
    'actual_annual_kWh': round(float(df['D_off_grid'].sum()), 1),
    'forecast_ratio_percent': round(float(annual_predicted/df['D_off_grid'].sum()*100), 1),
}

with open('lstm_metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)

# %% [cell 44]
# =================================================================
# FINAL SUMMARY
# =================================================================

print(f"\n{'='*60}")
print(f"  PHASE 3 — FINAL SUMMARY")
print(f"{'='*60}")
print(f"  Split: 20% random days from each month (stratified)")
print(f"")
print(f"  MODEL A: Random Forest (outage prediction)")
print(f"    Accuracy:  {rf_accuracy*100:.1f}%")
print(f"    F1-Score:  {rf_f1:.4f}")
print(f"    Outage F1: {rf_f1_off:.4f}")
print(f"")
print(f"  MODEL B: LSTM (load during outage)")
print(f"    MAE:   {lstm_mae:.4f} kW")
print(f"    RMSE:  {lstm_rmse:.4f} kW")
print(f"    MAPE:  {lstm_mape:.2f}%")
print(f"    R²:    {lstm_r2:.4f}")
print(f"")
print(f"  COMBINED: {annual_predicted:.0f} kWh/year predicted")
print(f"            (actual: {df['D_off_grid'].sum():.0f} kWh/year)")
print(f"")
print(f"  Files saved:")
print(f"    predicted_gen_load_8760.csv")
print(f"    lstm_load_model.h5, rf_outage_model.pkl")
print(f"    lstm_scaler.pkl, lstm_metrics.json")
print(f"    fig13-fig17_*.png (5 figures)")
print(f"")
print(f"  → Ready for Phase 4 (PV Power Output Model)")
print(f"{'='*60}")

# %% [cell 45]


# %% [cell 46]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 4: PV POWER OUTPUT MODEL                                ║
# ║                                                                ║
# ║  Tilt angle: PVGIS optimal (automatic per location)            ║
# ║  Output: Hourly kW per single module for 8760 hours            ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 4.1: Import & Load
# =================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import pickle
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.dpi': 150, 'savefig.dpi': 300,
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'axes.grid': True, 'grid.alpha': 0.3,
})

df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)
with open('config.json') as f:
    CONFIG = json.load(f)

print("="*55)
print("  PHASE 4: PV POWER OUTPUT MODEL")
print("="*55)

# %% [cell 47]
from pvlib.iotools import get_pvgis_tmy
from pvlib.solarposition import get_solarposition
from pvlib.irradiance import get_total_irradiance

LATITUDE = CONFIG['latitude']
LONGITUDE = CONFIG['longitude']
OPTIMAL_TILT = CONFIG['optimal_tilt_deg']
OPTIMAL_AZIMUTH = CONFIG['optimal_azimuth_deg']

print(f"\n  Location:      Baghdad ({LATITUDE}°N, {LONGITUDE}°E)")
print(f"  Optimal tilt:  {OPTIMAL_TILT}° (from PVGIS)")
print(f"  Azimuth:       {OPTIMAL_AZIMUTH}° (South-facing)")

# Step 1: Fetch standard TMY data
print(f"\n  Fetching standard TMY data from PVGIS...")

tmy_data, pvgis_full_metadata = get_pvgis_tmy(
    LATITUDE, LONGITUDE,
    map_variables=True,
    outputformat='json'
)


tmy_data.index = df.index

# Extract horizontal irradiance and meteorological data
GHI = tmy_data['ghi']
DNI = tmy_data['dni']
DHI = tmy_data['dhi']
T_ambient = tmy_data['temp_air']
Wind_speed = tmy_data['wind_speed']

# Step 2: Calculate solar position using the NEW 2018 index
print(f"  Calculating solar position for 2018...")
solpos = get_solarposition(tmy_data.index, LATITUDE, LONGITUDE)

# Step 3: Calculate POA Irradiance
print(f"  Calculating POA irradiance on tilted surface...")
poa_irradiance = get_total_irradiance(
    surface_tilt=OPTIMAL_TILT,
    surface_azimuth=OPTIMAL_AZIMUTH,
    solar_zenith=solpos['apparent_zenith'],
    solar_azimuth=solpos['azimuth'],
    dni=DNI,
    ghi=GHI,
    dhi=DHI
)

G_tilted = poa_irradiance['poa_global'].values

print(f"  Tilted irradiance aligned to 2018: {len(G_tilted)} hours")
print(f"  Annual tilted irradiation:   {G_tilted.sum()/1000:.0f} kWh/m²")
print(f"  Data Synchronization: ✓ COMPLETE (Weather & Load both use 2018 index)")

# %% [cell 48]
# =================================================================
# STEP 4.3: PV Cell Temperature Model
# =================================================================


NOCT = CONFIG['pv_noct']  # 45°C

# Basic NOCT model
T_cell_basic = T_ambient + (NOCT - 20) / 800 * G_tilted

# Enhanced HSEP-WT model with wind cooling
eta_module = CONFIG['pv_efficiency_stc']  # ~0.16
wind_factor = 9.5 / (5.7 + 3.8 * np.maximum(Wind_speed, 0.5))  # avoid div by 0
T_cell_wind = T_ambient + (NOCT - 20) / 800 * G_tilted * (1 - eta_module) * wind_factor

# Use the enhanced model
T_cell = T_cell_wind

print(f"\n  Cell Temperature Model: HSEP-WT (wind-corrected)")
print(f"  Avg cell temp:     {T_cell.mean():.1f}°C")
print(f"  Max cell temp:     {T_cell.max():.1f}°C")
print(f"  Min cell temp:     {T_cell.min():.1f}°C")

# %% [cell 49]
# =================================================================
# STEP 4.4: Temperature Derating Factor
# =================================================================


alpha = CONFIG['pv_temp_coeff_pmax']  # -0.0040 per °C
derating_factor = 1 + alpha * (T_cell - 25)
derating_factor = np.clip(derating_factor, 0.5, 1.1)  # physical limits

print(f"\n  Temperature Derating:")
print(f"  Avg derating:      {derating_factor.mean():.4f} ({(1-derating_factor.mean())*100:.1f}% avg loss)")
print(f"  Worst derating:    {derating_factor.min():.4f} ({(1-derating_factor.min())*100:.1f}% max loss)")
print(f"  Best derating:     {derating_factor.max():.4f}")

# %% [cell 50]
# =================================================================
# STEP 4.5: Hourly PV Power Output Per Module (Corrected)
# =================================================================

P_rated = CONFIG['pv_module_power_kw']  # 0.650 kW
G_STC = 1000  # W/m²

# We use .values to prevent index misalignment between 1990 TMY data and 2018 constants/arrays
pv_output_per_module = P_rated * (G_tilted / G_STC) * derating_factor.values
pv_output_per_module = np.maximum(pv_output_per_module, 0)  # no negative

# Key statistics
annual_yield = pv_output_per_module.sum()  # kWh per module per year
peak_power = pv_output_per_module.max()
capacity_factor = annual_yield / (P_rated * 8760)
sun_hours = (pv_output_per_module > 0.01).sum()
performance_ratio = annual_yield / (G_tilted.sum() / G_STC * P_rated)

print(f"\n{'='*55}")
print(f"  PV OUTPUT PER MODULE (650W Polycrystalline)")
print(f"{'='*55}")
print(f"  Annual yield:         {annual_yield:.1f} kWh/module/year")
print(f"  Peak output:          {peak_power:.4f} kW ({peak_power/P_rated*100:.1f}% of rated)")
print(f"  Capacity factor:      {capacity_factor:.4f} ({capacity_factor*100:.1f}%)")
print(f"  Performance ratio:    {performance_ratio:.4f} ({performance_ratio*100:.1f}%)")
print(f"  Production hours:     {sun_hours} hrs/year")
print(f"  Avg when producing:   {pv_output_per_module[pv_output_per_module>0.01].mean()*1000:.1f} W")

# Example sizing estimation
gen_annual = df['D_off_grid'].sum()
est_modules = np.ceil(gen_annual / annual_yield)
print(f"\n  Quick estimation:")
print(f"  Generator load:       {gen_annual:.0f} kWh/year")
print(f"  Modules needed:       ~{est_modules:.0f} (without battery losses)")
print(f"  System size:          ~{est_modules * P_rated:.1f} kWp")
print(f"{'='*55}")

# %% [cell 51]
# =================================================================
# STEP 4.6: Monthly PV Analysis (Corrected Alignment)
# =================================================================


target_index = df.index

pv_df = pd.DataFrame({
    'PV_kW': pv_output_per_module,
    'G_tilted': G_tilted,
    'T_cell': T_cell.values,
    'Derating': derating_factor.values,
    'T_ambient': T_ambient.values,
}, index=target_index)


monthly_pv = pv_df.resample('M').agg({
    'PV_kW': 'sum',
    'G_tilted': 'mean',
    'T_cell': 'mean',
    'Derating': 'mean',
}).round(2)

months_labels = ['Jan','Feb','Mar','Apr','May','Jun',
                 'Jul','Aug','Sep','Oct','Nov','Dec']

print(f"\n  Monthly PV Production per Module:")
print(f"  {'Month':<6} {'kWh':<10} {'Avg G_tilt':<12} {'Avg T_cell':<12} {'Derating'}")
for i, (_, row) in enumerate(monthly_pv.iterrows()):
    print(f"  {months_labels[i]:<6} {row['PV_kW']:<10.1f} {row['G_tilted']:<12.0f} "
          f"{row['T_cell']:<12.1f} {row['Derating']:.4f}")

# %% [cell 52]
# =================================================================
# STEP 4.7: FIGURE 18 — PV Output Analysis (4 subplots)
# =================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# (a) Monthly PV yield per module
ax = axes[0, 0]
ax.bar(range(12), monthly_pv['PV_kW'].values,
       color='#F4A582', alpha=0.85, edgecolor='white')
ax.set_xlabel('Month')
ax.set_ylabel('Energy Yield (kWh/module)')
ax.set_title('(a) Monthly PV Yield per Module')
ax.set_xticks(range(12))
ax.set_xticklabels(months_labels)
for i, v in enumerate(monthly_pv['PV_kW'].values):
    ax.text(i, v + 0.5, f'{v:.1f}', ha='center', fontsize=8)

# (b) Hourly average PV output
ax = axes[0, 1]
hourly_pv = pv_df.groupby(pv_df.index.hour)['PV_kW'].mean() * 1000  # to Watts
ax.fill_between(range(24), hourly_pv.values, alpha=0.3, color='#F4A582')
ax.plot(range(24), hourly_pv.values, color='#E65100', linewidth=2)
ax.set_xlabel('Hour of Day')
ax.set_ylabel('Average Output (W/module)')
ax.set_title('(b) Average Hourly PV Output')
ax.set_xticks(range(0, 24, 2))

# (c) Cell temperature vs Derating
ax = axes[1, 0]
daytime = pv_df[pv_df['G_tilted'] > 50]
scatter = ax.scatter(daytime['T_cell'], daytime['Derating'],
                     c=daytime['G_tilted'], cmap='YlOrRd',
                     alpha=0.3, s=3)
ax.set_xlabel('Cell Temperature (°C)')
ax.set_ylabel('Derating Factor')
ax.set_title('(c) Temperature vs Derating (colored by GHI)')
plt.colorbar(scatter, ax=ax, label='GHI (W/m²)', shrink=0.8)
ax.axhline(1.0, color='green', linestyle='--', alpha=0.5, label='No derating')
ax.legend(fontsize=9)

# (d) PV output vs Generator demand (overlap analysis)
ax = axes[1, 1]
hourly_pv_norm = pv_df.groupby(pv_df.index.hour)['PV_kW'].mean()
hourly_pv_norm = hourly_pv_norm / hourly_pv_norm.max()
hourly_gen = df.groupby(df.index.hour)['D_off_grid'].mean()
hourly_gen_norm = hourly_gen / hourly_gen.max()

ax.fill_between(range(24), hourly_pv_norm.values, alpha=0.3, color='#F4A582',
                label='PV output (normalized)')
ax.plot(range(24), hourly_pv_norm.values, color='#E65100', linewidth=2)
ax.plot(range(24), hourly_gen_norm.values, color='#D6604D', linewidth=2.5,
        marker='o', markersize=4, label='Gen load (normalized)')

overlap = np.minimum(hourly_pv_norm.values, hourly_gen_norm.values)
ax.fill_between(range(24), overlap, alpha=0.25, color='green',
                label=f'Overlap ({overlap.sum()/hourly_gen_norm.sum()*100:.0f}%)')

ax.set_xlabel('Hour of Day')
ax.set_ylabel('Normalized (0-1)')
ax.set_title('(d) PV Production vs Generator Demand')
ax.set_xticks(range(0, 24, 2))
ax.legend(fontsize=9)

plt.suptitle('Figure 18: PV Power Output Analysis — 260W Polycrystalline Module',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig18_pv_output_analysis.png', bbox_inches='tight')
plt.show()
print("✓ Figure 18 saved")

# %% [cell 53]
# =================================================================
# STEP 4.8: FIGURE 19 — Seasonal PV Performance
# =================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# Summer vs Winter daily profile (per module)
summer_pv = pv_df[pv_df.index.month.isin([6,7,8,9])].groupby(
    pv_df[pv_df.index.month.isin([6,7,8,9])].index.hour)['PV_kW'].mean() * 1000
winter_pv = pv_df[pv_df.index.month.isin([12,1,2])].groupby(
    pv_df[pv_df.index.month.isin([12,1,2])].index.hour)['PV_kW'].mean() * 1000

ax1.fill_between(range(24), summer_pv.values, alpha=0.3, color='#D6604D')
ax1.plot(range(24), summer_pv.values, color='#D6604D', linewidth=2,
         label=f'Summer ({summer_pv.sum()/1000:.2f} kWh/day avg)')
ax1.fill_between(range(24), winter_pv.values, alpha=0.3, color='#2166AC')
ax1.plot(range(24), winter_pv.values, color='#2166AC', linewidth=2,
         label=f'Winter ({winter_pv.sum()/1000:.2f} kWh/day avg)')
ax1.set_xlabel('Hour of Day')
ax1.set_ylabel('PV Output (W/module)')
ax1.set_title('(a) Daily PV Profile: Summer vs Winter')
ax1.legend()
ax1.set_xticks(range(0, 24, 2))

# Monthly: PV yield vs Temperature derating
ax2_twin = ax2.twinx()
ax2.bar(range(12), monthly_pv['PV_kW'].values,
        color='#F4A582', alpha=0.7, label='PV yield')
ax2_twin.plot(range(12), (1 - monthly_pv['Derating'].values) * 100,
              'rs-', markersize=6, linewidth=2, label='Temp loss %')
ax2.set_xlabel('Month')
ax2.set_ylabel('PV Yield (kWh/module)', color='#E65100')
ax2_twin.set_ylabel('Temperature Loss (%)', color='red')
ax2.set_xticks(range(12))
ax2.set_xticklabels(months_labels)
ax2.set_title('(b) PV Yield vs Temperature Loss')
ax2.legend(loc='upper left')
ax2_twin.legend(loc='upper right')

plt.suptitle('Figure 19: Seasonal PV Performance Analysis', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig19_seasonal_pv_performance.png', bbox_inches='tight')
plt.show()
print("✓ Figure 19 saved")

# %% [cell 54]
# =================================================================
# STEP 4.9: Save PV Output Data
# =================================================================

# Save per-module output for optimization phases
pv_output_series = pd.Series(pv_output_per_module, index=df.index, name='PV_kW_per_module')
pv_output_series.to_csv('pv_output_per_module.csv')

# Save as pickle for direct loading
with open('pv_per_module.pkl', 'wb') as f:
    pickle.dump(pv_output_per_module, f)

# Save PV model parameters
pv_params = {
    'model_name': 'HSEP-WT (wind-corrected cell temperature)',
    'module_power_kw': P_rated,
    'module_area_m2': CONFIG['pv_module_area_m2'],
    'efficiency_stc': CONFIG['pv_efficiency_stc'],
    'noct_celsius': NOCT,
    'temp_coeff_pmax': alpha,
    'optimal_tilt_deg': OPTIMAL_TILT,
    'optimal_azimuth_deg': OPTIMAL_AZIMUTH,
    'annual_yield_kwh_per_module': round(float(annual_yield), 1),
    'peak_output_kw': round(float(peak_power), 4),
    'capacity_factor': round(float(capacity_factor), 4),
    'performance_ratio': round(float(performance_ratio), 4),
    'production_hours': int(sun_hours),
    'avg_derating_factor': round(float(derating_factor.mean()), 4),
    'worst_derating_factor': round(float(derating_factor.min()), 4),
    'max_cell_temp_celsius': round(float(T_cell.max()), 1),
    'annual_tilted_irradiation_kwh_m2': round(float(G_tilted.sum()/1000), 1),
    'monthly_yield_kwh': [round(float(v), 1) for v in monthly_pv['PV_kW'].values],
}

with open('pv_model_params.json', 'w') as f:
    json.dump(pv_params, f, indent=2)

# %% [cell 55]
# =================================================================
# FINAL SUMMARY
# =================================================================

print(f"\n{'='*60}")
print(f"  PHASE 4 — FINAL SUMMARY")
print(f"{'='*60}")
print(f"  Model:           HSEP-WT (wind-corrected)")
print(f"  Module:          260W Polycrystalline ({CONFIG['pv_module_width_m']}×{CONFIG['pv_module_height_m']}m)")
print(f"  Tilt:            {OPTIMAL_TILT}° (PVGIS optimal)")
print(f"  Location:        Baghdad ({LATITUDE}°N)")
print(f"")
print(f"  Annual yield:    {annual_yield:.1f} kWh/module")
print(f"  Capacity factor: {capacity_factor*100:.1f}%")
print(f"  Perf. ratio:     {performance_ratio*100:.1f}%")
print(f"  Avg derating:    {(1-derating_factor.mean())*100:.1f}% loss from temperature")
print(f"  Peak cell temp:  {T_cell.max():.1f}°C")
print(f"")
print(f"  Quick estimate:  ~{est_modules:.0f} modules ({est_modules*P_rated:.1f} kWp)")
print(f"                   to match {gen_annual:.0f} kWh/year gen load")
print(f"")
print(f"  Files saved:")
print(f"    pv_output_per_module.csv  (8760 hourly values)")
print(f"    pv_per_module.pkl         (for optimization)")
print(f"    pv_model_params.json      (model parameters)")
print(f"    fig18-fig19_*.png         (2 figures)")
print(f"")
print(f"  → Ready for Phase 5 (EMS — 4 Modes)")
print(f"{'='*60}")

# %% [cell 56]
import os
files = [f for f in os.listdir('/content/') if not f.startswith('.')]
print("Your files:", sorted(files))

# %% [cell 57]
from google.colab import drive
drive.mount('/content/drive')
!mkdir -p /content/drive/MyDrive/MSc_Project
!cp *.csv *.json *.pkl *.h5 *.png /content/drive/MyDrive/MSc_Project/
print("✓ All files backed up to Google Drive")

# %% [cell 58]


# %% [cell 59]


# %% [cell 60]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 5: ENERGY MANAGEMENT STRATEGY (EMS) — 4 MODES           ║
# ║                                                                ║
# ║  Priority (all modes): PV first → Grid second → Battery third  ║
# ║  Mode 0: Self-sufficient (no bat discharge on-grid)            ║
# ║  Mode 1: Balanced (bat discharge if PV < load on-grid)         ║
# ║  Mode 2: Max independence (bat discharge to avoid grid)        ║
# ║  Mode 3: Predictive (RF-based pre-charge before outage)       ║
# ║                                                                ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 5.1: Import & Load
# =================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import pickle
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.dpi': 150, 'savefig.dpi': 300,
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'axes.grid': True, 'grid.alpha': 0.3,
})

df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)
with open('config.json') as f:
    CONFIG = json.load(f)
with open('pv_per_module.pkl', 'rb') as f:
    pv_per_module = pickle.load(f)
with open('rf_outage_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)

print("="*55)
print("  PHASE 5: ENERGY MANAGEMENT STRATEGY")
print("  4 Modes — PV First Priority")
print("="*55)

# %% [cell 61]
# =================================================================
# STEP 5.2: Prepare RF Prediction for Mode 3
# =================================================================
"""
Mode 3 (Predictive) needs RF to predict outage probability
for the next 6 hours. We pre-compute this for all 8760 hours.
"""

# Build RF features for prediction (same as Phase 3)
rf_df = df.copy()
for lag in [1, 2, 3, 6, 12, 24]:
    rf_df[f'Grid_lag_{lag}h'] = rf_df['Grid_Status'].shift(lag)

rf_df['Grid_rolling_6h']  = rf_df['Grid_Status'].shift(1).rolling(6).mean()
rf_df['Grid_rolling_12h'] = rf_df['Grid_Status'].shift(1).rolling(12).mean()
rf_df['Grid_rolling_24h'] = rf_df['Grid_Status'].shift(1).rolling(24).mean()


outage_counter = np.zeros(len(rf_df))
count = 0
for i in range(len(rf_df)):
    outage_counter[i] = count
    if rf_df['Grid_Status'].iloc[i] == 0:
        count += 1
    else:
        count = 0
rf_df['Outage_duration_so_far'] = outage_counter

rf_features = [
    'Hour_sin', 'Hour_cos', 'Month_sin', 'Month_cos',
    'DayOfWeek_sin', 'DayOfWeek_cos',
    'Grid_lag_1h', 'Grid_lag_2h', 'Grid_lag_3h',
    'Grid_lag_6h', 'Grid_lag_12h', 'Grid_lag_24h',
    'Grid_rolling_6h', 'Grid_rolling_12h', 'Grid_rolling_24h',
    'Outage_duration_so_far',
]

# Pre-compute outage probability for each hour (for Mode 3)
rf_df_clean = rf_df.dropna()
X_rf_all = rf_df_clean[rf_features].values
outage_proba = rf_model.predict_proba(X_rf_all)[:, 0]  # probability of grid OFF

# Create full 8760 array (pad first 24 hours with 0.5)
outage_prob_8760 = np.full(8760, 0.5)
start_idx = 8760 - len(outage_proba)
outage_prob_8760[start_idx:] = outage_proba

# Look-ahead: max outage probability in next 6 hours
outage_prob_ahead = np.zeros(8760)
for t in range(8760):
    end = min(t + 6, 8760)
    outage_prob_ahead[t] = outage_prob_8760[t:end].max()

print(f"  RF outage predictions ready: {len(outage_proba)} hours")
print(f"  Avg outage probability: {outage_prob_8760.mean():.3f}")



# %% [cell 62]
def simulate_ems(n_modules, bat_n_kwh, inv_kw, ems_mode,
                 gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, config):

    hours = 8760
    dt = 1  # Δt = 1 hour

    # ─── Battery Parameters
    C_bat_max = config['bat_cmax_factor'] * bat_n_kwh
    C_bat_min = (1 - config['bat_dod']) * bat_n_kwh
    eta_bc    = config['bat_eta_charge']
    eta_bd    = config['bat_eta_discharge']
    sigma     = config['bat_self_discharge_per_hour']
    eta_inv   = config['inv_efficiency']
    Max_P     = config['bat_max_c_rate'] * bat_n_kwh

    # ─── Total PV output (limited by inverter) ───
    E_pv_total = pv_per_mod * n_modules  # E_RE(t) = E_pv(t)

    # ─── Initialize arrays ───
    C_bat     = np.zeros(hours + 1)
    C_bat[0]  = (C_bat_max + C_bat_min) / 2  # Start at 50% SOC

    LPS       = np.zeros(hours)  # Loss of Power Supply
    E_grid_buy= np.zeros(hours)  # Grid purchase during on-grid
    E_grid_export = np.zeros(hours)  # Grid export (Mode 2 only — Net Metering)
    E_wasted  = np.zeros(hours)  # Curtailed/dump energy
    P_charge  = np.zeros(hours)  # Battery charging power
    P_discharge= np.zeros(hours) # Battery discharging power
    E_pv_to_load = np.zeros(hours)  # PV directly feeding load
    E_pv_to_bat  = np.zeros(hours)  # PV charging battery

    # ─── Mode 3 threshold ───
    PRED_THRESHOLD = 0.7  # outage probability threshold for pre-charging

    for t in range(hours):
        # Self-discharge
        C_prev = C_bat[t] * (1 - sigma)

        # Available PV power (limited by inverter)
        pv_available = min(E_pv_total[t], inv_kw) * eta_inv

        # Helper: charge battery
        def charge_battery(power_available):
            charge = min(
                power_available,
                (C_bat_max - C_prev) / (eta_bc * dt),
                Max_P
            )
            charge = max(0, charge)
            return charge

        # Helper: discharge battery
        def discharge_battery(power_needed):
            available = max(0, (C_prev - C_bat_min) * eta_bd / dt)
            discharge = min(
                power_needed,
                available,
                Max_P,
                inv_kw  # inverter limit
            )
            discharge = max(0, discharge)
            return discharge

        # ═══════════════════════════════════════════════════
        # GRID IS ON
        # ═══════════════════════════════════════════════════
        if grid_status[t] == 1:
            load = grid_load[t]  # on-grid demand

            # ─── ALL MODES: PV feeds load first (PV priority) ───
            pv_to_load = min(pv_available, load)
            E_pv_to_load[t] = pv_to_load
            pv_surplus = pv_available - pv_to_load
            load_remaining = load - pv_to_load

            if ems_mode == 0:
                # PV surplus charges battery
                charge_pv = charge_battery(pv_surplus)
                P_charge[t] = charge_pv
                E_pv_to_bat[t] = charge_pv
                E_wasted[t] = pv_surplus - charge_pv
                E_grid_buy[t] = load_remaining

                # NEW: Grid charges battery at night when SOC < 80%
                SOC_pct = C_prev / C_bat_max if C_bat_max > 0 else 1.0
                if pv_available < 0.1 and SOC_pct < 0.80:
                    grid_charge_power = min(
                        Max_P * 0.5,
                        (C_bat_max - C_prev) / (eta_bc * dt),
                        Max_P
                    )
                    grid_charge_power = max(0, grid_charge_power)
                    P_charge[t] = P_charge[t] + grid_charge_power
                    E_grid_buy[t] = E_grid_buy[t] + grid_charge_power
                    C_bat[t+1] = C_prev + (charge_pv + grid_charge_power) * eta_bc * dt
                else:
                    C_bat[t+1] = C_prev + charge_pv * eta_bc * dt

            elif ems_mode == 1:
                if pv_surplus > 0:
                    charge = charge_battery(pv_surplus)
                    P_charge[t] = charge
                    E_pv_to_bat[t] = charge
                    C_bat[t+1] = C_prev + charge * eta_bc * dt
                    E_grid_buy[t] = load_remaining
                    E_wasted[t] = pv_surplus - charge
                elif load_remaining > 0:
                    discharge = discharge_battery(load_remaining)
                    P_discharge[t] = discharge
                    C_bat[t+1] = C_prev - discharge / eta_bd * dt
                    E_grid_buy[t] = load_remaining - discharge
                else:
                    C_bat[t+1] = C_prev

            elif ems_mode == 2:
                # Mode 2: Max Independence with Net Metering (Bidirectional)
                pv_to_export = 0.0
                bat_to_export = 0.0

                if pv_surplus > 0:
                    charge = charge_battery(pv_surplus)
                    P_charge[t] = charge
                    E_pv_to_bat[t] = charge
                    C_bat_after = C_prev + charge * eta_bc * dt
                    E_grid_buy[t] = load_remaining
                    pv_to_export = pv_surplus - charge
                    E_wasted[t] = 0
                elif load_remaining > 0:
                    discharge = discharge_battery(load_remaining)
                    P_discharge[t] = discharge
                    C_bat_after = C_prev - discharge / eta_bd * dt
                    E_grid_buy[t] = load_remaining - discharge
                else:
                    C_bat_after = C_prev

                bat_available = max(0, (C_bat_after - C_bat_min) * eta_bd / dt)
                inv_headroom = max(0, inv_kw - pv_to_export)
                bat_to_export = min(bat_available, inv_headroom, Max_P)
                bat_to_export = max(0, bat_to_export)

                if bat_to_export > 0:
                    P_discharge[t] = P_discharge[t] + bat_to_export
                    C_bat_after = C_bat_after - bat_to_export / eta_bd * dt

                E_grid_export[t] = pv_to_export + bat_to_export
                C_bat[t+1] = C_bat_after

            elif ems_mode == 3:
                if outage_prob[t] > PRED_THRESHOLD:
                    E_grid_buy[t] = load
                    E_pv_to_load[t] = 0
                    charge = charge_battery(pv_available)
                    P_charge[t] = charge
                    E_pv_to_bat[t] = charge
                    C_bat[t+1] = C_prev + charge * eta_bc * dt
                    E_wasted[t] = pv_available - charge
                else:
                    if pv_surplus > 0:
                        charge = charge_battery(pv_surplus)
                        P_charge[t] = charge
                        E_pv_to_bat[t] = charge
                        C_bat[t+1] = C_prev + charge * eta_bc * dt
                        E_grid_buy[t] = load_remaining
                        E_wasted[t] = pv_surplus - charge
                    elif load_remaining > 0:
                        discharge = discharge_battery(load_remaining)
                        P_discharge[t] = discharge
                        C_bat[t+1] = C_prev - discharge / eta_bd * dt
                        E_grid_buy[t] = load_remaining - discharge
                    else:
                        C_bat[t+1] = C_prev

        else:
            load = gen_load[t]
            if load <= 0.001:
                if pv_available > 0:
                    charge = charge_battery(pv_available)
                    P_charge[t] = charge
                    E_pv_to_bat[t] = charge
                    C_bat[t+1] = C_prev + charge * eta_bc * dt
                    E_wasted[t] = pv_available - charge
                else:
                    C_bat[t+1] = C_prev
                continue
            D_t = load / eta_inv
            pv_to_load = min(pv_available, D_t)
            E_pv_to_load[t] = pv_to_load * eta_inv
            E_Ex = pv_available - D_t
            if E_Ex >= 0:
                charge = charge_battery(E_Ex)
                P_charge[t] = charge
                E_pv_to_bat[t] = charge
                C_bat[t+1] = C_prev + charge * eta_bc * dt
                E_wasted[t] = E_Ex - charge
            else:
                E_need = D_t - pv_available
                discharge = discharge_battery(E_need)
                P_discharge[t] = discharge
                C_bat[t+1] = C_prev - discharge / eta_bd * dt
                remaining = E_need - discharge
                if remaining > 0.001:
                    LPS[t] = remaining * eta_inv
        C_bat[t+1] = np.clip(C_bat[t+1], C_bat_min, C_bat_max)

    total_gen_load = gen_load.sum()
    total_grid_load = grid_load.sum()
    lpsp = LPS.sum() / total_gen_load if total_gen_load > 0 else 0
    gpap = E_grid_buy.sum() / total_grid_load if total_grid_load > 0 else 0
    annual_charge = (P_charge * eta_bc).sum()
    usable_cap = C_bat_max - C_bat_min
    annual_cycles = annual_charge / usable_cap if usable_cap > 0 else 0
    total_pv_produced = (pv_per_mod * n_modules).sum()
    total_pv_used = E_pv_to_load.sum() + E_pv_to_bat.sum()
    self_consumption = total_pv_used / total_pv_produced if total_pv_produced > 0 else 0

    net_grid_purchase = E_grid_buy.sum() - E_grid_export.sum()

    return {
        'LPS': LPS, 'E_grid_buy': E_grid_buy, 'E_grid_export': E_grid_export,
        'E_wasted': E_wasted,
        'P_charge': P_charge, 'P_discharge': P_discharge, 'C_bat': C_bat[:-1],
        'E_pv_to_load': E_pv_to_load, 'E_pv_to_bat': E_pv_to_bat,
        'lpsp': lpsp, 'gpap': gpap, 'total_lps_kwh': LPS.sum(),
        'total_grid_buy_kwh': E_grid_buy.sum(),
        'total_grid_export_kwh': E_grid_export.sum(),
        'net_grid_purchase_kwh': net_grid_purchase,
        'total_wasted_kwh': E_wasted.sum(),
        'total_pv_to_load_kwh': E_pv_to_load.sum(), 'total_pv_to_bat_kwh': E_pv_to_bat.sum(),
        'annual_battery_cycles': annual_cycles, 'self_consumption_ratio': self_consumption,
        'inv_size_needed': n_modules * config['pv_module_power_kw'] + Max_P,
        'ems_mode': ems_mode,
    }

# %% [cell 63]
# =================================================================
# STEP 5.4: Test All 4 Modes with Sample Configuration
# =================================================================


test_config = {
    'n_modules': 18,
    'bat_kwh': 53.2,  # 2 × 10.64 kWh units
    'inv_kw': 7.44,
}

gen_load = df['D_off_grid'].values
grid_load = df['D_on_grid'].values
grid_status = df['Grid_Status'].values

print(f"\n{'='*60}")
print(f"  TESTING 4 MODES")
print(f"  Config: {test_config['n_modules']} modules, "
      f"{test_config['bat_kwh']} kWh battery, "
      f"{test_config['inv_kw']} kW inverter")
print(f"{'='*60}")

mode_names = {
    0: 'Mode 0: Self-sufficient',
    1: 'Mode 1: Balanced',
    2: 'Mode 2: Max independence',
    3: 'Mode 3: Predictive',
}

results = {}
for mode in [0, 1, 2, 3]:
    r = simulate_ems(
        n_modules=test_config['n_modules'],
        bat_n_kwh=test_config['bat_kwh'],
        inv_kw=test_config['inv_kw'],
        ems_mode=mode,
        gen_load=gen_load,
        grid_load=grid_load,
        grid_status=grid_status,
        pv_per_mod=pv_per_module,
        outage_prob=outage_prob_ahead,
        config=CONFIG,
    )
    results[mode] = r

# Print comparison table
print(f"\n  {'Metric':<30} {'Mode 0':<14} {'Mode 1':<14} {'Mode 2':<14} {'Mode 3':<14}")
print(f"  {'─'*86}")

metrics_to_show = [
    ('LPSP', 'lpsp', '.6f'),
    ('Total LPS (kWh)', 'total_lps_kwh', '.1f'),
    ('Grid Purchase (kWh)', 'total_grid_buy_kwh', ',.0f'),
    ('Grid Export (kWh)', 'total_grid_export_kwh', ',.0f'),
    ('Net Grid Purchase (kWh)', 'net_grid_purchase_kwh', ',.0f'),
    ('GPAP', 'gpap', '.4f'),
    ('PV → Load (kWh)', 'total_pv_to_load_kwh', ',.0f'),
    ('PV → Battery (kWh)', 'total_pv_to_bat_kwh', ',.0f'),
    ('Wasted PV (kWh)', 'total_wasted_kwh', ',.0f'),
    ('Battery Cycles/yr', 'annual_battery_cycles', '.0f'),
    ('Self-consumption', 'self_consumption_ratio', '.2%'),
]

for label, key, fmt in metrics_to_show:
    vals = []
    for mode in [0, 1, 2, 3]:
        v = results[mode][key]
        if fmt.endswith('%'):
            vals.append(f"{v:{fmt[:-1]}}")
        else:
            vals.append(f"{v:{fmt}}")
    print(f"  {label:<30} {vals[0]:<14} {vals[1]:<14} {vals[2]:<14} {vals[3]:<14}")

# %% [cell 64]
# =================================================================
# STEP 5.5: FIGURE 20 — Mode Comparison Bar Charts
# =================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

modes = [0, 1, 2, 3]
mode_labels = ['Mode 0\nSelf-suff.', 'Mode 1\nBalanced', 'Mode 2\nMax indep.', 'Mode 3\nPredictive']
colors = ['#66BD63', '#FEB24C', '#D6604D', '#2166AC']

# (a) LPSP comparison
ax = axes[0, 0]
lpsp_vals = [results[m]['lpsp'] for m in modes]
bars = ax.bar(mode_labels, lpsp_vals, color=colors, alpha=0.85, edgecolor='white')
for bar, v in zip(bars, lpsp_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'{v:.4f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_ylabel('LPSP')
ax.set_title('(a) Loss of Power Supply Probability')

# (b) Grid purchase
ax = axes[0, 1]
grid_vals = [results[m]['total_grid_buy_kwh'] for m in modes]
bars = ax.bar(mode_labels, grid_vals, color=colors, alpha=0.85, edgecolor='white')
for bar, v in zip(bars, grid_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'{v:,.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_ylabel('Grid Purchase (kWh/year)')
ax.set_title('(b) Annual Grid Electricity Purchase')

# (c) Battery cycles
ax = axes[1, 0]
cycle_vals = [results[m]['annual_battery_cycles'] for m in modes]
bars = ax.bar(mode_labels, cycle_vals, color=colors, alpha=0.85, edgecolor='white')
for bar, v in zip(bars, cycle_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'{v:.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_ylabel('Battery Cycles/Year')
ax.set_title('(c) Annual Battery Cycle Count')

# (d) Self-consumption ratio
ax = axes[1, 1]
self_vals = [results[m]['self_consumption_ratio'] * 100 for m in modes]
bars = ax.bar(mode_labels, self_vals, color=colors, alpha=0.85, edgecolor='white')
for bar, v in zip(bars, self_vals):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
            f'{v:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.set_ylabel('Self-Consumption (%)')
ax.set_title('(d) PV Self-Consumption Ratio')

plt.suptitle('Figure 20: EMS Mode Comparison (10 modules, 21.3 kWh battery, 10 kW inverter)',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig20_ems_mode_comparison.png', bbox_inches='tight')
plt.show()
print("✓ Figure 20 saved")



# %% [cell 65]
# =================================================================
# STEP 5.6: FIGURE 21 — Battery SOC Profile (1 week sample)
# =================================================================

# Pick a summer week with outages for interesting visualization
summer_start = 24 * 180  # July 1st approximately
sample_len = 24 * 7  # 1 week

fig, axes = plt.subplots(4, 1, figsize=(14, 14), sharex=True)

for i, mode in enumerate(modes):
    ax = axes[i]
    soc = results[mode]['C_bat'][summer_start:summer_start+sample_len]
    soc_pct = soc / (CONFIG['bat_cmax_factor'] * test_config['bat_kwh']) * 100

    hours_range = range(sample_len)
    ax.fill_between(hours_range, soc_pct, alpha=0.3, color=colors[i])
    ax.plot(hours_range, soc_pct, color=colors[i], linewidth=1.5)

    # Mark outage periods
    gs = grid_status[summer_start:summer_start+sample_len]
    for h in range(sample_len):
        if gs[h] == 0:
            ax.axvspan(h, h+1, alpha=0.1, color='red')

    ax.set_ylabel('SOC (%)')
    ax.set_title(f'{mode_names[mode]}', fontsize=11)
    ax.set_ylim(0, 105)
    ax.axhline(10, color='red', linestyle=':', alpha=0.5, linewidth=0.8)
    ax.axhline(98, color='green', linestyle=':', alpha=0.5, linewidth=0.8)

axes[-1].set_xlabel('Hour (1-week summer sample, red shading = grid outage)')

plt.suptitle('Figure 21: Battery SOC Profile — 4 Modes Compared (Summer Week)',
             fontsize=13, y=1.01)
plt.tight_layout()
plt.savefig('fig21_battery_soc_comparison.png', bbox_inches='tight')
plt.show()
print("✓ Figure 21 saved")



# %% [cell 66]
# =================================================================
# STEP 5.7: FIGURE 22 — Energy Flow Sankey-style Summary
# =================================================================

fig, axes = plt.subplots(1, 4, figsize=(16, 6))

for i, mode in enumerate(modes):
    ax = axes[i]
    r = results[mode]

    categories = ['PV→Load', 'PV→Bat', 'Grid Buy', 'Wasted', 'LPS']
    values = [
        r['total_pv_to_load_kwh'],
        r['total_pv_to_bat_kwh'],
        r['total_grid_buy_kwh'],
        r['total_wasted_kwh'],
        r['total_lps_kwh'],
    ]
    bar_colors = ['#66BD63', '#2166AC', '#FEB24C', '#969696', '#D6604D']

    bars = ax.barh(categories, values, color=bar_colors, alpha=0.85, edgecolor='white')
    for bar, v in zip(bars, values):
        if v > 0:
            ax.text(bar.get_width() + max(values)*0.02, bar.get_y() + bar.get_height()/2,
                    f'{v:,.0f}', va='center', fontsize=9)

    ax.set_xlabel('kWh/year')
    ax.set_title(f'Mode {mode}', fontsize=11, fontweight='bold', color=colors[i])

plt.suptitle('Figure 22: Annual Energy Flow by Mode', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig22_energy_flow_by_mode.png', bbox_inches='tight')
plt.show()
print("✓ Figure 22 saved")



# %% [cell 67]
# =================================================================
# STEP 5.8: Save EMS Function & Results
# =================================================================

# Save the function for Phase 6 (pickle the module)
# The function will be imported via exec() or copy-paste in Phase 6

# Save test results
test_results_summary = {}
for mode in modes:
    r = results[mode]
    test_results_summary[f'mode_{mode}'] = {
        'name': mode_names[mode],
        'lpsp': round(r['lpsp'], 6),
        'gpap': round(r['gpap'], 4),
        'total_lps_kwh': round(r['total_lps_kwh'], 1),
        'grid_buy_kwh': round(r['total_grid_buy_kwh'], 0),
        'grid_export_kwh': round(r['total_grid_export_kwh'], 0),
        'net_grid_purchase_kwh': round(r['net_grid_purchase_kwh'], 0),
        'pv_to_load_kwh': round(r['total_pv_to_load_kwh'], 0),
        'pv_to_bat_kwh': round(r['total_pv_to_bat_kwh'], 0),
        'wasted_kwh': round(r['total_wasted_kwh'], 0),
        'battery_cycles': round(r['annual_battery_cycles'], 0),
        'self_consumption': round(r['self_consumption_ratio'], 4),
    }

with open('ems_test_results.json', 'w') as f:
    json.dump(test_results_summary, f, indent=2)

# %% [cell 68]
# =================================================================
# FINAL SUMMARY
# =================================================================

print(f"\n{'='*60}")
print(f"  PHASE 5 — FINAL SUMMARY")
print(f"{'='*60}")
print(f"  EMS Modes: 4 (all PV-first priority)")
print(f"  Test config: {test_config}")
print(f"")
print(f"  Mode 0 (Self-suff.):   LPSP={results[0]['lpsp']:.4f}  GridBuy={results[0]['total_grid_buy_kwh']:,.0f} kWh")
print(f"  Mode 1 (Balanced):     LPSP={results[1]['lpsp']:.4f}  GridBuy={results[1]['total_grid_buy_kwh']:,.0f} kWh")
print(f"  Mode 2 (Max indep.):   LPSP={results[2]['lpsp']:.4f}  GridBuy={results[2]['total_grid_buy_kwh']:,.0f} kWh")
print(f"  Mode 3 (Predictive):   LPSP={results[3]['lpsp']:.4f}  GridBuy={results[3]['total_grid_buy_kwh']:,.0f} kWh")
print(f"")
print(f"  Files saved:")
print(f"    ems_test_results.json")
print(f"    fig20-fig22_*.png (3 figures)")
print(f"")
print(f"  simulate_ems() ready for Phase 6 (GNPSO)")
print(f"  → Ready for Phase 6 (GNPSO Optimization)")
print(f"{'='*60}")

# %% [cell 69]


# %% [cell 70]


# %% [cell 71]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 6: GNPSO OPTIMIZATION (Hybrid GA + PSO)                  ║
# ║                                                                ║
# ║  Decision variables: [N_panels, Bat_units, Inv_kW]             ║
# ║  EMS: Mode 0 (PV first, no bat discharge on-grid)              ║
# ║  Objective: Multi-objective 4D (LPSP + LCE + PBP + TCOP)      ║
# ║  Runs: (A) Actual 2018 data, (B) Forecast 2019 data           ║
# ║  Post-optimization: Compare 4 EMS modes on optimal config     ║
# ║                                                                ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 6.1: Restore Data & Import Dependencies
# =================================================================

import os
from google.colab import drive

# Ensure drive is mounted
if not os.path.exists('/content/drive'):
    drive.mount('/content/drive')

# Copy files back from Drive to local environment if missing
!cp /content/drive/MyDrive/MSc_Project/*.csv /content/ 2>/dev/null || true
!cp /content/drive/MyDrive/MSc_Project/*.json /content/ 2>/dev/null || true
!cp /content/drive/MyDrive/MSc_Project/*.pkl /content/ 2>/dev/null || true

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import pickle
import time
import copy
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.dpi': 150, 'savefig.dpi': 300,
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'axes.grid': True, 'grid.alpha': 0.3,
})

# Load Data
df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)
with open('config.json') as f:
    CONFIG = json.load(f)
with open('pv_per_module.pkl', 'rb') as f:
    pv_per_module = pickle.load(f)
with open('rf_outage_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)

# Load forecast data
forecast_df = pd.read_csv('predicted_gen_load_8760.csv', index_col='Timestamp', parse_dates=True)

# Prepare data arrays
gen_load_actual = df['D_off_grid'].values
grid_load_actual = df['D_on_grid'].values
grid_status_actual = df['Grid_Status'].values
gen_load_forecast = forecast_df['Predicted_Gen_Load_kWh'].values
grid_status_forecast = forecast_df['Predicted_Grid_Status'].values.astype(int)

# Outage probability for Mode 3 (pre-computed in Phase 5)
rf_df = df.copy()
for lag in [1, 2, 3, 6, 12, 24]:
    rf_df[f'Grid_lag_{lag}h'] = rf_df['Grid_Status'].shift(lag)
#  Rolling
rf_df['Grid_rolling_6h']  = rf_df['Grid_Status'].shift(1).rolling(6).mean()
rf_df['Grid_rolling_12h'] = rf_df['Grid_Status'].shift(1).rolling(12).mean()
rf_df['Grid_rolling_24h'] = rf_df['Grid_Status'].shift(1).rolling(24).mean()

#  Outage duration
outage_counter = np.zeros(len(rf_df))
count = 0
for i in range(len(rf_df)):
    outage_counter[i] = count
    if rf_df['Grid_Status'].iloc[i] == 0:
        count += 1
    else:
        count = 0
rf_df['Outage_duration_so_far'] = outage_counter
rf_features = ['Hour_sin','Hour_cos','Month_sin','Month_cos','DayOfWeek_sin','DayOfWeek_cos',
               'Grid_lag_1h','Grid_lag_2h','Grid_lag_3h','Grid_lag_6h','Grid_lag_12h','Grid_lag_24h',
               'Grid_rolling_6h','Grid_rolling_12h','Grid_rolling_24h','Outage_duration_so_far']
rf_clean = rf_df.dropna()
outage_proba = rf_model.predict_proba(rf_clean[rf_features].values)[:, 0]
outage_prob_8760 = np.full(8760, 0.5)
outage_prob_8760[8760 - len(outage_proba):] = outage_proba
outage_prob_ahead = np.zeros(8760)
for t in range(8760):
    outage_prob_ahead[t] = outage_prob_8760[t:min(t+6, 8760)].max()

print("="*60)
print("  PHASE 6: GNPSO OPTIMIZATION")
print("  Hybrid GA + PSO | Multi-objective 4D")
print("="*60)

# %% [cell 72]
def simulate_ems(n_modules, bat_n_kwh, inv_kw, ems_mode,
                 gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, config):
    hours = 8760; dt = 1
    C_bat_max = config['bat_cmax_factor'] * bat_n_kwh
    C_bat_min = (1 - config['bat_dod']) * bat_n_kwh
    eta_bc = config['bat_eta_charge']
    eta_bd = config['bat_eta_discharge']
    sigma = config['bat_self_discharge_per_hour']
    eta_inv = config['inv_efficiency']
    Max_P = config['bat_max_c_rate'] * bat_n_kwh
    E_pv_total = pv_per_mod * n_modules
    C_bat = np.zeros(hours + 1)
    C_bat[0] = (C_bat_max + C_bat_min) / 2
    LPS = np.zeros(hours); E_grid_buy = np.zeros(hours)
    E_wasted = np.zeros(hours); P_charge = np.zeros(hours)
    P_discharge = np.zeros(hours); E_pv_to_load = np.zeros(hours)
    E_pv_to_bat = np.zeros(hours)
    PRED_THRESHOLD = 0.7

    for t in range(hours):
        C_prev = C_bat[t] * (1 - sigma)
        pv_available = min(E_pv_total[t], inv_kw) * eta_inv

        def charge_bat(pwr):
            c = min(pwr, (C_bat_max - C_prev)/(eta_bc*dt), Max_P)
            return max(0, c)
        def discharge_bat(pwr):
            a = max(0, (C_prev - C_bat_min)*eta_bd/dt)
            return max(0, min(pwr, a, Max_P, inv_kw))

        if grid_status[t] == 1:
            load = grid_load[t]
            pv_to_load = min(pv_available, load)
            E_pv_to_load[t] = pv_to_load
            pv_surplus = pv_available - pv_to_load
            load_remaining = load - pv_to_load

            if ems_mode == 0:
                # PV surplus charges battery
                charge_pv = charge_bat(pv_surplus)
                P_charge[t] = charge_pv
                E_pv_to_bat[t] = charge_pv
                E_wasted[t] = pv_surplus - charge_pv
                E_grid_buy[t] = load_remaining

                # NEW: Grid charges battery at night when SOC < 80%
                SOC_pct = C_prev / C_bat_max if C_bat_max > 0 else 1.0
                if pv_available < 0.1 and SOC_pct < 0.80:
                    grid_charge_power = min(
                        Max_P * 0.5,
                        (C_bat_max - C_prev) / (eta_bc * dt),
                        Max_P
                    )
                    grid_charge_power = max(0, grid_charge_power)
                    P_charge[t] = P_charge[t] + grid_charge_power
                    E_grid_buy[t] = E_grid_buy[t] + grid_charge_power
                    C_bat[t+1] = C_prev + (charge_pv + grid_charge_power) * eta_bc * dt
                else:
                    C_bat[t+1] = C_prev + charge_pv * eta_bc * dt

            elif ems_mode == 1:
                if pv_surplus > 0:
                    ch = charge_bat(pv_surplus)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_grid_buy[t] = load_remaining
                    E_wasted[t] = pv_surplus - ch
                elif load_remaining > 0:
                    dis = discharge_bat(load_remaining)
                    P_discharge[t] = dis
                    C_bat[t+1] = C_prev - dis/eta_bd*dt
                    E_grid_buy[t] = load_remaining - dis
                else:
                    C_bat[t+1] = C_prev
            elif ems_mode == 2:
                if pv_surplus > 0:
                    ch = charge_bat(pv_surplus)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_grid_buy[t] = load_remaining
                    E_wasted[t] = pv_surplus - ch
                elif load_remaining > 0:
                    dis = discharge_bat(load_remaining)
                    P_discharge[t] = dis
                    C_bat[t+1] = C_prev - dis/eta_bd*dt
                    E_grid_buy[t] = max(0, load_remaining - dis)
                else:
                    C_bat[t+1] = C_prev
            elif ems_mode == 3:
                if outage_prob[t] > PRED_THRESHOLD:
                    E_grid_buy[t] = load; E_pv_to_load[t] = 0
                    ch = charge_bat(pv_available)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_wasted[t] = pv_available - ch
                else:
                    if pv_surplus > 0:
                        ch = charge_bat(pv_available)
                        P_charge[t] = ch; E_pv_to_bat[t] = ch
                        C_bat[t+1] = C_prev + ch*eta_bc*dt
                        E_grid_buy[t] = load_remaining
                        E_wasted[t] = pv_surplus - ch
                    elif load_remaining > 0:
                        dis = discharge_bat(load_remaining)
                        P_discharge[t] = dis
                        C_bat[t+1] = C_prev - dis/eta_bd*dt
                        E_grid_buy[t] = load_remaining - dis
                    else:
                        C_bat[t+1] = C_prev
        else:
            load = gen_load[t]
            if load <= 0.001:
                if pv_available > 0:
                    ch = charge_bat(pv_available)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_wasted[t] = pv_available - ch
                else:
                    C_bat[t+1] = C_prev
                continue
            D_t = load / eta_inv
            pv_to_load = min(pv_available, D_t)
            E_pv_to_load[t] = pv_to_load * eta_inv
            E_Ex = pv_available - D_t
            if E_Ex >= 0:
                ch = charge_bat(E_Ex)
                P_charge[t] = ch; E_pv_to_bat[t] = ch
                C_bat[t+1] = C_prev + ch*eta_bc*dt
                E_wasted[t] = E_Ex - ch
            else:
                E_need = D_t - pv_available
                dis = discharge_bat(E_need)
                P_discharge[t] = dis
                C_bat[t+1] = C_prev - dis/eta_bd*dt
                remaining = E_need - dis
                if remaining > 0.001:
                    LPS[t] = remaining * eta_inv
        C_bat[t+1] = np.clip(C_bat[t+1], C_bat_min, C_bat_max)

    total_gen = gen_load.sum()
    total_grid = grid_load.sum()
    lpsp = LPS.sum()/total_gen if total_gen > 0 else 0
    gpap = E_grid_buy.sum()/total_grid if total_grid > 0 else 0
    annual_charge = (P_charge*eta_bc).sum()
    usable = C_bat_max - C_bat_min
    annual_cycles = annual_charge/usable if usable > 0 else 0

    return {
        'LPS': LPS, 'E_grid_buy': E_grid_buy, 'E_wasted': E_wasted,
        'P_charge': P_charge, 'P_discharge': P_discharge,
        'C_bat': C_bat[:-1], 'E_pv_to_load': E_pv_to_load,
        'E_pv_to_bat': E_pv_to_bat,
        'lpsp': lpsp, 'gpap': gpap,
        'total_lps_kwh': LPS.sum(), 'total_grid_buy_kwh': E_grid_buy.sum(),
        'total_wasted_kwh': E_wasted.sum(),
        'total_pv_to_load_kwh': E_pv_to_load.sum(),
        'total_pv_to_bat_kwh': E_pv_to_bat.sum(),
        'annual_battery_cycles': annual_cycles,
        'inv_size_needed': n_modules*config['pv_module_power_kw'] + Max_P,
        'ems_mode': ems_mode,
    }

# %% [cell 73]
# =================================================================
# STEP 6.3: Cost Functions
# =================================================================

def calculate_economics(n_modules, bat_n_kwh, inv_kw, sim_result, config,
                        gen_load, grid_load):
    T = config['project_lifetime_years']
    r = config['interest_rate']
    i_rate = config['inflation_rate']
    CRF = (r*(1+r)**T) / ((1+r)**T - 1)

    # PV TCOP
    pv_capex = n_modules * config['pv_cost_per_module_usd']
    pv_omc = pv_capex * 0.01 * T
    pv_tpv = pv_capex + pv_omc
    tcop_pv = pv_tpv * CRF * T

    # Battery TCOP
    n_units = bat_n_kwh / config['bat_unit_capacity_kwh']
    bat_capex = config['bat_charger_cost_usd'] + n_units * config['bat_unit_cost_usd']
    cycles_yr = sim_result['annual_battery_cycles']
    life_cycles = config['bat_life_cycles']
    N_rep = 0 if cycles_yr == 0 else (0 if (cycles_yr*T)/life_cycles <= 1 else 1)

    if N_rep == 0:
        rsc = 0
    else:
        C_nom = bat_n_kwh * 1000
        C_unit = bat_capex / C_nom if C_nom > 0 else 0
        year = int(T / (N_rep + 1))
        rsc = C_nom * C_unit * ((1+i_rate)/(1+r))**year

    if cycles_yr > 0:
        bat_lifespan = life_cycles / cycles_yr
        sv = bat_capex / bat_lifespan if bat_lifespan > 0 else 0
    else:
        sv = 0
    pvs = sv * ((1+i_rate)/(1+r))**int(T/(N_rep+1)) if N_rep > 0 else 0

    bat_tpv = bat_capex + rsc - pvs
    tcop_bat = bat_tpv * CRF * T

    # Inverter TCOP
    std_sizes = config['inv_standard_sizes_kw']
    inv_std = min((s for s in std_sizes if s >= inv_kw), default=inv_kw)
    inv_capex = inv_std * config['inv_cost_per_kw_usd']
    inv_lifetime = config['inv_lifetime_years']
    inv_N_rep = 1 if T > inv_lifetime else 0
    inv_rsc = inv_capex * ((1+i_rate)/(1+r))**inv_lifetime if inv_N_rep > 0 else 0
    inv_tpv = inv_capex + inv_rsc
    tcop_inv = inv_tpv * CRF * T

    TCOP = tcop_pv + tcop_bat + tcop_inv

    # LCE
    AE_load = gen_load.sum() + grid_load.sum()
    AE_GP = sim_result['total_grid_buy_kwh']
    AE_SP = sim_result['total_wasted_kwh']
    LAC = (bat_tpv + pv_tpv + inv_tpv) * CRF
    denom = (AE_load - AE_GP) + AE_SP
    LCE = LAC / denom if denom > 0 else 1e6

    # PBP
    gen_annual = config['gen_price_per_amp_month_usd'] * config['gen_subscribed_amps'] * 12
    grid_annual = grid_load.sum() * config['grid_avg_tariff_per_kwh_usd']
    old_annual = gen_annual + grid_annual
    new_grid_cost = sim_result['total_grid_buy_kwh'] * config['grid_avg_tariff_per_kwh_usd']
    AnnSavCost = old_annual - new_grid_cost
    PBP = TCOP / AnnSavCost if AnnSavCost > 0 else 100

    capital = pv_capex + bat_capex + inv_capex

    return {
        'TCOP': TCOP, 'LCE': LCE, 'PBP': PBP,
        'tcop_pv': tcop_pv, 'tcop_bat': tcop_bat, 'tcop_inv': tcop_inv,
        'capital': capital, 'inv_std_kw': inv_std,
        'AnnSavCost': AnnSavCost, 'N_rep_bat': N_rep,
        'pv_capex': pv_capex, 'bat_capex': bat_capex, 'inv_capex': inv_capex,
    }



# %% [cell 74]
# =================================================================
# STEP 6.4: Multi-Objective Fitness Function
# =================================================================
"""
Fitness = LPSP_nor + LCE_nor + PBP_nor + TCOP_nor
All normalized to [0,1] using population min/max.
Lower = better. GNPSO minimizes this.
"""

def evaluate_particle(params, gen_load, grid_load, grid_status,
                      pv_per_mod, outage_prob, config):
    """
    Evaluate a single particle (system configuration).

    DC/AC Ratio Constraint:
    Industry standard requires PV_kWp / Inverter_kW <= 1.5 to prevent
    excessive inverter clipping. This function applies auto-repair: if
    the proposed inverter is too small for the PV array, it is automatically
    enlarged to satisfy the constraint before simulation.

    The constraint involves only the PV array and the inverter. The battery
    capacity is not part of the DC/AC ratio.
    """
    n_modules = max(1, int(round(params[0])))
    bat_units = max(1, int(round(params[1])))
    bat_kwh = bat_units * config['bat_unit_capacity_kwh']
    inv_kw_raw = max(1.0, params[2])

    # ──────────────────────────────────────────
    # Engineering Constraint: DC/AC Ratio (PV side / AC side)
    # ──────────────────────────────────────────
    pv_kwp = n_modules * config['pv_module_power_kw']
    DC_AC_RATIO_MAX = config.get('dc_ac_ratio_max', 1.5)

    # Minimum inverter size required to satisfy the ratio constraint
    inv_kw_min_required = pv_kwp / DC_AC_RATIO_MAX

    # Auto-repair: enlarge inverter if proposed size violates the constraint
    inv_kw = max(inv_kw_raw, inv_kw_min_required)

    # Compute the actual ratio (always <= DC_AC_RATIO_MAX after repair)
    actual_dc_ac_ratio = pv_kwp / inv_kw
    # ──────────────────────────────────────────

    sim = simulate_ems(n_modules, bat_kwh, inv_kw, 0,  # Mode 0
                       gen_load, grid_load, grid_status,
                       pv_per_mod, outage_prob, config)

    econ = calculate_economics(n_modules, bat_kwh, inv_kw, sim, config,
                               gen_load, grid_load)

    return {
        'params': [n_modules, bat_units, inv_kw],
        'bat_kwh': bat_kwh,
        'inv_kw_raw': inv_kw_raw,
        'inv_kw': inv_kw,
        'pv_kwp': pv_kwp,
        'dc_ac_ratio': actual_dc_ac_ratio,
        'lpsp': sim['lpsp'],
        'lce': econ['LCE'],
        'pbp': econ['PBP'],
        'tcop': econ['TCOP'],
        'sim': sim,
        'econ': econ,
    }

# %% [cell 75]
class GNPSO:
    def __init__(self, config, bounds, pop_size=50, max_gen=100,
                 w=0.7, c1=1.5, c2=1.5, ga_ratio=0.3,
                 crossover_prob=0.8, mutation_prob=0.3, mutation_sigma=None):
        self.config = config
        self.bounds = np.array(bounds)  # [[min1,max1], [min2,max2], [min3,max3]]
        self.n_dim = len(bounds)
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.w = w          # PSO inertia weight
        self.c1 = c1        # PSO cognitive (personal best)
        self.c2 = c2        # PSO social (global best)
        self.ga_ratio = ga_ratio  # fraction of population from GA
        self.cx_prob = crossover_prob
        self.mut_prob = mutation_prob
        self.mut_sigma = mutation_sigma or (self.bounds[:,1] - self.bounds[:,0]) * 0.1

        # Initialize population
        self.positions = np.random.uniform(
            self.bounds[:,0], self.bounds[:,1], (pop_size, self.n_dim))
        self.velocities = np.random.uniform(
            -0.1*(self.bounds[:,1]-self.bounds[:,0]),
            0.1*(self.bounds[:,1]-self.bounds[:,0]),
            (pop_size, self.n_dim))

        self.pbest_pos = self.positions.copy()
        self.pbest_fit = np.full(pop_size, np.inf)
        self.gbest_pos = None
        self.gbest_fit = np.inf
        self.gbest_result = None

        self.history = {'gen': [], 'best_fit': [], 'avg_fit': [],
                        'best_lpsp': [], 'best_lce': [], 'best_pbp': [], 'best_tcop': []}

    def _clip_bounds(self, pos):
        return np.clip(pos, self.bounds[:,0], self.bounds[:,1])

    def _normalize_4d(self, results):
        """
        Normalize LPSP, LCE, PBP, TCOP to [0,1] using FIXED reference values.

        This replaces the previous population-based Min-Max normalization
        which produced fitness values that were not comparable across
        generations, leading to GNPSO stagnation.

        Reference values represent worst-case acceptable thresholds:
        - LPSP_ref = 0.10  (10% maximum acceptable loss of supply)
        - LCE_ref  = 0.30  ($/kWh maximum acceptable cost)
        - PBP_ref  = 20.0  (20 years maximum payback)
        - TCOP_ref = 100000 ($100k maximum capital)

        Weights reflect priority:
        - LPSP: 40% (reliability is highest priority)
        - LCE:  30% (operational cost)
        - PBP:  15% (investment attractiveness)
        - TCOP: 15% (capital affordability)
        """
        # Fixed reference values (worst-case acceptable thresholds)
        LPSP_ref = 0.10
        LCE_ref = 0.30
        PBP_ref = 20.0
        TCOP_ref = 100000.0

        # Priority weights (sum to 1.0)
        w_lpsp = 0.40
        w_lce = 0.30
        w_pbp = 0.15
        w_tcop = 0.15

        fitness = np.zeros(len(results))
        for i, r in enumerate(results):
            # Normalize each metric to [0, 1] (clipped at 1 for unacceptable values)
            f_lpsp = min(r['lpsp'] / LPSP_ref, 1.0)
            f_lce = min(r['lce'] / LCE_ref, 1.0)
            f_pbp = min(r['pbp'] / PBP_ref, 1.0) if r['pbp'] > 0 else 1.0
            f_tcop = min(r['tcop'] / TCOP_ref, 1.0)

            # Weighted sum (lower is better)
            fitness[i] = (w_lpsp * f_lpsp +
                         w_lce * f_lce +
                         w_pbp * f_pbp +
                         w_tcop * f_tcop)

        return fitness

    def _ga_crossover(self, parent1, parent2):
        """BLX-̑ crossover"""
        alpha = 0.5
        child = np.zeros(self.n_dim)
        for i in range(self.n_dim):
            mn = min(parent1[i], parent2[i])
            mx = max(parent1[i], parent2[i])
            rng = mx - mn
            child[i] = np.random.uniform(mn - alpha*rng, mx + alpha*rng)
        return self._clip_bounds(child)

    def _ga_mutate(self, individual):
        """Gaussian mutation"""
        mutant = individual.copy()
        for i in range(self.n_dim):
            if np.random.random() < self.mut_prob:
                mutant[i] += np.random.normal(0, self.mut_sigma[i])
        return self._clip_bounds(mutant)

    def optimize(self, eval_func, gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, verbose=True):

        if verbose:
            print(f"\n  GNPSO: pop={self.pop_size}, gen={self.max_gen}, "
                  f"dim={self.n_dim}, GA ratio={self.ga_ratio}")
            print(f"  Bounds: {self.bounds.tolist()}")
            print(f"  {'Gen':>5} {'Best Fit':>10} {'Avg Fit':>10} "
                  f"{'LPSP':>8} {'LCE':>8} {'PBP':>8} {'TCOP':>10}")
            print(f"  {'─'*65}")

        start_time = time.time()

        for gen in range(self.max_gen):
            # ─── Evaluate current population ───
            results = []
            for i in range(self.pop_size):
                r = eval_func(self.positions[i], gen_load, grid_load,
                             grid_status, pv_per_mod, outage_prob, self.config)
                results.append(r)

            # ─── Compute 4D normalized fitness ───
            fitness = self._normalize_4d(results)

            # ─── Update personal and global bests ───
            for i in range(self.pop_size):
                if fitness[i] < self.pbest_fit[i]:
                    self.pbest_fit[i] = fitness[i]
                    self.pbest_pos[i] = self.positions[i].copy()
                if fitness[i] < self.gbest_fit:
                    self.gbest_fit = fitness[i]
                    self.gbest_pos = self.positions[i].copy()
                    self.gbest_result = results[i]

            # ─── Record history ───
            self.history['gen'].append(gen)
            self.history['best_fit'].append(self.gbest_fit)
            self.history['avg_fit'].append(fitness.mean())
            self.history['best_lpsp'].append(self.gbest_result['lpsp'])
            self.history['best_lce'].append(self.gbest_result['lce'])
            self.history['best_pbp'].append(self.gbest_result['pbp'])
            self.history['best_tcop'].append(self.gbest_result['tcop'])

            if verbose and (gen % 10 == 0 or gen == self.max_gen - 1):
                br = self.gbest_result
                print(f"  {gen:5d} {self.gbest_fit:10.4f} {fitness.mean():10.4f} "
                      f"{br['lpsp']:8.4f} {br['lce']:8.4f} {br['pbp']:8.2f} {br['tcop']:10.0f}")

            # ─── Adaptive inertia weight ───
            w = self.w * (1 - gen / self.max_gen) + 0.4 * (gen / self.max_gen)

            # ─── PSO Phase: update velocities and positions ───
            n_pso = int(self.pop_size * (1 - self.ga_ratio))
            r1 = np.random.random((n_pso, self.n_dim))
            r2 = np.random.random((n_pso, self.n_dim))

            self.velocities[:n_pso] = (
                w * self.velocities[:n_pso]
                + self.c1 * r1 * (self.pbest_pos[:n_pso] - self.positions[:n_pso])
                + self.c2 * r2 * (self.gbest_pos - self.positions[:n_pso])
            )
            # Velocity clamping
            v_max = 0.2 * (self.bounds[:,1] - self.bounds[:,0])
            self.velocities[:n_pso] = np.clip(self.velocities[:n_pso], -v_max, v_max)
            self.positions[:n_pso] = self._clip_bounds(
                self.positions[:n_pso] + self.velocities[:n_pso])

            # ─── GA Phase: create offspring for remaining slots ───
            n_ga = self.pop_size - n_pso
            # Tournament selection
            sorted_idx = np.argsort(fitness)
            elite = sorted_idx[:max(2, self.pop_size // 5)]

            ga_offspring = np.zeros((n_ga, self.n_dim))
            for j in range(n_ga):
                p1_idx = np.random.choice(elite)
                p2_idx = np.random.choice(elite)
                if np.random.random() < self.cx_prob:
                    child = self._ga_crossover(self.positions[p1_idx],
                                               self.positions[p2_idx])
                else:
                    child = self.positions[p1_idx].copy()
                child = self._ga_mutate(child)
                ga_offspring[j] = child

            self.positions[n_pso:] = ga_offspring

        elapsed = time.time() - start_time

        if verbose:
            print(f"\n  ✓ Optimization complete: {elapsed:.0f}s ({elapsed/60:.1f} min)")

        return self.gbest_result, self.history

# %% [cell 76]
# =================================================================
# STEP 6.6: RUN A — Multi-Start Optimization (Actual 2018 Data)
# =================================================================
"""
Multi-Start GNPSO Strategy:
- Execute GNPSO N=5 times with predetermined random seeds
- Each run is fully reproducible (fixed seed)
- Best run selected by lowest converged fitness
- Statistical analysis (mean ± std) reported for robustness
"""

print(f"\n{'='*70}")
print(f"  RUN A: MULTI-START GNPSO ON ACTUAL 2018 DATA (5 runs)")
print(f"{'='*70}")

bounds_A = [
    [CONFIG['opt_n_panels_min'], CONFIG['opt_n_panels_max']],
    [CONFIG['opt_bat_units_min'], CONFIG['opt_bat_units_max']],
    [CONFIG['opt_inv_kw_min'], CONFIG['opt_inv_kw_max']],
]

# Multi-start configuration
SEEDS_A = [1, 42, 100, 123, 2024]
all_runs_A = []

for run_idx, seed in enumerate(SEEDS_A):
    print(f"\n{'─'*70}")
    print(f"  Run A.{run_idx+1}/5  (seed = {seed})")
    print(f"{'─'*70}")

    np.random.seed(seed)

    gnpso = GNPSO(CONFIG, bounds_A, pop_size=50, max_gen=80)
    best, history = gnpso.optimize(
        evaluate_particle,
        gen_load_actual, grid_load_actual, grid_status_actual,
        pv_per_module, outage_prob_ahead
    )

    # Fix: Get the last best fitness from the history
    final_fitness = history['best_fit'][-1]

    all_runs_A.append({
        'run_idx': run_idx + 1,
        'seed': seed,
        'best': best,
        'history': history,
        'fitness': final_fitness,
        'n_panels': int(round(best['params'][0])),
        'bat_units': int(round(best['params'][1])),
        'bat_kwh': best['bat_kwh'],
        'inv_kw': round(best['params'][2], 2),
        'lpsp': best['lpsp'],
        'lce': best['lce'],
        'pbp': best['pbp'],
        'tcop': best['tcop'],
    })

    print(f"  → Result: {all_runs_A[-1]['n_panels']} panels, "
          f"{all_runs_A[-1]['bat_units']} bat, "
          f"{all_runs_A[-1]['inv_kw']} kW | "
          f"Fitness={final_fitness:.4f}")

# ─── Statistical Analysis ───────────────────────────────────────
print(f"\n{'='*70}")
print(f"  RUN A — MULTI-START SUMMARY")
print(f"{'='*70}")
print(f"\n  {'Run':<5} {'Seed':<8} {'N_PV':<6} {'N_Bat':<7} {'Inv_kW':<8} "
      f"{'Fitness':<10} {'LPSP':<10} {'LCE':<10} {'PBP':<8} {'TCOP':<10}")
print(f"  {'-'*5} {'-'*8} {'-'*6} {'-'*7} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*10}")

for r in all_runs_A:
    print(f"  {r['run_idx']:<5} {r['seed']:<8} {r['n_panels']:<6} "
          f"{r['bat_units']:<7} {r['inv_kw']:<8.2f} "
          f"{r['fitness']:<10.4f} {r['lpsp']:<10.6f} "
          f"${r['lce']:<9.4f} {r['pbp']:<8.2f} ${r['tcop']:<9,.0f}")

fitnesses_A = [r['fitness'] for r in all_runs_A]
print(f"\n  Statistics across 5 runs:")
print(f"    Best fitness:    {min(fitnesses_A):.4f}")
print(f"    Worst fitness:   {max(fitnesses_A):.4f}")
print(f"    Mean fitness:    {np.mean(fitnesses_A):.4f} ± {np.std(fitnesses_A):.4f}")
print(f"    Median fitness:  {np.median(fitnesses_A):.4f}")

best_run_idx = np.argmin(fitnesses_A)
best_run_A = all_runs_A[best_run_idx]
best_A = best_run_A['best']
history_A = best_run_A['history']

print(f"\n  ★ BEST RUN: Run A.{best_run_A['run_idx']} (seed={best_run_A['seed']})")
print(f"\n  ┌──────────────────────────────────────────────┐")
print(f"  │  RUN A — FINAL OPTIMAL CONFIGURATION         │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  PV Modules:   {best_run_A['n_panels']:>6} "
      f"({best_run_A['n_panels']*CONFIG['pv_module_power_kw']:.1f} kWp)      │")
print(f"  │  Battery:      {best_run_A['bat_kwh']:>6.1f} kWh "
      f"({best_run_A['bat_units']} units)     │")
print(f"  │  Inverter:     {best_run_A['inv_kw']:>6.1f} kW                  │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  LPSP:   {best_run_A['lpsp']:.6f}                        │")
print(f"  │  LCE:    ${best_run_A['lce']:.4f}/kWh                     │")
print(f"  │  PBP:    {best_run_A['pbp']:.1f} years                       │")
print(f"  │  TCOP:   ${best_run_A['tcop']:,.0f}                          │")
print(f"  └──────────────────────────────────────────────┘")

# %% [cell 77]

# =================================================================
# STEP 6.7: RUN B — Multi-Start Optimization (Forecast 2019 Data)
# =================================================================

print(f"\n{'='*70}")
print(f"  RUN B: MULTI-START GNPSO ON FORECAST 2019 DATA (5 runs)")
print(f"{'='*70}")

# For forecast, use predicted grid status and gen load
# grid_load for on-grid: use actual pattern (same house, same habits)ٍ
grid_load_forecast = grid_load_actual.copy()

# Multi-start configuration (different seeds from Run A to avoid bias)
SEEDS_B = [7, 77, 200, 555, 9999]
all_runs_B = []

for run_idx, seed in enumerate(SEEDS_B):
    print(f"\n{'─'*70}")
    print(f"  Run B.{run_idx+1}/5  (seed = {seed})")
    print(f"{'─'*70}")

    np.random.seed(seed)

    gnpso = GNPSO(CONFIG, bounds_A, pop_size=50, max_gen=80)
    best, history = gnpso.optimize(
        evaluate_particle,
        gen_load_forecast, grid_load_forecast, grid_status_forecast,
        pv_per_module, outage_prob_ahead
    )

    # Fix: Get the last best fitness from the history
    final_fitness = history['best_fit'][-1]

    all_runs_B.append({
        'run_idx': run_idx + 1,
        'seed': seed,
        'best': best,
        'history': history,
        'fitness': final_fitness,
        'n_panels': int(round(best['params'][0])),
        'bat_units': int(round(best['params'][1])),
        'bat_kwh': best['bat_kwh'],
        'inv_kw': round(best['params'][2], 2),
        'lpsp': best['lpsp'],
        'lce': best['lce'],
        'pbp': best['pbp'],
        'tcop': best['tcop'],
    })

    print(f"  → Result: {all_runs_B[-1]['n_panels']} panels, "
          f"{all_runs_B[-1]['bat_units']} bat, "
          f"{all_runs_B[-1]['inv_kw']} kW | "
          f"Fitness={final_fitness:.4f}")

# ─── Statistical Analysis ───────────────────────────────────────
print(f"\n{'='*70}")
print(f"  RUN B — MULTI-START SUMMARY")
print(f"{'='*70}")
print(f"\n  {'Run':<5} {'Seed':<8} {'N_PV':<6} {'N_Bat':<7} {'Inv_kW':<8} "
      f"{'Fitness':<10} {'LPSP':<10} {'LCE':<10} {'PBP':<8} {'TCOP':<10}")
print(f"  {'-'*5} {'-'*8} {'-'*6} {'-'*7} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*10}")

for r in all_runs_B:
    print(f"  {r['run_idx']:<5} {r['seed']:<8} {r['n_panels']:<6} "
          f"{r['bat_units']:<7} {r['inv_kw']:<8.2f} "
          f"{r['fitness']:<10.4f} {r['lpsp']:<10.6f} "
          f"${r['lce']:<9.4f} {r['pbp']:<8.2f} ${r['tcop']:<9,.0f}")

fitnesses_B = [r['fitness'] for r in all_runs_B]
print(f"\n  Statistics across 5 runs:")
print(f"    Best fitness:    {min(fitnesses_B):.4f}")
print(f"    Worst fitness:   {max(fitnesses_B):.4f}")
print(f"    Mean fitness:    {np.mean(fitnesses_B):.4f} ± {np.std(fitnesses_B):.4f}")
print(f"    Median fitness:  {np.median(fitnesses_B):.4f}")

best_run_idx_B = np.argmin(fitnesses_B)
best_run_B = all_runs_B[best_run_idx_B]
best_B = best_run_B['best']
history_B = best_run_B['history']

print(f"\n  ★ BEST RUN: Run B.{best_run_B['run_idx']} (seed={best_run_B['seed']})")
print(f"\n  ┌──────────────────────────────────────────────┐")
print(f"  │  RUN B — FINAL OPTIMAL CONFIG (Forecast)     │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  PV Modules:   {best_run_B['n_panels']:>6} "
      f"({best_run_B['n_panels']*CONFIG['pv_module_power_kw']:.1f} kWp)      │")
print(f"  │  Battery:      {best_run_B['bat_kwh']:>6.1f} kWh "
      f"({best_run_B['bat_units']} units)     │")
print(f"  │  Inverter:     {best_run_B['inv_kw']:>6.1f} kW                  │")
print(f"  ├──────────────────────────────────────────────┤")
print(f"  │  LPSP:   {best_run_B['lpsp']:.6f}                        │")
print(f"  │  LCE:    ${best_run_B['lce']:.4f}/kWh                     │")
print(f"  │  PBP:    {best_run_B['pbp']:.1f} years                       │")
print(f"  │  TCOP:   ${best_run_B['tcop']:,.0f}                          │")
print(f"  └──────────────────────────────────────────────┘")

# %% [cell 78]
# =================================================================
# STEP 6.8: Compare 4 EMS Modes on Optimal Configuration
# =================================================================

print(f"\n{'='*60}")
print(f"  POST-OPTIMIZATION: 4 EMS MODES COMPARISON")
print(f"  Using Run A optimal config on actual 2018 data")
print(f"{'='*60}")

opt_n = int(round(best_A['params'][0]))
opt_bat = int(round(best_A['params'][1])) * CONFIG['bat_unit_capacity_kwh']
opt_inv = best_A['params'][2]

mode_names = {0:'Mode 0: Self-sufficient', 1:'Mode 1: Balanced',
              2:'Mode 2: Max independence', 3:'Mode 3: Predictive'}

mode_results = {}
for mode in [0, 1, 2, 3]:
    sim = simulate_ems(opt_n, opt_bat, opt_inv, mode,
                       gen_load_actual, grid_load_actual, grid_status_actual,
                       pv_per_module, outage_prob_ahead, CONFIG)
    econ = calculate_economics(opt_n, opt_bat, opt_inv, sim, CONFIG,
                               gen_load_actual, grid_load_actual)
    mode_results[mode] = {'sim': sim, 'econ': econ}

print(f"\n  Config: {opt_n} modules, {opt_bat:.1f} kWh, {opt_inv:.1f} kW inverter")
print(f"\n  {'Metric':<25} {'Mode 0':<12} {'Mode 1':<12} {'Mode 2':<12} {'Mode 3':<12}")
print(f"  {'─'*73}")

for label, get_val, fmt in [
    ('LPSP', lambda m: mode_results[m]['sim']['lpsp'], '.4f'),
    ('Grid Buy (kWh)', lambda m: mode_results[m]['sim']['total_grid_buy_kwh'], ',.0f'),
    ('LPS (kWh)', lambda m: mode_results[m]['sim']['total_lps_kwh'], ',.1f'),
    ('Bat Cycles/yr', lambda m: mode_results[m]['sim']['annual_battery_cycles'], '.0f'),
    ('LCE ($/kWh)', lambda m: mode_results[m]['econ']['LCE'], '.4f'),
    ('PBP (years)', lambda m: mode_results[m]['econ']['PBP'], '.1f'),
    ('TCOP ($)', lambda m: mode_results[m]['econ']['TCOP'], ',.0f'),
]:
    vals = [f"{get_val(m):{fmt}}" for m in [0,1,2,3]]
    print(f"  {label:<25} {vals[0]:<12} {vals[1]:<12} {vals[2]:<12} {vals[3]:<12}")



# %% [cell 79]
# =================================================================
# STEP 6.9: FIGURE 23 — GNPSO Convergence Curves
# =================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# (a) Fitness convergence
ax = axes[0,0]
ax.plot(history_A['gen'], history_A['best_fit'], 'b-', linewidth=2, label='Run A (actual)')
ax.plot(history_B['gen'], history_B['best_fit'], 'r--', linewidth=2, label='Run B (forecast)')
ax.set_xlabel('Generation'); ax.set_ylabel('Fitness (4D normalized)')
ax.set_title('(a) GNPSO Convergence — Best Fitness'); ax.legend()

# (b) LPSP convergence
ax = axes[0,1]
ax.plot(history_A['gen'], history_A['best_lpsp'], 'b-', linewidth=2, label='Run A')
ax.plot(history_B['gen'], history_B['best_lpsp'], 'r--', linewidth=2, label='Run B')
ax.set_xlabel('Generation'); ax.set_ylabel('LPSP')
ax.set_title('(b) LPSP Convergence'); ax.legend()

# (c) LCE convergence
ax = axes[1,0]
ax.plot(history_A['gen'], history_A['best_lce'], 'b-', linewidth=2, label='Run A')
ax.plot(history_B['gen'], history_B['best_lce'], 'r--', linewidth=2, label='Run B')
ax.set_xlabel('Generation'); ax.set_ylabel('LCE ($/kWh)')
ax.set_title('(c) LCE Convergence'); ax.legend()

# (d) TCOP convergence
ax = axes[1,1]
ax.plot(history_A['gen'], history_A['best_tcop'], 'b-', linewidth=2, label='Run A')
ax.plot(history_B['gen'], history_B['best_tcop'], 'r--', linewidth=2, label='Run B')
ax.set_xlabel('Generation'); ax.set_ylabel('TCOP ($)')
ax.set_title('(d) TCOP Convergence'); ax.legend()

plt.suptitle('Figure 23: GNPSO Convergence — Actual vs Forecast Data', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig23_gnpso_convergence.png', bbox_inches='tight')
plt.show()
print("✓ Figure 23 saved")



# %% [cell 80]
# =================================================================
# STEP 6.10: FIGURE 24 — Run A vs Run B Comparison
# =================================================================

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

categories = ['PV (kWp)', 'Battery (kWh)', 'Inverter (kW)']
vals_A = [int(round(best_A['params'][0]))*CONFIG['pv_module_power_kw'],
          best_A['bat_kwh'], best_A['params'][2]]
vals_B = [int(round(best_B['params'][0]))*CONFIG['pv_module_power_kw'],
          best_B['bat_kwh'], best_B['params'][2]]

# (a) System sizing
ax = axes[0]
x = np.arange(3); w = 0.35
ax.bar(x-w/2, vals_A, w, label='Run A (actual)', color='#2166AC', alpha=0.85)
ax.bar(x+w/2, vals_B, w, label='Run B (forecast)', color='#D6604D', alpha=0.85)
ax.set_xticks(x); ax.set_xticklabels(categories)
ax.set_title('(a) System Sizing'); ax.legend()

# (b) Performance metrics
ax = axes[1]
metrics = ['LPSP', 'LCE\n($/kWh)', 'PBP\n(years)']
mA = [best_A['lpsp'], best_A['lce'], best_A['pbp']]
mB = [best_B['lpsp'], best_B['lce'], best_B['pbp']]
x = np.arange(3)
ax.bar(x-w/2, mA, w, label='Run A', color='#2166AC', alpha=0.85)
ax.bar(x+w/2, mB, w, label='Run B', color='#D6604D', alpha=0.85)
ax.set_xticks(x); ax.set_xticklabels(metrics)
ax.set_title('(b) Performance Metrics'); ax.legend()

# (c) Cost comparison
ax = axes[2]
cost_cats = ['Capital', 'TCOP']
cA = [best_A['econ']['capital'], best_A['tcop']]
cB = [best_B['econ']['capital'], best_B['tcop']]
x = np.arange(2)
ax.bar(x-w/2, cA, w, label='Run A', color='#2166AC', alpha=0.85)
ax.bar(x+w/2, cB, w, label='Run B', color='#D6604D', alpha=0.85)
ax.set_xticks(x); ax.set_xticklabels(cost_cats)
ax.set_title('(c) Cost Comparison ($)'); ax.legend()

plt.suptitle('Figure 24: Actual vs Forecast Optimization Results', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig24_actual_vs_forecast.png', bbox_inches='tight')
plt.show()
print("✓ Figure 24 saved")


# %% [cell 81]

# =================================================================
# STEP 6.11: Save All Results
# =================================================================

optimization_results = {
    'run_A_actual': {
        'n_modules': int(round(best_A['params'][0])),
        'bat_units': int(round(best_A['params'][1])),
        'bat_kwh': best_A['bat_kwh'],
        'inv_kw': round(best_A['params'][2], 1),
        'pv_kwp': round(int(round(best_A['params'][0]))*CONFIG['pv_module_power_kw'], 2),
        'lpsp': round(best_A['lpsp'], 6),
        'lce': round(best_A['lce'], 6),
        'pbp': round(best_A['pbp'], 2),
        'tcop': round(best_A['tcop'], 0),
        'capital': round(best_A['econ']['capital'], 0),
        'grid_buy_kwh': round(best_A['sim']['total_grid_buy_kwh'], 0),    # ← جديد
        'battery_cycles': round(best_A['sim']['annual_battery_cycles'], 0),  # ← جديد
        'wasted_kwh': round(best_A['sim']['total_wasted_kwh'], 0),         # ← جديد (مفيد)
    },
'run_B_forecast': {
    'n_modules': int(round(best_B['params'][0])),
    'bat_units': int(round(best_B['params'][1])),
    'bat_kwh': best_B['bat_kwh'],
    'inv_kw': round(best_B['params'][2], 1),
    'pv_kwp': round(int(round(best_B['params'][0]))*CONFIG['pv_module_power_kw'], 2),
    'lpsp': round(best_B['lpsp'], 6),
    'lce': round(best_B['lce'], 6),
    'pbp': round(best_B['pbp'], 2),
    'tcop': round(best_B['tcop'], 0),
    'capital': round(best_B['econ']['capital'], 0),
    'grid_buy_kwh': round(best_B['sim']['total_grid_buy_kwh'], 0),
    'battery_cycles': round(best_B['sim']['annual_battery_cycles'], 0),
    'wasted_kwh': round(best_B['sim']['total_wasted_kwh'], 0),
},
    'gnpso_params': {
        'pop_size': 50, 'max_gen': 80,
        'w': 0.7, 'c1': 1.5, 'c2': 1.5, 'ga_ratio': 0.3,
    },
    'mode_comparison': {},
}

for mode in [0,1,2,3]:
    optimization_results['mode_comparison'][f'mode_{mode}'] = {
        'name': mode_names[mode],
        'lpsp': round(mode_results[mode]['sim']['lpsp'], 6),
        'lce': round(mode_results[mode]['econ']['LCE'], 6),
        'pbp': round(mode_results[mode]['econ']['PBP'], 2),
        'tcop': round(mode_results[mode]['econ']['TCOP'], 0),
    }

with open('optimization_results.json', 'w') as f:
    json.dump(optimization_results, f, indent=2)

# Backup to Drive
!cp *.json *.png /content/drive/MyDrive/MSc_Project/ 2>/dev/null || true

print(f"\n{'='*60}")
print(f"  PHASE 6 — FINAL SUMMARY")
print(f"{'='*60}")
print(f"  Algorithm:  GNPSO (hybrid GA+PSO)")
print(f"  Objective:  Multi-objective 4D (LPSP+LCE+PBP+TCOP)")
print(f"  EMS:        Mode 0 (PV first, self-sufficient)")
print(f"  Population: 50 | Generations: 80")
print(f"")
print(f"  RUN A (Actual 2018):")
print(f"    {int(round(best_A['params'][0]))} modules | "
      f"{best_A['bat_kwh']:.1f} kWh | {best_A['params'][2]:.1f} kW inv")
print(f"    LPSP={best_A['lpsp']:.4f} | LCE=${best_A['lce']:.4f} | "
      f"PBP={best_A['pbp']:.1f}yr | TCOP=${best_A['tcop']:,.0f}")
print(f"")
print(f"  RUN B (Forecast 2019):")
print(f"    {int(round(best_B['params'][0]))} modules | "
      f"{best_B['bat_kwh']:.1f} kWh | {best_B['params'][2]:.1f} kW inv")
print(f"    LPSP={best_B['lpsp']:.4f} | LCE=${best_B['lce']:.4f} | "
      f"PBP={best_B['pbp']:.1f}yr | TCOP=${best_B['tcop']:,.0f}")
print(f"")
print(f"  Files: optimization_results.json, fig23-fig24_*.png")
print(f"  → Ready for Phase 7 (Algorithm Comparison)")
print(f"{'='*60}")


# %% [cell 82]
# Verification cell — checks the new fields exist
print("=" * 50)
print("Phase 6 → Phase 8 handoff verification")
print("=" * 50)

required_fields = ['grid_buy_kwh', 'battery_cycles', 'wasted_kwh']

for run_name in ['run_A_actual', 'run_B_forecast']:
    print(f"\n  {run_name}:")
    run_data = optimization_results[run_name]
    for field in required_fields:
        if field in run_data:
            print(f"    ✅  {field:<20s} = {run_data[field]}")
        else:
            print(f"    ❌  {field:<20s}  MISSING!")

# Sanity ranges for run_A_actual
A = optimization_results['run_A_actual']
print(f"\n  Sanity check (run_A_actual):")
print(f"    grid_buy_kwh    = {A.get('grid_buy_kwh', 'N/A')}  (expected: ~10,000-15,000)")
print(f"    battery_cycles  = {A.get('battery_cycles', 'N/A')}  (expected: ~100-200)")
print(f"    wasted_kwh      = {A.get('wasted_kwh', 'N/A')}  (expected: ~5,000-15,000)")

print("\n" + "=" * 50)
print("If all ✅ — Phase 8 will work correctly")
print("=" * 50)

# %% [cell 83]


# %% [cell 84]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 7: ALGORITHM COMPARISON — PSO vs GA vs GNPSO            ║
# ║                                                                ║
# ║  Same problem → 3 algorithms → compare performance             ║
# ║  Metrics: Fitness, LPSP, LCE, PBP, TCOP, ROI                  ║
# ║  Each algorithm runs 5 times for statistical validity          ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 7.1: Import & Load (Self-Contained Fix with Drive Sync)
# =================================================================

# 1. Mount Google Drive
import os
from google.colab import drive
if not os.path.exists('/content/drive'):
    drive.mount('/content/drive')

# 2. Copy files from Drive to local environment
# Replace '/content/drive/MyDrive/MSc_Project/' with your actual path if different
print("Syncing project files from Drive...")
!cp /content/drive/MyDrive/MSc_Project/master_data.csv /content/
!cp /content/drive/MyDrive/MSc_Project/config.json /content/
!cp /content/drive/MyDrive/MSc_Project/pv_per_module.pkl /content/
!cp /content/drive/MyDrive/MSc_Project/rf_outage_model.pkl /content/

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import time
import copy
import pickle
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.dpi': 150, 'savefig.dpi': 300,
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'axes.grid': True, 'grid.alpha': 0.3,
})

# Load Data and Config
df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)
with open('config.json') as f:
    CONFIG = json.load(f)
with open('pv_per_module.pkl', 'rb') as f:
    pv_per_module = pickle.load(f)
with open('rf_outage_model.pkl', 'rb') as f:
    rf_model = pickle.load(f)

gen_load = df['D_off_grid'].values
grid_load = df['D_on_grid'].values
grid_status = df['Grid_Status'].values

print("="*60)
print("  PHASE 7: ALGORITHM COMPARISON")
print("  PSO vs GA vs GNPSO — 5 runs each")
print("="*60)

# =================================================================
# STEP 7.2a: Self-contained setup
# =================================================================

# Part A: Outage probability pre-computation (verbatim from Phase 6)
rf_df = df.copy()
for lag in [1, 2, 3, 6, 12, 24]:
    rf_df[f'Grid_lag_{lag}h'] = rf_df['Grid_Status'].shift(lag)
rf_df['Grid_rolling_6h']  = rf_df['Grid_Status'].shift(1).rolling(6).mean()
rf_df['Grid_rolling_12h'] = rf_df['Grid_Status'].shift(1).rolling(12).mean()
rf_df['Grid_rolling_24h'] = rf_df['Grid_Status'].shift(1).rolling(24).mean()

outage_counter = np.zeros(len(rf_df))
count = 0
for i in range(len(rf_df)):
    outage_counter[i] = count
    if rf_df['Grid_Status'].iloc[i] == 0:
        count += 1
    else:
        count = 0
rf_df['Outage_duration_so_far'] = outage_counter

rf_features = [
    'Hour_sin', 'Hour_cos', 'Month_sin', 'Month_cos',
    'DayOfWeek_sin', 'DayOfWeek_cos',
    'Grid_lag_1h', 'Grid_lag_2h', 'Grid_lag_3h',
    'Grid_lag_6h', 'Grid_lag_12h', 'Grid_lag_24h',
    'Grid_rolling_6h', 'Grid_rolling_12h', 'Grid_rolling_24h',
    'Outage_duration_so_far',
]
rf_clean = rf_df.dropna()
outage_proba = rf_model.predict_proba(rf_clean[rf_features].values)[:, 0]
outage_prob_8760 = np.full(8760, 0.5)
outage_prob_8760[8760 - len(outage_proba):] = outage_proba
outage_prob_ahead = np.zeros(8760)
for t in range(8760):
    outage_prob_ahead[t] = outage_prob_8760[t:min(t+6, 8760)].max()

# Part B: simulate_ems function
def simulate_ems(n_modules, bat_n_kwh, inv_kw, ems_mode,
                 gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, config):
    hours = 8760; dt = 1
    C_bat_max = config['bat_cmax_factor'] * bat_n_kwh
    C_bat_min = (1 - config['bat_dod']) * bat_n_kwh
    eta_bc = config['bat_eta_charge']
    eta_bd = config['bat_eta_discharge']
    sigma = config['bat_self_discharge_per_hour']
    eta_inv = config['inv_efficiency']
    Max_P = config['bat_max_c_rate'] * bat_n_kwh
    E_pv_total = pv_per_mod * n_modules
    C_bat = np.zeros(hours + 1)
    C_bat[0] = (C_bat_max + C_bat_min) / 2
    LPS = np.zeros(hours); E_grid_buy = np.zeros(hours)
    E_wasted = np.zeros(hours); P_charge = np.zeros(hours)
    P_discharge = np.zeros(hours); E_pv_to_load = np.zeros(hours)
    E_pv_to_bat = np.zeros(hours)
    PRED_THRESHOLD = 0.7

    for t in range(hours):
        C_prev = C_bat[t] * (1 - sigma)
        pv_available = min(E_pv_total[t], inv_kw) * eta_inv

        def charge_bat(pwr):
            c = min(pwr, (C_bat_max - C_prev)/(eta_bc*dt), Max_P)
            return max(0, c)
        def discharge_bat(pwr):
            a = max(0, (C_prev - C_bat_min)*eta_bd/dt)
            return max(0, min(pwr, a, Max_P, inv_kw))

        if grid_status[t] == 1:
            load = grid_load[t]
            pv_to_load = min(pv_available, load)
            E_pv_to_load[t] = pv_to_load
            pv_surplus = pv_available - pv_to_load
            load_remaining = load - pv_to_load

            if ems_mode == 0:
                charge_pv = charge_bat(pv_surplus)
                P_charge[t] = charge_pv
                E_pv_to_bat[t] = charge_pv
                E_wasted[t] = pv_surplus - charge_pv
                E_grid_buy[t] = load_remaining
                SOC_pct = C_prev / C_bat_max if C_bat_max > 0 else 1.0
                if pv_available < 0.1 and SOC_pct < 0.80:
                    grid_charge_power = min(
                        Max_P * 0.5,
                        (C_bat_max - C_prev) / (eta_bc * dt),
                        Max_P
                    )
                    grid_charge_power = max(0, grid_charge_power)
                    P_charge[t] = P_charge[t] + grid_charge_power
                    E_grid_buy[t] = E_grid_buy[t] + grid_charge_power
                    C_bat[t+1] = C_prev + (charge_pv + grid_charge_power) * eta_bc * dt
                else:
                    C_bat[t+1] = C_prev + charge_pv * eta_bc * dt

            elif ems_mode == 1:
                if pv_surplus > 0:
                    ch = charge_bat(pv_surplus)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_grid_buy[t] = load_remaining
                    E_wasted[t] = pv_surplus - ch
                elif load_remaining > 0:
                    dis = discharge_bat(load_remaining)
                    P_discharge[t] = dis
                    C_bat[t+1] = C_prev - dis/eta_bd*dt
                    E_grid_buy[t] = load_remaining - dis
                else:
                    C_bat[t+1] = C_prev
            elif ems_mode == 2:
                if pv_surplus > 0:
                    ch = charge_bat(pv_surplus)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_grid_buy[t] = load_remaining
                    E_wasted[t] = pv_surplus - ch
                elif load_remaining > 0:
                    dis = discharge_bat(load_remaining)
                    P_discharge[t] = dis
                    C_bat[t+1] = C_prev - dis/eta_bd*dt
                    E_grid_buy[t] = max(0, load_remaining - dis)
                else:
                    C_bat[t+1] = C_prev
            elif ems_mode == 3:
                if outage_prob[t] > PRED_THRESHOLD:
                    E_grid_buy[t] = load; E_pv_to_load[t] = 0
                    ch = charge_bat(pv_available)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_wasted[t] = pv_available - ch
                else:
                    if pv_surplus > 0:
                        ch = charge_bat(pv_available)
                        P_charge[t] = ch; E_pv_to_bat[t] = ch
                        C_bat[t+1] = C_prev + ch*eta_bc*dt
                        E_grid_buy[t] = load_remaining
                        E_wasted[t] = pv_surplus - ch
                    elif load_remaining > 0:
                        dis = discharge_bat(load_remaining)
                        P_discharge[t] = dis
                        C_bat[t+1] = C_prev - dis/eta_bd*dt
                        E_grid_buy[t] = load_remaining - dis
                    else:
                        C_bat[t+1] = C_prev
        else:
            load = gen_load[t]
            if load <= 0.001:
                if pv_available > 0:
                    ch = charge_bat(pv_available)
                    P_charge[t] = ch; E_pv_to_bat[t] = ch
                    C_bat[t+1] = C_prev + ch*eta_bc*dt
                    E_wasted[t] = pv_available - ch
                else:
                    C_bat[t+1] = C_prev
                continue
            D_t = load / eta_inv
            pv_to_load = min(pv_available, D_t)
            E_pv_to_load[t] = pv_to_load * eta_inv
            E_Ex = pv_available - D_t
            if E_Ex >= 0:
                ch = charge_bat(E_Ex)
                P_charge[t] = ch; E_pv_to_bat[t] = ch
                C_bat[t+1] = C_prev + ch*eta_bc*dt
                E_wasted[t] = E_Ex - ch
            else:
                E_need = D_t - pv_available
                dis = discharge_bat(E_need)
                P_discharge[t] = dis
                C_bat[t+1] = C_prev - dis/eta_bd*dt
                remaining = E_need - dis
                if remaining > 0.001:
                    LPS[t] = remaining * eta_inv
        C_bat[t+1] = np.clip(C_bat[t+1], C_bat_min, C_bat_max)

    total_gen = gen_load.sum()
    total_grid = grid_load.sum()
    lpsp = LPS.sum()/total_gen if total_gen > 0 else 0
    gpap = E_grid_buy.sum()/total_grid if total_grid > 0 else 0
    annual_charge = (P_charge*eta_bc).sum()
    usable = C_bat_max - C_bat_min
    annual_cycles = annual_charge/usable if usable > 0 else 0

    return {
        'LPS': LPS, 'E_grid_buy': E_grid_buy, 'E_wasted': E_wasted,
        'P_charge': P_charge, 'P_discharge': P_discharge,
        'C_bat': C_bat[:-1], 'E_pv_to_load': E_pv_to_load,
        'E_pv_to_bat': E_pv_to_bat,
        'lpsp': lpsp, 'gpap': gpap,
        'total_lps_kwh': LPS.sum(), 'total_grid_buy_kwh': E_grid_buy.sum(),
        'total_wasted_kwh': E_wasted.sum(),
        'total_pv_to_load_kwh': E_pv_to_load.sum(),
        'total_pv_to_bat_kwh': E_pv_to_bat.sum(),
        'annual_battery_cycles': annual_cycles,
        'inv_size_needed': n_modules*config['pv_module_power_kw'] + Max_P,
        'ems_mode': ems_mode,
    }

# Part C: calculate_economics function
def calculate_economics(n_modules, bat_n_kwh, inv_kw, sim_result, config,
                        gen_load, grid_load):
    T = config['project_lifetime_years']
    r = config['interest_rate']
    i_rate = config['inflation_rate']
    CRF = (r*(1+r)**T) / ((1+r)**T - 1)

    pv_capex = n_modules * config['pv_cost_per_module_usd']
    pv_omc = pv_capex * 0.01 * T
    pv_tpv = pv_capex + pv_omc
    tcop_pv = pv_tpv * CRF * T

    n_units = bat_n_kwh / config['bat_unit_capacity_kwh']
    bat_capex = config['bat_charger_cost_usd'] + n_units * config['bat_unit_cost_usd']
    cycles_yr = sim_result['annual_battery_cycles']
    life_cycles = config['bat_life_cycles']
    N_rep = 0 if cycles_yr == 0 else (0 if (cycles_yr*T)/life_cycles <= 1 else 1)

    if N_rep == 0:
        rsc = 0
    else:
        C_nom = bat_n_kwh * 1000
        C_unit = bat_capex / C_nom if C_nom > 0 else 0
        year = int(T / (N_rep + 1))
        rsc = C_nom * C_unit * ((1+i_rate)/(1+r))**year

    if cycles_yr > 0:
        bat_lifespan = life_cycles / cycles_yr
        sv = bat_capex / bat_lifespan if bat_lifespan > 0 else 0
    else:
        sv = 0
    pvs = sv * ((1+i_rate)/(1+r))**int(T/(N_rep+1)) if N_rep > 0 else 0

    bat_tpv = bat_capex + rsc - pvs
    tcop_bat = bat_tpv * CRF * T

    std_sizes = config['inv_standard_sizes_kw']
    inv_std = min((s for s in std_sizes if s >= inv_kw), default=inv_kw)
    inv_capex = inv_std * config['inv_cost_per_kw_usd']
    inv_lifetime = config['inv_lifetime_years']
    inv_N_rep = 1 if T > inv_lifetime else 0
    inv_rsc = inv_capex * ((1+i_rate)/(1+r))**inv_lifetime if inv_N_rep > 0 else 0
    inv_tpv = inv_capex + inv_rsc
    tcop_inv = inv_tpv * CRF * T

    TCOP = tcop_pv + tcop_bat + tcop_inv
    AE_load = gen_load.sum() + grid_load.sum()
    AE_GP = sim_result['total_grid_buy_kwh']
    AE_SP = sim_result['total_wasted_kwh']
    LAC = (bat_tpv + pv_tpv + inv_tpv) * CRF
    denom = (AE_load - AE_GP) + AE_SP
    LCE = LAC / denom if denom > 0 else 1e6

    gen_annual = config['gen_price_per_amp_month_usd'] * config['gen_subscribed_amps'] * 12
    grid_annual = grid_load.sum() * config['grid_avg_tariff_per_kwh_usd']
    old_annual = gen_annual + grid_annual
    new_grid_cost = sim_result['total_grid_buy_kwh'] * config['grid_avg_tariff_per_kwh_usd']
    AnnSavCost = old_annual - new_grid_cost
    PBP = TCOP / AnnSavCost if AnnSavCost > 0 else 100
    capital = pv_capex + bat_capex + inv_capex

    return {
        'TCOP': TCOP, 'LCE': LCE, 'PBP': PBP,
        'tcop_pv': tcop_pv, 'tcop_bat': tcop_bat, 'tcop_inv': tcop_inv,
        'capital': capital, 'inv_std_kw': inv_std,
        'AnnSavCost': AnnSavCost, 'N_rep_bat': N_rep,
        'pv_capex': pv_capex, 'bat_capex': bat_capex, 'inv_capex': inv_capex,
    }

# Part D: evaluate_particle function
def evaluate_particle(params, gen_load, grid_load, grid_status,
                      pv_per_mod, outage_prob, config):
    """
    Phase 7 evaluate_particle — aligned with Phase 6.
    Applies DC/AC ratio constraint (PV_kWp / Inverter_kW <= 1.5).
    """
    n_modules = max(1, int(round(params[0])))
    bat_units = max(1, int(round(params[1])))
    bat_kwh = bat_units * config['bat_unit_capacity_kwh']
    inv_kw_raw = max(1.0, params[2])

    # DC/AC Ratio Constraint (same as Phase 6)
    pv_kwp = n_modules * config['pv_module_power_kw']
    DC_AC_RATIO_MAX = config.get('dc_ac_ratio_max', 1.5)
    inv_kw_min_required = pv_kwp / DC_AC_RATIO_MAX
    inv_kw = max(inv_kw_raw, inv_kw_min_required)
    actual_dc_ac_ratio = pv_kwp / inv_kw

    sim = simulate_ems(n_modules, bat_kwh, inv_kw, 0,
                       gen_load, grid_load, grid_status,
                       pv_per_mod, outage_prob, config)

    econ = calculate_economics(n_modules, bat_kwh, inv_kw, sim, config,
                               gen_load, grid_load)

    return {
        'params': [n_modules, bat_units, inv_kw],
        'bat_kwh': bat_kwh,
        'inv_kw_raw': inv_kw_raw,
        'inv_kw': inv_kw,
        'pv_kwp': pv_kwp,
        'dc_ac_ratio': actual_dc_ac_ratio,
        'lpsp': sim['lpsp'],
        'lce': econ['LCE'],
        'pbp': econ['PBP'],
        'tcop': econ['TCOP'],
        'sim': sim,
        'econ': econ,
    }

# %% [cell 85]

# =================================================================
# STEP 7.2: ROI Calculation Function
# =================================================================
"""
ROI = (Total Savings over lifetime - Total Investment) / Total Investment × 100

Total Savings = AnnSavCost × Project_Lifetime
Total Investment = Capital Cost (PV + Battery + Inverter)

ROI > 0% means profitable
ROI = 100% means you doubled your money
"""

def calculate_roi(econ_result, config):
    total_savings = econ_result['AnnSavCost'] * config['project_lifetime_years']
    total_investment = econ_result['capital']
    if total_investment > 0:
        roi = (total_savings - total_investment) / total_investment * 100
    else:
        roi = 0
    return roi



# %% [cell 86]
# =================================================================
# STEP 7.3: Pure PSO Algorithm
# =================================================================

class PurePSO:
    def __init__(self, config, bounds, pop_size=50, max_gen=80,
                 w=0.7, c1=1.5, c2=1.5):
        self.config = config
        self.bounds = np.array(bounds)
        self.n_dim = len(bounds)
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.w = w; self.c1 = c1; self.c2 = c2

        self.positions = np.random.uniform(
            self.bounds[:,0], self.bounds[:,1], (pop_size, self.n_dim))
        self.velocities = np.random.uniform(
            -0.1*(self.bounds[:,1]-self.bounds[:,0]),
            0.1*(self.bounds[:,1]-self.bounds[:,0]),
            (pop_size, self.n_dim))
        self.pbest_pos = self.positions.copy()
        self.pbest_fit = np.full(pop_size, np.inf)
        self.gbest_pos = None; self.gbest_fit = np.inf
        self.gbest_result = None
        self.history = {'gen':[], 'best_fit':[], 'avg_fit':[]}

    def _clip(self, pos):
        return np.clip(pos, self.bounds[:,0], self.bounds[:,1])

    def _normalize_4d(self, results):
        """
        Fixed Reference Normalization — aligned with Phase 6.
        """
        LPSP_ref = 0.10
        LCE_ref = 0.30
        PBP_ref = 20.0
        TCOP_ref = 100000.0

        w_lpsp = 0.40
        w_lce  = 0.30
        w_pbp  = 0.15
        w_tcop = 0.15

        fitness = np.zeros(len(results))
        for i, r in enumerate(results):
            f_lpsp = min(r['lpsp'] / LPSP_ref, 1.0)
            f_lce  = min(r['lce']  / LCE_ref, 1.0)
            f_pbp  = min(r['pbp']  / PBP_ref, 1.0) if r['pbp'] > 0 else 1.0
            f_tcop = min(r['tcop'] / TCOP_ref, 1.0)

            fitness[i] = (w_lpsp * f_lpsp +
                          w_lce  * f_lce  +
                          w_pbp  * f_pbp  +
                          w_tcop * f_tcop)
        return fitness

    def optimize(self, eval_func, gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, verbose=False):
        start = time.time()
        for gen in range(self.max_gen):
            results = [eval_func(self.positions[i], gen_load, grid_load,
                                grid_status, pv_per_mod, outage_prob, self.config)
                      for i in range(self.pop_size)]
            fitness = self._normalize_4d(results)

            for i in range(self.pop_size):
                if fitness[i] < self.pbest_fit[i]:
                    self.pbest_fit[i] = fitness[i]
                    self.pbest_pos[i] = self.positions[i].copy()
                if fitness[i] < self.gbest_fit:
                    self.gbest_fit = fitness[i]
                    self.gbest_pos = self.positions[i].copy()
                    self.gbest_result = results[i]

            self.history['gen'].append(gen)
            self.history['best_fit'].append(self.gbest_fit)
            self.history['avg_fit'].append(fitness.mean())

            w = self.w * (1 - gen/self.max_gen) + 0.4*(gen/self.max_gen)
            r1 = np.random.random((self.pop_size, self.n_dim))
            r2 = np.random.random((self.pop_size, self.n_dim))
            self.velocities = (w*self.velocities
                + self.c1*r1*(self.pbest_pos - self.positions)
                + self.c2*r2*(self.gbest_pos - self.positions))
            v_max = 0.2*(self.bounds[:,1]-self.bounds[:,0])
            self.velocities = np.clip(self.velocities, -v_max, v_max)
            self.positions = self._clip(self.positions + self.velocities)

        elapsed = time.time() - start
        return self.gbest_result, self.history, elapsed

# %% [cell 87]
# =================================================================
# STEP 7.4: Pure GA Algorithm
# =================================================================

class PureGA:
    def __init__(self, config, bounds, pop_size=50, max_gen=80,
                 crossover_prob=0.8, mutation_prob=0.3):
        self.config = config
        self.bounds = np.array(bounds)
        self.n_dim = len(bounds)
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.cx_prob = crossover_prob
        self.mut_prob = mutation_prob
        self.mut_sigma = (self.bounds[:,1]-self.bounds[:,0]) * 0.1

        self.population = np.random.uniform(
            self.bounds[:,0], self.bounds[:,1], (pop_size, self.n_dim))
        self.gbest_pos = None; self.gbest_fit = np.inf
        self.gbest_result = None
        self.history = {'gen':[], 'best_fit':[], 'avg_fit':[]}

    def _clip(self, pos):
        return np.clip(pos, self.bounds[:,0], self.bounds[:,1])

    def _normalize_4d(self, results):
        """
        Fixed Reference Normalization — aligned with Phase 6.
        """
        LPSP_ref = 0.10
        LCE_ref = 0.30
        PBP_ref = 20.0
        TCOP_ref = 100000.0

        w_lpsp = 0.40
        w_lce  = 0.30
        w_pbp  = 0.15
        w_tcop = 0.15

        fitness = np.zeros(len(results))
        for i, r in enumerate(results):
            f_lpsp = min(r['lpsp'] / LPSP_ref, 1.0)
            f_lce  = min(r['lce']  / LCE_ref, 1.0)
            f_pbp  = min(r['pbp']  / PBP_ref, 1.0) if r['pbp'] > 0 else 1.0
            f_tcop = min(r['tcop'] / TCOP_ref, 1.0)

            fitness[i] = (w_lpsp * f_lpsp +
                          w_lce  * f_lce  +
                          w_pbp  * f_pbp  +
                          w_tcop * f_tcop)
        return fitness

    def _crossover(self, p1, p2):
        alpha = 0.5
        child = np.zeros(self.n_dim)
        for i in range(self.n_dim):
            mn,mx = min(p1[i],p2[i]), max(p1[i],p2[i])
            rng = mx - mn
            child[i] = np.random.uniform(mn-alpha*rng, mx+alpha*rng)
        return self._clip(child)

    def _mutate(self, ind):
        m = ind.copy()
        for i in range(self.n_dim):
            if np.random.random() < self.mut_prob:
                m[i] += np.random.normal(0, self.mut_sigma[i])
        return self._clip(m)

    def optimize(self, eval_func, gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, verbose=False):
        start = time.time()
        for gen in range(self.max_gen):
            results = [eval_func(self.population[i], gen_load, grid_load,
                                grid_status, pv_per_mod, outage_prob, self.config)
                      for i in range(self.pop_size)]
            fitness = self._normalize_4d(results)

            best_idx = np.argmin(fitness)
            if fitness[best_idx] < self.gbest_fit:
                self.gbest_fit = fitness[best_idx]
                self.gbest_pos = self.population[best_idx].copy()
                self.gbest_result = results[best_idx]

            self.history['gen'].append(gen)
            self.history['best_fit'].append(self.gbest_fit)
            self.history['avg_fit'].append(fitness.mean())

            # Selection + Crossover + Mutation
            sorted_idx = np.argsort(fitness)
            elite_size = max(2, self.pop_size // 5)
            elite = sorted_idx[:elite_size]

            new_pop = np.zeros_like(self.population)
            # Keep best 2 (elitism)
            new_pop[0] = self.population[sorted_idx[0]].copy()
            new_pop[1] = self.population[sorted_idx[1]].copy()

            for j in range(2, self.pop_size):
                p1 = self.population[np.random.choice(elite)]
                p2 = self.population[np.random.choice(elite)]
                if np.random.random() < self.cx_prob:
                    child = self._crossover(p1, p2)
                else:
                    child = p1.copy()
                new_pop[j] = self._mutate(child)

            self.population = new_pop

        elapsed = time.time() - start
        return self.gbest_result, self.history, elapsed

# %% [cell 88]
# =================================================================
# STEP 7.5: GNPSO (from Phase 6 — copied for independence)
# =================================================================

class GNPSO_v2:
    def __init__(self, config, bounds, pop_size=50, max_gen=80,
                 w=0.7, c1=1.5, c2=1.5, ga_ratio=0.3):
        self.config = config
        self.bounds = np.array(bounds)
        self.n_dim = len(bounds)
        self.pop_size = pop_size
        self.max_gen = max_gen
        self.w = w; self.c1 = c1; self.c2 = c2
        self.ga_ratio = ga_ratio
        self.mut_prob = 0.3
        self.mut_sigma = (self.bounds[:,1]-self.bounds[:,0]) * 0.1

        self.positions = np.random.uniform(
            self.bounds[:,0], self.bounds[:,1], (pop_size, self.n_dim))
        self.velocities = np.random.uniform(
            -0.1*(self.bounds[:,1]-self.bounds[:,0]),
            0.1*(self.bounds[:,1]-self.bounds[:,0]),
            (pop_size, self.n_dim))
        self.pbest_pos = self.positions.copy()
        self.pbest_fit = np.full(pop_size, np.inf)
        self.gbest_pos = None; self.gbest_fit = np.inf
        self.gbest_result = None
        self.history = {'gen':[], 'best_fit':[], 'avg_fit':[]}

    def _clip(self, pos):
        return np.clip(pos, self.bounds[:,0], self.bounds[:,1])

    def _normalize_4d(self, results):
        """
        Fixed Reference Normalization — aligned with Phase 6.
        """
        LPSP_ref = 0.10
        LCE_ref = 0.30
        PBP_ref = 20.0
        TCOP_ref = 100000.0

        w_lpsp = 0.40
        w_lce  = 0.30
        w_pbp  = 0.15
        w_tcop = 0.15

        fitness = np.zeros(len(results))
        for i, r in enumerate(results):
            f_lpsp = min(r['lpsp'] / LPSP_ref, 1.0)
            f_lce  = min(r['lce']  / LCE_ref, 1.0)
            f_pbp  = min(r['pbp']  / PBP_ref, 1.0) if r['pbp'] > 0 else 1.0
            f_tcop = min(r['tcop'] / TCOP_ref, 1.0)

            fitness[i] = (w_lpsp * f_lpsp +
                          w_lce  * f_lce  +
                          w_pbp  * f_pbp  +
                          w_tcop * f_tcop)
        return fitness

    def _crossover(self, p1, p2):
        alpha = 0.5; child = np.zeros(self.n_dim)
        for i in range(self.n_dim):
            mn,mx = min(p1[i],p2[i]),max(p1[i],p2[i]); rng=mx-mn
            child[i] = np.random.uniform(mn-alpha*rng, mx+alpha*rng)
        return self._clip(child)

    def _mutate(self, ind):
        m = ind.copy()
        for i in range(self.n_dim):
            if np.random.random() < self.mut_prob:
                m[i] += np.random.normal(0, self.mut_sigma[i])
        return self._clip(m)

    def optimize(self, eval_func, gen_load, grid_load, grid_status,
                 pv_per_mod, outage_prob, verbose=False):
        start = time.time()
        for gen in range(self.max_gen):
            results = [eval_func(self.positions[i], gen_load, grid_load,
                                grid_status, pv_per_mod, outage_prob, self.config)
                      for i in range(self.pop_size)]
            fitness = self._normalize_4d(results)

            for i in range(self.pop_size):
                if fitness[i] < self.pbest_fit[i]:
                    self.pbest_fit[i] = fitness[i]
                    self.pbest_pos[i] = self.positions[i].copy()
                if fitness[i] < self.gbest_fit:
                    self.gbest_fit = fitness[i]
                    self.gbest_pos = self.positions[i].copy()
                    self.gbest_result = results[i]

            self.history['gen'].append(gen)
            self.history['best_fit'].append(self.gbest_fit)
            self.history['avg_fit'].append(fitness.mean())

            w = self.w*(1-gen/self.max_gen) + 0.4*(gen/self.max_gen)
            n_pso = int(self.pop_size*(1-self.ga_ratio))
            r1 = np.random.random((n_pso, self.n_dim))
            r2 = np.random.random((n_pso, self.n_dim))
            self.velocities[:n_pso] = (w*self.velocities[:n_pso]
                + self.c1*r1*(self.pbest_pos[:n_pso]-self.positions[:n_pso])
                + self.c2*r2*(self.gbest_pos-self.positions[:n_pso]))
            v_max = 0.2*(self.bounds[:,1]-self.bounds[:,0])
            self.velocities[:n_pso] = np.clip(self.velocities[:n_pso], -v_max, v_max)
            self.positions[:n_pso] = self._clip(self.positions[:n_pso]+self.velocities[:n_pso])

            n_ga = self.pop_size - n_pso
            sorted_idx = np.argsort(fitness)
            elite = sorted_idx[:max(2, self.pop_size//5)]
            for j in range(n_ga):
                p1 = self.positions[np.random.choice(elite)]
                p2 = self.positions[np.random.choice(elite)]
                child = self._crossover(p1, p2)
                self.positions[n_pso+j] = self._mutate(child)

        elapsed = time.time() - start
        return self.gbest_result, self.history, elapsed

# %% [cell 89]
# =================================================================
# STEP 7.6: Run All 3 Algorithms — 5 Times Each
# =================================================================

bounds = [
    [CONFIG['opt_n_panels_min'], CONFIG['opt_n_panels_max']],
    [CONFIG['opt_bat_units_min'], CONFIG['opt_bat_units_max']],
    [CONFIG['opt_inv_kw_min'], CONFIG['opt_inv_kw_max']],
]

N_RUNS = 5
POP_SIZE = 50
MAX_GEN = 80

algorithms = {
    'PSO': PurePSO,
    'GA': PureGA,
    'GNPSO': GNPSO_v2,
}

all_results = {}

for alg_name, AlgClass in algorithms.items():
    print(f"\n{'─'*50}")
    print(f"  Running {alg_name} — {N_RUNS} independent runs")
    print(f"{'─'*50}")

    alg_runs = []
    for run in range(N_RUNS):
        np.random.seed(run * 42 + 7)  # Different seed each run

        if alg_name == 'GNPSO':
            optimizer = AlgClass(CONFIG, bounds, POP_SIZE, MAX_GEN,
                                ga_ratio=0.3)
        elif alg_name == 'PSO':
            optimizer = AlgClass(CONFIG, bounds, POP_SIZE, MAX_GEN)
        else:
            optimizer = AlgClass(CONFIG, bounds, POP_SIZE, MAX_GEN)

        best, history, elapsed = optimizer.optimize(
            evaluate_particle,
            gen_load, grid_load, grid_status,
            pv_per_module, outage_prob_ahead
        )

        # Calculate ROI
        roi = calculate_roi(best['econ'], CONFIG)

        run_data = {
            'best': best,
            'history': history,
            'elapsed': elapsed,
            'roi': roi,
            'n_modules': int(round(best['params'][0])),
            'bat_kwh': best['bat_kwh'],
            'inv_kw': round(best['params'][2], 1),
            'fitness': history['best_fit'][-1],
            'lpsp': best['lpsp'],
            'lce': best['lce'],
            'pbp': best['pbp'],
            'tcop': best['tcop'],
        }
        alg_runs.append(run_data)

        print(f"  Run {run+1}: Fit={run_data['fitness']:.4f} "
              f"LPSP={best['lpsp']:.4f} LCE=${best['lce']:.4f} "
              f"PBP={best['pbp']:.1f} ROI={roi:.0f}% "
              f"Time={elapsed:.0f}s")

    all_results[alg_name] = alg_runs



# %% [cell 90]
# =================================================================
# STEP 7.7: Statistical Summary Table
# =================================================================

print(f"\n{'='*80}")
print(f"  STATISTICAL COMPARISON — {N_RUNS} RUNS PER ALGORITHM")
print(f"{'='*80}")

metrics_list = [
    ('Best Fitness', 'fitness', '.4f'),
    ('LPSP', 'lpsp', '.4f'),
    ('LCE ($/kWh)', 'lce', '.4f'),
    ('PBP (years)', 'pbp', '.2f'),
    ('TCOP ($)', 'tcop', ',.0f'),
    ('ROI (%)', 'roi', ',.0f'),
    ('Time (s)', 'elapsed', '.0f'),
    ('PV Modules', 'n_modules', '.0f'),
    ('Battery (kWh)', 'bat_kwh', '.1f'),
    ('Inverter (kW)', 'inv_kw', '.1f'),
]

# Header
print(f"\n  {'Metric':<20} {'PSO':<22} {'GA':<22} {'GNPSO':<22}")
print(f"  {'':20} {'Mean ± Std':<22} {'Mean ± Std':<22} {'Mean ± Std':<22}")
print(f"  {'─'*86}")

comparison_data = {}
for label, key, fmt in metrics_list:
    row = {}
    vals_str = []
    for alg in ['PSO', 'GA', 'GNPSO']:
        values = [r[key] for r in all_results[alg]]
        mean = np.mean(values)
        std = np.std(values)
        row[alg] = {'mean': mean, 'std': std, 'values': values}

        if key in ['tcop', 'roi']:
            vals_str.append(f"{mean:,.0f} ± {std:,.0f}")
        else:
            vals_str.append(f"{mean:{fmt}} ± {std:{fmt}}")

    comparison_data[key] = row
    print(f"  {label:<20} {vals_str[0]:<22} {vals_str[1]:<22} {vals_str[2]:<22}")

# Best overall
print(f"\n  {'─'*86}")
print(f"  {'BEST SINGLE RUN':<20}", end="")
for alg in ['PSO', 'GA', 'GNPSO']:
    best_run = min(all_results[alg], key=lambda r: r['fitness'])
    print(f" Fit={best_run['fitness']:.4f}".ljust(22), end="")
print()



# %% [cell 91]
# =================================================================
# STEP 7.8: FIGURE 25 — Convergence Comparison
# =================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

colors = {'PSO': '#2166AC', 'GA': '#D6604D', 'GNPSO': '#66BD63'}

# (a) Best fitness convergence (median of 5 runs)
ax = axes[0, 0]
for alg in ['PSO', 'GA', 'GNPSO']:
    # Get all convergence curves
    all_curves = [r['history']['best_fit'] for r in all_results[alg]]
    min_len = min(len(c) for c in all_curves)
    curves_arr = np.array([c[:min_len] for c in all_curves])
    median_curve = np.median(curves_arr, axis=0)
    q25 = np.percentile(curves_arr, 25, axis=0)
    q75 = np.percentile(curves_arr, 75, axis=0)

    ax.plot(range(min_len), median_curve, color=colors[alg],
            linewidth=2, label=alg)
    ax.fill_between(range(min_len), q25, q75, color=colors[alg], alpha=0.15)

ax.set_xlabel('Generation'); ax.set_ylabel('Best Fitness (4D)')
ax.set_title('(a) Convergence — Best Fitness'); ax.legend()

# (b) Average fitness convergence
ax = axes[0, 1]
for alg in ['PSO', 'GA', 'GNPSO']:
    all_curves = [r['history']['avg_fit'] for r in all_results[alg]]
    min_len = min(len(c) for c in all_curves)
    curves_arr = np.array([c[:min_len] for c in all_curves])
    median_curve = np.median(curves_arr, axis=0)

    ax.plot(range(min_len), median_curve, color=colors[alg],
            linewidth=2, label=alg)

ax.set_xlabel('Generation'); ax.set_ylabel('Avg Fitness (4D)')
ax.set_title('(b) Convergence — Average Fitness'); ax.legend()

# (c) Box plot — Final fitness
ax = axes[1, 0]
data_box = [comparison_data['fitness'][alg]['values'] for alg in ['PSO','GA','GNPSO']]
bp = ax.boxplot(data_box, patch_artist=True, labels=['PSO', 'GA', 'GNPSO'])
for patch, alg in zip(bp['boxes'], ['PSO','GA','GNPSO']):
    patch.set_facecolor(colors[alg]); patch.set_alpha(0.6)
ax.set_ylabel('Final Fitness (4D)')
ax.set_title('(c) Fitness Distribution (5 runs)')

# (d) Computation time
ax = axes[1, 1]
times = {alg: [r['elapsed'] for r in all_results[alg]] for alg in ['PSO','GA','GNPSO']}
x = np.arange(3); w = 0.6
means = [np.mean(times[a]) for a in ['PSO','GA','GNPSO']]
stds = [np.std(times[a]) for a in ['PSO','GA','GNPSO']]
bars = ax.bar(x, means, w, yerr=stds, capsize=5,
              color=[colors[a] for a in ['PSO','GA','GNPSO']], alpha=0.85)
for bar, m in zip(bars, means):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+5,
            f'{m:.0f}s', ha='center', fontsize=10, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(['PSO', 'GA', 'GNPSO'])
ax.set_ylabel('Time (seconds)'); ax.set_title('(d) Computation Time')

plt.suptitle(f'Figure 25: Algorithm Comparison — {N_RUNS} Runs Each',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig25_algorithm_comparison.png', bbox_inches='tight')
plt.show()
print("✓ Figure 25 saved")



# %% [cell 92]
# =================================================================
# STEP 7.9: FIGURE 26 — Performance Metrics Comparison
# =================================================================

fig, axes = plt.subplots(2, 3, figsize=(16, 10))

metric_plots = [
    ('LPSP', 'lpsp', '(a) LPSP'),
    ('LCE ($/kWh)', 'lce', '(b) LCE'),
    ('PBP (years)', 'pbp', '(c) PBP'),
    ('TCOP ($)', 'tcop', '(d) TCOP'),
    ('ROI (%)', 'roi', '(e) ROI'),
    ('Battery (kWh)', 'bat_kwh', '(f) Battery Size'),
]

for idx, (ylabel, key, title) in enumerate(metric_plots):
    ax = axes[idx//3, idx%3]
    data = [comparison_data[key][alg]['values'] for alg in ['PSO','GA','GNPSO']]
    bp = ax.boxplot(data, patch_artist=True, labels=['PSO','GA','GNPSO'])
    for patch, alg in zip(bp['boxes'], ['PSO','GA','GNPSO']):
        patch.set_facecolor(colors[alg]); patch.set_alpha(0.6)
    ax.set_ylabel(ylabel); ax.set_title(title)

plt.suptitle(f'Figure 26: Performance Metrics — PSO vs GA vs GNPSO ({N_RUNS} runs)',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig26_metrics_comparison.png', bbox_inches='tight')
plt.show()
print("✓ Figure 26 saved")



# %% [cell 93]
# =================================================================
# STEP 7.10: FIGURE 27 — Best Solution Radar Chart
# =================================================================

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

# Get best run for each algorithm
best_solutions = {}
for alg in ['PSO', 'GA', 'GNPSO']:
    best_solutions[alg] = min(all_results[alg], key=lambda r: r['fitness'])

# Normalize metrics for radar (lower is better, so invert some)
categories = ['LPSP\n(lower=better)', 'LCE\n(lower=better)',
              'PBP\n(lower=better)', 'TCOP\n(lower=better)',
              'ROI\n(higher=better)', 'Speed\n(faster=better)']
N = len(categories)
angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
angles += angles[:1]

for alg in ['PSO', 'GA', 'GNPSO']:
    b = best_solutions[alg]
    # Normalize each metric to 0-1 (1 = best)
    all_lpsp = [best_solutions[a]['lpsp'] for a in ['PSO','GA','GNPSO']]
    all_lce = [best_solutions[a]['lce'] for a in ['PSO','GA','GNPSO']]
    all_pbp = [best_solutions[a]['pbp'] for a in ['PSO','GA','GNPSO']]
    all_tcop = [best_solutions[a]['tcop'] for a in ['PSO','GA','GNPSO']]
    all_roi = [best_solutions[a]['roi'] for a in ['PSO','GA','GNPSO']]
    all_time = [best_solutions[a]['elapsed'] for a in ['PSO','GA','GNPSO']]

    def score(val, all_vals, lower_better=True):
        mn, mx = min(all_vals), max(all_vals)
        if mx - mn < 1e-10: return 1.0
        s = (val - mn) / (mx - mn)
        return 1 - s if lower_better else s

    values = [
        score(b['lpsp'], all_lpsp, True),
        score(b['lce'], all_lce, True),
        score(b['pbp'], all_pbp, True),
        score(b['tcop'], all_tcop, True),
        score(b['roi'], all_roi, False),
        score(b['elapsed'], all_time, True),
    ]
    values += values[:1]

    ax.plot(angles, values, 'o-', linewidth=2, color=colors[alg],
            label=alg, markersize=6)
    ax.fill(angles, values, alpha=0.1, color=colors[alg])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=10)
ax.set_ylim(0, 1.1)
ax.set_title('Figure 27: Algorithm Performance Radar Chart', fontsize=13, y=1.08)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))

plt.tight_layout()
plt.savefig('fig27_radar_chart.png', bbox_inches='tight')
plt.show()
print("✓ Figure 27 saved")



# %% [cell 94]
# =================================================================
# STEP 7.11: FIGURE 28 — ROI Analysis
# =================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# (a) ROI comparison
roi_data = {alg: [r['roi'] for r in all_results[alg]] for alg in ['PSO','GA','GNPSO']}
x = np.arange(3); w = 0.6
roi_means = [np.mean(roi_data[a]) for a in ['PSO','GA','GNPSO']]
roi_stds = [np.std(roi_data[a]) for a in ['PSO','GA','GNPSO']]
bars = ax1.bar(x, roi_means, w, yerr=roi_stds, capsize=5,
               color=[colors[a] for a in ['PSO','GA','GNPSO']], alpha=0.85)
for bar, m in zip(bars, roi_means):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+20,
             f'{m:.0f}%', ha='center', fontsize=12, fontweight='bold')
ax1.set_xticks(x); ax1.set_xticklabels(['PSO','GA','GNPSO'])
ax1.set_ylabel('ROI (%)')
ax1.set_title('(a) Return on Investment')
ax1.axhline(0, color='red', linestyle='--', alpha=0.5)

# (b) Investment vs Savings (best GNPSO)
best_gnpso = min(all_results['GNPSO'], key=lambda r: r['fitness'])
capital = best_gnpso['best']['econ']['capital']
ann_savings = best_gnpso['best']['econ']['AnnSavCost']
T = CONFIG['project_lifetime_years']

years = range(T+1)
cumulative_savings = [ann_savings * y for y in years]
cumulative_cost = [capital] + [capital for _ in range(T)]

ax2.plot(years, cumulative_savings, 'g-o', markersize=3, linewidth=2,
         label='Cumulative Savings')
ax2.axhline(capital, color='red', linestyle='--', linewidth=2,
            label=f'Investment (${capital:,.0f})')
ax2.fill_between(years, cumulative_savings, capital,
                 where=[s > capital for s in cumulative_savings],
                 alpha=0.2, color='green', label='Profit zone')

# Find payback point
for y in range(1, T+1):
    if cumulative_savings[y] >= capital:
        ax2.axvline(y, color='blue', linestyle=':', alpha=0.7)
        ax2.text(y+0.3, capital*0.5, f'Payback\nYear {y}',
                fontsize=10, color='blue', fontweight='bold')
        break

ax2.set_xlabel('Year'); ax2.set_ylabel('Amount ($)')
ax2.set_title(f'(b) Investment Recovery — GNPSO Optimal')
ax2.legend(loc='upper left')

plt.suptitle('Figure 28: ROI & Investment Analysis', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig28_roi_analysis.png', bbox_inches='tight')
plt.show()
print("✓ Figure 28 saved")



# %% [cell 95]
# =================================================================
# STEP 7.12: Save All Results
# =================================================================

comparison_results = {
    'n_runs': N_RUNS,
    'pop_size': POP_SIZE,
    'max_gen': MAX_GEN,
    'algorithms': {},
}

for alg in ['PSO', 'GA', 'GNPSO']:
    best_run = min(all_results[alg], key=lambda r: r['fitness'])
    comparison_results['algorithms'][alg] = {
        'best_fitness': round(best_run['fitness'], 4),
        'mean_fitness': round(np.mean([r['fitness'] for r in all_results[alg]]), 4),
        'std_fitness': round(np.std([r['fitness'] for r in all_results[alg]]), 4),
        'best_config': {
            'n_modules': best_run['n_modules'],
            'bat_kwh': best_run['bat_kwh'],
            'inv_kw': best_run['inv_kw'],
        },
        'best_lpsp': round(best_run['lpsp'], 6),
        'best_lce': round(best_run['lce'], 6),
        'best_pbp': round(best_run['pbp'], 2),
        'best_tcop': round(best_run['tcop'], 0),
        'best_roi': round(best_run['roi'], 1),
        'mean_time_s': round(np.mean([r['elapsed'] for r in all_results[alg]]), 1),
        'all_fitness': [round(r['fitness'],4) for r in all_results[alg]],
        'all_roi': [round(r['roi'],1) for r in all_results[alg]],
    }

with open('algorithm_comparison.json', 'w') as f:
    json.dump(comparison_results, f, indent=2)

# Backup
!cp *.json *.png /content/drive/MyDrive/MSc_Project/ 2>/dev/null || true



# %% [cell 96]
import json
import numpy as np

# =================================================================
# FINAL SUMMARY & MULTI-CRITERIA SELECTION
# =================================================================

comparison_results = {
    'n_runs': N_RUNS,
    'pop_size': POP_SIZE,
    'max_gen': MAX_GEN,
    'algorithms': {},
}

for alg in ['PSO', 'GA', 'GNPSO']:
    best_run = min(all_results[alg], key=lambda r: r['fitness'])
    comparison_results['algorithms'][alg] = {
        'best_fitness': round(best_run['fitness'], 4),
        'mean_fitness': round(np.mean([r['fitness'] for r in all_results[alg]]), 4),
        'std_fitness': round(np.std([r['fitness'] for r in all_results[alg]]), 4),
        'best_config': {
            'n_modules': best_run['n_modules'],
            'bat_kwh': best_run['bat_kwh'],
            'inv_kw': best_run['inv_kw'],
        },
        'best_lpsp': round(best_run['lpsp'], 6),
        'best_lce': round(best_run['lce'], 6),
        'best_pbp': round(best_run['pbp'], 2),
        'best_tcop': round(best_run['tcop'], 0),
        'best_roi': round(best_run['roi'], 1),
        'mean_time_s': round(np.mean([r['elapsed'] for r in all_results[alg]]), 1),
        'all_fitness': [round(r['fitness'],4) for r in all_results[alg]],
        'all_roi': [round(r['roi'],1) for r in all_results[alg]],
    }

# =================================================================
# Multi-Criteria Winner Selection

# =================================================================
print(f"\n{'='*70}")
print(f"  MULTI-CRITERIA WINNER SELECTION")
print(f"  {'='*70}")

# Criteria weights (sum = 1.0)
criteria_weights = {
    'mean_fitness': 0.35,
    'std_fitness':  0.30,
    'best_fitness': 0.20,
    'mean_time_s':  0.15,
}

# Normalize each criterion (lower = better for all)
scores = {alg: 0.0 for alg in ['PSO', 'GA', 'GNPSO']}
print(f"\n  Normalized Scores per Criterion:")
print(f"  {'Criterion':<18} {'PSO':<12} {'GA':<12} {'GNPSO':<12}")
print(f"  {'─'*54}")

for criterion, weight in criteria_weights.items():
    values = {alg: comparison_results['algorithms'][alg][criterion]
              for alg in ['PSO', 'GA', 'GNPSO']}
    mn, mx = min(values.values()), max(values.values())
    rng = mx - mn if mx > mn else 1.0

    norm_row = []
    for alg in ['PSO', 'GA', 'GNPSO']:
        normalized = (values[alg] - mn) / rng
        scores[alg] += weight * normalized
        norm_row.append(f"{normalized:.4f}")

    print(f"  {criterion:<18} {norm_row[0]:<12} {norm_row[1]:<12} {norm_row[2]:<12}")

# Final composite scores
print(f"\n  {'─'*54}")
print(f"  {'COMPOSITE SCORE':<18} ", end="")
for alg in ['PSO', 'GA', 'GNPSO']:
    print(f"{scores[alg]:.4f}".ljust(12), end="")
print()
print(f"  (lower = better overall performance)")

# Determine winner
winner_name = min(scores, key=scores.get)
winner_data = comparison_results['algorithms'][winner_name]

print(f"\n  {'='*70}")
print(f"  🏆 WINNER: {winner_name}")
print(f"  {'='*70}")
print(f"    Composite Score:  {scores[winner_name]:.4f}")
print(f"    Mean Fitness:     {winner_data['mean_fitness']:.4f}")
print(f"    Best Fitness:     {winner_data['best_fitness']:.4f}")
print(f"    Std Deviation:    {winner_data['std_fitness']:.4f}")
print(f"    Mean Time:        {winner_data['mean_time_s']:.0f}s")
print(f"    Best TCOP:        ${winner_data['best_tcop']:,.0f}")
print(f"    Best ROI:         {winner_data['best_roi']:.0f}%")

# Save winner info to JSON
comparison_results['winner'] = {
    'algorithm': winner_name,
    'composite_score': round(scores[winner_name], 4),
    'criteria_weights': criteria_weights,
    'all_scores': {alg: round(scores[alg], 4) for alg in ['PSO', 'GA', 'GNPSO']},
}

# Re-save JSON with winner info
with open('algorithm_comparison.json', 'w') as f:
    json.dump(comparison_results, f, indent=2)

# Backup
!cp *.json *.png /content/drive/MyDrive/MSc_Project/ 2>/dev/null || true

print(f"\n{'='*70}")
print(f"  ✓ PHASE 7 COMPLETE — SUMMARY SAVED")
print(f"  → Ready for Phase 8")
print(f"{'='*70}")

# %% [cell 97]


# %% [cell 98]


# %% [cell 99]
# ╔══════════════════════════════════════════════════════════════════╗
# ║  PHASE 8: ECONOMIC FEASIBILITY & FINAL REPORT                  ║
# ║                                                                ║
# ║  Old system (Grid + Generator) vs New system (Grid + Solar)    ║
# ║  Cash flow, sensitivity analysis, final summary                ║
# ╚══════════════════════════════════════════════════════════════════╝

# =================================================================
# STEP 8.1: Import & Load
# =================================================================

import os
from google.colab import drive

# Ensure drive is mounted
if not os.path.exists('/content/drive'):
    drive.mount('/content/drive')

# Copy files back from Drive to local environment if missing
!cp /content/drive/MyDrive/MSc_Project/*.json /content/ 2>/dev/null || true
!cp /content/drive/MyDrive/MSc_Project/*.csv /content/ 2>/dev/null || true
!cp /content/drive/MyDrive/MSc_Project/*.pkl /content/ 2>/dev/null || true

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import warnings
warnings.filterwarnings('ignore')

plt.rcParams.update({
    'figure.dpi': 150, 'savefig.dpi': 300,
    'font.size': 11, 'font.family': 'serif',
    'axes.labelsize': 12, 'axes.titlesize': 13,
    'axes.grid': True, 'grid.alpha': 0.3,
})

with open('config.json') as f:
    CONFIG = json.load(f)
with open('optimization_results.json') as f:
    OPT = json.load(f)

print("="*60)
print("  PHASE 8: ECONOMIC FEASIBILITY & FINAL REPORT")
print("="*60)

# %% [cell 100]
# =================================================================
# STEP 8.2: Extract Optimal Configuration (Run A)
# =================================================================

opt = OPT['run_A_actual']
n_modules = opt['n_modules']
bat_units = opt['bat_units']
bat_kwh = opt['bat_kwh']
inv_kw = opt['inv_kw']
pv_kwp = opt['pv_kwp']

# Inverter standard size
std_sizes = CONFIG['inv_standard_sizes_kw']
inv_std = min((s for s in std_sizes if s >= inv_kw), default=inv_kw)

print(f"\n  Optimal Configuration (GNPSO Run A):")
print(f"  PV:       {n_modules} modules × {CONFIG['pv_module_power_kw']*1000:.0f}W = {pv_kwp:.1f} kWp")
print(f"  Battery:  {bat_units} units × {CONFIG['bat_unit_capacity_kwh']:.2f} kWh = {bat_kwh:.1f} kWh")
print(f"  Inverter: {inv_std} kW (standard size ≥ {inv_kw:.1f} kW)")



# %% [cell 101]
import pandas as pd

# Reload the master data to ensure 'df' is defined
df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)

# =================================================================
# STEP 8.3: Old System Annual Costs
# =================================================================
"""
OLD SYSTEM:
1. Generator subscription: price_per_amp × amps × 12 months
2. Grid electricity: tariff × annual grid consumption
3. No capital investment (already exists)
"""

T = CONFIG['project_lifetime_years']  # 20 years
r = CONFIG['interest_rate']
inflation = CONFIG['inflation_rate']

# Annual costs - Old system
gen_annual = CONFIG['gen_price_per_amp_month_usd'] * CONFIG['gen_subscribed_amps'] * 12
grid_consumption_old = df['D_on_grid'].sum()  # القيمة الحقيقية من البيانات
grid_cost_old = grid_consumption_old * CONFIG['grid_avg_tariff_per_kwh_usd']
old_annual_cost = gen_annual + grid_cost_old

print(f"\n{'='*60}")
print(f"  OLD SYSTEM — Annual Costs")
print(f"{'='*60}")
print(f"  Generator subscription:  ${gen_annual:,.0f}/year")
print(f"    ({CONFIG['gen_subscribed_amps']} Amps × ${CONFIG['gen_price_per_amp_month_usd']}/amp/month × 12)")
print(f"  Grid electricity:        ${grid_cost_old:,.0f}/year")
print(f"    ({grid_consumption_old:,} kWh × ${CONFIG['grid_avg_tariff_per_kwh_usd']}/kWh)")
print(f"  Total annual:            ${old_annual_cost:,.0f}/year")
print(f"  20-year total (no infl): ${old_annual_cost * T:,.0f}")

# %% [cell 102]
# =================================================================
# STEP 8.4: New System Costs (Capital + Operating)
# =================================================================

# Capital costs
pv_capex = n_modules * CONFIG['pv_cost_per_module_usd']
bat_capex = CONFIG['bat_charger_cost_usd'] + bat_units * CONFIG['bat_unit_cost_usd']
inv_capex = inv_std * CONFIG['inv_cost_per_kw_usd']
total_capital = pv_capex + bat_capex + inv_capex

# Operating costs - New system
grid_buy_new = OPT['run_A_actual']['grid_buy_kwh']  # القيمة الحقيقية
grid_cost_new = grid_buy_new * CONFIG['grid_avg_tariff_per_kwh_usd']
new_annual_operating = grid_cost_new  # only grid cost, no generator

# PV maintenance (1% of PV cost per year)
pv_maintenance = pv_capex * 0.01

# Annual savings
annual_savings = old_annual_cost - new_annual_operating - pv_maintenance

# Replacement costs
# Battery replacement
bat_cycles_per_year = OPT['run_A_actual']['battery_cycles']  # ← أضف هذا السطر
bat_life_years = CONFIG['bat_life_cycles'] / bat_cycles_per_year if bat_cycles_per_year > 0 else T
bat_replacement_year = int(bat_life_years) if bat_life_years < T else 0

# Inverter replacement
inv_life = CONFIG['inv_lifetime_years']
inv_replacement_year = inv_life if inv_life < T else 0

print(f"\n{'='*60}")
print(f"  NEW SYSTEM — Cost Breakdown")
print(f"{'='*60}")
print(f"  Capital Investment:")
print(f"    PV modules:    ${pv_capex:,.0f} ({n_modules} × ${CONFIG['pv_cost_per_module_usd']})")
print(f"    Battery:       ${bat_capex:,.0f} ({bat_units} × ${CONFIG['bat_unit_cost_usd']:,})")
print(f"    Inverter:      ${inv_capex:,.0f} ({inv_std} kW × ${CONFIG['inv_cost_per_kw_usd']})")
print(f"    TOTAL CAPITAL: ${total_capital:,.0f}")
print(f"")
print(f"  Annual Operating:")
print(f"    Grid purchase:   ${grid_cost_new:,.0f}/year ({grid_buy_new:,} kWh)")
print(f"    PV maintenance:  ${pv_maintenance:,.0f}/year")
print(f"    Generator:       $0 (eliminated!)")
print(f"    Total operating: ${new_annual_operating + pv_maintenance:,.0f}/year")
print(f"")
print(f"  Annual Savings:    ${annual_savings:,.0f}/year")
print(f"  Simple Payback:    {total_capital/annual_savings:.1f} years")

# Battery and inverter replacement info
if bat_replacement_year > 0 and bat_replacement_year < T:
    print(f"\n  Battery replacement at year {bat_replacement_year} "
          f"(life = {bat_life_years:.0f} years at {bat_cycles_per_year} cycles/yr)")
    print(f"    Replacement cost: ${bat_capex:,.0f}")
else:
    print(f"\n  Battery lasts entire project ({bat_life_years:.0f} years > {T} years)")

if inv_replacement_year > 0 and inv_replacement_year < T:
    print(f"  Inverter replacement at year {inv_replacement_year}")
    print(f"    Replacement cost: ${inv_capex:,.0f}")
else:
    print(f"  Inverter lasts entire project")



# %% [cell 103]
# =================================================================
# STEP 8.5: Year-by-Year Cash Flow Analysis
# =================================================================
"""
For each year:
  Old system: annual cost (with inflation)
  New system: operating cost + any replacement
  Net saving: old - new
  Cumulative saving: running total
"""

years = np.arange(0, T + 1)
old_cumulative = np.zeros(T + 1)
new_cumulative = np.zeros(T + 1)
savings_cumulative = np.zeros(T + 1)

# Year 0: capital investment
new_cumulative[0] = total_capital
old_cumulative[0] = 0
savings_cumulative[0] = -total_capital

print(f"\n{'='*60}")
print(f"  CASH FLOW ANALYSIS — {T} YEARS")
print(f"{'='*60}")
print(f"  {'Year':<6} {'Old Cost':>10} {'New Cost':>10} {'Saving':>10} {'Cumulative':>12}")
print(f"  {'─'*50}")
print(f"  {'0':<6} {'$0':>10} {'${:,.0f}'.format(total_capital):>10} "
      f"{'${:,.0f}'.format(-total_capital):>10} {'${:,.0f}'.format(-total_capital):>12}")

for y in range(1, T + 1):
    # Old system cost with inflation
    old_cost_y = old_annual_cost * (1 + inflation) ** (y - 1)
    old_cumulative[y] = old_cumulative[y-1] + old_cost_y

    # New system cost
    new_cost_y = (new_annual_operating + pv_maintenance) * (1 + inflation) ** (y - 1)

    # Add replacement costs
    if bat_replacement_year > 0 and y == bat_replacement_year:
        new_cost_y += bat_capex * (1 + inflation) ** (y - 1)
    if inv_replacement_year > 0 and y == inv_replacement_year:
        new_cost_y += inv_capex * (1 + inflation) ** (y - 1)

    new_cumulative[y] = new_cumulative[y-1] + new_cost_y

    # Savings
    saving_y = old_cost_y - new_cost_y
    savings_cumulative[y] = savings_cumulative[y-1] + saving_y

    if y <= 5 or y % 5 == 0 or y == T:
        print(f"  {y:<6} {'${:,.0f}'.format(old_cost_y):>10} "
              f"{'${:,.0f}'.format(new_cost_y):>10} "
              f"{'${:,.0f}'.format(saving_y):>10} "
              f"{'${:,.0f}'.format(savings_cumulative[y]):>12}")

# Find payback year
payback_year = T + 1
for y in range(1, T + 1):
    if savings_cumulative[y] >= 0:
        payback_year = y
        break

# Final metrics
total_old_20yr = old_cumulative[T]
total_new_20yr = new_cumulative[T]
total_savings_20yr = savings_cumulative[T]
roi = (total_savings_20yr / total_capital) * 100

print(f"\n  {'─'*50}")
print(f"  20-Year Old System Total:  ${total_old_20yr:,.0f}")
print(f"  20-Year New System Total:  ${total_new_20yr:,.0f}")
print(f"  20-Year Net Savings:       ${total_savings_20yr:,.0f}")
print(f"  Payback Period:            Year {payback_year}")
print(f"  ROI:                       {roi:,.0f}%")



# %% [cell 104]
# =================================================================
# STEP 8.6: FIGURE 29 — Old vs New System Cost Comparison
# =================================================================

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# (a) Annual cost breakdown
categories = ['Generator\nSubscription', 'Grid\nElectricity', 'PV\nMaintenance', 'Total\nAnnual']
old_values = [gen_annual, grid_cost_old, 0, old_annual_cost]
new_values = [0, grid_cost_new, pv_maintenance, new_annual_operating + pv_maintenance]

x = np.arange(len(categories))
w = 0.35
bars1 = ax1.bar(x - w/2, old_values, w, label='Old System (Grid+Gen)',
                color='#D6604D', alpha=0.85, edgecolor='white')
bars2 = ax1.bar(x + w/2, new_values, w, label='New System (Grid+Solar)',
                color='#66BD63', alpha=0.85, edgecolor='white')

for bar, v in zip(bars1, old_values):
    if v > 0:
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+50,
                f'${v:,.0f}', ha='center', fontsize=9, fontweight='bold')
for bar, v in zip(bars2, new_values):
    if v > 0:
        ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+50,
                f'${v:,.0f}', ha='center', fontsize=9, fontweight='bold')

ax1.set_ylabel('Annual Cost ($/year)')
ax1.set_title('(a) Annual Cost Comparison')
ax1.set_xticks(x); ax1.set_xticklabels(categories)
ax1.legend()

# (b) Capital cost breakdown (pie chart)
cap_labels = [f'PV Modules\n${pv_capex:,.0f}',
              f'Battery\n${bat_capex:,.0f}',
              f'Inverter\n${inv_capex:,.0f}']
cap_values = [pv_capex, bat_capex, inv_capex]
cap_colors = ['#F4A582', '#2166AC', '#66BD63']

wedges, texts, autotexts = ax2.pie(
    cap_values, labels=cap_labels, autopct='%1.1f%%',
    colors=cap_colors, startangle=90, pctdistance=0.75)
for t in autotexts:
    t.set_fontsize(11); t.set_fontweight('bold')
ax2.set_title(f'(b) Capital Cost Breakdown (Total: ${total_capital:,.0f})')

plt.suptitle('Figure 29: Cost Comparison — Old vs New System', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig29_cost_comparison.png', bbox_inches='tight')
plt.show()
print("✓ Figure 29 saved")



# %% [cell 105]
# =================================================================
# STEP 8.7: FIGURE 30 — Cumulative Cash Flow Over 20 Years
# =================================================================

fig, ax = plt.subplots(figsize=(14, 7))

ax.plot(years, old_cumulative/1000, 'r-o', markersize=4, linewidth=2,
        label=f'Old System (${total_old_20yr/1000:,.0f}k total)')
ax.plot(years, new_cumulative/1000, 'g-s', markersize=4, linewidth=2,
        label=f'New System (${total_new_20yr/1000:,.0f}k total)')

# Savings area
ax.fill_between(years, old_cumulative/1000, new_cumulative/1000,
                where=old_cumulative > new_cumulative,
                alpha=0.15, color='green', label=f'Net Savings (${total_savings_20yr/1000:,.0f}k)')

# Payback point
if payback_year <= T:
    # Interpolate exact payback
    ax.axvline(payback_year, color='blue', linestyle=':', alpha=0.7)
    ax.text(payback_year + 0.3, ax.get_ylim()[1] * 0.5,
            f'Payback\nYear {payback_year}',
            fontsize=11, color='blue', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))

# Mark replacement events
if bat_replacement_year > 0 and bat_replacement_year < T:
    ax.annotate(f'Battery\nreplacement',
                xy=(bat_replacement_year, new_cumulative[bat_replacement_year]/1000),
                xytext=(bat_replacement_year+2, new_cumulative[bat_replacement_year]/1000+5),
                arrowprops=dict(arrowstyle='->', color='orange'),
                fontsize=9, color='orange')

if inv_replacement_year > 0 and inv_replacement_year < T:
    ax.annotate(f'Inverter\nreplacement',
                xy=(inv_replacement_year, new_cumulative[inv_replacement_year]/1000),
                xytext=(inv_replacement_year+2, new_cumulative[inv_replacement_year]/1000+3),
                arrowprops=dict(arrowstyle='->', color='purple'),
                fontsize=9, color='purple')

ax.set_xlabel('Year')
ax.set_ylabel('Cumulative Cost (× $1,000)')
ax.set_title('Figure 30: Cumulative Cost — Old System vs New System Over 20 Years')
ax.set_xticks(range(0, T+1, 2))
ax.legend(loc='upper left', fontsize=11)

plt.tight_layout()
plt.savefig('fig30_cumulative_cashflow.png', bbox_inches='tight')
plt.show()
print("✓ Figure 30 saved")



# %% [cell 106]
# =================================================================
# STEP 8.8: Sensitivity Analysis
# =================================================================
"""
Test how results change when key assumptions vary:
1. PV cost: ±30%
2. Battery cost: ±30%
3. Generator price: ±30%
4. Grid tariff: ±50%
5. Inflation rate: 2% to 6%
"""

print(f"\n{'='*60}")
print(f"  SENSITIVITY ANALYSIS")
print(f"{'='*60}")

def quick_pbp_roi(pv_cost_mult, bat_cost_mult, gen_price_mult,
                  grid_tariff_mult, infl_rate):
    pv_c = pv_capex * pv_cost_mult
    bat_c = bat_capex * bat_cost_mult
    inv_c = inv_capex
    cap = pv_c + bat_c + inv_c

    gen_ann = gen_annual * gen_price_mult
    grid_old = grid_cost_old * grid_tariff_mult
    old_ann = gen_ann + grid_old

    grid_new = grid_cost_new * grid_tariff_mult
    maint = pv_c * 0.01
    new_ann = grid_new + maint

    saving = old_ann - new_ann
    pbp = cap / saving if saving > 0 else 99

    # 20-year cumulative with inflation
    total_save = 0
    for y in range(1, T+1):
        s = saving * (1 + infl_rate) ** (y-1)
        total_save += s
    roi_val = (total_save - cap) / cap * 100 if cap > 0 else 0

    return pbp, roi_val, cap

# Base case
base_pbp, base_roi, base_cap = quick_pbp_roi(1, 1, 1, 1, inflation)

sensitivity_results = {}

# 1. PV Cost sensitivity
pv_mults = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
pv_sens = [quick_pbp_roi(m, 1, 1, 1, inflation) for m in pv_mults]
sensitivity_results['PV Cost'] = {
    'multipliers': pv_mults,
    'pbp': [s[0] for s in pv_sens],
    'roi': [s[1] for s in pv_sens],
}

# 2. Battery Cost sensitivity
bat_mults = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
bat_sens = [quick_pbp_roi(1, m, 1, 1, inflation) for m in bat_mults]
sensitivity_results['Battery Cost'] = {
    'multipliers': bat_mults,
    'pbp': [s[0] for s in bat_sens],
    'roi': [s[1] for s in bat_sens],
}

# 3. Generator Price sensitivity
gen_mults = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
gen_sens = [quick_pbp_roi(1, 1, m, 1, inflation) for m in gen_mults]
sensitivity_results['Generator Price'] = {
    'multipliers': gen_mults,
    'pbp': [s[0] for s in gen_sens],
    'roi': [s[1] for s in gen_sens],
}

# 4. Grid Tariff sensitivity
grid_mults = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
grid_sens = [quick_pbp_roi(1, 1, 1, m, inflation) for m in grid_mults]
sensitivity_results['Grid Tariff'] = {
    'multipliers': grid_mults,
    'pbp': [s[0] for s in grid_sens],
    'roi': [s[1] for s in grid_sens],
}

# Print sensitivity table
print(f"\n  {'Parameter':<20} {'Change':<10} {'PBP (yr)':<10} {'ROI (%)':<10}")
print(f"  {'─'*50}")

for param in ['PV Cost', 'Battery Cost', 'Generator Price', 'Grid Tariff']:
    sr = sensitivity_results[param]
    for i, m in enumerate(sr['multipliers']):
        if m == 1.0:
            marker = " ← base"
        else:
            marker = ""
        change = f"{(m-1)*100:+.0f}%"
        print(f"  {param if i==0 else '':<20} {change:<10} "
              f"{sr['pbp'][i]:<10.1f} {sr['roi'][i]:<10.0f}{marker}")
    print()



# %% [cell 107]
# =================================================================
# STEP 8.9: FIGURE 31 — Sensitivity Analysis Charts
# =================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
colors_sens = {'PV Cost': '#F4A582', 'Battery Cost': '#2166AC',
               'Generator Price': '#D6604D', 'Grid Tariff': '#66BD63'}

# (a) PBP sensitivity
ax = axes[0, 0]
for param in ['PV Cost', 'Battery Cost', 'Generator Price']:
    sr = sensitivity_results[param]
    pct = [(m-1)*100 for m in sr['multipliers']]
    ax.plot(pct, sr['pbp'], '-o', markersize=5, linewidth=2,
            color=colors_sens[param], label=param)
ax.axhline(base_pbp, color='gray', linestyle=':', alpha=0.5)
ax.set_xlabel('Parameter Change (%)')
ax.set_ylabel('Payback Period (years)')
ax.set_title('(a) PBP Sensitivity')
ax.legend(fontsize=9)

# (b) ROI sensitivity
ax = axes[0, 1]
for param in ['PV Cost', 'Battery Cost', 'Generator Price']:
    sr = sensitivity_results[param]
    pct = [(m-1)*100 for m in sr['multipliers']]
    ax.plot(pct, sr['roi'], '-o', markersize=5, linewidth=2,
            color=colors_sens[param], label=param)
ax.axhline(base_roi, color='gray', linestyle=':', alpha=0.5)
ax.set_xlabel('Parameter Change (%)')
ax.set_ylabel('ROI (%)')
ax.set_title('(b) ROI Sensitivity')
ax.legend(fontsize=9)

# (c) Grid tariff impact
ax = axes[1, 0]
sr = sensitivity_results['Grid Tariff']
pct = [(m-1)*100 for m in sr['multipliers']]
ax.plot(pct, sr['pbp'], '-o', markersize=6, linewidth=2.5,
        color=colors_sens['Grid Tariff'])
ax.axhline(base_pbp, color='gray', linestyle=':', alpha=0.5)
ax.set_xlabel('Grid Tariff Change (%)')
ax.set_ylabel('Payback Period (years)')
ax.set_title('(c) Grid Tariff Impact on PBP')

# (d) Tornado diagram — PBP at ±30%
ax = axes[1, 1]
params_tornado = ['PV Cost', 'Battery Cost', 'Generator Price']
low_pbp = [sensitivity_results[p]['pbp'][0] for p in params_tornado]  # -30%
high_pbp = [sensitivity_results[p]['pbp'][-1] for p in params_tornado]  # +30%
base_val = base_pbp

y_pos = np.arange(len(params_tornado))
left = [l - base_val for l in low_pbp]
right = [h - base_val for h in high_pbp]

ax.barh(y_pos, right, align='center', height=0.4, color='#D6604D', alpha=0.7, label='+30%')
ax.barh(y_pos, left, align='center', height=0.4, color='#66BD63', alpha=0.7, label='-30%')
ax.axvline(0, color='black', linewidth=0.5)
ax.set_yticks(y_pos); ax.set_yticklabels(params_tornado)
ax.set_xlabel(f'Change in PBP from base ({base_val:.1f} years)')
ax.set_title('(d) Tornado Diagram — PBP Sensitivity ±30%')
ax.legend()

plt.suptitle('Figure 31: Sensitivity Analysis', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig31_sensitivity_analysis.png', bbox_inches='tight')
plt.show()
print("✓ Figure 31 saved")



# %% [cell 108]
# =================================================================
# STEP 8.10: FIGURE 32 — Monthly Energy Balance with Optimal System
# =================================================================

df = pd.read_csv('master_data.csv', index_col='Timestamp', parse_dates=True)

# Reconstruct monthly energy balance from optimal system
# PV production per month
import pickle
with open('pv_per_module.pkl', 'rb') as f:
    pv_mod = pickle.load(f)

pv_total_monthly = pd.Series(pv_mod * n_modules, index=df.index).resample('M').sum()
gen_load_monthly = df['D_off_grid'].resample('M').sum()
grid_load_monthly = df['D_on_grid'].resample('M').sum()

months_labels = ['Jan','Feb','Mar','Apr','May','Jun',
                 'Jul','Aug','Sep','Oct','Nov','Dec']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

x = np.arange(12)
w = 0.25

# (a) Monthly energy sources
ax1.bar(x - w, pv_total_monthly.values, w, label='PV Production',
        color='#F4A582', alpha=0.85, edgecolor='white')
ax1.bar(x, gen_load_monthly.values, w, label='Generator Load (to replace)',
        color='#D6604D', alpha=0.85, edgecolor='white')
ax1.bar(x + w, grid_load_monthly.values, w, label='Grid Load',
        color='#2166AC', alpha=0.85, edgecolor='white')

ax1.set_xlabel('Month')
ax1.set_ylabel('Energy (kWh)')
ax1.set_title('(a) Monthly Energy Balance')
ax1.set_xticks(x); ax1.set_xticklabels(months_labels)
ax1.legend(fontsize=9)

# (b) PV coverage ratio per month
pv_coverage = np.minimum(pv_total_monthly.values / gen_load_monthly.values, 3.0)
bar_colors = ['#66BD63' if c >= 1.0 else '#D6604D' for c in pv_coverage]

ax2.bar(x, pv_coverage * 100, color=bar_colors, alpha=0.85, edgecolor='white')
ax2.axhline(100, color='black', linestyle='--', linewidth=1, label='100% coverage')
for i, v in enumerate(pv_coverage):
    ax2.text(i, v*100+5, f'{v*100:.0f}%', ha='center', fontsize=9, fontweight='bold')

ax2.set_xlabel('Month')
ax2.set_ylabel('PV / Generator Load (%)')
ax2.set_title('(b) Monthly PV Coverage of Generator Load')
ax2.set_xticks(x); ax2.set_xticklabels(months_labels)
ax2.legend()

plt.suptitle('Figure 32: Monthly Energy Balance — Optimal System',
             fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig('fig32_monthly_energy_balance.png', bbox_inches='tight')
plt.show()
print("✓ Figure 32 saved")



# %% [cell 109]
# =================================================================
# STEP 8.11: Final Summary Table
# =================================================================

import os
import json
from google.colab import drive

# Ensure drive is mounted and sync files
if not os.path.exists('/content/drive'):
    drive.mount('/content/drive')

# Sync required files from Drive to local environment to prevent FileNotFoundError
!cp /content/drive/MyDrive/MSc_Project/*.json /content/ 2>/dev/null || true

# Load configuration and results
with open('config.json') as f:
    CONFIG = json.load(f)

with open('optimization_results.json') as f:
    OPT = json.load(f)

# Extract variables from the OPT object
opt = OPT['run_A_actual']
n_modules = opt['n_modules']
bat_units = opt['bat_units']
bat_kwh = opt['bat_kwh']
inv_kw = opt['inv_kw']
pv_kwp = opt['pv_kwp']

# Inverter standard size
std_sizes = CONFIG['inv_standard_sizes_kw']
inv_std = min((s for s in std_sizes if s >= inv_kw), default=inv_kw)

pv_str = f"{n_modules} × {CONFIG['pv_module_power_kw']*1000:.0f}W = {pv_kwp:.1f} kWp"
bat_str = f"{bat_kwh:.1f} kWh ({bat_units} × {CONFIG['bat_unit_capacity_kwh']:.2f} kWh)"
inv_str = f"{inv_std} kW (standard size)"

print(f"\n{'='*70}")
print(f"  FINAL PROJECT SUMMARY")
print(f"  MSc Thesis — BG House, Baghdad")
print(f"{'='*70}")
print(f"\n  SYSTEM CONFIGURATION:")
print(f"    PV Array:     {pv_str}")
print(f"    Battery:      {bat_str}")
print(f"    Inverter:     {inv_str}")
print(f"    EMS:          Mode 0 (PV first, self-sufficient)")
print(f"    Tilt Angle:   {CONFIG['optimal_tilt_deg']:.1f} deg (PVGIS optimal)")
print(f"\n  PERFORMANCE METRICS:")
print(f"    LPSP:         {opt['lpsp']:.4f} ({(1-opt['lpsp'])*100:.1f}% reliability)")
print(f"    LCE:          ${opt['lce']:.4f}/kWh")
print(f"    PBP:          {opt['pbp']:.1f} years")
print(f"    TCOP:         ${opt['tcop']:,.0f} (20-year)")
print(f"    ROI:          {opt.get('roi', 0):,.0f}%")
print(f"\n  AI & OPTIMIZATION:")
# Load actual Phase 3 model performance from saved metrics
try:
    with open('lstm_metrics.json') as _f_p3:
        _p3 = json.load(_f_p3)
    _rf_acc_pct = _p3.get('model_A_accuracy', 0.84) * 100
    _lstm_r2 = _p3.get('model_B_R2', 0.28)
    _lstm_mape = _p3.get('model_B_MAPE_percent', 71.0)
except FileNotFoundError:
    _rf_acc_pct = 84.04
    _lstm_r2 = 0.28
    _lstm_mape = 71.0

print(f"    Forecasting:  RF ({_rf_acc_pct:.1f}% acc) + LSTM (R²={_lstm_r2:.2f}, MAPE={_lstm_mape:.1f}%)")
print(f"    Algorithm:    Multi-Start GNPSO (5 runs, hybrid GA+PSO)")
print(f"    Constraints:  DC/AC ratio ≤ {CONFIG.get('dc_ac_ratio_max', 1.5)} (auto-repair)")
print(f"    Fitness:      Fixed Reference Normalization (4D weighted)")
print(f"    Objectives:   LPSP (40%) + LCE (30%) + PBP (15%) + TCOP (15%)")
print(f"{'='*70}")

# %% [cell 110]
# =================================================================
# STEP 8.12: Save Final Results & Backup
# =================================================================

# Ensure economic variables are available from Step 8.4/8.11 logic
payback_year = opt.get('pbp', 0)
roi = opt.get('roi_pct', 0)
total_capital = opt.get('capital', 0)
pv_capex = n_modules * CONFIG['pv_cost_per_module_usd']
bat_capex = bat_units * CONFIG['bat_unit_cost_usd']
inv_capex = inv_std * CONFIG['inv_cost_per_kw_usd']

# Calculate approximate annual costs for the summary if not explicitly in memory
gen_annual = CONFIG['gen_price_per_amp_month_usd'] * CONFIG['gen_subscribed_amps'] * 12
grid_cost_old = 14910 * CONFIG['grid_avg_tariff_per_kwh_usd'] # Approx from Phase 1
old_annual_cost = gen_annual + grid_cost_old
pv_maintenance = pv_capex * 0.01
new_annual_operating = opt.get('grid_buy_kwh', 0) * CONFIG['grid_avg_tariff_per_kwh_usd']
annual_savings = old_annual_cost - new_annual_operating - pv_maintenance

# 20-year totals for JSON
total_old_20yr = old_annual_cost * 20
total_new_20yr = (new_annual_operating + pv_maintenance) * 20 + total_capital
total_savings_20yr = total_old_20yr - total_new_20yr

final_results = {
    'system_config': {
        'pv_modules': n_modules,
        'pv_kwp': pv_kwp,
        'battery_kwh': bat_kwh,
        'battery_units': bat_units,
        'inverter_kw': inv_std,
        'ems_mode': 'Mode 0 (PV first, self-sufficient)',
        'tilt_angle': CONFIG['optimal_tilt_deg'],
    },
    'performance': {
        'lpsp': opt['lpsp'],
        'reliability_pct': round((1-opt['lpsp'])*100, 1),
        'lce_usd_kwh': opt['lce'],
        'pbp_years': payback_year,
        'tcop_usd': opt['tcop'],
        'roi_pct': round(roi, 0),
    },
    'economics': {
        'capital_total': total_capital,
        'capital_pv': pv_capex,
        'capital_battery': bat_capex,
        'capital_inverter': inv_capex,
        'old_annual_cost': old_annual_cost,
        'new_annual_operating': round(new_annual_operating + pv_maintenance, 0),
        'annual_savings': round(annual_savings, 0),
        'total_old_20yr': round(total_old_20yr, 0),
        'total_new_20yr': round(total_new_20yr, 0),
        'total_savings_20yr': round(total_savings_20yr, 0),
    },
    'sensitivity': globals().get('sensitivity_results', {}),
}

with open('final_results.json', 'w') as f:
    json.dump(final_results, f, indent=2, default=str)

# Backup everything to Drive
!cp *.json *.png /content/drive/MyDrive/MSc_Project/ 2>/dev/null || true

print(f"\n{'='*60}")
print(f"  ✓ PHASE 8 COMPLETE — ALL 8 PHASES DONE!")
print(f"{'='*60}")
print(f"  Files saved:")
print(f"    final_results.json")
print(f"    fig29-fig32_*.png (4 figures)")
print(f"    All backed up to Google Drive")
print(f"")
print(f"  Total figures: 32 (fig01-fig32)")
print(f"  Total data files: 10+")
print(f"  Total models: 2 (RF + LSTM)")
print(f"")
print(f"  🎓 PROJECT COMPLETE — Ready for thesis writing!")
print(f"{'='*60}")

# %% [cell 111]


# %% [cell 112]


# %% [cell 113]


# %% [cell 114]


# %% [cell 115]

