# Crowdstrike Prevention Health Sensor

> A reporting tool that audits the **sensor & prevention health** of every CrowdStrike-protected host using the **Zero Trust Assessment** signals, producing a per-OS snapshot of which protection features are enabled, degraded, or in **Reduced Functionality Mode (RFM)**.

<p align="center">
  <img src="Files/prevention-health-report.png" alt="Example prevention health report: per-host sensor score alongside an OK / ATTENTION verdict for each Zero Trust Assessment signal, one CSV per operating system.">
</p>

<table width="100%">
<thead>
<tr><th align="left">Before<div><img width="300" height="1" alt=""></div></th><th align="left">Now<div><img width="300" height="1" alt=""></div></th><th align="left">What it buys<div><img width="400" height="1" alt=""></div></th></tr>
</thead>
<tbody>
<tr><td>policies drift and sensors silently fall into Reduced Functionality Mode — endpoints that look protected but aren't</td><td>every host's Zero Trust Assessment signals normalized into a simple OK / ATTENTION verdict, one report per OS</td><td>degraded sensors found and fixed before they matter</td></tr>
</tbody>
</table>

---

## Overview

A CrowdStrike sensor is only as effective as the protection features actually enabled on it. Policies drift, hosts fall into **Reduced Functionality Mode**, and individual prevention controls silently fail, leaving endpoints that *look* protected but aren't.

This tool queries the Falcon platform for every managed host and cross-references it with the host's **Zero Trust Assessment**, turning each sensor signal into a simple, auditable verdict (**OK** or **ATTENTION**) and exporting one report per operating system. The result is an at-a-glance view of prevention posture across the fleet, so degraded sensors can be found and fixed before they matter.

## How It Works

The toolkit runs a single script that stitches together two Falcon data sources:

- **Stage 1. Inventory.** The **Hosts API** lists every managed device and pulls its core metadata (hostname, type, OS, hidden state, RFM flag, Linux sensor mode).
- **Stage 2. Assessment.** The **Zero Trust Assessment API** is queried in chunks of up to **1000 AIDs** per call, returning each host's `sensor_config` score and the per-signal results. Every signal is normalized to `OK` / `ATTENTION`, with special handling for RFM:
  - The **RFM signal** itself is the root cause: `OK` when in full functionality, `ATTENTION` otherwise.
  - A **Linux host in RFM** marks every other item as `Check RFM`, since RFM is the underlying reason any of them would fail.
- **Stage 3. Export.** Hosts are grouped by OS and written to one CSV per platform, dropping signal columns that don't apply to that OS and filling missing values with `-`.

> 🧩 **Signals are OS-specific.** Windows, macOS, and Linux each expose a different set of sensor signals, so each report carries its own columns. That's why the output is split per OS rather than one combined file.

> 🐧 **RFM is more severe on Linux.** It leaves many capabilities non-functional, and remediation usually means fixing the **kernel**, fixing the **OS**, or switching the sensor from **Kernel Mode** to **User Mode**:
> - **User Mode.** Hosts running in User Mode on Linux sensor **7.15 and later** include detection and prevention capabilities equivalent to Kernel Mode, so a User Mode sensor on a supported version is *not* a coverage gap.
> - **Kernel Mode.** When the sensor is in Kernel Mode, RFM can often be fixed quickly by reattaching the backend and restarting the service:
>
> ```bash
> sudo /opt/CrowdStrike/falconctl -s --backend=auto
> sudo systemctl restart falcon-sensor
> ```

---

<details>
<summary><strong>Requirements</strong> (click to expand)</summary>

- **CrowdStrike Falcon** with **Zero Trust Assessment** enabled
- A Falcon **API client** with **Hosts** and **Zero Trust Assessment** read scopes

</details>

<details>
<summary><strong>Setup</strong> (click to expand)</summary>

### 1. Environment and dependencies

```bash
# Virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows (PowerShell)
source .venv/bin/activate        # Linux / macOS

# Install dependencies
pip install -r Scripts/requirements.txt
```

<table width="100%">
<thead>
<tr><th align="left">Dependency<div><img width="300" height="1" alt=""></div></th><th align="left">Purpose<div><img width="900" height="1" alt=""></div></th></tr>
</thead>
<tbody>
<tr><td><code>crowdstrike-falconpy</code></td><td>Official CrowdStrike Falcon SDK (Hosts + Zero Trust Assessment APIs)</td></tr>
<tr><td><code>pandas</code></td><td>Groups hosts by OS and writes the per-OS CSV reports</td></tr>
<tr><td><code>python-dotenv</code></td><td>Loads API credentials from <code>.env</code></td></tr>
</tbody>
</table>

