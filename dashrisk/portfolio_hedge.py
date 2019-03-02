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


# main model class
class SingleLayerNet(nn.Module):
    def __init__(self, D_in, D_out):
        super(SingleLayerNet, self).__init__()
        self.linear1 = nn.Linear(D_in, D_out) 
    def forward(self, x):
        return self.linear1(x)

class PytorchHedge():
    def __init__(self,df=None,portfolio_value_col=None,date_column=None,num_of_test_days=None):
        self.portfolio_value_col = portfolio_value_col if portfolio_value_col is not None else 'SPY'
        self.df = df if df is not None else self.fetch_sector_spdr_df()
        self.date_column  = date_column
        ntd = num_of_test_days
        if ntd is None:
            ntd = int(len(self.df) * .1)
        self.num_of_test_days = ntd
    
    def fetch_sector_spdr_df(self):
        hist_path = './temp_folder/df_hist_portfolio_hedge.csv'
        if not os.path.isfile(hist_path):
            yf = vm.YahooFetcher()
            portfolio_value_col = self.portfolio_value_col
            symbol_list = [portfolio_value_col] + ['XLE', 'XLU', 'XLK', 'XLB', 'XLP', 'XLY', 'XLI', 'XLC', 'XLV', 'XLF']
            dt_end = datetime.datetime.now()
            dt_beg = dt_end - datetime.timedelta(30*5)
            yf.fetch_histories(symbol_list, dt_beg, dt_end)
            histories = yf.history_dict
            close_dict = {symbol:list(histories[symbol].close) for symbol in histories.keys()}
            df_hist = pd.DataFrame(close_dict)
            df_hist.to_csv(hist_path,index=None)
        else:
            df_hist = pd.read_csv(hist_path)
        return df_hist  
    
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
    ph = PytorchHedge()
    ph.run_model()
    ph.plot_hedge_ratios_vs_real()
    print(ph.hedge_ratio_dict)
