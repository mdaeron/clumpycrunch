# ClumpyCrunch

Web application for standardizing Δ<sub>47</sub> measurements using the `D47crunch` library

## Quick start

### Raw data

Paste your data into the __Raw Data Input__ text box, using the following format, with cells separated by tabs, commas, or semicolons:

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

Without a `Session` column, all analyses will be treated as belonging to a single analytical session.

### WG settings

Two options are available.

By default, the bulk composition of the WG in each session is computed based on all analyses of a given carbonate standard within that session.

Alternatively, you may specify the WG bulk composition explicitly in, by including fields `d13Cwg_VPDB` and `d18Owg_VSMOW` in the raw data table.

### Standardization settings

Two options are available.

