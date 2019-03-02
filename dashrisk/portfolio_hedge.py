'''
Created on Mar 1, 2019

@author: bperlman1
'''
import sys,os
from passlib.utils.compat import num_types
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')

import pandas as pd

import numpy as np
# import os,sys
# import pdb
import torch 
from torch import nn
from torch.autograd import Variable
from torch import optim
# import torch.nn.functional as F
from dashrisk import var_models as vm
import datetime
import matplotlib.pyplot as plt
from textwrap import wrap
import argparse as ap

RANDOM_PORTFOLIO_PATH = './temp_folder/df_random_portfolio.csv'
SPDR_HISTORY_PATH = './temp_folder/df_hist_portfolio_hedge.csv'

def fetch_histories(symbol_list,dt_beg=None,dt_end=None):
    yf = vm.YahooFetcher()
    dt_end = dt_end if dt_end is not None else datetime.datetime.now()
    dt_beg = dt_beg if dt_beg is not None else dt_end - datetime.timedelta(30*5)
    yf.fetch_histories(symbol_list, dt_beg, dt_end)
    histories = yf.history_dict
    close_dict = {symbol:list(histories[symbol].close) for symbol in histories.keys()}
    df_hist = pd.DataFrame(close_dict)
    return df_hist

def create_random_portfolio_history(num_of_symbols=20,weights=None,dt_beg=None,dt_end=None,csv_save_path=None):
    url_constituents = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
    df_constit = pd.read_csv(url_constituents)
    all_symbols = sorted(list(df_constit.Symbol))
    random_indices = np.random.randint(0,len(all_symbols)-1,num_of_symbols)
    symbol_list = [all_symbols[i] for i in random_indices]
    w = weights
    if w is None:
        w = np.random.rand(len(symbol_list))
    port_path = RANDOM_PORTFOLIO_PATH if csv_save_path is None else csv_save_path
    df =  create_portfolio_history(symbol_list,weights=w,dt_beg=dt_beg,dt_end=dt_end)
    df_spdr = fetch_sector_spdr_df(refresh=True)
    df_spdr = df_spdr.drop('SPY',axis=1)
    df_spdr['port'] = df.port
    df_spdr.to_csv(port_path,index=None)
    return df_spdr

def create_portfolio_history(symbol_list,weights,dt_beg=None,dt_end=None):
    '''
    Create a Data frame with columns 'date' and 'port', where port lists the value of a 
    randomly created portfolio of 20 SP 500 stocks, with  weights = weights.  If weights is None, 
        then randomly assign weights.
    :param num_of_symbols: default is 20
    :param dt_beg: default is 150
    :param dt_end: default is today
    '''
    df_hist = fetch_histories(symbol_list,dt_beg,dt_end)
    hist_matrix = df_hist[symbol_list].as_matrix()
    # now create random weights
    prices = hist_matrix @ weights
    df = pd.DataFrame({'port':prices})
    return df

def fetch_sector_spdr_df(refresh=False,csv_save_path=None):
    hist_path = SPDR_HISTORY_PATH if csv_save_path is None else csv_save_path
    if refresh:
        symbol_list = ['SPY','XLE', 'XLU', 'XLK', 'XLB', 'XLP', 'XLY', 'XLI', 'XLC', 'XLV', 'XLF']
        df_hist = fetch_histories(symbol_list)
        df_hist.to_csv(hist_path,index=None)
    else:
        df_hist = pd.read_csv(hist_path)
    return df_hist  



# main model class
class SingleLayerNet(nn.Module):
    def __init__(self, D_in, D_out):
        super(SingleLayerNet, self).__init__()
        self.linear1 = nn.Linear(D_in, D_out) 
    def forward(self, x):
        return self.linear1(x)


