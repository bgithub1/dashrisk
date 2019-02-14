
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
import sys

class ProgressComponent():
    INPUT_ID = 'pg_input_data'
    OUTPUT_ID = 'pg_output_data'
    def __init__(self,
        theapp,
        long_running_process,
        display_div_id,
        div_to_show=None,
        div_to_hide = None
    ):
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
        self.theapp.layout
        # input from user
        @self.theapp.callback(
            Output('show','data'),
            [Input(ProgressComponent.INPUT_ID,'data')],
            [State('show','data')]
        )
        def input_callback(input_data,show_data):
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
            [Output(ProgressComponent.OUTPUT_ID,'data'),Output('hide','data')],
            # input
            [Input(ProgressComponent.INPUT_ID,'data')],
            [State('hide','data')]
        )
        def output_callback(input_data,hide_data):
            print('entering output_callback')
            result = None
            try:
                result = self.long_running_process(input_data)
                print(result)
            except:
                pass
            hide_count = 1 if hide_data is None else int(str(hide_data['data'])) + 1
            return result,{'data':str(hide_count)}
    
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
        sleep_time = 7
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
    
    app.run_server(port=8600) 