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
import pandas as pd

        
row_first = html.H2('Examples of grids')

df1 = pd.read_csv('test_portfolio.csv')
df2 = pd.read_csv('test_portfolio2.csv')

g1_div = dg2.create_grid(
    [
        dg2.GridTable('02_01_gt', 'GT 02_01', df_in=df1),
        dg2.GridTable('02_02_gt', 'GT 02_02', df_in=df2),
        dg2.GridGraph('02_01_gr', 'GR 02_01', df_in=df1),
        dg2.GridGraph('02_02_gr', 'GR 02_02', df_in=df2),
    ])

g2_div = dg2.create_grid(['03_01','03_02','03_03','04_01','04_02','04_03'],
                          num_columns=3)

row_last = html.H4('this is the end')


if __name__== '__main__':    
    main_div = html.Div(
        children=[row_first,g1_div,g2_div,row_last],
        id='00'
    )
    app = dash.Dash()
    app.layout = main_div
    app.run_server(host='127.0.0.1',port=8500)
    