'''
Created on Feb 2, 2019

Show an example of using Dash (https://dash.plot.ly/) to retrieve and display 
market data
@author: Bill Perlman
'''

import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.graph_objs as go

import pandas as pd
import base64
import datetime
import pytz
import io 
import pandas_datareader.data as pdr
from dashrisk import var_models as varm

# Step 1: Define the app 
app = dash.Dash('Dash Risk',external_stylesheets=[dbc.themes.BOOTSTRAP])
# Step 2: add custom css
app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})


# Step 3: Define some often used variables
TIME_COLUMN='Date'
DEFAULT_PAGE_SIZE = 100 # number of rows to show
DEFAULT_TIMEZONE = 'US/Eastern'

# Step 4: Define a default dash DataTable, that will be used as a "placeholder"
#         html element, and quickly replaced when we retrieve market data
DT_DEFAULT = dash_table.DataTable(
    id='table',
    pagination_settings={
        'current_page': 0,
        'page_size': DEFAULT_PAGE_SIZE
    },
    pagination_mode='fe',
    sorting='fe',
    filtering='fe',
)

# Step 5: !!!! DEFINE THE app.layout !!!!!!
#         The layout property of the app object defines all of the html that you will
#            display in your app
header_markdown = '''

'''

button_style={
    'width': '99.5%',
    'height': '40px',
    'lineHeight': '40px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
    'margin': '2px'
}


app.layout = html.Div(
    [
        html.Div([
              html.H3("Load a csv file containing your portfolio")],
              style={'margin': '5px'}
        ),
        html.Div([
               html.Span(
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(['',html.A('Select a Portfolio Csv File')]),
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                    className='dcc_tab',
                    style=button_style,                         
                ),
            ],
        ),      
        html.Div([html.H6("Risk Profile")]),        
        html.Div([DT_DEFAULT],id='dt'),
        html.Div([html.H6("Var Profile")]),       
        dcc.Graph(id='my-graph'),
        dcc.Store(id='df_memory'),        
        # Hidden div inside the app that stores the intermediate value
        html.Div(id='intermediate_value', style={'display': 'none'}),
    ], 
)

# Step 6:  Define all of your callbacks

# step 6.1 update memory after getting new data
@app.callback(
    Output('df_memory', 'data'), 
    [
        Input('upload-data', 'contents'),
    ],
)
def update_memory(contents):
    if contents is None:
        df = pd.read_csv('test_portfolio.csv')
    else:
        df = parse_contents(contents)
    vm = varm.VarModel(df)
    var_dict = vm.compute_var()
    port_var = var_dict['port_var']
    df_positions = var_dict['df_positions']
    sp_dollar_equiv = var_dict['sp_dollar_equiv']        
    return df_positions.to_dict("rows")


# Step 6.2: update html DataTable
@app.callback(
    Output('dt', 'children'), 
    [
        Input(component_id='df_memory', component_property='data'),
    ]
)
def update_table(df_memory_dict):
    df = pd.DataFrame(df_memory_dict)
    df = df[['symbol','position','position_var','unit_var','stdev','close']]

    dt = dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("rows"),
        pagination_settings={
            'current_page': 0,
            'page_size': DEFAULT_PAGE_SIZE
        },
        pagination_mode='fe',
        sorting='fe',
        filtering='fe',
        content_style='grow',
        n_fixed_rows=2,
        style_table={'maxHeight':'400','overflowX': 'scroll'}
    )
    return dt

# Step 6.3: update graph
@app.callback(
    Output('my-graph', 'figure'), 
    [
        Input(component_id='df_memory', component_property='data'),
    ]
)
# def update_graph(df_memory_dict,pagination_settings):
def update_graph(df_memory_dict):
    df = pd.DataFrame(df_memory_dict)    
    fig = go.Figure(data = [go.Bar(
                x=df.symbol.as_matrix().reshape(-1),
                y=df.position_var.as_matrix().reshape(-1)
        )])
    
    return fig
#     return create_dash_return(df)


# Step 7:  Define various helper methods

def get_df(symbol):
    '''
    get_df gets market data from some on-line source (usually yahoo), or, if that source
      fails, then attempts to find the data for the requested security from a few
      csv files that exist in the ./marketdata folder
    :param symbol:  like SPY, AAPL or XLK
    :returns pandas DataFrame with at least a close column
    '''
    try:
        dt_end = datetime.datetime.now()
        dt_beg = dt_end - datetime.timedelta(365*10)         
        df = pdr.DataReader(symbol, 'yahoo', dt_beg, dt_end)
    except Exception as e:
        try:                    
            df = pd.read_csv('./marketdata/%s.csv' %(symbol))
        except Exception as e2:
            print(str(e))
            print(str(e2))
            df = pd.read_csv('./marketdata/XLK.csv')
            
    if TIME_COLUMN in df.columns.values:
        df = df.sort_values(TIME_COLUMN)
    elif df.index.name.lower() == 'date':
        df[TIME_COLUMN] = df.index
    renamed_cols_dict = {s:s.lower() for s in df.columns.values}
    df = df.rename(columns=renamed_cols_dict)
    return df

def create_dash_return(df):
    '''
    Turn a pandas DataFrame into dictionary that the dash DataTable class accepts
    :param df:
    '''
    return {
        'data': [{
            'x': df.index,
            'y': df.close
        }],
        'layout': {'margin': {'l': 40, 'r': 0, 't': 20, 'b': 30}}
    }

def parse_contents(contents):
    '''
    app.layout contains a dash_core_component object (dcc.Store(id='df_memory')), 
      that holds the last DataFrame that has been displayed. 
      This method turns the contents of that dash_core_component.Store object into
      a DataFrame.
      
    :param contents: the contents of dash_core_component.Store with id = 'df_memory'
    :returns pandas DataFrame of those contents
    '''
    c = contents.split(",")[1]
    c_decoded = base64.b64decode(c)
    c_sio = io.StringIO(c_decoded.decode('utf-8'))
    df = pd.read_csv(c_sio)
    # create a date column if there is not one, and there is a timestamp column instead
    cols = df.columns.values
    cols_lower = [c.lower() for c in cols] 
    if 'date' not in cols_lower and 'timestamp' in cols_lower:
        date_col_index = cols_lower.index('timestamp')
        # make date column
        def _extract_dt(t):
            y = int(t[0:4])
            mon = int(t[5:7])
            day = int(t[8:10])
            hour = int(t[11:13])
            minute = int(t[14:16])
            return datetime.datetime(y,mon,day,hour,minute,tzinfo=pytz.timezone(DEFAULT_TIMEZONE))
        # create date
        df['date'] = df.iloc[:,date_col_index].apply(_extract_dt)
    return df


if __name__ == '__main__':
    app.run_server(port=8400)
