
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import time
import sys



class ProgressComponent():
    @staticmethod
    def default_wait_function():
        print('i am going to sleep')
        time.sleep(10)
        print('i am awake')
        
    max_interval_value = int(sys.maxsize/100)
    wait_interval_value = 200

    def __init__(self,
        theapp,
        input_component_id = 'dcc_input',
        input_component_property = 'n_submit',
        input_component_value = 'value',
        display_component_id = 'status',
        display_component_property = 'children',
        display_component_value = 'children',
        display_component_div_to_show = 'waiting',
        display_component_div_to_hide = [],
        wait_function = None
        ):
        self.theapp = theapp
        self.input_component_id = input_component_id
        self.input_component_property = input_component_property
        self.input_component_value = input_component_value        
        self.display_component_id = display_component_id
        self.display_component_property = display_component_property
        self.display_component_value = display_component_value
        self.display_component_div_to_show = display_component_div_to_show
        self.display_component_div_to_hide = display_component_div_to_hide
        self.dcc_interval = html.Div(dcc.Interval(id='int_val',interval=ProgressComponent.max_interval_value,n_intervals=0))
        self.wait_function = ProgressComponent.default_wait_function if wait_function is None else wait_function
        
    def define_callbacks(self):
        # callback 1
        self.theapp.layout
        @self.theapp.callback(
            # outputs
            [
                Output('v1','data'),
                Output(self.display_component_id,self.display_component_property)
            ],
            # inputs
            [
                Input(self.input_component_id,self.input_component_property),
                Input('int_val','n_intervals')
            ],
            # states
            [
                State(self.input_component_id,self.input_component_value),
                State('int_val','interval'),State('v1','data'),
                State(self.display_component_id,self.display_component_value)
            ]
        )
        def cb1(_display_component_property,n_intervals,input_component_value,interval,v1_in,_display_component_value):
            v1 = {'r':0} if v1_in is None else v1_in 
            print('cb1',_display_component_property,n_intervals,input_component_value,interval,v1_in,_display_component_value)
            if input_component_value is None:
                return [{'r':0}, self.display_component_div_to_hide]
            if v1['r'] == 0 and interval == ProgressComponent.max_interval_value:
                return [{'r':1},self.display_component_div_to_show]
            if v1['r'] == 1 and interval == ProgressComponent.wait_interval_value:
                return [{'r':0},self.display_component_div_to_hide]    
            return [{'r':0}, self.display_component_div_to_hide]
        
        # callback 2
        @self.theapp.callback(
            # output
            Output('int_val','interval'),
            # input
            [Input('v1','data')],
            # states
            [
                State('int_val','interval'),
                State(self.input_component_id,self.input_component_value)
            ]
        )
        def cb2(v1_in,int_val,input_component_value):
            v1 = {'r':0} if v1_in is None else v1_in
            print('cb2',input_component_value,int_val,v1)
            if input_component_value is None:
                return ProgressComponent.max_interval_value
            if v1['r'] == 1 and int_val == ProgressComponent.max_interval_value:
                self.wait_function()
#                 print('sleeping')
#                 time.sleep(10)
#                 print('waking')
                return ProgressComponent.wait_interval_value
            return ProgressComponent.max_interval_value
    
        return {'cb1':cb1,'cb2':cb2}

    
if __name__ == '__main__':
    
    
    app = dash.Dash()
    # app.config['suppress_callback_exceptions']=True

    
    my_input_component_id = 'stock'
    my_input_component_property = 'n_submit'
    my_input_component_value = 'value'
     
    my_display_component_id = 'status'
    my_display_component_property = 'children'
    my_display_component_value = 'children'
    loader_div = html.Div([],className='loader')
    my_display_component_div_to_show =  html.Div(['waiting 10 seconds',loader_div])
    my_display_component_div_to_hide = []
    
    prog = ProgressComponent(app, my_input_component_id, 
                             my_input_component_property, 
                             my_input_component_value, 
                             my_display_component_id, 
                             my_display_component_property, 
                             my_display_component_value, 
                             my_display_component_div_to_show, 
                             my_display_component_div_to_hide)
    
    
    app.layout = html.Div(
        [
            html.Div(['enter text and hit enter key: ',dcc.Input(id=my_input_component_id, type='text')]),
            html.Span(
                [
                    html.Div('status: ',style={'display':'inline'}),
                    html.Div(
                        my_display_component_div_to_hide,
                        id=my_display_component_id,
                        style={'display':'inline'})
                ]
            ),
            prog.dcc_interval,
            dcc.Store(id='v1'),
            dcc.Store(id='v2'),
            dcc.Store(id='v3'),
        ]
    )
    
    callbacks = prog.define_callbacks()

    callbacks['cb1']
    callbacks['cb2']
    
    app.run_server(port=8600) 