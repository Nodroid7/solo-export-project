|auther: spider
# Data export tool for SOLOII.DAT binary file

This is a data export tool to extract data from the **Geo Solo II Energy Display** `SOLOII.DAT` binary data file.

The [SOLOII.DAT binary data file format](SOLOII_DAT_FILE_FORMAT.md) is my personal reverse engineering effort by using only some energynote.eu detailedReadings.csv export files as points of reference and doing some testing with the actual device.

The binary file has three sections. I have named them as "header", "extra header" and "data".
This tool is mainly to extract information from the data section, but can also be used to get some information from the header section and dump the extra header section for inspection.

* The header section stores the basic settings of the device. A new entry in recorded every time some setting is changed but there is no timestamp of the change. The header can store 116 such entries.
* The extra header is an unknown section between the header and the data filled almost completely with binary ones. Only a few bytes differ with some unspecified values.
* The data section contains 38912 entries of the readings stored in 15 minute intervals, which means the file contains 405 days and 8 hours worth of data. The values include the power consumption with the configured tariff price applied at the time of the entry, the indoor and outdoor temperatures and the signal level of the external sensor unit.


## Requirements

 * Python >= 3.6

The tool is developed in Linux platform so YMMV with Windows and MacOS platforms.


## Data output formats

| Output format (-f) | Description |
| --- | --- |
| influxdb   | Full file data including indoor and outdoor temperatures in the InfluxDB line format. |
| json       | Full file data including indoor and outdoor temperatures in JSON format. |
| csv        | Full file data including indoor and outdoor temperatures in CSV format. |
| energynote | The standard energynote.eu (now discontinued) `detailedReadings.csv` CSV export format containing only the energy readings. |
| (default)  | Text lines to take a quick look of the data contents. |


## Usage:

    usage: solo-export.py [-h] [-H] [-E] [-D] [-f {influxdb,json,csv,energynote}]
                          [-m MEASUREMENT] [-t TIME_SHIFT] [-d] [-v]
                          filename

    Export data from Geo Solo 2 SOLOII.DAT binary data file.

    positional arguments:
      filename              SOLOII.DAT binary file to read

    optional arguments:
      -h, --help            show this help message and exit
      -H, --header          Read header entries
      -E, --extra           Read header extra data
      -D, --data            Read data entries (default)
      -f {influxdb,json,csv,energynote}, --format {influxdb,json,csv,energynote}
                            Output format (influxdb line format, JSON, CSV,
                            energynote.eu detailedReadings.csv)
      -m MEASUREMENT, --measurement MEASUREMENT
                            Measurement name for influxdb (default: solo)
      -t TIME_SHIFT, --time-shift TIME_SHIFT
                            Change original entry timestamp (hours)
      -d, --debug           Print debug information to stderr
      -v, --verbose         Increase verbosity (can be used multiple times)

The Geo Solo device stores times as "local time" without timezone information but the InfluxDB requires data timestamps in UTC so the tool has an option to configure time shift offset during export. Note however that if you have changed the device time at some point (for summer time for example), there is no record of it in the data and you must manage the appropriate time shift at export time yourself for different time periods in the file. My recommendation is that you do not change the device time for summer time and just keep it unchanged throughout the year so you can just use the same fixed time shift value always. Or you could also set up the UTC time for the device to not have to use the time shift option at all.

## Hexdump

The `hexdump/` directory contains some formatting files and a wrapper script for the `hexdump` command line tool that can be used to inspect the binary file raw data without python.
