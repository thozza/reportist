# reportist
The missing tool for Todoist status reporting.

## How to install
Simply install the project using PIP.
```
pip3 install --user git+https://github.com/thozza/reportist.git
```

## Usage
```
usage: reportist [-h] [-d] [-k APIKEY] [--store-apikey] [-p PROJECT]
                 [--no-subprojects] [-w WEEK] [-m MONTH] [-y YEAR]
                 [-r {week,month}]

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           Show debug messages.
  -k APIKEY, --apikey APIKEY
                        API Key to use when communicating with Todoist.
  --store-apikey        Store the provided API Key in ~/.reportinst.yaml.
  -p PROJECT, --project PROJECT
                        Report on project that contains the provided string.
                        First matching project is used.
  --no-subprojects      Don't check any subprojects of the requested project
  -w WEEK, --week WEEK  Number of week to report on. (Default: current week)
  -m MONTH, --month MONTH
                        Number of month to report on. (Default: current month)
  -y YEAR, --year YEAR  Year to report on. (Default: current year)
  -r {week,month}, --report {week,month}
                        Type of report to generate. (Default: week)
```
