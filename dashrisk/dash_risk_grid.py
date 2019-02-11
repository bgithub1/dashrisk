'''
Created on Feb 10, 2019

@author: bperlman1
'''
import dash
from dash.dependencies import Input, Output, State

import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import datetime
import plotly.graph_objs as go

from dashrisk import var_models as varm
from dashrisk import option_models as opmod
import base64
import pytz
import io 
from dashrisk.dash_grid import GridTable

# Step 3: Define some often used variables
TIME_COLUMN='Date'
DEFAULT_PAGE_SIZE = 100 # number of rows to show
DEFAULT_TIMEZONE = 'US/Eastern'


# Step 4.2 define some helpfule css
button_style={
    'line-height': '40px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
    'background-color':'#ffffcc',
    'vertical-align':'middle',
}

select_file_style={
    'line-height': '40px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
    'background-color':'#42e2f4',
    'vertical-align':'middle',
}

buttons_grid_style = {'display': 'grid',
  'grid-template-columns': '49.5% 49.5%',
  'grid-gap': '1px'
}

grid_style = {'display': 'grid',
  'grid-template-columns': '98.5%',
  'grid-gap': '10px'
}


from dashrisk import dash_grid as dg


app = dash.Dash()


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


def format_df(df_in,non_value_cols):
    df = df_in.copy()
#     non_value_cols = ['symbol','position','underlying']
    value_columns = [c for c in df.columns.values if c not in non_value_cols]
    for c in value_columns:
        try:
            df[c] = df[c].round(3)
        except:
            pass
    all_cols = non_value_cols + value_columns 
    df = df[all_cols]
    return df
    



#********
DEFAULT_PORTFOLIO_NAME=  'test_portfolio2.csv'             
DF_NO_POSITION = pd.read_csv(DEFAULT_PORTFOLIO_NAME)

dt = dg.GridTable('dt','Risk Profile').html
dt_pos = dg.GridTable('dt_pos','Original Position').html
dt_greeks_full = dg.GridTable('dt_greeks_full','Greeks Full').html
dt_greeks_by_underlying = dg.GridTable('dt_greeks_by_underlying','Greeks By Underlying').html

# my_graph = dg.GridGraph('my-graph','Var By Underlying',['no_position'],[0],'Underlying','Value at Risk').html



         
app.layout = html.Div([
        html.Div([
              html.H1("LiveRisk Analysis")],
        ),
        html.Div([
               html.Span(
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(['CLICK to select a portfolio csv'],id='select_div'),
                        # Allow multiple files to be uploaded
                        multiple=False,
                    ),
                    style=select_file_style
                ),
               html.Span(
                    html.Div([DEFAULT_PORTFOLIO_NAME],id='portfolio_name'),
                    style=select_file_style
                ),
               html.Span(
                    html.Div(['Portfolio 1/99 VaR = 0'],id='pvar_div'),
                    style=button_style
                ),
               html.Span(
                    html.Div(['S&P500 Equivilant Position = 0'],id='sp_eq_div'),
                    style=button_style
                ),
            ],
        style=buttons_grid_style),      
        html.Div([html.H2("Var Profile")]),       
        dcc.Graph(id='my-graph',style={'background-color':'#f5f5f0'}),
        # datatable grid
        html.Div([html.H2("Risk Tables")]),       
        html.Div(
            html.Div([
                dt, dt_pos, dt_greeks_full,dt_greeks_by_underlying,#my_graph
                ], 
#                 className='item1',style=dg.grid_style
                className='item1',style=grid_style
            ),
            id='risk_tables'
        ),
        dcc.Store(id='var_dict'),        
        # Hidden div inside the app that stores the intermediate value
        html.Div(id='intermediate_value', style={'display': 'none'}),
    ]
)

#********
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
        return DEFAULT_PORTFOLIO_NAME
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
    df_var_all = var_dict['df_underlying_positions']
    sp_dollar_equiv = var_dict['sp_dollar_equiv'] 
    
    # do greeks
    df_positions_all = var_dict['df_positions_all']
    df_atm_price = var_dict['df_atm_price']
    df_atm_price = df_atm_price.rename(columns={'close':'price'})
    df_std = var_dict['df_std']
    model_per_underlying_dict = {u:opmod.BsModel for u in df_atm_price.underlying}
    greeks_dict = opmod.get_df_greeks(df_positions_all, df_atm_price, model_per_underlying_dict)
    df_greeks = greeks_dict['df_greeks']
    # merge var and greeks
    df_risk_all = df_greeks.merge(df_positions_all[['symbol','position_var']],how='inner',on='symbol')
    df_risk_all = df_risk_all.drop(['option_price'],axis=1)
    print(f'End computing VaR {datetime.datetime.now()}')
    return {'df_std':df_std.to_dict('rows'),'df_risk_all':df_risk_all.to_dict('rows'),'port_var':port_var,'sp_dollar_equiv':sp_dollar_equiv}



# Step 6.3: update graph
@app.callback(
    Output('my-graph', 'figure'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def update_graph(data):
    df = pd.DataFrame(data['df_risk_all'])    
    x_vals=df.underlying.as_matrix().reshape(-1)
    y_vals=df.position_var.as_matrix().reshape(-1)
        

    fig = go.Figure(data = [go.Bar(
                x=x_vals,
                y=y_vals
        )],
        layout= go.Layout(plot_bgcolor='#f5f5f0')
    )
    
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


@app.callback(
    Output('risk_tables', 'children'), 
    [
        Input(component_id='var_dict', component_property='data'),
    ]
)
def update_risk_tables(data):
    # all positions
    df_risk_by_symbol = pd.DataFrame(data['df_risk_all'])
    risk_agg_cols = [c for c in df_risk_by_symbol.columns.values if c not in ['symbol','position']]
    df_risk_by_symbol = format_df(df_risk_by_symbol,['symbol','underlying','position'])
    # all by underlying
    df_risk_by_underlying = df_risk_by_symbol[risk_agg_cols].groupby('underlying',as_index=False).sum()
    df_risk_by_underlying = format_df(df_risk_by_underlying,['underlying'])
    # get and format DataFrames
    
    # create GridTable's
    dt_risk_by_symbol = dg.GridTable('dt_risk_by_symbol','Value at Risk and Greeks by Symbol',df_risk_by_symbol).html
    dt_risk_by_underlying = dg.GridTable('dt_risk_by_underlying','Value at Risk and Greeks by Underlying',df_risk_by_underlying).html
    
    # create return Div
    ret = html.Div([
        dt_risk_by_symbol,dt_risk_by_underlying
        ], 
        className='item1',style=grid_style
    )
    return ret
    



if __name__ == '__main__':
    app.run_server(port=8400)
