'''
Created on Feb 10, 2019

@author: bperlman1
'''
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import dash_table
import plotly.graph_objs as go
import numpy as np



class GridTable():
    def __init__(self,html_id,title,df=None):
        self.dt = dash_table.DataTable(
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
        if df is not None:
            self.dt.data=df.to_dict("rows")
            self.dt.columns=[{"name": i, "id": i} for i in df.columns]

        self.dt_html = html.Div(
            [
                html.H4(title,style={'height':'3px'}),
                self.dt
            ],
            id=html_id,
            style={'margin-right':'auto' ,'margin-left':'auto' ,'height': '98%','width':'98%'}
        )
    @property
    def html(self):
        return self.dt_html        

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
    def __init__(self,html_id,title,x_vals,y_vals,x_title,y_title,figure=None):
        f = charts(x_vals,y_vals,title,x_title,y_title) if figure is None else figure
        gr = dcc.Graph(
                id=html_id,
                figure=f,
                )
        self.gr_html = html.Div(gr,className='item1')         
    @property
    def html(self):
        return self.gr_html        

animals=['giraffes', 'orangutans', 'monkeys']
animal_heights=[20, 14, 23]
t = 'Animal Chart'
x_t = 'animal'
y_t = 'animal height'

#**************************************************************************************************

grid_style = {'display': 'grid',
  'grid-template-columns': '49.9% 49.9%',
  'grid-gap': '10px'
}
chart_style = {'margin-right':'auto' ,'margin-left':'auto' ,'height': '98%','width':'98%'}

#**************************************************************************************************




if __name__ == '__main__':

    NO_POSITION = {
        'symbol':['no_position' for _ in range(1001)],
        'underlying':['no_position' for _ in range(1001)],
        'position':np.linspace(0, 1000,1001),
        'position_var':np.linspace(2, 1002,1001),
        'unit_var':np.linspace(2, 1002,1001),
        'stdev':np.linspace(3, 1003,1001),
        'close':np.linspace(4, 1004,1001),
    }
    
    DF_NO_POSITION = pd.DataFrame(NO_POSITION)
    
    dts = [GridTable(f't{i}',f'table {i}',DF_NO_POSITION).html for i in range(2)]
    grs = [GridGraph(f'g{i}', f'{t} {i}', animals, animal_heights, x_t, y_t).html for i in range(2)]
    
    app = dash.Dash()
    
             
    app.layout = html.Div([
    
        html.Div([
            dts[0],dts[1],grs[0],grs[1]
        ], className='item1',style=grid_style),
    ])

    app.run_server(port=8700)