class PytorchHedge():
    '''
    Create hedge rations using a simple pytorch Linear model.
    
    Toy Example where your portfolio is SPY, and you want to hedge it using the sector spdr's:
    ph = PytorchHedge()
    ph.run_model()
    ph.plot_hedge_ratios_vs_real()
    print(ph.hedge_ratio_dict)

    Example of a 20 random memebers of the SP 500 as your portfolio, with random weights, and the sector spdr's as your hedge
    yf = 
    '''
    def __init__(self,df,portfolio_value_col,date_column=None,num_of_test_days=None):
        '''        
        :param df: pandas DataFrame containing historical prices for each security that you will use to hedge,
            and the prices of your portfolio in a column whose name = portfolio_value_col.
            If df == None, then this class will use the sector spdr ETFs as the hedging securities
        :param portfolio_value_col: the name of the column in df which holds the hitorical prices of your portfolio.
            IF None, then use 'SPY' has your portfolio.
        :param date_column: None ,if your DataFrame does not have a date column, otherwise the column name of that column
        :param num_of_test_days: Number or rows in df to use as out of sample data. If None, then use int(len(df) * .1).
            The size of the training set will equal len(df) - num_of_test_days
        '''
        self.portfolio_value_col = portfolio_value_col
        self.df = df
        self.date_column  = date_column
        ntd = num_of_test_days
        if ntd is None:
            ntd = int(len(self.df) * .1)
        self.num_of_test_days = ntd
        

    
    
    def run_model(self):
        Ynp = self.df[self.portfolio_value_col].as_matrix()[:-self.num_of_test_days]
        x_cols = list(filter(lambda s: s.lower() != self.portfolio_value_col.lower(),self.df.columns.values))
        if self.date_column is not None:
            x_cols = list(filter(lambda s: s.lower()!= self.date_column.lower(),x_cols))
        Xnp = self.df[x_cols].as_matrix()[:-self.num_of_test_days]
        b=1
        # number of epochs
        epochs=10000
        # instantiate model
        m1 = SingleLayerNet(Xnp.shape[1],1)
        # Create input torch Variables for X and Y
        X = Variable(torch.Tensor(Xnp))
        Y = Variable(torch.Tensor(Ynp).reshape(-1,1))
        
        # create loss and optimize
        
        loss_fn = nn.MSELoss(size_average = False) 
        optimizer = optim.Adam(m1.parameters(), lr = 0.01)
        
        # Training loop
        for i in range(epochs):
            # create a batch of x values and y values (labels)
            indices = list(range(Xnp.shape[0]))
            np.random.shuffle(indices)
            xb = X[indices[:b]]    
            yb = Y[indices][:b]
            # zero the optimizer
            optimizer.zero_grad()  # clear previous gradients
            
            # execute the forward pass to compute y values from equation xA^T + b (the linear transformation)
            output_batch = m1(xb)           # compute model output
            
            # calculate a loss
            loss = loss_fn(output_batch, yb)  # calculate loss
        
            # compute gradients
            loss.backward()        # compute gradients of all variables wrt loss
            optimizer.step()       # perform updates using calculated gradients
            # print out progress
            if i % 500 == 0 :
                print('epoch {}, loss {}'.format(i,loss.data))
        
        # print model results
        model_A = m1.linear1.weight.data.numpy()
        model_bias = m1.linear1.bias.data.numpy()
        self.hedge_ratio_dict = {x_cols[i]:model_A[0][i] for i in range(len(x_cols))}
        self.bias = model_bias[0]

    def plot_hedge_ratios_vs_real(self):
        df = self.df.copy()
        ntd = self.num_of_test_days
        yreal = df[self.portfolio_value_col].as_matrix().reshape(-1)
        df = df.drop(self.portfolio_value_col,axis=1)
        if self.date_column is not None:
            df = df.drop(self.date_column)
        all_Xnp = df.as_matrix().reshape(-1,len(df.columns.values))
        hedge_ratios = np.array([self.hedge_ratio_dict[symbol] for symbol in df.columns.values])
        ysim = np.array(all_Xnp @ hedge_ratios + self.bias)
        # plot with without pandas
        x_train = list(range(len(all_Xnp)))[:-ntd]
        x_test =  list(range(len(all_Xnp)))[-ntd-1:]
        ysim_train = ysim[:-ntd]
        ysim_test = ysim[-ntd-1:]
        yreal_train = yreal[:-ntd]
        yreal_test = yreal[-ntd-1:]
        fig, ax = plt.subplots(figsize = (16,7))
    
        ax.plot(x_train,yreal_train,color='blue',label='y_train_real')
        ax.plot(x_train,ysim_train,color='orange',label='y_train_model')
        ax.plot(x_test,yreal_test,color='red',label='y_test_real')
        ax.plot(x_test,ysim_test,color='green',label='y_test_model')
        ax.legend()
        ax.grid()
        hr = {k:round(self.hedge_ratio_dict[k],4) for k in self.hedge_ratio_dict.keys()}
        t = f'{self.portfolio_value_col} vs {hr}'
        t = t.replace("'","")
        title = ax.set_title("\n".join(wrap(t, 60)))
        fig.tight_layout()
        title.set_y(1.05)
        fig.subplots_adjust(top=0.8)
        plt.show()

if __name__ == '__main__':
#     parser = ap.ArgumentParser()
#     parser.add_argument('--portfolio_symbols',type=str,
#                         help='Comma separated list of symbols in portfolio to hedge, whose history you must fetch (Default is SPY',
#                         nargs="?")
#     parser.add_argument('--hedge_symbols',type=str,
#                         help='Comma separated list of symbols in hedge list, whose history you must fetch (Default is SPY',
#                         nargs="?")
#     args = parser.parse_args()
#     port_sym_list = args.porfolio_symbols

    use_spy = False
    if use_spy:
        portfolio_column_name = 'SPY'
        df = fetch_sector_spdr_df()
    else:
        portfolio_column_name = 'port'
        df = pd.read_csv(RANDOM_PORTFOLIO_PATH)
#         df = create_random_portfolio_history()
    ph = PytorchHedge(df,portfolio_column_name)
    ph.run_model()
    ph.plot_hedge_ratios_vs_real()
    print(ph.hedge_ratio_dict)
