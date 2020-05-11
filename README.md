# ClumpyCrunch

A web application for processing Δ<sub>47</sub> measurements using the [D47crunch] library.

[D47crunch]: https://github.com/mdaeron/D47crunch

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

Without a `D17O` column, all analyses will be treated as having an <sup>17</sup>O anomaly of zero relative to SMOW (with a λ value defined in the __Oxygen-17 Correction Settings__ panel).

Empty cells are treated as `nan` (not a number).

Table cells may be separated by tabs, by commas, or by semicolons (no mixing of delimitors), and spaces surrounding these delimitors are ignored.

### WG settings

Two options are available. By default, the bulk composition of the WG in each session is computed based on all analyses of a given carbonate standard within that session.

Alternatively, you may specify the WG bulk composition explicitly in, by including columns `d13Cwg_VPDB` and `d18Owg_VSMOW` in the raw data table.

### Standardization settings

> under construction...
