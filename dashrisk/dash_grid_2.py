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
import flask
from dashrisk.dash_grid import grid_style

DEFAULT_TIMEZONE = 'US/Eastern'

#**************************************************************************************************


grid_style = {'display': 'grid',
  'grid-template-columns': '49.9% 49.9%',
  'grid-gap': '1px',
  'border': '1px solid #000',
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

blue_button_style={
    'line-height': '40px',
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'textAlign': 'center',
    'background-color':'#A9D0F5',
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
                 df_in=None,
                 columns_to_display=None,
                 editable_columns=None,
                 input_transformer=None,
                 use_html_table=False):
        self.html_id = html_id
        self.title = title
        self.input_content_tuple =  input_content_tuple
        self.columns_to_display = columns_to_display
        self.editable_columns = [] if editable_columns is None else editable_columns
        self.datatable_id = f'{html_id}_datatable'
        self.output_content_tuple = (self.datatable_id,'data')
        self.input_transformer = input_transformer
        self.use_html_table = use_html_table
        if self.input_transformer is None:
            self.input_transformer = lambda dict_df: None if dict_df is None else pd.DataFrame(dict_df)
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
                    'textAlign': 'left',
                } for c in ['symbol', 'underlying']
            ],
            
            style_as_list_view=False,
#             n_fixed_rows=1,
            style_table={
                'maxHeight':'450','overflowX': 'scroll',
            } ,
            editable=True,
