'''
Created on Mar 1, 2019

@author: bperlman1
'''
import sys,os
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')

import pandas as pd
import numpy as np
from dashrisk import portfolio_hedge as phedge
import argparse as ap
from itertools import combinations


RANDOM_PORTFOLIO_PATH = './temp_folder/df_random_portfolio.csv'
SPDR_HISTORY_PATH = './temp_folder/df_hist_portfolio_hedge.csv'



if __name__ == '__main__':
    parser = ap.ArgumentParser()
#     parser.add_argument('--use_min_variance',type=bool,
#                         help='Use minimum variance calculation, as opposed to Pytorch regression. (Default = False)',
#                         default=False)
    parser.add_argument('--use_spy',type=bool,
                        help='Use SPY as your portfolio, otherwise use 20 randomly created members of SP 500, with random weights. (Default = False)',
                        default=False)
    parser.add_argument('--refetch_data',type=bool,
                        help='Re-fetch all data. (Default = False)',
                        default=False)
    parser.add_argument('--max_hedge_symbols',type=int,
                        help='Maximum number of symbols from sector spdrs that you will use to hedge. (Default = 5)',
                        default = 5)
    parser.add_argument('--rounding_value_for_hedge_comarisons',type=float,
                        help='Round all absolute differences to this percent, so that simpler portfolios can end up being the best. (Default = .002)',
                        default = .002)
    args = parser.parse_args()

#     use_min_variance = args.use_min_variance
    use_spy = args.use_spy
    refetch_data = args.refetch_data
    max_hedge_symbols = args.max_hedge_symbols
    if max_hedge_symbols > 10:
        max_hedge_symbols = 10
    rounding_value_for_hedge_comarisons = args.rounding_value_for_hedge_comarisons
    
    if use_spy:
        portfolio_column_name = 'SPY'
        df = phedge.fetch_sector_spdr_df(refresh=refetch_data)
    else:
        portfolio_column_name = 'port'
        if refetch_data:
            df = phedge.create_random_portfolio_history()
        else:
            df = pd.read_csv(RANDOM_PORTFOLIO_PATH)

    hedge_cols = df.columns.values
    hedge_cols = np.setdiff1d(hedge_cols, np.array([portfolio_column_name]))

    
    sets = set([])
    for i in range(1,max_hedge_symbols+1):
        for l in combinations(hedge_cols,i): 
            sets.add(l)
    
    for _ in range(1):
        best_value = sys.float_info.max
        best_set = None
        best_ph = None
        for s in sets:
            dfs = df[[portfolio_column_name] + list(s)]
            ph = phedge.MinVarianceHedge(dfs,portfolio_column_name)
            ph.run_model()
            d = ph.get_train_test_values()
            first_ysim_test = d['ysim_test'][1]
            first_yreal_test = d['yreal_test'][1]
            abs_diff = abs(first_yreal_test-first_ysim_test)
            # round it
            abs_diff_round = int(abs_diff * rounding_value_for_hedge_comarisons * 10000)/10000
            if best_ph is None:
                best_value = abs_diff
                best_set = s
                best_ph = ph
            elif abs_diff_round < best_value:
                if len(s) < len(best_set):
                    best_value = abs_diff
                    best_set = s
                    best_ph = ph
        
        best_ph.plot_hedge_ratios_vs_real()
        print(best_ph.hedge_ratio_dict)
