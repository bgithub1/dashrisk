'''
Created on Feb 10, 2019

@author: bperlman1
'''
import sys
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')

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
from dashrisk import dash_grid as dg
from dashrisk import progress_component as pgcm
from dashrisk import build_history as bh
from dashrisk import portfolio_hedge as ph
import argparse as ap
import numpy as np


# Step 3: Define some often used variables
TIME_COLUMN='Date'
DEFAULT_PAGE_SIZE = 100 # number of rows to show
DEFAULT_TIMEZONE = 'US/Eastern'





# Step 4.2 define some helpful css
button_style={
    'line-height': '40px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
    'background-color':'#fffff0',
    'vertical-align':'middle',
}

select_file_style={
    'line-height': '40px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
#     'background-color':'#42e2f4',
    'background-color':'#b0e2f4',
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



#********
DEFAULT_PORTFOLIO_NAME=  'hi_volume_stocks.csv'             
# DEFAULT_PORTFOLIO_NAME=  'test_portfolio.csv'             
DF_NO_POSITION = pd.read_csv(DEFAULT_PORTFOLIO_NAME)

dt = dg.GridTable('dt','Risk Profile').html
dt_pos = dg.GridTable('dt_pos','Original Position').html
dt_greeks_full = dg.GridTable('dt_greeks_full','Greeks Full').html
dt_greeks_by_underlying = dg.GridTable('dt_greeks_by_underlying','Greeks By Underlying').html
dt_hedge_ratios = dg.GridTable('dt_hedge_ratios','Best Hedge Portfolio using Sector SPDR ETFs').html

# my_graph = dg.GridGraph('my-graph','Var By Underlying',['no_position'],[0],'Underlying','Value at Risk').html
loader_div = html.Div([],className='loader')
my_display_component_div_to_show =  html.Div(['waiting for historical data ... (this can take up to 1 second per underlying)',loader_div])
my_display_component_div_to_hide = []


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

def update_risk_data(contents,USE_POSTGRES=False,
        dburl=None,databasename=None,username=None,
        password=None,schema_name=None,yahoo_daily_table=None):
    print('entering update_memory')
    if contents is None:
        print('contents is None')
        df = DF_NO_POSITION.copy()
    else:
        df = parse_contents(contents)
    print(f'Start computing VaR {datetime.datetime.now()}')
    if USE_POSTGRES:
#         hb = bh.HistoryBuilder(dburl,databasename,username,password,schema_name,yahoo_daily_table)
        hb = bh.HistoryBuilder(dburl=dburl, databasename=databasename, 
                               username=username, password=password, 
                               schema_name=schema_name, yahoo_daily_table=yahoo_daily_table, )
        history_fetcher = varm.PostgresFetcher(hb)
    else:
        history_fetcher = varm.YahooFetcher()
    vm = varm.VarModel(df,history_fetcher)
    var_dict = vm.compute_var()
    port_var = var_dict['port_var']
#     df_var_all = var_dict['df_underlying_positions']
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
    
    # do hedge values
    # first create a history of this portfolio as on price per day
    symbol_list = sorted(df_atm_price.underlying)
    series_weights = df_greeks[['underlying','delta']].groupby('underlying').sum()['delta']
    weights = [series_weights[c] for c in symbol_list] 

    df_port_prices = vm.get_history_matrix()
    hist_matrix = df_port_prices[symbol_list].as_matrix()
    # now create random weights
    port_price_history = hist_matrix @ weights
    df_port = pd.DataFrame({'date':df_port_prices.date,'port':port_price_history})
    
    # next get price history of sector spdrs
    spdr_symbols = [ 'XLB', 'XLC', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY']
    df_sector_spdr = pd.DataFrame({'symbol':spdr_symbols,'position':np.repeat(1, len(spdr_symbols))})
    vm_hedge = varm.VarModel(df_sector_spdr,history_fetcher)
    df_hedge_prices = vm_hedge.get_history_matrix()
    
    # next, merge history of "portfolio value" with history of spdr's.
    #  MAKE SURE THAT THE FIRST COLUMN IS THE PORTFOLIO HISTORY, AND NAME THAT COLUMN "port"
    df_hedge_prices = df_hedge_prices.merge(df_port,how='inner',on='date')
    df_hedge_prices = df_hedge_prices[['port'] + spdr_symbols]

    port_hedger = ph.MinVarianceHedge(df_hedge_prices, 'port')
    port_hedger.run_model()
    hedge_values = [port_hedger.hedge_ratio_dict[s] * port_hedger.last_day_ratio for s in spdr_symbols]
    df_hedge_ratios = pd.DataFrame({'symbol':spdr_symbols,'hedge':hedge_values})
    n = datetime.datetime.now()
    print(f'End computing VaR {n}')
    yyyymmddhhmmssmmmmmm = '%04d%02d%02d%02d%02d%02d%06d' %(n.year,n.month,n.day,n.hour,n.minute,n.second,n.microsecond)
    return {'yyyymmddhhmmssmmmmmm':str(yyyymmddhhmmssmmmmmm),'df_std':df_std.to_dict('rows'),'df_risk_all':df_risk_all.to_dict('rows'),
            'port_var':port_var,'sp_dollar_equiv':sp_dollar_equiv,'df_hedge_ratios':df_hedge_ratios.to_dict('rows')}

if __name__ == '__main__':
    parser = ap.ArgumentParser()
    parser.add_argument('--ip',type=str,default='127.0.0.1',help='ip address of server')
    parser.add_argument('--port',type=int,default=8400,help='port of server')
    parser.add_argument('--initial_portolio',type=str,default=DEFAULT_PORTFOLIO_NAME,help='initial portfolio to Load')
    parser.add_argument('--use_postgres',type=bool,default=False,help='set to True if using Postgres db for history data')
    parser.add_argument('--dburl',type=str,
                    help='database url (None will be localhost)',
                    nargs='?')
    parser.add_argument('--databasename',type=str,
                    help='databasename (None will be maindb)',
                    nargs='?')
    parser.add_argument('--username',type=str,
                    help='username (None will be postgres)',
                    nargs='?')
    parser.add_argument('--password',type=str,
                    help='password (None will be blank)',
                    nargs='?')
    parser.add_argument('--schema_name',type=str,
                    help='schema name for table (None will be test_schema)',
                    nargs='?')
    parser.add_argument('--yahoo_daily_table',type=str,
                    help='table name for table (None will be yahoo_daily)',
                    nargs='?')
    args = parser.parse_args()
    
    ip = args.ip
    port = args.port 
    #None,args.use_postgres,
    default_risk_data = update_risk_data(
        None, USE_POSTGRES=args.use_postgres, dburl=args.dburl, 
        databasename=args.databasename, username=args.username, 
        password=args.password, schema_name=args.schema_name, 
        yahoo_daily_table=args.yahoo_daily_table)
    app = dash.Dash(__name__)
    app.secret_key = 'development key'
         
    app.layout = html.Div([
            html.Div([html.Div([],style={'display': 'none'})],id='spinner'),
            html.Div([html.H1("LiveRisk Analysis")],
                     style={'background-color':'#2a3f5f','border':'1px solid #C8D4E3','border-radius': '3px'}
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
    #                     html.Div([DEFAULT_PORTFOLIO_NAME],id='portfolio_name'),
                        html.Div([],id='portfolio_name'),
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
            html.Div(
                [html.H2("Var Profile")],
                style={'background-color':'#eefaf7','border':'1px solid #C8D4E3','border-radius': '3px'}
            ),       
            dcc.Graph(id='my-graph',style={'background-color':'#f5f5f0'}),
            # datatable grid
            html.Div(
                [html.H2("Risk Tables")],
                style={'background-color':'#eefaf7','border':'1px solid #C8D4E3','border-radius': '3px'}
            ),       
            html.Div(
                html.Div([
                    dt, dt_pos, dt_greeks_full,dt_greeks_by_underlying,dt_hedge_ratios], 
                    className='item1',style=grid_style
                ),
                id='risk_tables'
            ),
            html.Div(
                [html.H2("Sector Spdr Best Hedge")],
                style={'background-color':'#eefaf7','border':'1px solid #C8D4E3','border-radius': '3px'}
            ),       
            dcc.Store(id='var_dict'),        
            # Hidden div inside the app that stores the intermediate value
            html.Div(id='intermediate_value', style={'display': 'none'}),
        ]
    )
    
    def process_risk_data(contents):
        if contents is None:
            return default_risk_data
        return update_risk_data(
                        contents, USE_POSTGRES=args.use_postgres, dburl=args.dburl, 
                        databasename=args.databasename, username=args.username, 
                        password=args.password, schema_name=args.schema_name, 
                        yahoo_daily_table=args.yahoo_daily_table)
        
    prog = pgcm.ProgressComponent(app, process_risk_data, 'spinner', my_display_component_div_to_show, my_display_component_div_to_hide)
    prog.callbacks
    
    @app.callback(
        [
            Output('portfolio_name', 'children'),
            Output(pgcm.ProgressComponent.INPUT_ID,'data'),
            ], 
        [
            Input('upload-data', 'filename'),
        ],
        [
            State('upload-data','contents')
        ]
    )
    def  update_filename(filename,contents):
        print('entering update_filename')
        if filename is None or len(filename)<1:
            r =  f'portfolio loaded: {DEFAULT_PORTFOLIO_NAME}'
        else:
            r =  f'portfolio loaded: {filename}'
        return [r],contents
    
    @app.callback(
        Output('var_dict', 'data'),
        [Input(pgcm.ProgressComponent.OUTPUT_ID,'data')]
    )
    def display_results(output_data):
        print(str(output_data))
        return output_data
    
    
      
      
      
    @app.callback(
        Output('pvar_div', 'children'), 
        [
            Input(component_id='var_dict', component_property='data'),
        ]
    )
    def  update_pvar_div(data):
        print('entering update_pvar_div')
        if data is None:
            port_var = 0.0
        else:
            port_var = round(float(data['port_var']),3)
        return f"Portfolio VaR = {port_var}"
       
       
    @app.callback(
        Output('sp_eq_div', 'children'), 
        [
            Input('pvar_div', 'children'),
        ],
        [
            State(component_id='var_dict', component_property='data'),
        ]    
    )
    def  update_sp_eq_div(children,data):
        print('entering update_sp_eq_div')
        if data is None:
            sp_dollar_equiv = 0.0
        else:
            sp_dollar_equiv = round(float(data['sp_dollar_equiv']),3)
        return f"S&P500 Equivilant Position = {sp_dollar_equiv}"
       
       
       
    @app.callback(
        Output('my-graph', 'figure'), 
        [
            Input('sp_eq_div', 'children'),
        ],
        [
            State(component_id='var_dict', component_property='data'),
            State('my-graph', 'figure')
        ]    
    )
    def update_graph(children,data,figure):
        print('entering update_graph')
        x_vals = []
        y_vals = []
        if data is not None:
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
        Output('risk_tables', 'children'),    
        [
            Input('sp_eq_div', 'children'),
        ],
        [
            State(component_id='var_dict', component_property='data'),
            State('risk_tables', 'children')
        ]
    )
    def update_risk_tables(fig,data,children):
        print('entering update_risk_tables')
        # all positions
        if data is None:
            return html.Div([], 
                className='item1',style=grid_style
            )
            
        # get and format DataFrames
        df_risk_by_symbol = pd.DataFrame(data['df_risk_all'])
        risk_agg_cols = [c for c in df_risk_by_symbol.columns.values if c not in ['symbol','position']]
        df_risk_by_symbol = format_df(df_risk_by_symbol,['symbol','underlying','position'])
        # all by underlying
        df_risk_by_underlying = df_risk_by_symbol[risk_agg_cols].groupby('underlying',as_index=False).sum()
        df_risk_by_underlying = format_df(df_risk_by_underlying,['underlying'])
        df_hedge_ratios = format_df(pd.DataFrame(data['df_hedge_ratios']),['symbol'])
            
        # create GridTable's
        dt_risk_by_symbol = dg.GridTable('dt_risk_by_symbol','Value at Risk and Greeks by Symbol',df_risk_by_symbol).html
        dt_risk_by_underlying = dg.GridTable('dt_risk_by_underlying','Value at Risk and Greeks by Underlying',df_risk_by_underlying).html
        dt_hedge_ratios = dg.GridTable('dt_hedge_ratios','Best Hedge Portfolio using Sector SPDR ETFs',df_hedge_ratios).html
        # create return Div
        ret = html.Div([
            dt_risk_by_symbol,dt_risk_by_underlying,dt_hedge_ratios
            ], 
            className='item1',style=grid_style
        )
        return ret
         
    
        


    app.run_server(host=ip,port=port)
