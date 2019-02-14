'''
Created on Feb 14, 2019

@author: bperlman1

'''


import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State


app = dash.Dash()

app.layout = html.Div(
    [
        html.Div("enter something below: "),
        dcc.Input(id='inp', type='text'),
        html.Div("output:"),
        html.Div([],id='hw1'),
        html.Div([],id='hw2'),
    ]
)

@app.callback(
        [Output('hw1','children'),Output('hw2','children')],
        [Input('inp','n_submit')],
        [State('inp','value')],
        )
def process_input(n_submit,value):
    r =  'from callback: %s time, value is %s' %(str(n_submit),str(value)) 
    return [r],[r]
    
app.run_server(port=8400)