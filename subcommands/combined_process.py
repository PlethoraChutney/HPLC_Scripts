from subcommands import assemble_hplc, assemble_fplc
from glob import glob
import os
import sys
import argparse
import logging


def combined_df(files, h_system):
    # including fplc in system extensions for ~*~* futureproofing *~*~
    f_system = 'akta'
    system_extensions = {
        'akta': '.csv',
        'waters': '.arw',
        'shimadzu': '.asc'
    }

    globbed_files = []
    for pattern in files:
        globbed_files.extend(glob(pattern))
    files = [os.path.abspath(x) for x in globbed_files]
    files = set(files)
    hplc_files = []
    fplc_files = []

    for file in files:
        try:
            if file.endswith(system_extensions[f_system]):
                fplc_files.append(file)
            elif file.endswith(system_extensions[h_system]):
                hplc_files.append(file)
            else:
                raise KeyError
        except KeyError:
            logging.error(f'Unexpected file extension in {file}. Please check your system and file arguments.')
            sys.exit(1)

    if len(hplc_files) == 0 or len(fplc_files) != 1:
        logging.error('Must have at least one HPLC file and exactly one FPLC file for combined processing')
        sys.exit(2)

    # keep [0] because append_chroms returns a list of [long, wide] dfs
    h_df = assemble_hplc.append_chroms(hplc_files, h_system)[0]
    h_df.to_csv('test_h.csv')


def main(args):
    cdf = combined_df(args.files, args.system)

parser = argparse.ArgumentParser(
    description = 'Combined FPLC and HPLC processing',
    add_help=False
)
parser.set_defaults(func = main)
parser.add_argument(
    'files',
    help = 'All files to combine and process.',
    type = str,
    nargs = '+'
)
parser.add_argument(
    '--system',
    default = 'waters',
    help = 'What HPLC system. Default Waters',
    type = str.lower,
    choices = ['waters', 'shimadzu']
)