#             id=self.html_id + '_datatable'
            id=self.datatable_id
        )
        if df_in is None:
            df = pd.DataFrame({'no_data':[]})
        else:
            df = df_in.copy()
            if self.columns_to_display is not None:
                df = df[self.columns_to_display]                
        dt.data=df.to_dict("rows")
        dt.columns=[{"name": i, "id": i,'editable': True if i in self.editable_columns else False} for i in df.columns.values]                    
        return [
                html.H4(self.title,style={'height':'3px'}),
                dt
            ]
    
    def create_dt_html(self,df_in=None):         
        dt_html = html.Div(self.create_dt_div(df_in=df_in),
            id=self.html_id,
            style={'margin-right':'auto' ,'margin-left':'auto' ,'height': '98%','width':'98%','border':'thin solid'}
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
#             if dict_df is None:
#                 return None
            df = self.input_transformer(dict_df)
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


#**************************************************************************************************
class GridGraph():
    def __init__(self,html_id,title,
                 input_content_tuple=None,
                 df_x_column=None,
                 df_y_column=None,
                 x_title=None,
                 y_title=None,
                 figure=None,
                 df_in=None,
                 input_transformer=None):
        self.html_id = html_id
        self.input_content_tuple = input_content_tuple

        self.output_content_tuple = (self.html_id,'figure')        
        self.df_x_column = df_x_column
        self.df_y_column = df_y_column
        self.title = title
        self.x_title = 'x_title' if x_title is None else x_title
        self.y_title = 'y_title' if y_title is None else y_title
        x_vals = []
        y_vals = []
        if df_in is not None:
            x_vals,y_vals = self.get_x_y_values(df_in)
        
        self.input_transformer = input_transformer 
        if self.input_transformer is None:
            self.input_transformer = lambda dict_df: pd.DataFrame(dict_df)
            
        f = charts(x_vals,y_vals,title,x_title,y_title) if figure is None else figure
        gr = dcc.Graph(
                id=html_id,
                figure=f,               
                )
        self.gr_html = html.Div(
            gr,
            className='item1',
            style={'margin-right':'auto' ,'margin-left':'auto' ,'height': '98%','width':'98%','border':'thin solid'}
        ) 
    @property
    def html(self):
        return self.gr_html        

    def get_x_y_values(self,df):
        if df is None or len(df)<1:
            return ([],[])
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
        def update_graph(dict_df,*args):
            x_vals = []
            y_vals = []
            if dict_df is not None:
                df = self.input_transformer(dict_df)#pd.DataFrame(dict_df)
                x_vals,y_vals = self.get_x_y_values(df)                 
            fig = go.Figure(data = [go.Bar(
                        x=x_vals,
                        y=y_vals
                )],
                layout= go.Layout(title = self.title,plot_bgcolor='#f5f5f0'),
            )
            return fig
#**************************************************************************************************

#**************************************************************************************************
class DccStore():        
    def __init__(self,html_id,
                 input_content_tuple,
                 transformer_module):
        self.html_id = html_id
        self.input_content_tuple = input_content_tuple
        self.transformer_module = transformer_module
        self.dcc_store = dcc.Store(id=html_id)
        self.dcc_html = html.Div(self.dcc_store,style={"display": "none"})
        self.output_content_tuple = (self.html_id,'data')

    @property
    def html(self):
        return self.dcc_html        

    def callback(self,theapp):
        @theapp.callback(
            Output(self.html_id,'data'), 
            [Input(component_id=self.input_content_tuple[0], component_property=self.input_content_tuple[1])],
        )
        def update_store(input_data,*args):
            return self.transformer_module(input_data)
 #**************************************************************************************************
           


def create_grid(component_array,num_columns=2):
    gs = grid_style.copy()
#     if num_columns>2:
#         gs = grid_style_3
    percents = [str(round(100/num_columns-.006,1))+'%' for _ in range(num_columns)]
    perc_string = " ".join(percents)
    gs['grid-template-columns'] = perc_string
    g =  html.Div([GridItem(c).html if type(c)==str else c.html for c in component_array], style=gs)
    return g

#**************************************************************************************************
class ReactiveDiv():
    def __init__(self,html_id,input_tuple,
                 input_transformer=None,display=True,
                 style=None):
        self.html_id = html_id
        self.input_tuple = input_tuple
        s = button_style if style is None else style
        if display:
            self.div = html.Div([],id=self.html_id,style=s)
        else:
            self.div = html.Div([],id=self.html_id,style={'display':'none'})
        self.input_transformer = input_transformer 
        if self.input_transformer is None:
            self.input_transformer = lambda x: str(x)
            
    @property
    def html(self):
        return self.div        
    
    def callback(self,theapp):
        @theapp.callback(
            Output(self.html_id,'children'),
            [Input(self.input_tuple[0],self.input_tuple[1])]
        )
        def update_div(input):
            return self.input_transformer(input)        
        return update_div
#**************************************************************************************************
default_markdown_style={
    'borderWidth': '1px',
    'borderStyle': 'dashed',
    'borderRadius': '1px',
    'background-color':'#ffffff',
}

class MarkDownDiv():
    def __init__(self,html_id,markdown_text,markdown_style=None):
        self.html_id = html_id
        ms = default_markdown_style if  markdown_style is None else markdown_style
        self.html_element = html.Span(dcc.Markdown(markdown_text),style=ms)
            
    @property
    def html(self):
        return self.html_element        
#**************************************************************************************************

#**************************************************************************************************


#**************************************************************************************************
class StatusDiv():
    '''
    Use a list of lists to update display a status message from multiple inputs:
        The inner dimension is a list where:
            dimension 0 is an input_tuple
            dimension 1 is a string message to display if that input fires
    
    Example:
      [
        [
            (input_tuple_from_gridtable1),'gridtable1 is completed'
        ],
        [
            (input_tuple_from_gridtable2),'gridtable2 is completed'
        ],
        [
            (input_tuple_from_gridtable3),'gridtable3 is completed'
        ]
      ]
    '''
    def __init__(self,html_id,input_tuple_list,style=None):
        '''
        
        :param html_id:
        :param input_tuple_list: a list of lists as described above
        '''
        self.html_id = html_id
        self.store_list = []
        for i in range(len(input_tuple_list)):
            dccs = DccStore(f'{html_id}_{i}', input_tuple_list[i][0], lambda x: input_tuple_list[i][1])
            self.store_list.append(dccs)
        s = style
        if s is None:
            s = select_file_style
        self.div = html.Div([html.Div([],id=self.html_id,style=s)]+[s.html for s in self.store_list])
        self.input_history=[None for _ in input_tuple_list]   
        
    @property
    def html(self):
        return self.div        
    
    def callback(self,theapp):
        @theapp.callback(
            Output(self.html_id,'children'),
            [Input(inp.output_content_tuple[0],inp.output_content_tuple[1]) for inp in self.store_list]
        )
        def update_div(*inputs):
            print('entering StatusDiv callback')
            print(inputs)
            for i in range(len(inputs)):
                if inputs[i] is not None and self.input_history[i] is None:
                    self.input_history[i] = inputs[i]
                    return inputs[i]
                if inputs[i] is not None and inputs[i] != self.input_history[i]:
                    self.input_history[i] = inputs[i]
                    return inputs[i]                     
            return None  
        [c.callback(theapp) for c in self.store_list]      
        return update_div

#**************************************************************************************************

#**************************************************************************************************
class CsvUploadButton():
    def __init__(self,button_id,display_text=None,style=None):
        self.style = button_style if style is None else style
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
        return html.Div([self.dc,self.store],style=self.style)       
    
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
#**************************************************************************************************

    
    
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

#**************************************************************************************************
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

class CsvUploadGrid():
    def __init__(self,html_id,display_text=None,file_name_transformer=None):    
        csv_ub = CsvUploadButton(html_id,style=blue_button_style,display_text=display_text)
        csv_name = ReactiveDiv(f'{html_id}_csv_name',(csv_ub.html_id,'filename'),style=blue_button_style,
                               input_transformer=file_name_transformer)
        self.upload_components = [csv_ub,csv_name]
        self.grid = create_grid(self.upload_components)
        self.output_tuple = csv_ub.output_tuple

#**************************************************************************************************

#**************************************************************************************************
class FileDownLoadDiv():
    def __init__(self,html_id,
                 dropdown_labels,dropdown_values,a_link_text,
                 create_file_name_transformer=None,
                 style=None):
        self.html_id = html_id
        s = button_style if style is None else style
        self.input_tuple = (f'{html_id}_dropdown','value')
        dropdown_choices = [{'label':l,'value':v} for l,v in zip(dropdown_labels,dropdown_values)]
        dropdown_div = html.Div([
                dcc.Dropdown(id=self.input_tuple[0], value=dropdown_values[0],
                options=dropdown_choices
                ,style=s,placeholder="Select a File Download Option")
        ])
        self.output_tuple = (f'{html_id}_last_downloaded','href')
        href_div = html.Div(html.A(a_link_text,href='',id=self.output_tuple[0]),style=s)
        gs= grid_style
        gs['background-color'] = '#fffff0'
        self.fd_div = html.Div([dropdown_div,href_div],style=gs)
        self.create_file_name_transformer = lambda value: str(value) if create_file_name_transformer is None else create_file_name_transformer
    @property
    def html(self):
        return self.fd_div
        

    def callback(self,theapp):     
        @theapp.callback(
            Output(self.output_tuple[0], self.output_tuple[1]), 
            [Input(self.input_tuple[0],self.input_tuple[1])]
            )
        def update_link(value):
            return '/dash/urlToDownload?value={}'.format(value)        
        return update_link
    
    def route(self,theapp):
        @theapp.server.route('/dash/urlToDownload')
        def download_csv():
            value = flask.request.args.get('value')            
            fn = self.create_file_name_transformer(value)
            print(f'FileDownLoadDiv callback file name = {fn}')
            return flask.send_file(fn,
                               mimetype='text/csv',
                               attachment_filename=fn,
                               as_attachment=True)
            return download_csv
                
#**************************************************************************************************


def toy_example(host,port):

    # create a span with a file upload button and a div  for the filename 
    up_span = CsvUploadSpan('upload-data')
    file_upload_div = up_span.up_div

    
    # create 2 grid tables
    columns_to_display=['symbol','position']
    editable_cols = ['position']
    gts_input = up_span.output_tuple
    gts = [GridTable(f't{i}',f'table {i}',gts_input,editable_columns=editable_cols,columns_to_display=columns_to_display) for i in range(2)]
    
    # create 2 reactive grid graphs
    grs = [GridGraph(f'g{i}', f'graph {i}',(f't{i}_datatable','data'),df_x_column='symbol') for i in range(2)]

    # create status line
    input_tuples = [
        [gts[0].output_content_tuple,'STATUS: gridtable1 is done'],
        [grs[0].output_content_tuple,'STATUS: All Loaded']
    ]
    st = StatusDiv('load_status', input_tuples)
    status_grid = create_grid([st],num_columns=1)
    # combine tables and graph into main grid
    main_grid =  create_grid([gts[0],grs[0],gts[1],grs[1]])

    # create title for page
    title_div = html.H2('Click on the left side of the next line to upload a csv file that contains a symbol and a position column ')

    
    # create the app layout         
    app = dash.Dash()
#     app.layout = html.Div(children=[title_div,file_upload_div,status_grid,main_grid] + [s.html for s in st.store_list])
    app.layout = html.Div(children=[title_div,file_upload_div,status_grid,main_grid])

    # create the call backs
    all_components = up_span.upload_components + gts + grs + [st] #+ st.store_list
    [c.callback(app) for c in all_components]
    
    # run server
    
    app.run_server(host=host,port=port)
    
    
if __name__ == '__main__':
    parser = ap.ArgumentParser()
    parser.add_argument('--host',type=str,
                        help='host url to run server.  Default=127.0.0.1',
                        default='127.0.0.1')   
    parser.add_argument('--port',type=str,
                        help='port to run server.  Default=8400',
                        default='8500')   
    args = parser.parse_args()
    host = args.host
    port = args.port
    toy_example(host,port)
