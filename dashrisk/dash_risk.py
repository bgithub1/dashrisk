'''
Created on Feb 2, 2019

Show an example of using Dash (https://dash.plot.ly/) to calculate Greeks 
  and VaR on a portfolio.  Also display the "S&P500 equivilant VaR" of the 
  portfolio.
  
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
from dashrisk import option_models as opmod



NO_POSITION = {
    'symbol':['no_position'],
    'underlying':['no_position'],
    'position':[0],
    'position_var':[0],
    'unit_var':[0],
    'stdev':[0],
    'close':[0],
}

DEFAULT_PORTFOLIO_NAME=  'test_portfolio2.csv'             
DF_NO_POSITION = pd.read_csv(DEFAULT_PORTFOLIO_NAME) #pd.DataFrame(NO_POSITION)

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
    filtering=False, # 'fe',
)

DT_DEFAULT_2 = dash_table.DataTable(
    id='table_2',
    pagination_settings={
        'current_page': 0,
        'page_size': DEFAULT_PAGE_SIZE
    },
    pagination_mode='fe',
    sorting='fe',
    filtering=False, # 'fe',
)

DT_DEFAULT_3 = dash_table.DataTable(
    id='table_3',
    pagination_settings={
        'current_page': 0,
        'page_size': DEFAULT_PAGE_SIZE
    },
    pagination_mode='fe',
    sorting='fe',
    filtering=False, # 'fe',
)
DT_DEFAULT_4 = dash_table.DataTable(
    id='table_4',
    pagination_settings={
        'current_page': 0,
        'page_size': DEFAULT_PAGE_SIZE
    },
    pagination_mode='fe',
    sorting='fe',
    filtering=False, # 'fe',
)



# Step 5: !!!! DEFINE THE app.layout !!!!!!
#         The layout property of the app object defines all of the html that you will
#            display in your app
header_markdown = '''

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

var_profile_style={
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
              html.H4("Position Risk Analysis")],
        ),
        html.Div([
               html.Span(
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(['',html.A('SELECT A PORTFOLIO CSV FILE')],id='select_div'),
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                    className='dcc_tab',
                    style=button_style,                         
                ),
               html.Span(
                    html.Div([DEFAULT_PORTFOLIO_NAME],id='portfolio_name'),
                    className='dcc_tab',
                    style=button_style,                         
                ),
            ],
        ),      
        html.Div([
               html.Span(
                    html.Div(['Portfolio 1/99 VaR = 0'],id='pvar_div'),
                    className='var_results_tab',
                    style=button_style,                         
                ),
               html.Span(
                    html.Div(['S&P500 Equivilant Position = 0'],id='sp_eq_div'),
                    className='var_results_tab',
                    style=button_style,                         
                ),
            ],
        ), 
        
        html.Div([html.H6("Risk Profile")]),        
        html.Div([DT_DEFAULT],id='dt',style={'margin-right':'auto' ,'margin-left':'auto' ,'height': '99.5%','width':'98%'}),
        html.Div([html.H6("Var Profile")]),       
        dcc.Graph(id='my-graph'),
        html.Div([html.H6("Original Position")]),        
        html.Div([DT_DEFAULT_2],id='dt_pos',style={'margin': '10px'}),
        html.Div([html.H6("Greeks Full")]),        
        html.Div([DT_DEFAULT_3],id='dt_greeks_full',style={'margin': '10px'}),
        html.Div([html.H6("Greeks By Underlying")]),        
        html.Div([DT_DEFAULT_4],id='dt_greeks_by_underlying',style={'margin': '10px'}),
        dcc.Store(id='var_dict'),        
        # Hidden div inside the app that stores the intermediate value
        html.Div(id='intermediate_value', style={'display': 'none'}),
        
    ],
    style = {'margin':'1px'} 
)

# Step 6:  Define all of your callbacks
# step 6. update file name
@app.callback(
    Output('portfolio_name', 'children'), 
    [
        Input('upload-data', 'filename'),
    ],
)
def  update_filename(filename):
    if filename is None or len(filename)<1:
        return 'no portoflio loaded'
    return f'portfolio loaded: {filename}'
    

# step 6.1 update memory after getting new data
@app.callback(
    Output('var_dict', 'data'), 
    [
        Input('upload-data', 'contents'),
    ],
)
def  update_memory(contents):
    if contents is None:
        print('contents is None')
#         return {'df_positions':DF_NO_POSITION.to_dict('rows'),'port_var':0,'sp_dollar_equiv':0}
        df = DF_NO_POSITION.copy()
    else:
        df = parse_contents(contents)
    print(f'Start computing VaR {datetime.datetime.now()}')
    vm = varm.VarModel(df)
    var_dict = vm.compute_var()
    port_var = var_dict['port_var']
    df_positions = var_dict['df_underlying_positions']
    sp_dollar_equiv = var_dict['sp_dollar_equiv'] 
    # do greeks
    df_portfolio = var_dict['df_positions_all']
    df_atm_price = var_dict['df_atm_price']
    df_atm_price = df_atm_price.rename(columns={'close':'price'})
    df_std = var_dict['df_std']
    model_per_underlying_dict = {u:opmod.BsModel for u in df_atm_price.underlying}
    greeks_dict = opmod.get_df_greeks(df_portfolio, df_atm_price, model_per_underlying_dict)
    df_greeks = greeks_dict['df_greeks']
    df_greeks_totals = greeks_dict['df_greeks_totals']
     
    print(f'End computing VaR {datetime.datetime.now()}')
