
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
import argparse as ap

class ProgressComponent():
    INPUT_ID = 'pg_input_data'
    OUTPUT_ID = 'pg_output_data'
    def __init__(self,
        theapp,
        long_running_process,
        display_div_id,
        div_to_show=None,
        div_to_hide = None,
        by_pass = False
    ):
        self.by_pass = by_pass
        self.theapp = theapp
        self.long_running_process = long_running_process
        self.display_div_id = display_div_id
        self.div_to_show = 'waiting' if div_to_show is None else div_to_show
        self.div_to_hide = 'waiting' if div_to_hide is None else div_to_hide
        # add v1 component to layout
        self.theapp.layout.children.append(dcc.Store(id='show'))
        self.theapp.layout.children.append(dcc.Store(id='hide'))
        self.theapp.layout.children.append(dcc.Store(id=ProgressComponent.INPUT_ID))
        self.theapp.layout.children.append(dcc.Store(id=ProgressComponent.OUTPUT_ID))
        self.callbacks = self.define_callbacks()
        
    def define_callbacks(self):
        if not self.by_pass:
            self.theapp.layout
            # input from user
            @self.theapp.callback(
                Output('show','data'),
                [Input(ProgressComponent.INPUT_ID,'data')],
                [State('show','data')]
            )
            def input_callback(input_data,show_data):
                print('entering input_callback')
                if self.by_pass:
                    return {'data':'1'}
                show_count = 1 if show_data is None else int(str(show_data['data'])) + 1
                return {'data':str(show_count)}
        
            # this callback displays the show div or the hide div
            @self.theapp.callback(
                Output(self.display_div_id,'children'),
                [Input('show','data'),Input('hide','data')],
                [State(self.display_div_id,'children')]
            )
            def display_callback(show,hide,children):
                print('entering display_callback')
                if self.by_pass:
                    return self.div_to_hide
                show_count = int(show['data'])
                hide_count = int(hide['data'])
                r =  self.div_to_hide
                if show_count != hide_count:
                    r =  self.div_to_show
                print(f'exiting with r = {r}')
                return r
        
        # callback to fire long process
        @self.theapp.callback(
            # outputs
            [Output(ProgressComponent.OUTPUT_ID,'data'),Output('hide','data')] if not self.by_pass else Output(ProgressComponent.OUTPUT_ID,'data'),
            # input
            [Input(ProgressComponent.INPUT_ID,'data')],
            [State('hide','data')]
        )
        def output_callback(input_data,hide_data):
            print('entering output_callback')
            result = None
            try:
                result = self.long_running_process(input_data)
#                 print(result)
            except Exception as e:
                print('output_callback',str(e))
            hide_count = 1 if hide_data is None else int(str(hide_data['data'])) + 1
            print('leaving output_callback')
            if self.by_pass:
                return result
            return result,{'data':str(hide_count)}
        
        if self.by_pass:
            return [output_callback]
        return [input_callback,display_callback,output_callback]



    
if __name__ == '__main__':
    
    app = dash.Dash()
    # app.config['suppress_callback_exceptions']=True

    
    input_div_id = 'input_div_id'
    loader_div = html.Div([],className='loader')
    progress_animation_div_to_show =  html.Div(['waiting a few seconds',loader_div])
    hide_div = []
    hide_show_div_id = 'status'
    
    
    
    app.layout = html.Div(
        [
            html.Div(['enter text and hit enter key: ',dcc.Input(id=input_div_id, type='text')]),
            html.Span(
                [
                    html.Div('status: ',style={'display':'inline'}),
                    html.Div(
                        hide_div,
                        id=hide_show_div_id,
                        style={'display':'inline'}
                    ),
                    html.Div([],id='results')
                ]
            ),
        ]
    )
    
    def default_wait_function(data):
        print(data['sleep_message'])
        time.sleep(data['sleep_time'])
        print(data['awake_message'])
        return {'data':str(datetime.datetime.now())}
    
    prog = ProgressComponent(app, default_wait_function, hide_show_div_id, progress_animation_div_to_show, hide_div)
    prog.callbacks


    import datetime
    # local callbacks
    @app.callback(
        Output(ProgressComponent.INPUT_ID,'data'),
        [Input(input_div_id,'n_submit')],
        [State(input_div_id,'value')]
    )
    def from_input_box(n_submit,value):
        sleep_time = 20 #7
        if value is None:
            sleep_time = .1
        data = {
            'sleep_message':f'{str(value)} is going to sleep',
            'sleep_time':sleep_time,
            'awake_message':f'{str(value)} is baaaaack!!'
        }
        return data
        
    @app.callback(
        Output('results','children'),
        [Input(ProgressComponent.OUTPUT_ID,'data')]
    )
    def display_results(output_data):
        return None if output_data is None else output_data['data']
    
    parser = ap.ArgumentParser()
    parser.add_argument('--ip',type=str,default='127.0.0.1',help='ip address of server')
    parser.add_argument('--port',type=int,default=8400,help='port of server')
    args = parser.parse_args()
    ip = args.ip
    port = args.port 
    app.run_server(host=ip,port=port) 
    
    