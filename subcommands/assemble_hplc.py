import pandas as pd
import sys
import os
import shutil
import subprocess
import argparse
import logging

# 1 Import functions -----------------------------------------------------------


def get_file_list(directory, extension):
	file_list = []
	for file in os.listdir(directory):
		if file.endswith(extension):
			file_list.append(os.path.join(directory, file))

	return file_list

# 2 Data processing functions --------------------------------------------------


def append_chroms(file_list, system):

	flow_rates = {
		'10_300': 0.5,
		'5_150': 0.3
	}

	column_volumes = {
		'10_300': 24,
		'5_150': 3
	}

	chroms = pd.DataFrame(columns = ['Time', 'Signal', 'Channel', 'Sample'])

	if system == 'waters':
		header_rows = 2
		data_row = 0
		for file in file_list:
			to_append = pd.read_csv(
				file,
				delim_whitespace = True,
				skiprows = header_rows,
				names = ["Time", "Signal"],
				header = None
			)
			sample_info = pd.read_csv(
				file,
				delim_whitespace = True,
				nrows = header_rows
			)
			sample_name = str(sample_info.loc[data_row]['SampleName'])
			channel_ID = str(sample_info.loc[data_row]['Channel'])
			to_append['Channel'] = channel_ID
			to_append['Sample'] = sample_name

			if 'Instrument Method Name' in sample_info:
				method = str(sample_info.loc[data_row]['Instrument Method Name'])

				if '10_300' in method:
					column = '10_300'
				elif '5_150' in method:
					column = '5_150'

				to_append['Volume'] = to_append['Time']*flow_rates[column]
				to_append['Column Volume'] = to_append['Volume']/column_volumes[column]

			chroms = chroms.append(to_append, ignore_index = False)
	elif system == 'shimadzu':
		header_rows = 16
		data_row = 0
		# if you don't have two detectors, or want to rename the channels, change that here
		# and in filename_human_readable()
		channel_names = ['A', 'B']
		for file in file_list:
			to_append = pd.read_csv(
				file,
				sep = '\t',
				skiprows = header_rows,
				names = ['Signal'],
				header = None,
				dtype = 'float64'
			)
			sample_info = pd.read_csv(
				file,
				sep = '\t',
				nrows = header_rows,
				names = ['Stat'] + channel_names + ['Units'],
				engine = 'python'
			)
			sample_info.set_index('Stat', inplace = True)
			to_append['Sample'] = str(sample_info.loc['Sample ID:'][0])
			number_samples = int(sample_info.loc['Total Data Points:'][0])
			to_append['Channel'] = [x for x in channel_names for i in range(number_samples)]
			sampling_interval = float(sample_info.loc['Sampling Rate:'][0])
			seconds_list = [x * sampling_interval for x in range(number_samples)] * len(channel_names)
			to_append['Time'] = [x/60 for x in seconds_list]

			chroms = chroms.append(to_append, ignore_index = True, sort = True)

		chroms = chroms[['Time', 'Signal', 'Channel', 'Sample']]

	wide_table = chroms.copy()
	wide_table['Sample'] = wide_table['Sample'].astype(str) + ' ' + wide_table['Channel']
	wide_table.drop('Channel', axis = 1)
	wide_table = wide_table.pivot_table(
		index = 'Time',
		columns = 'Sample',
		values = 'Signal'
	)

	return (chroms, wide_table)


def filename_human_readable(file_name, system):
	if system == 'waters':
		header_rows = 2
		data_row = 0
		headers = pd.read_csv(
			file_name,
			delim_whitespace = True,
			nrows = header_rows
		)
		readable_dir_name = str(headers.loc[data_row]['Sample Set Name']).replace('/', '-').replace(" ", "_") + "_processed"

	elif system == 'shimadzu':
		# change channel names here and in append_chroms()
		header_rows = 16
		channel_names = ['A', 'B']
		sample_info = pd.read_csv(
			file_name,
			sep = '\t',
			nrows = header_rows,
			names = ['Stat'] + channel_names + ['Units'],
			engine = 'python'
		)
		sample_info.set_index('Stat', inplace = True)
		readable_dir_name = str(sample_info.loc['Acquisition Date and Time:'][0]).replace('/', '-').replace(' ', '_').replace(':', '-') + '_processed'

	return readable_dir_name

def post_to_slack(config, new_fullpath):
	from subcommands import slack_bot
	client = slack_bot.get_client(config)
	if client is None:
		return

	slack_bot.send_graphs(
		config,
		client,
		[os.path.join(os.path.normpath(new_fullpath), x) for x in ['fsec_traces.pdf', 'normalized_traces.pdf']]
	)

# 2 Main -----------------------------------------------------------------------


