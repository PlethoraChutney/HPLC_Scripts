# Appia - simple chromatography processing
Appia is a set of scripts to process and view chromatography data from AKTA, Shimadzu, and
Waters systems. Chromatography data can then be viewed on the easy-to-use and intuitive
web interface, built with [plotly dash](https://plotly.com/dash/). Please check out the
[web demo](https://appia-demo.herokuapp.com/) hosted on heroku!

Additionally, automatic plots will be prepared for all 
data using [ggplot](https://ggplot2.tidyverse.org/) in R. Options to copy a manual file for plot tweaking are
available.

## Installation
### Server installation
1. Install [docker](https://www.docker.com/)
2. Copy `docker-compose.yml` wherever you want the database to save data
3. Set the $COUCHDB_USER and $COUCHDB_PASSWORD environment variables (**in your environment!**)
4. Run `docker-compose up` in the same directory as docker-compose.yml

### Local/processing-only installation:
This process will install Python, R, and all the packages/libraries you need.
I highly recommend you use a virtual environment for the python packages. Conda
is also fine, but I'm trying to keep this as simple as possible.

1. Clone this repo (or if you don't have git installed, just download it)
2. Install [python](https://www.python.org/)
    1. Run `python -m virtualenv venv` (use python 3)
    2. Run `venv/Scripts/activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
    3. Run `python -m pip install -r requirements.txt`
3. Install [R](https://www.r-project.org/)
    1. In an R session (R.exe/R for Windows/Mac) run:
    2. `install.packages('tidyverse')`
4. *(Optional) Install [R Studio](https://www.rstudio.com/) for easier use of the
    manual plot scripts*

## HPLC Processing
Appia reads `.arw` or `.asc` files (from Waters and Shimadzu HPLCs, respectively)
for information about the sample and how it was run, then optionally collects all the indicated
traces into an Experiment for upload to the visualization database.

**Please note** that our lab uses Waters instruments. Others are supported, but
we will need more information from you for non-Waters bug reports and
feature requests!

### Waters Export Method
When exporting your data, please export the headers as two rows with multiple columns,
rather than two columns with multiple rows.

The Waters script requires `SampleName`, `Channel`, `Instrument Method Name` and
`Sample Set Name`. The order is not important, so long as the
required headers are present in the .arw file. Other information can be there as
well, it won't hurt anything. Flow rate information is pulled from
`processors/flow_rates.json`. If your Instrument Method contains *exactly one* key
from that JSON file, the flow rate is set accordingly. If the file does not exist,
or if your Method matches more or fewer than one key, you will be asked to fill
provide a flow rate. They can also be provided using the `--hplc-flow-rate`
argument.

### Shimadzu Data Export

If you are using a Shimadzu instrument, your method will need the
standard headers, including `Sample ID`, `Total Data Points`, and `Sampling Rate`. When you process, you will need
to pass a set of arguments to tell Appia which channel corresponds to what,
since Shimadzu instruments only output a letter. Additionally, you will be prompted
for a flow rate (or you can provide one with `--hplc-flow-rate`).

### Agilent Data Export

Unfortunately, Agilent has rather limited support for data export. Versions of OpenLab
prior to 2.4 lack the ability to export data in a format that Appia can read. However,
OpenLab 2.4 [introduced the ability to export data as a csv](https://community.agilent.com/technical/software/f/forum/1297/saving-dx-in-csv-excel-format).

Following those instructions
should yield a CSV with two unnamed columns, one representing retention time and the other
signal. Given this lack of information, other data has to be provided by the user. If your
file includes the pattern `Channel<###>` (where <###> is replaced by exactly
three digits), Appia will set the channel for that file to the provided number. If your
file includes the pattern `Flow<##.##>` (where <##.##> is replaced by any number of digits
and a period followed by any number of digits, e.g., 1.25) Appia will set the flow
rate for that file to that number, in mL/min. Otherwise, the user will be prompted for this
information at the command line.

We do not have access to an Agilent instrument, and we welcome collaboration on this front!

## AKTA FPLC Processing
The AKTA processing is straightforward. First, export your data from the AKTA in
.csv format. You'll have to open the trace in Unicorn and use the export button there,
just using "Export Data" saves a zipped binary which Appia can't read. Everything is
handled automatically, but there are several arguments for producing and customizing
automatic plots, if desired.

## Web UI

When you
process HPLC and/or FPLC data with Appia, you create an Experiment. These Experiments
are then uploaded to a CouchDB server. The Appia web server pulls data from the
CouchDB to display traces using plotly dash. This is the main power of Appia --- you
can use your browser to quickly see your data, zoom in and out, select different
traces, combine experiments to compare different runs, re-normalize the data, and
share links with lab members.

### Uploading an Experiment
To upload an experiment, when you process it include the `-d` flag. This will
attempt to read the environment variables `$COUCHDB_USER`, `$COUCHDB_PASSWORD`,
and `$COUCHDB_HOST` and use those to upload the Experiment to the correct database.
You can also pass a JSON file to `-d` instead (but you should never save passwords
in plaintext).

### Viewing the experiment
Simply navigate to your server and view the trace page. The docker default is
`{myserver}:8080/traces`. You can search
experiments in the dropdown menu and concatenate HPLC results to compare across
experiments. Clicking "Renormalize HPLC" will re-normalize the traces to set the
maximum of the currently-viewed unnormalized region to 1, allowing you to compare
specific peaks.

## Batch scripts
From the command line, the best way to use Appia is to run appia.py. However,
several batch scripts are included in this repo to give users who prefer not
to use command line interfaces a set of commonly-used options. You could write
equivalent shell scripts for Linux or Mac machines, but since most chromatography
systems run on Windows I've included these for those machines.

### process.bat
Read all files in the current directory and process all CSV, ASC, and ARW files
into a new experiment which is uploaded to the database using environment variables

### process-and-rename.bat
Same as above, but specify an Experiment ID yourself instead of reading one from
the data.

# Example Data
Examples of correctly-formatted Waters, Shimadzu, and AKTA files can be found in `/test-files/`. The directory `/processed-tests/` is the result of the command:

```python appia.py process test-files/* -kpo processed-tests -f 18 24```

I included the -k parameter because I want to keep the raw files there, but if I
had not, they'd be moved to their own respective directories in
`/processed-tests/`. You'll see that in `/processed-tests/` there are three
files representing the compiled data.

## HPLC Data
For ease of use, HPLC data is stored in both a long and wide format.

### Long format
mL is calculated from Time during processing. Sample and Channel are self-explanatory.
Normalization tells if Value is the raw signal or a normalized Signal from 0 to 1,
0 being the minimum and 1 being the maximum over that sample/channel combination,
unless a specific range over which to normalize was passed into Appia during processing.

| mL | Sample   | Channel | Time | Normalization | Value |
|----|----------|---------|------|---------------|-------|
| 0  | 05_25_BB | GFP     | 0    | Signal        | -1    |
| 0  | 05_25_BB | Trp     | 0    | Signal        | -35   |
| 0  | 05_25_D  | GFP     | 0    | Signal        | 3     |
| 0  | 05_25_D  | Trp     | 0    | Signal        | 0     |

### Wide format
Wide format is the same data, but presented in a more traditional, "excel-style" format.
Each column represents a trace, with a single column for Time to go along with it. You
may note that the example wide table has a strange format, with many empty rows. This is
because Shimadzu and Waters sample at different rates, meaning they do not have overlapping
sampling points for the most part. Appia handles this, by using a single Time column
and introducing empty rows in the Signal columns. Your plotting software should be able
to deal with that, or you can just filter for non-empty rows.

| Time     | 05_25_BB GFP | 05_25_BB Trp | 05_25_D GFP | 05_25_D Trp |
|----------|--------------|--------------|-------------|-------------|
| 0        | -1           | -35          | 3           | 0           |
| 0.033333 | -1           | -20          | 0           | -1          |

## FPLC data
FPLC data is only stored in long format, since by-and-large it is the same as
what wide format would be. You just need to filter out channels you don't care about
to reproduce what a wide-format table would be. Interestingly, AKTAs sample each channel
at different rates, meaning that each channel has different x-axis values. This is all
handled correctly by Appia, but that would introduce blank rows in the wide table, as
with the HPLC example data. The fraction column indicates the vial into which that
data point was dumped. This is used to fill fractions of interest, as seen in the
example FPLC plot and the web interface.

| mL       | CV       | Channel | Fraction | Sample                     | Normalization | Value    |
|----------|----------|---------|----------|----------------------------|---------------|----------|
| -0.00701 | -0.00029 | mAU     | 1        | 2018_0821SEC_detergentENaC | Signal        | 0.031309 |
| -0.00618 | -0.00026 | mAU     | 1        | 2018_0821SEC_detergentENaC | Signal        | 0.022083 |
| -0.00535 | -0.00022 | mAU     | 1        | 2018_0821SEC_detergentENaC | Signal        | 0.022115 |
