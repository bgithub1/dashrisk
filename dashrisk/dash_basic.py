'''
Created on Feb 14, 2019

@author: bperlman1

'''


import dash
import dash_core_components as dcc
import dash_html_components as html
import argparse as ap


app = dash.Dash(__name__)
app.secret_key = 'development key'


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
        [dash.dependencies.Output('hw1','children'),dash.dependencies.Output('hw2','children')],
        [dash.dependencies.Input('inp','n_submit')],
        [dash.dependencies.State('inp','value')],
        )
def process_input(n_submit,value):
    r =  'from callback: %s time, value is %s' %(str(n_submit),str(value)) 
    return [r],[r]

if __name__=='__main__':    
    parser = ap.ArgumentParser()
    parser.add_argument('--ip',type=str,default='127.0.0.1',help='ip address of server')
    parser.add_argument('--port',type=int,default=8400,help='port of server')
    args = parser.parse_args()
    ip = args.ip
    port = args.port 
    app.run_server(host=ip,port=port) 
    app.run_server(port=8400)