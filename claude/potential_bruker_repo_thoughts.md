# Potential shared repository: `bruker_ultima_utils`

**Date:** 2026-04-02
**Context:** The z_voxel_size bug (top-level PVStateShard reporting wrong ZAxis value) was fixed in brukerbridge (`tiff_to_nii.py`) but the same bug persisted in `snake_brainsss/workflow/scripts/build_fly.py:create_imaging_json()` because both repos parse the Bruker XML independently. This motivated the idea of a shared `bruker_ultima_utils` package (similar to `anatomical_orientation`) that both repos import.

---

## Motivation

- Eliminate duplicated Bruker XML parsing logic across brukerbridge and snake_brainsss
- Single source of truth for microscope-specific constants and metadata extraction
- Prevent bugs from diverging implementations (the z_voxel_size bug is the canonical example)

---

## Inventory of Bruker-specific logic across both repos

### Priority 5 -- Extract immediately (duplicated + already caused bugs)

| Logic | brukerbridge | snake_brainsss | Notes |
|---|---|---|---|
| **micronsPerPixel parsing** (x/y/z voxel sizes) | `tiff_to_nii.py:104-132` | `build_fly.py:972-983` | **This is the z_voxel_size bug.** Two implementations, one wrong. Top-level PVStateShard can report wrong ZAxis; must use Sequence-level shard. |
| **Sequence type detection** (TSeries Timed vs ZSeries) | `tiff_to_nii.py:135-145` | `build_fly.py:1015-1033` | Duplicated logic, determines 2D vs 3D |
| **scan.json creation** | doesn't exist here yet | `build_fly.py:918-1109` | Should live in shared lib, called from both |
| **Datetime extraction from XML** | `utils.py:672-684` | `build_fly.py:1144-1195` | Two implementations of the same thing |

### Priority 4 -- Strong extraction candidates (duplicated or hardware-specific)

| Logic | brukerbridge | snake_brainsss | Notes |
|---|---|---|---|
| **Laser power parsing** (`xml_laser_functions`) | -- | `build_fly.py:1111-1142` | Bruker-specific laser name mapping (Pockels, 1040, 640nm) |
| **PMT gain parsing** | -- | `build_fly.py:1000-1006` | PrairieView-specific XML structure |
| **Pixel dimensions** (pixelsPerLine, linesPerFrame) | `tiff_to_nii.py:93-102` | `build_fly.py:1008-1011` | Duplicated |
| **Timestamp extraction** from Frame/@relativeTime | -- | `build_fly.py:1051-1109`, `bruker_metadata_utils.py:8-96` | Already duplicated *within* snake_brainsss |
| **Channel ID detection** | `tiff_to_nii.py:21-40` | -- | Bruker-specific File/channel attribute parsing |

### Priority 3 -- Worth extracting (microscope-specific constants/knowledge)

| Logic | Location | Notes |
|---|---|---|
| **PVScan version handling** | `brukerbridge/scripts/main.py:136-183` | Versions 5.8.64.800/814/818/900 -- ripper behavior per version |
| **Data range constant** (0-8191, 14-bit) | `snake_brainsss/constants.py:13-22`, `preprocessing.py:49-58` | Hardware-defined, duplicated within snake_brainsss |
| **Bidirectional Z handling** | `tiff_to_nii.py:148-152, 383-388` | Bruker-specific scan attribute |
| **Scanner voltage calibration** (volts_per_voxel) | `snake_brainsss/warp_utils.py:79-107` | minVoltage/maxVoltage XML parsing |
| **Z motor/piezo position extraction** | `snake_brainsss/warp_utils.py:119-153` | 'Z Focus', 'Bruker 400 um Piezo' |

### Priority 2 -- Could extract but lower urgency

