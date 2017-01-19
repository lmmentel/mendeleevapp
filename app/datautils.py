
import os
import pandas as pd


def add_plot_columns(elements):
    '''
    Add columns needed for the creating the plots

    Args:
        elements: pd.DataFrame
    '''

    mask = elements['group_id'].notnull()

    elements.loc[mask, 'x'] = elements.loc[mask, 'group_id'].astype(int)
    elements.loc[:, 'y'] = elements.loc[:, 'period'].astype(int)

    elements.loc[mask, 'group_name'] = elements.loc[mask, 'group_id'].astype(int).astype(str)
    elements.loc[~mask, 'group_name'] = 'f block'

    for period in [6, 7]:
        mask = (elements['block'] == 'f') & (elements['period'] == period)
        elements.loc[mask, 'x'] = elements.loc[mask, 'atomic_number'] -\
                                        elements.loc[mask, 'atomic_number'].min() + 3
        elements.loc[mask, 'y'] = elements.loc[mask, 'period'] + 2.5

    # additional columns for positioning of the text

    elements.loc[:, 'y_symbol'] = elements['y'] - 0.05
    elements.loc[:, 'y_anumber'] = elements['y'] - 0.3
    elements.loc[:, 'y_name'] = elements['y'] + 0.18

    return elements


def get_data():

    fpkl = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                        "neutral.pkl")

    return pd.read_pickle(fpkl)
