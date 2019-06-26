'''
Created on Mar 5, 2019

@author: bperlman1
'''
import sys
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')

import pandas as pd
import dash
import dash_html_components as html
# from dashrisk import dash_grid_2 as dg2
from dashrisk import dgrid as dg2
from dashrisk import risk_tables as rt
import argparse as ap        

USE_POSTGRES=True
DEFAULT_PORTFOLIO_NAME=  'spdr_stocks.csv'             
# DEFAULT_PORTFOLIO_NAME=  'test_portfolio.csv'             
DF_NO_POSITION = pd.read_csv(DEFAULT_PORTFOLIO_NAME)

STYLE_TITLE={
    'line-height': '20px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
    'background-color':'#21618C',
    'color':'#FFFFF9',
    'vertical-align':'middle',
} 


STYLE_UPGRID = STYLE_TITLE.copy()
STYLE_UPGRID['background-color'] = '#EAEDED'
STYLE_UPGRID['line-height'] = '10px'
STYLE_UPGRID['color'] = '#21618C'

table_head_div = lambda s:html.Div([s],style={'text-align': 'center','color':'#22aaff'})

class DashRisk():
    def __init__(self,
                 page_title,
                 host,port,
                 use_postgres=False,
                 dburl=None,databasename=None,
                 username=None,
                 password=None,
                 schema_name=None,
                 yahoo_daily_table=None):
        self.page_title = page_title
        self.host = host
        self.port = port
        self.use_postgres = use_postgres
        self.dburl = dburl
        self.databasename=databasename
        self.username=username
        self.password=password
        self.schema_name=schema_name
        self.yahoo_daily_table=yahoo_daily_table

    def create_risk_tables(self,dict_df):
        print ('entering create_risk_tables')
        if dict_df is None or len(dict_df)<=0:
            return {}
