# ClumpyCrunch

A web application for processing Δ<sub>47</sub> measurements using the [D47crunch] library. Currently hosted at [clumpycrunch.pythonanywhere.com].

[D47crunch]: https://github.com/mdaeron/D47crunch
[clumpycrunch.pythonanywhere.com]: https://clumpycrunch.pythonanywhere.com

## Quick start

### Raw data

Paste your data into the __Raw Data Input__ text box, using the following format:

|UID|Session| Sample |D17O|d45|d46|d47|d48|d49|
|:-:|:-----:|:------:|---:|--:|--:|--:|--:|--:|
|001|2020-01|ETH-1   |... |...|...|...|...|...|
|002|2020-01|IAEA-C2 |... |...|...|...|...|...|
|003|2020-01|ETH-3   |... |...|...|...|...|...|
|...|...    |...     |... |...|...|...|...|...|
|030|2020-01|ETH-2   |... |...|...|...|...|...|
|031|2020-02|ETH-3   |... |...|...|...|...|...|
|032|2020-02|IAEA-C1 |... |...|...|...|...|...|
|...|...    |...     |... |...|...|...|...|...|
|060|2020-02|ETH-1   |... |...|...|...|...|...|

The only mandatory columns are `Sample`, `d45`, `d46`, and `d47`.

`UID` cells are treated as arbitrary strings and are intended to provide an unique identifier for ech analysis.

`Session` cells are also treated as arbitrary strings and are intended to provide an unique identifier for each analytical session (defined as a discrete time window during which analytical conditions are presumed to have remained stable). Without a `Session` column, all analyses will be treated as belonging to the same session.

Without a `D17O` column, all analyses will be treated as having an <sup>17</sup>O anomaly of zero relative to VSMOW (with a λ value defined in the __Oxygen-17 Correction Settings__ panel).

Optional `d13Cwg_VPDB` and `d18Owg_VSMOW` columns may be used to specify explicitly the “bulk” isotopic composition of the working gas. These fields must be filled in for analysis (i.e. each line). If the option _Explicitly defined in the raw data_ is not selected in the __Working Gas Composition Settings__ panel, these fields are ignored.

Optional `Nominal_d13C_VPDB` and 	`Nominal_d18O_VPDB` columns may be used to treat some samples as carbonate standards for δ<sup>13</sup>C and δ<sup>18</sup>O normalization (see __Carbon-13 Standardization__ and __Oxygen-18 Standardization__ panels) and/or to compute working gas compositions (see __Working Gas Composition Settings__).

Empty cells are treated as `nan` (not a number).

Table cells may be separated by tabs, by commas, or by semicolons (no mixing of delimitors), and spaces surrounding these delimitors are ignored.

### WG settings

Two options are available. By default, the bulk composition of the WG in each session is computed based on carbonate standard analyses (i.e. lines with non-empty values for both `Nominal_d13C_VPDB ` and `Nominal_d18O_VPDB `) within that session.

Alternatively, you may specify the WG bulk composition explicitly in, by including columns `d13Cwg_VPDB` and `d18Owg_VSMOW` in the raw data table.

### <sup>13</sup>C and <sup>18</sup>O standardization settings

By default, bulk isotopic compositions are standardized using a “two-point” affine transformation (correcting for small offsets and stretching effects) based on carbonate standard analyses (i.e. lines with non-empty values for `Nominal_d13C_VPDB ` and/or `Nominal_d18O_VPDB `) within each session.

Optionally, you may opt instead for a “single-point” standardization approach not correcting for strecthing effects, for instance if the cabonate standards cover only a small fraction of the full isotopic range of your measurements.

You may also opt to perform no _a posteriori_ standardization of bulk isotopic compositions, which implies that the quality of your final δ<sup>13</sup>C and δ<sup>18</sup>O values will depend strongly on the accuracy of your working gas composition and the linearity of your instrument.

### Δ<sub>47</sub> standardization settings

> under construction...
