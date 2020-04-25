# ClumpyCrunch

Web application for standardizing Δ<sub>47</sub> measurements using the `D47crunch` library

## Quick start

Paste your data into the __Raw Data Input__ text box, using the following tab-delimited format:

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

Columns `D17O`, `d48`, and `d49` are optional (the missing columns will be treated as zero).

