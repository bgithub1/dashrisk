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
from dashrisk import dash_grid_2 as dg2
from dashrisk import risk_tables as rt
import argparse as ap        

USE_POSTGRES=True
DEFAULT_PORTFOLIO_NAME=  'spdr_stocks.csv'             
# DEFAULT_PORTFOLIO_NAME=  'test_portfolio.csv'             
DF_NO_POSITION = pd.read_csv(DEFAULT_PORTFOLIO_NAME)


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
        
        df = pd.DataFrame(dict_df)
        return rt.update_risk_data(df, self.use_postgres, 
                self.dburl, self.databasename, self.username, self.password, 
                self.schema_name, self.yahoo_daily_table)
        

    def position_grid_table(self,up_span):
        columns_to_display=['symbol','position']
        editable_cols = ['position']
        gts_input = up_span.output_tuple
        pos_gridtable = dg2.GridTable('portfolio', 'Portfolio Table',gts_input,editable_columns=editable_cols,columns_to_display=columns_to_display)
        return pos_gridtable
    
#     def risk_tables(self,gts1):
#         # Step 1: create dcc.Store for risk info
#         risk_tables_store = dg2.DccStore('port_storage', gts1.output_content_tuple, self.create_risk_tables)
    
    def create_risk_components(self,risk_tables_store):
        # Step 2: define the columns in the order you want to show them
        risk_info_cols = ['symbol','underlying','position']
        risk_value_cols = ['position_var','delta','gamma','vega','theta','rho']
        risk_cols = risk_info_cols + risk_value_cols
        # data that you get from the DccStore component is a dictionary that contains a list of json
        #  the "tranformer" function below creates a DataFrame out of that json
        #  Pass this function to the constructor of GridTable via the input_transformer argument
        def _rbs_trans(risk_type,rounding_cols):
            def _ret(data):
                if data is None or risk_type not in data:
                    return None
                df = pd.DataFrame(data[risk_type] ) 
                for c in rounding_cols:
                    df[c] = df[c].round(4)   
                return df
            return _ret
        
        # Step 3: create GridTables for risk components
        var_by_symbol = dg2.GridTable('var_by_symbol', 'Position Var By Symbol',
                risk_tables_store.output_content_tuple,
                editable_columns=['position'],
                columns_to_display=['symbol','position','position_var'],
                input_transformer=_rbs_trans('df_var',['position_var']))
        risk_by_symbol = dg2.GridTable('risk_by_symbol', 'Risk By Symbol',
                risk_tables_store.output_content_tuple,
                editable_columns=[],
                columns_to_display=risk_cols,
                input_transformer=_rbs_trans('df_risk_all',risk_value_cols))
        risk_by_underlying = dg2.GridTable('df_risk_by_underlying', 'Risk By Underlying',
                risk_tables_store.output_content_tuple,
                editable_columns=[],
                columns_to_display=[c for c in risk_cols if c not in ['symbol','position']],
                input_transformer=_rbs_trans('df_risk_by_underlying',risk_value_cols))
        
        # return dict of components and whole risk grid
        risk_grid =  dg2.create_grid([risk_by_symbol,risk_by_underlying,risk_tables_store])
        return {'risk_grid':risk_grid,'risk_by_symbol':risk_by_symbol,
                'risk_by_underlying':risk_by_underlying,
                'var_by_symbol':var_by_symbol,
                'risk_tables_store':risk_tables_store}
    
    def create_app(self):
        # Step 1: create a span with a file upload button and a div  for the filename 
        up_span = dg2.CsvUploadSpan('upload-data')
        file_upload_div = up_span.up_div
        

#         # Step 2: create Portfolio grid table
#         gts1 = self.position_grid_table(up_span)
#         
#         # Step 3: create reactive graph of position dollars
#         grs1 = dg2.GridGraph('graph1', 'Position Dollars',gts1.output_content_tuple,df_x_column='symbol')
# 
#         # Step 4 create position grid
#         position_grid =  dg2.create_grid([gts1,grs1])
#         position_components = [gts1,grs1]
# 
#         # Step 5: create a storage component to store dataframes in the browser's DOM
# 
#         # Step 6: create risk by instrument grid
#         risk_grid_dict  = self.risk_tables(gts1)
        
        # Step 2: create position_by_symbol GridTable
        position_by_symbol = self.position_grid_table(up_span)

        # Step 3: create dcc.Store of all DataFrames (in json format) that will be used as inputs to various GridTables and GridGraphs
        risk_tables_store = dg2.DccStore('port_storage', position_by_symbol.output_content_tuple, self.create_risk_tables)
        
        # Step 3: create GridTable Dash components to display risk, correlation and symbol info (like atm_price, std and highs/lows)
        risk_grid_dict  = self.create_risk_components(risk_tables_store)
        
        #      3.2 var_by_symbol_graph
        def _transform_var_graph(data):
            if data is None or 'df_var' not in data:
                return None
            return pd.DataFrame(data['df_var'])
        var_by_symbol_graph = dg2.GridGraph('graph1', 'Var Dollars by Symbol',
                risk_tables_store.output_content_tuple,df_x_column='symbol',df_y_column='position_var',
                input_transformer=_transform_var_graph)

        # Step 4 create position grid 
        position_grid =  dg2.create_grid([position_by_symbol,var_by_symbol_graph])

        # Step 5: create title for page
        title_div = html.Div([html.H2(self.page_title)],
                     style={'background-color':'#2a3f5f','border':'1px solid #C8D4E3','border-radius': '3px'}
        )
                
        # Step 6: create the app layout         
        app = dash.Dash()
        app.layout = html.Div([title_div,file_upload_div,position_grid,risk_grid_dict['risk_grid']])
    
        # Step 7: create the call backs using all Dash components that we created above
        position_components = [position_by_symbol,var_by_symbol_graph]
        risk_by_keys = [k for k in risk_grid_dict.keys() if 'risk_by' in k]
        risk_components = [risk_grid_dict['risk_tables_store']] + [risk_grid_dict[r] for r in risk_by_keys]
        all_components = up_span.upload_components + position_components + risk_components
        [c.callback(app) for c in all_components]
        
        # Step 10: run server
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
    