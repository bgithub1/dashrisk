'''
Created on Jun 21, 2019

this module contains one method: update_risk_data.

It calls the classes and methods in the var_models module to create
a dictionary of json objects that you can inject into 
the dash_core_components.Store component for later use as the source
of DataFrames for other Dash components.

@author: bperlman1
'''
import sys,os
if  not './' in sys.path:
    sys.path.append(os.path.abspath('./'))
if  not '../' in sys.path:
    sys.path.append(os.path.abspath('../'))
    
from dashrisk import var_models as varm
from dashrisk import option_models as opmod
from dashrisk import portfolio_hedge as ph
from dashrisk import build_history as bh

import pandas as pd
import numpy as np
import datetime 

#********
DEFAULT_PORTFOLIO_NAME=  'spdr_stocks.csv'             
# DEFAULT_PORTFOLIO_NAME=  'test_portfolio.csv'             
DF_NO_POSITION = pd.read_csv(DEFAULT_PORTFOLIO_NAME)

def update_risk_data(df,USE_POSTGRES=False,
        dburl=None,databasename=None,username=None,
        password=None,schema_name=None,yahoo_daily_table=None):
    print(f'Start computing VaR {datetime.datetime.now()}')
    if USE_POSTGRES:
#         hb = bh.HistoryBuilder(dburl,databasename,username,password,schema_name,yahoo_daily_table)
        hb = bh.HistoryBuilder(dburl=dburl, databasename=databasename, 
                               username=username, password=password, 
                               schema_name=schema_name, yahoo_daily_table=yahoo_daily_table, )
        history_fetcher = varm.PostgresFetcher(hb)
    else:
        history_fetcher = varm.YahooFetcher()
    vm = varm.VarModel(df,history_fetcher)
    var_dict = vm.compute_var()
    port_var = var_dict['port_var']
#     df_var_all = var_dict['df_underlying_positions']
    sp_dollar_equiv = var_dict['sp_dollar_equiv'] 
      
    # do greeks
    df_positions_all = var_dict['df_positions_all']
    df_atm_price = var_dict['df_atm_price']
    df_atm_price = df_atm_price.rename(columns={'close':'price'})
    
    model_per_underlying_dict = {u:opmod.BsModel for u in df_atm_price.underlying}
    greeks_dict = opmod.get_df_greeks(df_positions_all, df_atm_price, model_per_underlying_dict)
    df_greeks = greeks_dict['df_greeks']
    # merge var and greeks
    df_risk_all = df_greeks.merge(df_positions_all[['symbol','position_var']],how='inner',on='symbol')
    df_risk_all = df_risk_all.drop(['option_price'],axis=1)

    df_var = df_risk_all[['symbol','position','position_var']]

    risk_agg_cols = [c for c in df_risk_all.columns.values if c not in ['symbol','position']]
    df_risk_by_underlying = df_risk_all[risk_agg_cols].groupby('underlying',as_index=False).sum()
    # do hedge values
    # first create a history of this portfolio as on price per day
    symbol_list = sorted(df_atm_price.underlying)
    series_weights = df_greeks[['underlying','delta']].groupby('underlying').sum()['delta']
    weights = [series_weights[c] for c in symbol_list] 

    df_port_prices = vm.get_history_matrix()
    hist_matrix = df_port_prices[symbol_list].as_matrix()
    # now create random weights
    port_price_history = hist_matrix @ weights
    df_port = pd.DataFrame({'date':df_port_prices.date,'port':port_price_history})
    
    # next get price history of sector spdrs
    spdr_symbols = [ 'XLB', 'XLC', 'XLE', 'XLF', 'XLI', 'XLK', 'XLP', 'XLU', 'XLV', 'XLY']
    df_sector_spdr = pd.DataFrame({'symbol':spdr_symbols,'position':np.repeat(1, len(spdr_symbols))})
    vm_hedge = varm.VarModel(df_sector_spdr,history_fetcher)
    df_hedge_prices = vm_hedge.get_history_matrix()
    
    # next, merge history of "portfolio value" with history of spdr's.
    #  MAKE SURE THAT THE FIRST COLUMN IS THE PORTFOLIO HISTORY, AND NAME THAT COLUMN "port"
    df_hedge_prices = df_hedge_prices.merge(df_port,how='inner',on='date')
    df_hedge_prices = df_hedge_prices[['port'] + spdr_symbols]

    print('entering hedge ratio calc')
    max_hedge_symbols = len(var_dict['df_underlying_positions'])//5
    max_hedge_symbols = 1 if max_hedge_symbols<=0 else max_hedge_symbols
    best_ph = ph.best_hedge(df_hedge_prices, 'port',max_hedge_symbols=max_hedge_symbols)
    hedge_symbols = list(best_ph.hedge_ratio_dict.keys())
    hedge_values = [best_ph.hedge_ratio_dict[s] * best_ph.last_day_ratio for s in hedge_symbols]
    df_hedge_ratios = pd.DataFrame({'symbol':hedge_symbols,'hedge':hedge_values})
    print('leaving hedge ratio calc')

    n = datetime.datetime.now()
    print(f'End computing VaR {n}')
    yyyymmddhhmmssmmmmmm = '%04d%02d%02d%02d%02d%02d%06d' %(n.year,n.month,n.day,n.hour,n.minute,n.second,n.microsecond)
    ret =  {
        'yyyymmddhhmmssmmmmmm':str(yyyymmddhhmmssmmmmmm),
        'df_std':var_dict['df_std'].to_dict('rows'),
        'df_high_low':var_dict['df_high_low'].to_dict('rows'),
        'df_risk_all':df_risk_all.to_dict('rows'),
        'df_risk_by_underlying':df_risk_by_underlying.to_dict('rows'),
        'df_var':df_var.to_dict('rows'),
        'port_var':port_var,
        'sp_dollar_equiv':sp_dollar_equiv,
        'df_hedge_ratios':df_hedge_ratios.to_dict('rows'),
        'df_corr':var_dict['df_corr'].to_dict('rows'),
        'df_corr_price':var_dict['df_corr_price'].to_dict('rows'),
        'df_atm_price':var_dict['df_atm_price'].to_dict('rows')}
    print('leaving update_memory')
    return ret