#     return df_positions.to_dict("rows")
    return {'df_std':df_std.to_dict('rows'),'df_positions':df_positions.to_dict('rows'),'port_var':port_var,'sp_dollar_equiv':sp_dollar_equiv,'df_greeks':df_greeks.to_dict('rows'),'df_greeks_totals':df_greeks_totals.to_dict('rows')}



# Step 6.2: update html DataTable
@app.callback(
    Output('dt', 'children'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def update_table(data):
    df = pd.DataFrame(data['df_positions'])
    cols = ['underlying','position','position_var','unit_var','stdev','close']
    df = df[cols]
    cols_no_sym = [c for c in cols if c != 'underlying']
    for c in cols_no_sym:
        df[c] = df[c].round(3)
    dt = dash_table.DataTable(
        id='table',
        style_data={'whiteSpace': 'normal'},
        css=[{
            'selector': '.dash-cell div.dash-cell-value',
            'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
        }],
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("rows"),
        pagination_settings={
            'current_page': 0,
            'page_size': DEFAULT_PAGE_SIZE
        },
        pagination_mode='fe',
        sorting='fe',
        filtering=False, # 'fe',
        content_style='grow',
        n_fixed_rows=2,
        style_table={'maxHeight':'400','overflowX': 'scroll'}
    )
    return dt

# Step 6.3: update graph
@app.callback(
    Output('my-graph', 'figure'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def update_graph(data):
    df = pd.DataFrame(data['df_positions'])    
    x_vals=df.underlying.as_matrix().reshape(-1)
    y_vals=df.position_var.as_matrix().reshape(-1)
        

    fig = go.Figure(data = [go.Bar(
                x=x_vals,
                y=y_vals
        )])
    
    return fig


@app.callback(
    Output('pvar_div', 'children'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def  update_pvar_div(var_dict):
    port_var = round(float(var_dict['port_var']),3)
    return f"Portfolio VaR = {port_var}"


@app.callback(
    Output('sp_eq_div', 'children'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def  update_sp_eq_div(data):
    sp_dollar_equiv = round(float(data['sp_dollar_equiv']),3)
    return f"S&P500 Equivilant Position = {sp_dollar_equiv}"


#     return create_dash_return(df)


# Step 6.4: update html DataTable
@app.callback(
    Output('dt_pos', 'children'), 
    [
        Input('upload-data', 'contents'),
    ]
)
def update_orignal_positions(contents):
    if contents is None:
        df = DF_NO_POSITION.copy()
    else:
        df = parse_contents(contents)
    cols = ['symbol','position']
    df = df[cols]
    dt2 = dash_table.DataTable(
        id='table_2',
        style_data={'whiteSpace': 'normal'},
        css=[{
            'selector': '.dash-cell div.dash-cell-value',
            'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
        }],
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("rows"),
        pagination_settings={
            'current_page': 0,
            'page_size': DEFAULT_PAGE_SIZE
        },
        pagination_mode='fe',
        sorting='fe',
        filtering=False, # 'fe',
        content_style='grow',
        n_fixed_rows=1,
        style_table={'maxHeight':'400','overflowX': 'scroll'}
    )
    return dt2


# Step 6.5: update graph
@app.callback(
    Output('dt_greeks_full', 'children'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)


    
def update_greeks(var_dict):
    df = pd.DataFrame(var_dict['df_greeks']) 
    non_value_cols = ['symbol','position','underlying']
    value_columns = [c for c in df.columns.values if c not in non_value_cols]
    for c in value_columns:
        try:
            df[c] = df[c].round(3)
        except:
            pass
    all_cols = non_value_cols + value_columns 
    df = df[all_cols]
    dt3 = dash_table.DataTable(
        id='table_3',
        style_data={'whiteSpace': 'normal'},
        css=[{
            'selector': '.dash-cell div.dash-cell-value',
            'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
        }],
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("rows"),
        pagination_settings={
            'current_page': 0,
            'page_size': DEFAULT_PAGE_SIZE
        },
        pagination_mode='fe',
        sorting='fe',
        filtering=False, # 'fe',
        content_style='grow',
        n_fixed_rows=1,
        style_table={'maxHeight':'400','overflowX': 'scroll'}
    )
    return dt3       

# Step 6.6: update graph
@app.callback(
    Output('dt_greeks_by_underlying', 'children'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def update_greeks_by_underlying(var_dict):
    df = pd.DataFrame(var_dict['df_greeks_totals'])
    non_value_cols = ['underlying']
    value_columns = [c for c in df.columns.values if c not in non_value_cols]
    for c in value_columns:
        try:
            df[c] = df[c].round(3)
        except:
            pass
    all_cols = non_value_cols + value_columns 
    df = df[all_cols]
    dt4 = dash_table.DataTable(
        id='table_4',
        style_data={'whiteSpace': 'normal'},
        css=[{
            'selector': '.dash-cell div.dash-cell-value',
            'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
        }],
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("rows"),
        pagination_settings={
            'current_page': 0,
            'page_size': DEFAULT_PAGE_SIZE
        },
        pagination_mode='fe',
        sorting='fe',
        filtering=False, # 'fe',
        content_style='grow',
        n_fixed_rows=1,
        style_table={'maxHeight':'400','overflowX': 'scroll'}
    )
    return dt4        

# # Step 654 update Interval
# @app.callback(
#     Output('portfolio_name', 'children'), 
#     [
#         Input('interval-component', 'n_intervals'),
#     ]
# )
# def update_var_percent_done(n_intervals):
#     click_text = ''
#     if n_intervals > 0:
#         click_text = f'intervals={n_intervals}'
#          
#     return click_text


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