| Logic | Location | Notes |
|---|---|---|
| **Multipage vs singlepage TIFF detection** (.companion.ome) | `tiff_to_nii.py:86-91` | Bruker-specific file convention |
| **TSeries folder naming** (TSeries-timestamp-###) | `brukerbridge/utils.py:709-734` | Bruker naming convention |
| **Bruker file renaming** (ch1_concat -> channel_1, etc.) | `snake_brainsss/build_fly.py:369-497` | Bruker output naming |
| **SingleImage folder handling** | both repos | Minor utility |

### Priority 1 -- Leave in place (too workflow-specific)

| Logic | Location | Notes |
|---|---|---|
| **TIFF loading/assembly** (4 cases in tiff_to_nii) | `tiff_to_nii.py:231-462` | Tightly coupled to NIfTI conversion workflow |
| **Raw-to-TIFF ripping** (ripper.bat) | `brukerbridge/raw_to_tiff.py` | Machine-specific subprocess |
| **Orientation matrices** | `snake_brainsss/constants.py:58-172` | Already handled by `anatomical_orientation` package |
| **Motion correction channel routing** | snake_brainsss pipeline | Workflow-specific, not microscope-specific |

---

## Recommended initial scope

The package would start with:

1. **XML parser module** -- single correct implementation for reading PVStateShard (with the Sequence-level fix), extracting voxel sizes, dimensions, laser power, PMT gains, timestamps, datetime, sequence type
2. **scan.json builder** -- takes parsed XML, returns dict or writes json
3. **Constants** -- data range (14-bit/0-8191), PVScan version table, laser name mappings
4. **Voltage/position utilities** -- scanner calibration, Z motor/piezo extraction

---

## Key technical detail: the z_voxel_size bug

The PrairieView XML has two levels of PVStateShard:

```
PVScan (root)
  PVStateShard          <-- top-level: can have WRONG ZAxis (e.g. 5 instead of 1)
    PVStateValue key="micronsPerPixel"
      IndexedValue index="ZAxis" value="5.0"   <-- WRONG
  Sequence
    PVStateShard        <-- sequence-level: has CORRECT acquisition values
      PVStateValue key="micronsPerPixel"
        IndexedValue index="ZAxis" value="1.0"  <-- CORRECT
```

The fix (already in brukerbridge `tiff_to_nii.py:108-120`) is to prefer the Sequence-level PVStateShard, falling back to top-level only if the Sequence has no shard.

The bug still exists in `snake_brainsss/workflow/scripts/build_fly.py:971-983` which reads from the top-level PVStateShard by iterating `root` children directly.

A fix script also exists at `snake_brainsss/workflow/dev/fix_scan_json_z_voxel.py` which retroactively patches existing scan.json files, confirming this bug has bitten before.

---

## Existing shared package precedent

`anatomical_orientation` is already a shared package imported by both repos for imaging orientation/direction matrices. The same pattern (pip-installable package, imported by both) would work for `bruker_ultima_utils`.

---

## XML attributes and keys reference

| XML Element | Attribute/Key | Purpose | Value Type |
|---|---|---|---|
| PVScan (root) | version | PrairieView software version | string (e.g. "5.8.64.900") |
| PVScan (root) | date | Imaging session timestamp | string (e.g. "6/13/2024 04:54:23 PM") |
| Sequence | type | Scan type | "TSeries Timed Element" or "TSeries ZSeries Element" |
| Sequence | bidirectionalZ | Bidirectional scanning flag | "True" or "False" |
| Sequence | cycle | Cycle number | string (e.g. "1") |
| PVStateValue | key="micronsPerPixel" | Voxel sizes | IndexedValue children with XAxis/YAxis/ZAxis |
| PVStateValue | key="pixelsPerLine" | X dimension (pixels) | int via value attr |
| PVStateValue | key="linesPerFrame" | Y dimension (pixels) | int via value attr |
| PVStateValue | key="laserPower" | Laser power settings | IndexedValue children |
| PVStateValue | key="laserWavelength" | Laser wavelength | IndexedValue children |
| PVStateValue | key="pmtGain" | PMT detector gains | IndexedValue children with description attr |
| PVStateValue | key="maxVoltage" / key="minVoltage" | Scanner voltage range | IndexedValue with XAxis/YAxis |
| PVStateValue | key="currentScanCenter" | XY scan center | IndexedValue with XAxis/YAxis |
| Frame | relativeTime | Timestamp per frame | float (seconds) |
| Frame | index | Z-slice index (in volumetric) | int |
| File | channel | Channel identifier | string (e.g. "1", "2") |
| File | filename | TIFF filename | string |
