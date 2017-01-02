from collections import OrderedDict

import numpy as np
import pandas as pd

import matplotlib.colors as colors
import matplotlib.cm as cmx

from bokeh.plotting import Figure
from bokeh.models import HoverTool, ColumnDataSource, FixedTicker
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.palettes import Spectral6, viridis
from bokeh.models.mappers import CategoricalColorMapper

import flask
from flask import render_template

from mendeleev import get_table

from mendeleevapp import app

from datautils import get_data


PLOT_WIDTH = 1200
PLOT_HEIGHT = 800


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


def get_category_names():
    '''
    Return a dict with attribute names as keys and their printable names as
    values
    '''

    out = {'None': '---', 'block': 'Block', 'group_name': 'Group',
           'period': 'Period', 'name_series': 'Series',
           'is_radioactive': 'Radioactive', 'is_monoisotopic': 'Monoisotopic'}

    return OrderedDict(sorted(out.items(), key=lambda x: x[0]))


def get_property_names(data):

    propattrs = data.columns.values

    exclude = ['annotation', 'color', 'cpk_color', 'description',
               'electronic_configuration',
               'is_radioactive', 'is_monoisotopic',
               'id', 'index',
               'jmol_color', 'lattice_structure', 'name', 'symbol',
               'x', 'y', 'y_anumber', 'y_name', 'y_prop',
               'symbol_group', 'name_group', 'name_series', 'color_series',
               'block', 'group_id', 'period', 'series_id', 'property']

    attrs = list(set(propattrs) - set(exclude))

    properties = {p: p.replace('_', ' ').title() for p in attrs}

    for k, v in properties.items():
        if k.startswith('en_'):
            properties[k] = '{} Electronegativity'.format(k.replace('en_', '').title().replace('-', ' and '))

    return OrderedDict(sorted(properties.items(), key=lambda x: x[0]))


def get_cmap_names():
    'return colormap names'

    return ['viridis', 'inferno', 'magma', 'plasma'] +\
        sorted(m for m in cmx.datad if not m.endswith("_r"))


def periodic_plot(cds, title='Periodic Table', width=1200,
                  height=800, missing='#ffffff', cmap='viridis',
                  showfblock=True, long_version=False):
    '''
    Create the periodic plot

    Args:
      df : DataFrame
        Pandas DataFrame with the data on elements
      tile : str
        Title to appear above the periodic table
      colorby : str
        Name of the column containig the colors
      width : int
        Width of the figure in pixels
      height : int
        Height of the figure in pixels
      missing : str
        Hex code of the color to be used for the missing values
      cmap : str
        Colormap to use, see matplotlib colormaps
      long_version : bool
        Show the long version of the periodic table with the f block between
        the s and d blocks
      showfblock : bool
        Show the elements from the f block

    .. note::

        `property` attribute holds the current property to be displayed

    '''

    fig = Figure(title=title,
                 x_axis_location='above',
                 x_range=(0.5, 18.5),
                 y_range=(10.0, 0.5),
                 plot_width=width,
                 plot_height=height,
                 tools='box_zoom,pan,resize,save,reset',
                 toolbar_location='above',
                 toolbar_sticky=False,
                 )

    fig.rect("x", "y", 0.9, 0.9, color='color', source=cds, fill_alpha=0.6)

    # adjust the ticks and axis bounds
    fig.yaxis.bounds = (1, 7)
    fig.axis[1].ticker.num_minor_ticks = 0
    fig.axis[0].ticker = FixedTicker(ticks=list(range(1, 19)))

    text_props = {
        "source": cds,
        "angle": 0,
        "color": "black",
        "text_align": "center",
        "text_baseline": "middle"
    }

    fig.text(x="x", y="y_symbol", text="symbol",
             text_font_style="bold", text_font_size="15pt", **text_props)

    fig.text(x="x", y="y_anumber", text="atomic_number",
             text_font_size="9pt", **text_props)

    fig.text(x="x", y="y_name", text="name",
             text_font_size="7pt", **text_props)

    fig.text(x="x", y="y_prop", text='property',
             text_font_size="7pt", **text_props)

    fig.grid.grid_line_color = None

    hover = HoverTool(tooltips=[
        ("symbol", "@symbol"),
        ("name", "@name"),
        ("atomic number", "@atomic_number"),
        ("electronic configuration", "@electronic_configuration"),
    ])

    fig.add_tools(hover)

    return fig


def set_property(df, colname, decimals=4):
    'Set the column `property with formatted values` from `colname`'

    df.loc[df[colname].notnull(), 'y_prop'] = df.loc[df[colname].notnull(), 'y'] + 0.35
    df.loc[df[colname].notnull(), 'property'] = df.loc[df[colname].notnull(), colname]

    return df


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