def main(args):
	# The visualization database depends on a dictionary from a file
	# in the appia subcommands directory called `config.py`. This dictionary
	# must also be named `config` and have the relevant keys and values
	try:
		from subcommands import config
	except ImportError:
		logging.warning('You must have a config file named config.py in subcommands to use the visualization database and slack bot.')
	logging.debug(args)
	script_location = os.path.dirname(os.path.realpath(__file__))
	directory = os.path.abspath(args.directory)

# * 2.1 Import files -----------------------------------------------------------

	system_extensions = {
		'waters': '.arw',
		'shimadzu': '.asc'
	}

	logging.info(f'Checking {directory} for {system_extensions[args.system]} files...')

	file_list = get_file_list(directory, system_extensions[args.system])

	if len(file_list) == 0:
		logging.error(f'No {system_extensions[args.system]} files found. Exiting...')
		sys.exit(1)

	if args.rename is not None:
		readable_dir = os.path.join(directory, args.rename)
	else:
		readable_dir = os.path.join(directory, filename_human_readable(file_list[0], args.system))

	if not args.no_move:
		logging.info(f'Found {len(file_list)} files. Moving to {readable_dir}...')
		new_fullpath = readable_dir
		os.makedirs(new_fullpath)

		for file in file_list:
			shutil.move(file, os.path.join(readable_dir, os.path.basename(file)))
	else:
		logging.info(f'Found {len(file_list)} files. Processing in place...')
		new_fullpath = directory

# * 2.2 Assemble .arw to .csv --------------------------------------------------

	logging.info('Assembling traces...')

	file_list = get_file_list(new_fullpath, system_extensions[args.system])
	long_and_wide = append_chroms(file_list, args.system)
	file_name = os.path.join(new_fullpath, 'long_chromatograms.csv')
	long_and_wide[0].to_csv(file_name, index = False)
	file_name = os.path.join(new_fullpath, 'wide_chromatograms.csv')
	long_and_wide[1].to_csv(file_name, index = True)

# * 2.3 Add traces to couchdb --------------------------------------------------

	if not args.no_db:
		logging.info('Adding experiment to visualization database...')
		try:
			from subcommands import backend

			db = backend.init_db(config.config)
			backend.collect_experiments(os.path.abspath(new_fullpath), db, args.reduce)
		except ModuleNotFoundError:
			logging.error('No config. Skipping visualization db.')

# * 2.4 Plot traces ------------------------------------------------------------

	if not args.no_plots:
		logging.info('Making plots...')
		subprocess.run(['Rscript', os.path.join(os.path.normpath(script_location), 'auto_graph_HPLC.R'), os.path.normpath(new_fullpath)])

	# send both R plots to the chromatography channel in slack
	# channel and bot token need to be in the config file with the
	# couchdb setup
	if args.post_to_slack:
		logging.info('Posting to slack')
		try:
			post_to_slack(config.config, new_fullpath)
		except UnboundLocalError:
			logging.error('No config. Skipping slack posting.')

	if args.copy_manual:
		logging.info('Copying manual R script...')
		shutil.copyfile(os.path.join(script_location, 'manual_plot_HPLC.R'), os.path.join(new_fullpath, 'manual_plot_HPLC.R'))

	logging.info('Done!')


parser = argparse.ArgumentParser(description = 'A script to collect and plot Waters HPLC traces.', add_help=False)
parser.set_defaults(func = main)
parser.add_argument(
	'directory',
	default = os.getcwd(),
	help = 'Which directory to pull all .arw files from'
)
parser.add_argument(
	'-r', '--rename',
	help = 'Use a non-default name'
)
parser.add_argument(
	'--reduce',
	help = 'Keep only one in REDUCE points, e.g., `--reduce 10` keeps only 1/10th of your points.',
	default = 1,
	type = int
)
parser.add_argument(
	'-d', '--no-db',
	help = 'Do not add to couchdb',
	action = 'store_true',
	default = False
)

plot_group = parser.add_mutually_exclusive_group()
plot_group.add_argument(
	'-p', '--no-plots',
	help = 'Do not make R plots',
	action = 'store_true',
	default = False
)
plot_group.add_argument(
	'-s', '--post-to-slack',
	help = "Send completed plots to Slack",
	action = 'store_true',
	default = False
)
parser.add_argument(
	'-c', '--copy-manual',
	help = 'Copy R plot file for manual plot editing',
	action = 'store_true',
	default = False
)
parser.add_argument(
	'-k', '--no-move',
	help = 'Process data files in place (do not move to new directory)',
	action = 'store_true',
	default = False
)
parser.add_argument(
	'--system',
	help = 'What HPLC system. Default Waters',
	type = str.lower,
	choices = ['waters', 'shimadzu'],
	default = 'waters'
)
