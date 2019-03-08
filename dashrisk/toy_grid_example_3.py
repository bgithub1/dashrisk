'''
Created on Mar 5, 2019

@author: bperlman1
'''
import sys
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')

import dash
import dash_html_components as html
from dashrisk import dash_grid_2 as dg2


        
row_first = html.H2('Examples of interactive grids')
up_span = dg2.CsvUploadSpan('csv_ub')
gts_input = up_span.output_tuple
g_components = [
        dg2.GridTable('02_01_gt', 'GT 02_01',input_content_tuple=gts_input),
        dg2.GridTable('02_02_gt', 'GT 02_02',input_content_tuple=gts_input),
        dg2.GridGraph('02_01_gr', 'GR 02_01',input_content_tuple=gts_input),
        dg2.GridGraph('02_02_gr', 'GR 02_02',input_content_tuple=gts_input),
]
g1_div = dg2.create_grid(g_components)
g2_div = dg2.create_grid(['03_01','03_02','03_03','04_01','04_02','04_03'],num_columns=3)
row_last = html.H4('this is the end')


if __name__== '__main__':    
    main_div = html.Div(
        children=[row_first,up_span.up_div,g1_div,g2_div,row_last],
        id='00'
    )
    app = dash.Dash()
    app.layout = main_div
    [c.callback(app) for c in up_span.upload_components + g_components]
    app.run_server(host='127.0.0.1',port=8500)
    