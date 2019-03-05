'''
Created on Feb 10, 2019

@author: bperlman1
'''
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output,State
import pandas as pd
import dash_table
import plotly.graph_objs as go
import numpy as np
import argparse as ap
import datetime,base64,io,pytz

DEFAULT_TIMEZONE = 'US/Eastern'

#**************************************************************************************************


grid_style = {'display': 'grid',
  'grid-template-columns': '49.9% 49.9%',
  'grid-gap': '10px'
}


chart_style = {'margin-right':'auto' ,'margin-left':'auto' ,'height': '98%','width':'98%'}

#**************************************************************************************************

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

#**************************************************************************************************

def format_df(df_in,non_value_cols):
    df = df_in.copy()
    value_columns = [c for c in df.columns.values if c not in non_value_cols]
    for c in value_columns:
        try:
            df[c] = df[c].round(3)
        except:
            pass
    all_cols = non_value_cols + value_columns 
    df = df[all_cols]
    return df

#**************************************************************************************************

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

#**************************************************************************************************
class GridItem():
    def __init__(self,child,html_id=None):
        self.child = child
        self.html_id = html_id
    @property
    def html(self):
        if self.html_id is not None:
            return html.Div(children=self.child,className='grid-item',id=self.html_id)
        else:
            return html.Div(children=self.child,className='grid-item')
#**************************************************************************************************

class GridTable():
    def __init__(self,html_id,title,
                 input_content_tuple=None,
                 df_in=None):
#         self.theapp = theapp
        self.html_id = html_id
        self.title = title
        self.input_content_tuple = input_content_tuple
        self.dt_html = self.create_dt_html(df_in=df_in)
        
    def create_dt_div(self,df_in=None):
        dt = dash_table.DataTable(
            pagination_settings={
                'current_page': 0,
                'page_size': 100
            },
            pagination_mode='fe',
            sorting='fe',
            filtering=False, # 'fe',
            content_style='grow',
            style_cell_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ] + [
                {
                    'if': {'column_id': c},
                    'textAlign': 'left'
                } for c in ['symbol', 'underlying']
            ],
            
            style_as_list_view=True,
            n_fixed_rows=1,
            style_table={'maxHeight':'450','overflowX': 'scroll'}    
        )
        if df_in is None:
            df = pd.DataFrame({'no_data':[]})
        else:
            df = df_in.copy()
        dt.data=df.to_dict("rows")
        dt.columns=[{"name": i, "id": i} for i in df.columns]                    
        return [
                html.H4(self.title,style={'height':'3px'}),
                dt
            ]
    
    def create_dt_html(self,df_in=None):         
        dt_html = html.Div(self.create_dt_div(df_in=df_in),
            id=self.html_id,
            style={'margin-right':'auto' ,'margin-left':'auto' ,'height': '98%','width':'98%'}
        )
        return dt_html
        
    @property
    def html(self):
        return self.dt_html
        

    def callback(self,theapp):
        @theapp.callback(
            # outputs
            Output(self.html_id,'children'),
            [Input(component_id=self.input_content_tuple[0], component_property=self.input_content_tuple[1])]
        )
        def output_callback(dict_df):
            if dict_df is None:
                return None
#             df = parse_contents(dict_df)
            df = pd.DataFrame(dict_df)
            dt_div = self.create_dt_div(df)
            return dt_div
            
        return output_callback

#**************************************************************************************************

def charts(x_vals,y_vals,chart_title,x_title,y_title):
    fig = go.Figure(data = [go.Bar(
                x=x_vals,
                y=y_vals
        )])
    fig['layout'] = {
                'title':chart_title,
                'xaxis':{
                    'title':x_title
                },
                'yaxis':{
                     'title':y_title
                }
            }

    return fig


class GridGraph():
    def __init__(self,html_id,title,
                 input_content_tuple=None,
                 df_x_column=None,
                 df_y_column=None,
                 x_title=None,
                 y_title=None,
                 figure=None,
                 df_in=None):
        self.html_id = html_id
        self.input_content_tuple = input_content_tuple
        self.df_x_column = df_x_column
        self.df_y_column = df_y_column
        self.title = title
        self.x_title = 'x_title' if x_title is None else x_title
        self.y_title = 'y_title' if y_title is None else y_title
        x_vals = []
        y_vals = []
        if df_in is not None:
            x_vals,y_vals = self.get_x_y_values(df_in)
        f = charts(x_vals,y_vals,title,x_title,y_title) if figure is None else figure
        gr = dcc.Graph(
                id=html_id,
                figure=f,               
                )
        self.gr_html = html.Div(gr,className='item1')         
    @property
    def html(self):
        return self.gr_html        

    def get_x_y_values(self,df):
        if self.df_x_column is None:
            x_vals = list(df.index)
        else:
            x_vals=df[self.df_x_column].as_matrix().reshape(-1)    
        if self.df_y_column is None:
            y_vals = df.iloc[:,0].as_matrix().reshape(-1)
        else:
            y_vals=df[self.df_y_column].as_matrix().reshape(-1)
        return (x_vals,y_vals)
        
    def callback(self,theapp):
        @theapp.callback(
            Output(self.html_id,'figure'), 
            [Input(component_id=self.input_content_tuple[0], component_property=self.input_content_tuple[1])],
        )
        def update_graph(dict_df):
            x_vals = []
            y_vals = []
            if dict_df is not None:
                df = pd.DataFrame(dict_df)
                x_vals,y_vals = self.get_x_y_values(df)                 
            fig = go.Figure(data = [go.Bar(
                        x=x_vals,
                        y=y_vals
                )],
                layout= go.Layout(title = self.title,plot_bgcolor='#f5f5f0'),
            )
            return fig
        

