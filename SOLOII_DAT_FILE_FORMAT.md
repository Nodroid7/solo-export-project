# SOLOII.DAT binary data file format

This is a **Geo Solo II Energy Display** `SOLOII.DAT` binary data file format description.

The file format is my personal reverse engineering effort by using only some energynote.eu detailedReadings.csv export files as points of reference and doing some testing with the actual device.

The binary file has three sections. I have named them as "header", "extra header" and "data".


## Binary file sections

| Range        | Length | Section | Description |
| ------------ | ------ | ------- | ----------- |
| 0 - 5        | 6      | Magic string | `SoloII` - Static text |
| 6 - 8        | 3      | Extra header | `00 01 00` - Might be file format version number. |
| 9 - 4068     | 4060   | Header       | 116 entries, 35 bytes each. |
| 4069 - 4095  | 27     | Extra header | `FF ...` - All values are binary ones. |
| 4096 - 8191  | 4096   | Extra header | `FF ...` - Most values are binary ones. |
| 8192 - EOF   | -      | Data         | 38912 entries, 32 bytes each. |


## The magic string

The binary file starts with a string `SoloII`.


## Header

The header section stores 116 entries of the basic settings of the device.
A new entry in recorded every time some setting is changed but there is no timestamp of the change.

The entries are 35 bytes long and they start at offset 9.

| Range | Length | Field | Description |
| --- | --- | --- | --- |
| 0        | 1  | | The last entry has always `A5` while others have `00` |
| 1        | 1  | | Always `21` |
| 2 - 3    | 2  | tariff_1 | |
| 4 - 5    | 2  | tariff_2 | |
| 6 - 7    | 2  | tariff_3 | |
| 8 - 9    | 2  | std_charge | |
| 10 - 11  | 2  | budget_yearly | |
| 12 - 15  | 4  | | *TODO* |
| 16       | 1  | time_1_start | |
| 17       | 1  | time_1_end | |
| 18       | 1  | time_2_start | |
| 19       | 1  | time_2_end | |
| 20       | 1  | time_3_start | |
| 21       | 1  | time_3_end | |
| 22 - 31  | 10 | | *TODO* |
| 32 - 33  | 2  | | Always `00 00` |
| 34       | 1  | i | Sequential index number starting from `01` |


## Extra header

The extra header is a name for the unknown sections in the file.
The values are almost all binary ones (`FF` in hex).
Only a few bytes differ with some unspecified values.

| Range | Length | Description |
| --- | --- | --- |
| 6 - 8        | 3   | Bytes between magic string and header - `00 01 00` - Might be file format version number. |
| 4069 - 8191  | 4123 | Bytes between header and data - Almost all `FF` |
| 4132 - 4134  | 3  | Non-`FF` bytes, same as below |
| 4196 - 4198  | 3  | Non-`FF` bytes, same as others |
| 4260 - 4262  | 3  | Non-`FF` bytes, same as others |
| 4324 - 4326  | 3  | Non-`FF` bytes, same as above |
| 4352 - 4405  | 54 | Non-`FF` bytes, various bytes |


## Data

The data section contains 38912 entries of the readings stored in 15 minute intervals. So the file contains 405 days and 8 hours worth of data stored in a round-robin manner.

| Range | Length | Field | Description |
| --- | --- | --- | --- |
| 0 - 1    | 2  | | Sequential index number used together with the entry row number to calculate entry timestamp |
| 2 - 3    | 2  | | `FE FE` - Unknown |
| 4 - 5    | 2  | pwr_Wh | Power consumption |
| 6 - 9    | 4  | | `00` - Unknown |
| 10       | 1  | price | Configured tariff price applied during time of the entry |
| 11 - 22  | 12 | | `00` - Unknown |
| 23       | 1  | temp_out | Temperature from the external temperature sensor |
| 24       | 1  | temp_in | Temperature from the internal temperature sensor of the device. Not very useful since the device warms up when the display is on so the reading is much warmer than the actual room temperature. |
| 25       | 1  | signal | Signal level of the external power meter unit |
| 26 - 27  | 2  | | `FF 00` - Unknown |
| 28       | 1  | missed | Usually `00` but increases if there are missing readings from the external unit. If there is complete disconnect for the whole 15 minute period the value is `FE` |
| 29       | 1  | kk | Unknown - Changes at month boundary, but not sequentially. Sometimes might be `00` |
| 30 - 31  | 2  | | `00 00` - Unknown |