def make_table(cds, properties):
    '''
    Create the table widget

    Args:
        csd : ColumnDataSource
            ColumnDataSource
        properties : dict
            Dictionary with attribute names as keys and printable
            names as values
    '''

    table_columns = []
    for attr, name in properties.items():
        table_columns.append(TableColumn(field=attr, title=name))

    table = DataTable(source=cds, columns=table_columns,
                      width=PLOT_WIDTH, height=PLOT_HEIGHT)

    return table


@app.route('/')
@app.route('/periodic/')
def index():
    'Create the periodic table plot'

    args = flask.request.args

    prop = args.get('prop', 'mass')
    colorby = args.get('colorby', 'series_id')
    cmap = args.get('cmap', 'viridis')

    data = get_data()
    properties = get_property_names(data)
    categories = get_category_names()
    categories['property'] = 'Property'
    categories = OrderedDict(sorted(categories.items(), key=lambda x: x[0]))
    colormaps = get_cmap_names()

    data = set_property(data, prop)
    data = set_colors(data, colorby, cmap)

    if data[prop].dtype == np.float64:
        data.loc[:, prop] = data[prop].round(decimals=4).astype(str)

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    fig = periodic_plot(ColumnDataSource(data), title='Periodic Table',
                        width=PLOT_WIDTH, height=PLOT_HEIGHT)

    script, div = components(fig)

    html = render_template(
        'index.html',
        plot_script=script,
        plot_div=div,
        properties=properties,
        categories=categories,
        colormaps=colormaps,
        propselected=prop,
        catselected=colorby,
        cmapselected=cmap,
        js_resources=js_resources,
        css_resources=css_resources,
    )

    return encode_utf8(html)


@app.route('/correlations/')
def correlation():
    'the scatter plot'

    args = flask.request.args

    xattr = args.get('x', 'atomic_number')
    yattr = args.get('y', 'covalent_radius_pyykko')
    categ = args.get('categ', 'period')

    data = get_data()
    properties = get_property_names(data)
    categories = get_category_names()

    if categ == 'None':
        pass
    elif categ == 'block':
        factors = list(data[categ].unique())
        ccm = CategoricalColorMapper(palette='Set1_4', factors=factors)
    elif categ == 'period':
        factors = list(data[categ].unique())
        ccm = CategoricalColorMapper(palette='Dark2_7', factors=factors)
    elif categ == 'name_series':
        factors = list(data[categ].unique())
        ccm = CategoricalColorMapper(palette='Spectral10', factors=factors)
    elif categ == 'group_name':
        factors = list(data[categ].unique())
        ccm = CategoricalColorMapper(palette=viridis(18), factors=factors)
    elif categ in ['is_radioactive', 'is_monoisotopic']:
        factors = list(data[categ].unique())
        ccm = CategoricalColorMapper(palette='Set1_3', factors=factors)

    fig = Figure(title='{} vs {}'.format(properties[xattr], properties[yattr]),
                 plot_width=PLOT_WIDTH,
                 plot_height=PLOT_HEIGHT,
                 tools='box_zoom,pan,resize,save,reset',
                 toolbar_location='above',
                 toolbar_sticky=False,
                 )

    fig.xaxis.axis_label = properties[xattr]
    fig.yaxis.axis_label = properties[yattr]

    if categ == 'None':
        legend = None
        color_dict = '#1F77B4'
    else:
        legend = categ
        color_dict = {'field': categ, 'transform': ccm}

    fig.circle(x=xattr, y=yattr, fill_alpha=0.7, size=10,
               source=ColumnDataSource(data=data),
               fill_color=color_dict,
               line_color=color_dict,
               legend=legend)

    if categ != 'None':
        fig.legend.location = (0, 0)
        fig.legend.plot = None
        fig.add_layout(fig.legend[0], 'right')

    hover = HoverTool(tooltips=[
        ("symbol", "@symbol"),
        ("name", "@name"),
        ("atomic number", "@atomic_number"),
        ("electronic configuration", "@electronic_configuration"),
    ])

    fig.add_tools(hover)

    script, div = components(fig)

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    html = render_template(
        'correlations.html',
        plot_script=script,
        plot_div=div,
        properties=properties,
        categories=categories,
        xselected=xattr,
        yselected=yattr,
        catselected=categ,
        js_resources=js_resources,
        css_resources=css_resources,
    )

    return encode_utf8(html)


@app.route('/data/')
def data():

    data = get_data()
    columns = OrderedDict([
        ('atomic_number', 'Atomic number'),
        ('symbol', 'Symbol'),
        ('name', 'Name'),
        ('mass', 'Mass'),
    ])

    table = make_table(ColumnDataSource(data), columns)

    script, div = components(table)

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    html = render_template(
        'data.html',
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
    )

    return encode_utf8(html)
