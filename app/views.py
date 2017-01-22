from collections import OrderedDict

import numpy as np

from bokeh.plotting import Figure
from bokeh.models import HoverTool, ColumnDataSource, FixedTicker
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.embed import components
from bokeh.resources import INLINE
from bokeh.util.string import encode_utf8
from bokeh.palettes import viridis
from bokeh.models.mappers import CategoricalColorMapper, LinearColorMapper

import flask
from flask import render_template

from mendeleevapp import app, __version__

from datautils import get_data


PLOT_WIDTH = 1150
PLOT_HEIGHT = 800
HOVER_TOOLTIPS = [
    ("symbol", "@symbol"),
    ("name", "@name"),
    ("atomic number", "@atomic_number"),
    ("electronic configuration", "@electronic_configuration"),
    ("block", "@block"),
    ("group", "@name_group"),
    ("series", "@name_series"),
]


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
               'id', 'index', 'molcas_gv_color',
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


def get_color_mapper(column, df, palette='Viridis256'):
    '''
    Return a color mapper instace for a given category or continuous
    properties

    Args:
        column :  str
            name of the color that should be color mapped
        df : pandas.DataFrame
            data frame
    '''

    cmaps = {
        'block': 'Set1_4',
        'period': 'Dark2_7',
        'name_series': 'Spectral10',
        'group_name': viridis(18),
        'is_radioactive': 'Set1_3',
        'is_monoisotopic': 'Set1_3',
    }

    if column in cmaps.keys():
        factors = list(df[column].unique())
        ccm = CategoricalColorMapper(palette=cmaps[column], factors=factors)
    elif column == 'value':
        ccm = LinearColorMapper(palette=palette, low=df[column].min(),
                                high=df[column].max(), nan_color='#ffffff')
    else:
        ccm = None

    return ccm


def periodic_plot(cds, title='Periodic Table', width=PLOT_WIDTH,
                  height=PLOT_HEIGHT, cmap='viridis',
                  showfblock=True, long_version=False,
                  color_mapper=None):
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

    if color_mapper is None:
        color_dict = '#1F77B4'
    else:
        color_dict = {'field': 'value', 'transform': color_mapper}

    fig.rect("x", "y", 0.9, 0.9, source=cds, fill_alpha=0.6,
             fill_color=color_dict, line_color=color_dict)

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

    fig.text(x="x", y="y_prop", text='value_str',
             text_font_size="7pt", **text_props)

    fig.grid.grid_line_color = None

    hover = HoverTool(tooltips=HOVER_TOOLTIPS)

    fig.add_tools(hover)

    return fig


def set_property(colname, colorby, df):
    'Set the column `property with formatted values` from `colname`'

    mask = df[colname].notnull()
    df.loc[mask, 'y_prop'] = df.loc[mask, 'y'] + 0.35

    if colorby == 'property':
        df.loc[:, 'value'] = df.loc[:, colname].copy()
    else:
        df.loc[:, 'value'] = df.loc[:, colorby].copy()

    df.loc[:, 'value_str'] = ''
    if df[colname].dtype == np.float64:
        df.loc[mask, 'value_str'] = df.loc[mask, colname].apply('{:>.4f}'.format)
    else:
        df.loc[mask, 'value_str'] = df.loc[mask, colname].astype(str)

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

    sel_col = args.get('prop', 'atomic_weight')
    colorby = args.get('colorby', 'name_series')
    palette = args.get('palette', 'Viridis256')

    data = get_data()
    properties = get_property_names(data)
    categories = get_category_names()
    categories['property'] = 'Property'
    categories = OrderedDict(sorted(categories.items(), key=lambda x: x[0]))
    palettes = {k: k.rstrip('256') for k in
                ['Viridis256', 'Inferno256', 'Magma256', 'Plasma256']}

    # create new columns to display the chosen property
    data = set_property(sel_col, colorby, data)

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    if colorby == 'property':
        cmapper = get_color_mapper('value', data, palette=palette)
    else:
        cmapper = get_color_mapper(colorby, data)

    fig = periodic_plot(ColumnDataSource(data), title='Periodic Table',
                        width=PLOT_WIDTH, height=PLOT_HEIGHT,
                        color_mapper=cmapper)

    script, div = components(fig)

    html = render_template(
        'index.html',
        plot_script=script,
        plot_div=div,
        properties=properties,
        categories=categories,
        palettes=palettes,
        propselected=sel_col,
        catselected=colorby,
        palselected=palette,
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
    categ = args.get('categ', 'name_series')

    data = get_data()
    properties = get_property_names(data)
    categories = get_category_names()

    fig = Figure(title='{} vs {}'.format(properties[xattr], properties[yattr]),
                 plot_width=PLOT_WIDTH,
                 plot_height=PLOT_HEIGHT,
                 tools='box_zoom,pan,resize,save,reset',
                 toolbar_location='above',
                 toolbar_sticky=False,
                 )

    fig.xaxis.axis_label = properties[xattr]
    fig.yaxis.axis_label = properties[yattr]

    ccm = get_color_mapper(categ, data)

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

    hover = HoverTool(tooltips=HOVER_TOOLTIPS)

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
        ('atomic_weight', 'Atomic weight'),
        ('en_pauling', 'Electronegativity'),
        ('electron_affinity', 'Electron affinity'),
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


@app.route('/info/')
def info():

    html = render_template('info.html', version=__version__)

    return encode_utf8(html)
