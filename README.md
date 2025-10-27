# OpenDrive Log Analyzer

This project packages the legacy BLF-to-profile-message tooling as a Python wheel so it can be executed on platforms such as Databricks.  After building and installing the wheel you can run the analyzer through the `opendrive-log-analyzer` console script.

## Building the wheel

```bash
python3 -m build
```

The wheel can then be uploaded to your Databricks workspace and used in jobs or notebooks.

## Command line usage

```bash
opendrive-log-analyzer -d <input_dir> -o <output_dir> -t "0xcaf0054c,0xcaf0036d,0xcaf00370,0xcaf0025E,0xcaf0036a,0xcaf000a1,0x10a"
```

All of the original command line flags remain supported.