### 2. API credentials

Create `Scripts/.env` with a Falcon API client that has **Hosts** and **Zero Trust Assessment** read scopes:

```env
CLIENT_ID="your-falcon-client-id"
SECRET_ID="your-falcon-client-secret"
```

> ⚠️ **Never commit `.env`.** Add it to `.gitignore`. If credentials were ever committed, revoke and rotate them in the Falcon console.

</details>

<details>
<summary><strong>Usage</strong> (click to expand)</summary>

The toolkit is a single script. Run it to generate the current month's reports:

```bash
python Scripts/Generate_Prevention-Health-Sensor.py
```
→ `Datas/<MM-YYYY>/Windows_Prevention-Health-Sensor.csv`
→ `Datas/<MM-YYYY>/Mac_Prevention-Health-Sensor.csv`
→ `Datas/<MM-YYYY>/Linux_Prevention-Health-Sensor.csv`

> 🔧 Device inventory is capped at `filter_limit` (**5000** hosts) at the top of Part 2. Raise it if your fleet is larger.
>
> ✅ Reports are generated only for the operating systems in `target_os` (**Windows, Mac, Linux**).

**Suggested cadence:** run **monthly**. Output is bucketed into a `MM-YYYY` folder, so each run produces a fresh dated snapshot of fleet posture.

</details>

<details>
<summary><strong>Report Fields</strong> (click to expand)</summary>

Each `<OS>_Prevention-Health-Sensor.csv` carries the host metadata plus one column per sensor signal:

<table width="100%">
<thead>
<tr><th align="left">Field<div><img width="300" height="1" alt=""></div></th><th align="left">Description<div><img width="900" height="1" alt=""></div></th></tr>
</thead>
<tbody>
<tr><td><code>Host Id</code></td><td>Falcon device/agent id (AID)</td></tr>
<tr><td><code>Host Name</code></td><td>Hostname</td></tr>
<tr><td><code>Host Type</code></td><td>Product type (Workstation / Server / …)</td></tr>
<tr><td><code>Host OS</code></td><td>Platform (Windows / Mac / Linux)</td></tr>
<tr><td><code>Host State</code></td><td>Visibility state (e.g. <code>Normal</code>, <code>Hidden</code>)</td></tr>
<tr><td><code>RFM</code></td><td><code>True</code> if the host is in Reduced Functionality Mode</td></tr>
<tr><td><code>Linux Mode</code></td><td>Linux sensor mode <em>(Linux reports only)</em></td></tr>
<tr><td><code>Host Score</code></td><td>Sensor configuration score from the assessment</td></tr>
<tr><td><code>Item: &lt;signal&gt;</code></td><td>Per-signal verdict: <code>OK</code>, <code>ATTENTION</code>, or <code>Check RFM</code></td></tr>
<tr><td><code>Reference Month</code></td><td>Month the report was generated (<code>MM</code>)</td></tr>
<tr><td><code>Reference Year</code></td><td>Year the report was generated (<code>YYYY</code>)</td></tr>
<tr><td><code>Reference Date</code></td><td>Date the report was generated (<code>YYYY-MM-DD</code>)</td></tr>
</tbody>
</table>

> Empty / non-applicable values are written as `-`.

</details>

<details>
<summary><strong>File Structure</strong> (click to expand)</summary>

```
Crowdstrike-Prevention-Health-Sensor/
├── Scripts/
│   ├── Generate_Prevention-Health-Sensor.py   # Inventory + assessment + per-OS export
│   ├── .env                                    # Falcon API credentials (not committed)
│   └── requirements.txt
├── Datas/
│   └── <MM-YYYY>/                              # Generated monthly reports, one CSV per OS
└── Files/
    └── prevention-health-report.png           # Example: generated prevention health report
```

</details>

<details>
<summary><strong>Roadmap / Next Steps</strong> (click to expand)</summary>

- **Trend over time.** Compare consecutive monthly snapshots to highlight hosts whose posture *degraded* since the last run.
- **Alerting.** Push hosts with `ATTENTION` signals or active RFM to a ticket / chat channel instead of a static CSV.
- **Combined dashboard.** Feed the per-OS reports into a single view for fleet-wide prevention coverage metrics.

</details>

---

## License

This toolkit is provided as-is for reference and reuse. Adapt it freely to your environment.
