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
import argparse as ap
        
def toy_example(host,port):

    # create a span with a file upload button and a div  for the filename 
    up_span = dg2.CsvUploadSpan('upload-data')
    file_upload_div = up_span.up_div

    
    
    # create 2 grid tables
    columns_to_display=['symbol','position']
    editable_cols = ['position']
    gts_input = up_span.output_tuple
#     gts = [dg2.GridTable(f't{i}',f'table {i}',gts_input,editable_columns=editable_cols,columns_to_display=columns_to_display) for i in range(2)]
    gts1 = dg2.GridTable('portfolio1', 'Portfolio1 Table',gts_input,editable_columns=editable_cols,columns_to_display=columns_to_display)
    gts2 = dg2.GridTable('portfolio2', 'Portfolio2 Table',gts_input,editable_columns=editable_cols,columns_to_display=columns_to_display)
    gts = [gts1,gts2]
    
    # create 2 reactive grid graphs
#     grs = [dg2.GridGraph(f'g{i}', f'graph {i}',(f't{i}_datatable','data'),df_x_column='symbol') for i in range(2)]
    grs1 = dg2.GridGraph(f'graph1', f'Portfolio1 Graph',(f'portfolio1_datatable','data'),df_x_column='symbol')
    grs2 = dg2.GridGraph(f'graph2', f'Portfolio2 Graph',(f'portfolio2_datatable','data'),df_x_column='symbol')
    grs = [grs1,grs2] 
    
    # combine tables and graph into main grid
    main_grid =  dg2.create_grid([gts[0],grs[0],gts[1],grs[1]])

    # create title for page
    title_div = html.H2('dash_grid example')

    
    # create the app layout         
    app = dash.Dash()
    app.layout = html.Div([title_div,file_upload_div,main_grid])

    # create the call backs
    all_components = up_span.upload_components + gts + grs
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
    