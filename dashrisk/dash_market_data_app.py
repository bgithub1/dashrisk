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
from dashrisk import quantmod as qm


import pandas as pd
import base64
import datetime
import io 
import pandas_datareader.data as pdr

# Step 1: Define the app 
app = dash.Dash('Dash Market Data',external_stylesheets=[dbc.themes.BOOTSTRAP])
# Step 2: add custom css
app.css.append_css({'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})


# Step 3: Define some often used variables
TIME_COLUMN='Date'
DEFAULT_PAGE_SIZE = 100 # number of rows to show

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
  **This Dash app implements the following features in Dash:**  
  1) Chaining a dash_core_components.Graph element to button clicks from a dash_table.DataTable element;  
  2) Using pandas_datareader to fetch daily stock data;  
  3) Using dash_core_components.Store to cash pandas DataFrames so that those DataFrames can be the source of multiple dash_core_components components;  
  4) Using the dash_core_components.Upload component as an alternate source of data to populate the pandas DataFrame of market data;  
  5) Rendering dynamic pandas DataFrames, whose columns can change as you change read different csv files using Upload.  
'''

button_style={
    'width': '49.5%',
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
              html.H3("Dash Market Data Examples"),
              dcc.Markdown(header_markdown)
              ],
              style={'margin': '5px'}
        ),
        html.Div([
               html.Span(
                    dcc.Input(id='stock_entered', type='text', value='XLK'),
                    className='dcc_tab',
                    style=button_style
                ),
               html.Span(
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(['Drag and Drop or ',html.A('Select Files')]),
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                    className='dcc_tab',
                    style=button_style,                         
                ),
            ],
        ),      
        dcc.Graph(id='my-graph'),
        html.Div([html.H3("Data Table - Click Next or Previous buttons below to move graph")]),        
        html.Div([DT_DEFAULT],id='dt'),
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
        Input(component_id='stock_entered', component_property='n_submit'),
        Input('upload-data', 'contents'),
    ],
    [
        State(component_id='stock_entered', component_property='value'),
        State(component_id='stock_entered', component_property='n_submit_timestamp'),
    ]
)
def update_memory(n_submit,contents,stock_entered_data,n_submit_timestamp):
    dt_now = datetime.datetime.utcnow().timestamp()
    dt_submit = (datetime.datetime.strptime(n_submit_timestamp,'%Y-%m-%dT%H:%M:%S.%fZ') if n_submit_timestamp is not None else datetime.datetime(1970,1,1)).timestamp()
    dt_diff = dt_now - dt_submit
    print(dt_submit,dt_now,dt_diff)
    if contents is not None and dt_diff > .7:
        print('getting data from upload')
        df = parse_contents(contents)
    else:
        print(f'getting {str(stock_entered_data)}')
        sym = stock_entered_data    #
        df = get_df(sym)
    return df.to_dict("rows")


# Step 6.2: update html DataTable
@app.callback(
    Output('dt', 'children'), 
    [
        Input(component_id='df_memory', component_property='data'),
    ]
)
def update_table(df_memory_dict):
    df = pd.DataFrame(df_memory_dict)
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
        filtering=False, #'fe',
        content_style='grow',
        n_fixed_rows=1,
        style_table={'maxHeight':'400','overflowX': 'scroll'}
    )
    return dt

# Step 6.3: update graph
@app.callback(
    Output('my-graph', 'figure'), 
    [
        Input(component_id='df_memory', component_property='data'),
        Input(component_id='table', component_property='pagination_settings'),
    ]
)
def update_graph(df_memory_dict,pagination_settings):
    df = pd.DataFrame(df_memory_dict)
    page_size = pagination_settings['page_size']
    cur_page = pagination_settings['current_page']
    beg_row = cur_page * page_size
    end_row = beg_row + page_size
    df = df[beg_row:end_row]
    df2 = df.copy()
    cols = df2.columns.values
    rename_dict = {c:c[0].upper()+c[1:] for c in cols}
    df2 = df2.rename(columns=rename_dict)
    df2.index = df2.Date
    ch = qm.Chart(df2)
    fig = ch.to_figure(width=1100)
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

def create_candlestick_chart(df):
    dates = df[TIME_COLUMN].as_matrix().reshape(-1)
    trace = go.Candlestick(x=df[TIME_COLUMN].as_matrix().reshape(-1),
                           open=df.open.as_matrix().reshape(-1),
                           high=df.high.as_matrix().reshape(-1),
                           low=df.low.as_matrix().reshape(-1),
                           close=df.close.as_matrix().reshape(-1))
    data = [trace]    
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
    return df


if __name__ == '__main__':
    app.run_server(port=8400)
