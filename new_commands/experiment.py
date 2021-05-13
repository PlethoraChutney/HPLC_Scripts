from new_commands.core import normalizer
import pandas as pd
from .database import pull_experiment
from .core import *
from math import floor

class Experiment:
    def __init__(self, id):
        self.id = id
        self.version = 3
        self._hplc = None
        self._fplc = None

    @property
    def hplc(self):
        try:
            return self._hplc
        except AttributeError:
            return None

    @hplc.setter
    def hplc(self, df):
        if isinstance(df, pd.DataFrame):
            self._hplc = df
        else:
            raise TypeError('HPLC input is not a pandas dataframe')

    @property
    def fplc(self):
        try:
            return self._fplc
        except AttributeError:
            return None

    @fplc.setter
    def fplc(self, df):
        if isinstance(df, pd.DataFrame):
            self._fplc = df
        else:
            raise TypeError('FPLC input is not a pandas dataframe')

    def __repr__(self):
        to_return = f'Experiment "{self.id}" with '
        if self.hplc is not None:
            to_return += 'HPLC '
        if self.hplc is not None and self.fplc is not None:
            to_return += 'and '
        if self.fplc is not None:
            to_return += 'FPLC '
        if self.hplc is None and self.fplc is None:
            to_return += 'no '
        to_return += 'data.'

        return to_return

    def show_tables(self):
        print('HPLC:')
        print(self.hplc)
        print('FPLC:')
        print(self.fplc)

    def jsonify(self):
        if self.hplc is not None:
            hplc_json = self.hplc.to_json()
        else:
            hplc_json = ''

        if self.fplc is not None:
            fplc_json = self.fplc.to_json()
        else:
            fplc_json = ''

        doc = {
            '_id': self.id,
            'version': self.version,
            'hplc': h_json,
            'fplc': f_json
        }

        return doc

    def renormalize_hplc(self, norm_range, strict):
        if self.hplc is None:
            raise ValueError('No HPLC data')

        # this arcane string of pandas commands is the equivalent of pivot_wider from tidyverse
        # from https://medium.com/@durgaswaroop/reshaping-pandas-dataframes-melt-and-unmelt-9f57518c7738;.'/
        hplc = self.hplc.pivot(
                index = ['mL', 'Sample', 'Channel', 'Time'],
                columns = ['Normalization']
            )['Value'].reset_index()
        hplc = hplc.groupby(['Sample', 'Channel']).apply(lambda x: normalizer(x, norm_range, strict))
        hplc = hplc.melt(
            id_vars = ['mL', 'Sample', 'Channel', 'Time'],
            value_vars = ['Signal', 'Normalized'],
            var_name = 'Normalization',
            value_name = 'Value'
        )
        self.hplc = hplc

    def renormalize_fplc(self, norm_range, strict):
        if self.fplc is None:
            raise ValueError('No FPLC data')

        fplc = self.fplc.pivot(
                index = ['mL', 'CV', 'Fraction', 'Channel', 'Sample'],
                columns = ['Normalization']
            )['Value'].reset_index()
        fplc = fplc.groupby(['Sample', 'Channel']).apply(lambda x: normalizer(x, norm_range, strict))
        fplc = fplc.melt(
            id_vars = ['mL', 'CV', 'Channel', 'Fraction', 'Sample'],
            value_vars = ['Signal', 'Normalized'],
            var_name = 'Normalization',
            value_name = 'Value'
        )
        self.fplc = fplc

    def reduce_hplc(self, num_points):
        # reduce the number of points in the hplc trace to num_points per sample/channel/norm

        def reduction_factor(df, num_ponts):
            total_points = df.shape[0]
            reduction_factor = floor(total_points/num_points)
            return df[::reduction_factor]

        try:
            self.hplc = self.hplc.groupby(['Channel', 'Sample', 'Normalization']).apply(lambda x: reduction_factor(x, num_points))
        except AttributeError:
            return

def concat_experiments(exp_list):
        hplcs = []
        fplcs = []

        for exp in [x for x in exp_list if x.hplc is not None]:
            hplc = exp.hplc
            hplc['Sample'] = f'{exp.id}: ' + hplc['Sample'].astype(str)
            hplcs.append(hplc)

        for exp in [x for x in exp_list if x.fplc is not None]:
            fplc = exp.fplc
            fplc['Sample'] = exp.id
            fplcs.append(fplc)

        concat_exp = Experiment('concat')
        try:
            concat_exp.hplc = pd.concat(hplcs)
        except ValueError:
            pass

        try:
            concat_exp.fplc = pd.concat(fplcs)
        except ValueError:
            pass
        
        return concat_exp