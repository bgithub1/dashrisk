'''
Created on Jun 21, 2019

@author: bperlman1
'''

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import pandas as pd
from collections import OrderedDict

# create the app layout         

data = OrderedDict(
    [
        ("Date", ["2015-01-01", "2015-10-24", "2016-05-10", "2017-01-10", "2018-05-10", "2018-08-15"]),
        ("Region", ["Montreal", "Toronto", "New York City", "Miami", "San Francisco", "London"]),
        ("Temperature", [1, -20, 3.512, 4, 10423, -441.2]),
        ("Humidity", [10, 20, 30, 40, 50, 60]),
        ("Pressure", [2, 10924, 3912, -10, 3591.2, 15]),
    ]
)

df = pd.DataFrame(data)

election_data = OrderedDict(
    [
        (
            "Date",
            [
                "July 12th, 2013 - July 25th, 2013",
                "July 12th, 2013 - August 25th, 2013",
                "July 12th, 2014 - August 25th, 2014",
            ],
        ),
        (
            "Election Polling Organization",
            ["The New York Times", "Pew Research", "The Washington Post"],
        ),
        ("Rep", [1, -20, 3.512]),
        ("Dem", [10, 20, 30]),
        ("Ind", [2, 10924, 3912]),
        (
            "Region",
            [
                "Northern New York State to the Southern Appalachian Mountains",
                "Canada",
                "Southern Vermont",
            ],
        ),
    ]
)

df_election = pd.DataFrame(election_data)
df_long = pd.DataFrame(
    OrderedDict([(name, col_data * 10) for (name, col_data) in election_data.items()])
)
df_long_columns = pd.DataFrame(
    {
        "This is Column {} Data".format(i): [1, 2]
        for i in range(10)
    }
)

df_csv = pd.read_csv('/users/bperlman1/downloads/df_large_chg_nyse.csv').dropna()
for col in [c for c in df_csv.columns.values if 'sym' not in c.lower()]:
    try:
        df_csv[col] = df_csv[col].astype(float).round(3)
    except:
        pass
app = dash.Dash()

dt1 = dash_table.DataTable(
   style_data={'whiteSpace': 'normal'},
   css=[{
       'selector': '.dash-cell div.dash-cell-value',
       'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
   }],
   data=df_election.to_dict('records'),
   columns=[{'id': c, 'name': c} for c in df_election.columns]
)  

dt2 = dash_table.DataTable(
    data=df_csv.to_dict('records'),
    columns=[{'id': c, 'name': c} for c in df_csv.columns],
    pagination_mode='fe',
    sorting='fe',
    content_style='grow',
    style_as_list_view=False,
    n_fixed_rows=1,
    css=[{
        'selector': '.dash-cell div.dash-cell-value',
        'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'
    }],
    style_cell={
        'whiteSpace': 'no-wrap',
        'overflow': 'hidden',
        'textOverflow': 'ellipsis',
        'maxWidth': 0,
        'minWidth': 50
    },
)


app.layout = html.Div([dt2])



if __name__ == '__main__':
    app.run_server(host='127.0.0.1',port=8600)