#             df = DF_NO_POSITION.copy()
        else:
            df = pd.DataFrame(dict_df)
        return rt.update_risk_data(df, self.use_postgres, 
                self.dburl, self.databasename, self.username, self.password, 
                self.schema_name, self.yahoo_daily_table)
        
    def create_risk_components(self,risk_tables_store,rounding=2):
        '''
        Create dash_grid components (which are dash_core_components that are wrapped with callbacks)
        :param risk_tables_store: an instance of the class DccStore, which is used to hold all risk DataFrames 
                 that get created in calls to the module var_models
        :param rounding: the rounding that you want for your risk values (like position_var, detla, gamma, etc)
        '''
        # Step 2: *************** define the columns in the order you want to show them *******************
        risk_by_symbol_info_cols = ['symbol','position']
        risk_by_underlying_info_cols = ['underlying']
        risk_value_cols = ['position_var','delta','gamma','vega','theta','rho']
        risk_by_symbol_cols = risk_by_symbol_info_cols + risk_value_cols
        risk_by_underlying_cols = risk_by_underlying_info_cols + risk_value_cols
        # data that you get from the DccStore component is a dictionary that contains a list of json
        #  the "tranformer" function below creates a DataFrame out of that json
        #  Pass this function to the constructor of GridTable via the input_transformer argument
        def _rbs_trans(risk_type,rounding_cols):
            def _ret(data):
                if data is None or risk_type not in data:
                    return None
                df = pd.DataFrame(data[risk_type] ) 
                for c in rounding_cols:
                    df[c] = df[c].round(rounding)   
                return df
            return _ret
        
        # Step 3: ****************** create GridTables for risk components *****************************        
        risk_by_symbol_header = table_head_div('Risk By Symbol')
        risk_by_symbol = dg2.GridTable('risk_by_symbol', risk_by_symbol_header,
                risk_tables_store.output_content_tuple,
                editable_columns=[],
                columns_to_display=risk_by_symbol_cols,
                input_transformer=_rbs_trans('df_risk_all',risk_value_cols))

        risk_by_underlying_header = table_head_div('Risk By Underlying')
        risk_by_underlying = dg2.GridTable('df_risk_by_underlying', risk_by_underlying_header,
                risk_tables_store.output_content_tuple,
                editable_columns=[],
                columns_to_display=risk_by_underlying_cols,
                input_transformer=_rbs_trans('df_risk_by_underlying',risk_value_cols))

        atm_info_header = table_head_div('Atm, Std and N-day High-Low')
        atm_info = dg2.GridTable('df_atm_info', atm_info_header,
                risk_tables_store.output_content_tuple,
#                 editable_columns=[],
                columns_to_display=['underlying','close','stdev','d1','d5','d10','d15','d20'],
                input_transformer=_rbs_trans('df_atm_info',['close','stdev','d1','d5','d10','d15','d20']))

        def _corr_trans(risk_type):
            def _ret(data):
                if data is None or risk_type not in data:
                    return None
                df = pd.DataFrame(data[risk_type] ) 
                rounding_cols = [c for c in df.columns.values if c not in ['underlying','symbol','*underlying','*symbol']]
                for c in rounding_cols:
                    df[c] = df[c].round(rounding)   
                return df
            return _ret
        corr_returns_header = table_head_div('Correlations (Returns)')
        corr_returns = dg2.GridTable('df_corr',corr_returns_header,
                risk_tables_store.output_content_tuple,
                input_transformer=_corr_trans('df_corr'))
        corr_prices_header = table_head_div('Correlations (Prices)')
        corr_prices = dg2.GridTable('df_corr_price', corr_prices_header,
                risk_tables_store.output_content_tuple,
                input_transformer=_corr_trans('df_corr_price'))
        
        # Step 4: ******************* return dict of components and whole risk grid *******************
        risk_grid =  dg2.create_grid([risk_by_symbol,risk_by_underlying,risk_tables_store])
        info_grid = dg2.create_grid([corr_returns,corr_prices,atm_info],num_columns=1)
        
        return {
            'risk_grid':risk_grid,
            'info_grid':info_grid,
            'callback_components':[risk_by_symbol,risk_by_underlying,corr_returns,corr_prices,atm_info]
        }
    
    def create_app(self):
        # Step 1: *********************** create title for page *****************************
        title_div = html.Div([html.H3('Portfolio Risk Analysis'),html.H4(' (See Quick Start at page bottom for help)')],
                     style=STYLE_TITLE
        )

        # Step 2: ****************create a grid with a file upload button and a div  for the filename *****************
        up_grid = dg2.CsvUploadGrid('upload-data',
                        display_text="CLICK TO UPLOAD A LOCAL CSV",
                        file_name_transformer=lambda fn: f'YOU ARE VIEWING: {DEFAULT_PORTFOLIO_NAME if fn is None else fn}' )
        
        
        # Step 3: ***************** create position_by_symbol GridTable ******************
        position_by_symbol = dg2.GridTable('portfolio', 
                                   table_head_div('Portfolio Table (position sizes are editable)'), 
                                   up_grid.output_tuple,
                editable_columns=['position'],columns_to_display=['symbol','position'],
                input_transformer = lambda dict_df: DF_NO_POSITION if dict_df is None else pd.DataFrame(dict_df))
        
        # Step 4: ****** create dcc.Store of all DataFrames (in json format) that will be used as inputs to 
        #                  various GridTables and GridGraphs  *********************************
        risk_tables_store = dg2.DccStore('port_storage', position_by_symbol.output_content_tuple, self.create_risk_tables)
        
        # Step 5: ************** create divs of risk aggregates *************************
        pvar_div = dg2.ReactiveDiv('pvar_div', risk_tables_store.output_content_tuple, 
                        lambda data:f"Portfolio 1/99 VaR = {0 if 'port_var' not in data else round(data['port_var'],2)}")
        sp_eq_div = dg2.ReactiveDiv('sp_eq_div', risk_tables_store.output_content_tuple, 
                        lambda data:f"S&P500 Equivilant Position = {0 if 'sp_dollar_equiv' not in data else round(data['sp_dollar_equiv'],2)}")
        delta_div = dg2.ReactiveDiv('delta_div', risk_tables_store.output_content_tuple, 
                        lambda data:f"delta = {0 if 'delta' not in data else round(data['delta'],2)}")
        gamma_div = dg2.ReactiveDiv('gamma_div', risk_tables_store.output_content_tuple, 
                        lambda data:f"gamma = {0 if 'delta' not in data else round(data['gamma'],2)}")
        vega_div = dg2.ReactiveDiv('vega_div', risk_tables_store.output_content_tuple, 
                        lambda data:f"vega = {0 if 'delta' not in data else round(data['vega'],2)}")
        theta_div = dg2.ReactiveDiv('theta_div', risk_tables_store.output_content_tuple, 
                        lambda data:f"theta = {0 if 'delta' not in data else round(data['theta'],2)}")
        
        risk_agg1_grid = dg2.create_grid([pvar_div,sp_eq_div])
        risk_agg2_grid = dg2.create_grid([delta_div,gamma_div,vega_div,theta_div],num_columns=4)
        
        # Step 6: ********* create GridTable Dash components to display risk, 
        #                correlation and symbol info (like atm_price, std and highs/lows) ************************
        risk_grid_dict  = self.create_risk_components(risk_tables_store)
        
        #      6.2 var_by_symbol_graph
        def _transform_var_graph(data):
            if data is None or 'df_var' not in data:
                return None
            return pd.DataFrame(data['df_var'])
        var_by_symbol_graph = dg2.GridGraph('graph1', 'Var Dollars by Symbol',
                risk_tables_store.output_content_tuple,df_x_column='symbol',df_y_columns=['position_var'],
                input_transformer=_transform_var_graph)

        # Step 7 ********************** create position grid ***********************************
        position_grid =  dg2.create_grid([position_by_symbol,var_by_symbol_graph])

   