def create_grid(component_array,num_columns=2):
    gs = grid_style.copy()
#     if num_columns>2:
#         gs = grid_style_3
    percents = [str(round(100/num_columns-.006,1))+'%' for _ in range(num_columns)]
    perc_string = " ".join(percents)
    gs['grid-template-columns'] = perc_string
    g =  html.Div([GridItem(c).html if type(c)==str else c.html for c in component_array], className='item1',style=gs)
    return g

class ReactiveDiv():
    def __init__(self,html_id,input_tuple):
        self.html_id = html_id
        self.input_tuple = input_tuple
        self.div = html.Div([],id=self.html_id)
    @property
    def html(self):
        return self.div        
    
    def callback(self,theapp):
        @theapp.callback(
            Output(self.html_id,'children'),
            [Input(self.input_tuple[0],self.input_tuple[1])]
        )
        def update_div(input):
            return input        
        return update_div

class CsvUploadButton():
#     def __init__(self,output_list,button_id=None,display_text=None,style=None):
    def __init__(self,button_id,display_text=None,style=None):
#         self.output_list = output_list
        st = select_file_style if style is None else style
        self.button_id = button_id
        self.html_id = button_id
        self.output_tuple = (f'{self.button_id}_df','data')
        disp_txt = 'CLICK to select a portfolio csv' if display_text is None else display_text
        dc = dcc.Upload(
                id=self.button_id,
                children=html.Div([disp_txt]),
                # Allow multiple files to be uploaded
                multiple=False,
            )
        self.dc = dc
        self.store = dcc.Store(id=f'{self.button_id}_df')
    @property
    def html(self):
        return html.Div([self.dc,self.store])       
    
    def callback(self,theapp):
        @theapp.callback(
            Output(f'{self.button_id}_df','data'), 
            [
                Input(self.button_id, 'contents'),
            ]
        )
        def  update_filename(contents):
            if contents is None:
                return None
            dict_df = parse_contents(contents).to_dict('rows')
            return dict_df
        return update_filename

def create_span(html_content,html_id=None,style=None):
    if html_id is not None:
        htmldiv = html.Div(html_content,id=html_id)
    else:
        htmldiv = html.Div(html_content)
    s = html.Span(
            htmldiv,
           style=select_file_style if style is None else style
        )
    return s

class CsvUploadSpan():
    def __init__(self,html_id):    
        csv_ub = CsvUploadButton(html_id)
        csv_name = ReactiveDiv(f'{html_id}_csv_name',(csv_ub.html_id,'filename'))
        self.upload_components = [csv_ub,csv_name]
        self.up_div  = html.Div([create_span(c.html) for c in self.upload_components],style=buttons_grid_style)
        self.output_tuple = csv_ub.output_tuple
    @property
    def html(self):
        return self.up_div
#**************************************************************************************************



def toy_example(host,port):
    # create the Dash app
    gts_input = ('upload-data_df','data')
    # create 2 data tables
    gts = [GridTable(f't{i}',f'table {i}',gts_input) for i in range(2)]
    
    # create 2 graphs
    grs = [GridGraph(f'g{i}', f'g{i}',gts_input) for i in range(2)]
    
    # combine tables and graph into main grid
    main_grid =  create_grid(gts + grs)

    # create title for page
    title_div = html.H2('dash_grid example')

    # create a span with a file upload button and a div  for the filename 
    csv_ub = CsvUploadButton('upload-data')
    csv_name = ReactiveDiv('csv_name',('upload-data','filename'))
    
    ub_span = create_span(csv_ub.html,'ub')                       
    fn_span =  create_span(csv_name.html,'fn')
    
    file_upload_div = html.Div([ub_span,fn_span],style=buttons_grid_style)
    
    # create the app layout         
    app = dash.Dash()
    app.layout = html.Div([title_div,file_upload_div,main_grid])

    # create the call backs
    csv_ub.callback(app)
    csv_name.callback(app)
    [gt.callback(app) for gt in gts]
    [gr.callback(app) for gr in grs]
    
    # run server
    
    app.run_server(host=host,port=port)
    
    
if __name__ == '__main__':
    parser = ap.ArgumentParser()
    parser.add_argument('--host',type=str,
                        help='host url to run server.  Default=127.0.0.1',
                        default='127.0.0.1')   
    parser.add_argument('--port',type=str,
                        help='port to run server.  Default=8400',
                        default='8400')   
    args = parser.parse_args()
    host = args.host
    port = args.port
    toy_example(host,port)
