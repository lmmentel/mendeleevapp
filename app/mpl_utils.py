
import matplotlib.colors as colors
import matplotlib.cm as cmx


def get_cmap_names():
    'return colormap names'

    return ['viridis', 'inferno', 'magma', 'plasma'] +\
        sorted(m for m in cmx.datad if not m.endswith("_r"))


def colormap_column(df, column, cmap='viridis', missing='#ffffff'):
    '''
    Return a new DataFrame with the same size (and index) as `df` with a column
    `cmap` containing HEX color mapping from `cmap` colormap.

    Args:
      df : DataFrmae
        Pandas DataFrame with the data
      column : str
        Name of the column to be color mapped
      cmap : str
        Name of the colormap, see matplotlib.org
      missing : str
        HEX color for the missing values (NaN or None)
    '''

    colormap = cmx.get_cmap(cmap)
    cnorm = colors.Normalize(vmin=df[column].min(), vmax=df[column].max())
    scalarmap = cmx.ScalarMappable(norm=cnorm, cmap=colormap)
    out = pd.DataFrame(index=df.index)
    mask = df[column].isnull()
    rgba = scalarmap.to_rgba(df[column])
    out.loc[:, 'cmap'] = [colors.rgb2hex(row) for row in rgba]
    out.loc[mask, 'cmap'] = missing

    return out


def set_colors(df, colorby, cmap):
    '''
    Create a `color` column in the `df` DataFrame with HEX color
    codes from `cmap` colormap
    '''

    if colorby == 'block':
        df['temp'] = df['block'].map(dict((b, i) for i, b in enumerate(df['block'].unique())))
        dfc = colormap_column(df, 'temp', cmap=cmap, missing='#ffffff')
        df['color'] = dfc['cmap']
        df['legend'] = df['block']
    elif colorby in ['period', 'group_id', 'series_id']:
        dfc = colormap_column(df, colorby, cmap=cmap, missing='#ffffff')
        df['color'] = dfc['cmap']
        if colorby == 'series_id':
            df['legend'] = df['name_series']
        elif colorby == 'group_id':
            df['legend'] = df['name_group']
        else:
            df['legend'] = df[colorby]
    elif colorby == 'property':
        dfc = colormap_column(df, 'property', cmap=cmap, missing='#ffffff')
        df['color'] = dfc['cmap']

    return df