#         # create status line
#         input_tuples = [
#             [position_by_symbol.output_content_tuple,'STATUS: creating risk tables ...'],
#             [var_by_symbol_graph.output_content_tuple,'STATUS: All Loaded']
#         ]
#         st = dg2.StatusDiv('load_status', input_tuples)
#         status_grid = dg2.create_grid([st],num_columns=1)
        
        # Step 8: ************************* create example file download ********************************
        dropdown_labels = ['Simple Stock Example','SPDR ETF Options example','Mixed with Commodities Example']
        dropdown_values = ['example_simple_stocks.csv','spdr_stocks.csv','example_commodities.csv']
        file_download_component = dg2.FileDownLoadDiv('example_download', dropdown_labels, 
                            dropdown_values, 
                            'SELECT AN EXAMPLE CSV to Download',
                            'CLICK TO DOWNLOAD EXAMPLE CSV')
        fd_div = file_download_component.html
            
        # Step 9: ************************ create instruction markdowns ********************************
        mark_help_main = dg2.MarkDownDiv('general_help',
                open('./markdown_quick_start.txt','r').read())
        mark_sym_col = dg2.MarkDownDiv('symbol_help',
                open('./markdown_symbol_column.txt','r').read())
        mark_pos_col = dg2.MarkDownDiv('position_help',
                open('./markdown_position_column.txt','r').read())
        help_main_grid = dg2.create_grid([mark_help_main],num_columns=1)
        help_column_explanation_grid = dg2.create_grid([mark_sym_col,mark_pos_col])

        # Step 10: ************************* create the app layout ***************************************
        app = dash.Dash()
        app.secret_key = 'development key'
        
        app.layout = html.Div([title_div,up_grid.grid,risk_agg1_grid,risk_agg2_grid,position_grid,
                               risk_grid_dict['risk_grid'],risk_grid_dict['info_grid'],
                               help_main_grid,fd_div,help_column_explanation_grid])
    
        
        # Step 11: ********************* define flask route for file download component *******************
        file_download_component.route(app)

        # Step 12: *************** create the call backs using all Dash components that we created above *******************
        risk_agg_components  = [pvar_div,sp_eq_div,delta_div,gamma_div,vega_div,theta_div]
        position_components = [position_by_symbol,var_by_symbol_graph,file_download_component]
        risk_components = [risk_tables_store] + risk_grid_dict['callback_components']
        all_components = up_grid.upload_components + risk_agg_components + position_components + risk_components
        [c.callback(app) for c in all_components]

        
        # Step 13: ************************* run server **************************************
        app.run_server(host=self.host,port=self.port)
        
    

if __name__ == '__main__':
    parser = ap.ArgumentParser()
    parser.add_argument('--page_title',type=str,default='LiveRisk Analysis',help='Title that displays on main page')
    parser.add_argument('--ip',type=str,default='127.0.0.1',help='ip address of server')
    parser.add_argument('--port',type=int,default=8500,help='port of server')
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
    

    dr = DashRisk(args.page_title,args.ip,args.port,
        use_postgres=args.use_postgres, dburl=args.dburl, 
        databasename=args.databasename, username=args.username, 
        password=args.password, schema_name=args.schema_name, 
        yahoo_daily_table=args.yahoo_daily_table)
    dr.create_app()
    