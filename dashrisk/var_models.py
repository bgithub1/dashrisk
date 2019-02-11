'''
Created on Feb 5, 2019

@author: bperlman1
'''
import pandas_datareader.data as pdr
import pandas as pd
import datetime
import pytz
from dashrisk import barchart_api as bcapi
from dashrisk import option_models as opmod
from scipy.stats import norm
from pandas_datareader import data as web

class YahooFetcher():
    def __init__(self):
        self.history_dict = {}

    def fetch_histories(self,symbol_list,dt_beg,dt_end):
        for symbol in symbol_list:
            if symbol in self.history_dict:
                continue
            self.fetch_history(symbol, dt_beg, dt_end)
    def fetch_history(self,symbol,dt_beg,dt_end):
        if symbol in self.history_dict:
            return self.history_dict[symbol]            
        df = pdr.DataReader(symbol, 'yahoo', dt_beg, dt_end)
        # move index to date column, sort and recreate index
        df['date'] = df.index
        df = df.sort_values('date')
        df.index = list(range(len(df)))
        # make adj close the close
        df['Close'] = df['Adj Close']
        df = df.drop(['Adj Close'],axis=1)
        cols = df.columns.values 
        cols_dict = {c:c[0].lower() + c[1:] for c in cols}
        df = df.rename(columns = cols_dict)
        self.history_dict[symbol] = df
        return df
    

class BarChartFetcher30Min():
    def __init__(self,api_key=None, bar_type=None, interval=None,endpoint_type = None):
        self.api_key = open('./temp_folder/free_api_key.txt','r').read() if api_key is None else api_key
        self.bar_type = 'minutes' if bar_type is None else bar_type
        self.interval = 30 if interval is None else interval
        self.endpoint_type = 'free_url' if endpoint_type is None else endpoint_type
        self.bch = bcapi.BcHist(self.api_key, bar_type=self.bar_type, interval=self.interval,endpoint_type = self.endpoint_type)
        self.history_dict = {}
        
    def fetch_histories(self,symbol_list,dt_beg,dt_end):
        for symbol in symbol_list:
            if symbol in self.history_dict:
                continue
            self.fetch_history(symbol, dt_beg, dt_end)

    # fetch history for a symbol
    def fetch_history(self,symbol,dt_beg,dt_end,interval=1):
        if symbol in self.history_dict:
            return self.history_dict[symbol]            
        y = dt_beg.year 
        m = dt_beg.month 
        d = dt_beg.day 
        beg_yyyymmdd = '%04d%02d%02d' %(y,m,d)
        y = dt_end.year 
        m = dt_end.month 
        d = dt_end.day 
        end_yyyymmdd = '%04d%02d%02d' %(y,m,d)
        tup = self.bch.get_history(symbol, beg_yyyymmdd, end_yyyymmdd)
        df = tup[1]
        cols = df.columns.values 
        cols_dict = {c:c[0].lower() + c[1:] for c in cols}
        df = df.rename(columns = cols_dict)
        # make date col
        def _make_date(t):
            y = int(t[0:4])
            mon = int(t[5:7])
            d = int(t[8:10])
            h = int(t[11:13])
            minute = int(t[14:16])
            dt = datetime.datetime(y,mon,d,h,minute,tzinfo=pytz.timezone('US/Eastern'))
            return dt 
        df['date'] = df.timestamp.apply(_make_date)
        df = df.drop(['timestamp'],axis=1)
        self.history_dict[symbol] = df
        return df
    
class FixedRateModel():
    
    def __init__(self):
        # see if you can get Libor from the FRED API
        n = datetime.datetime.now() - datetime.timedelta(14)
        y = n.year
        m = n.month
        d = n.day
        beg = '%04d-%02d-%02d' %(y,m,d)
        df = web.DataReader('USD3MTD156N', "fred", f'{beg}', '2200-12-31')
        self.fixed_rate = float(df.iloc[len(df)-1].USD3MTD156N)/100
        
        
    def get_rate(self,date):
        return self.fixed_rate    


class VarModel():
    DEFAULT_PRICE_COLUMN = 'close'
    DEFAULT_DATE_COLUMN = 'date'
    
    def __init__(self,df_portfolio,history_fetcher=None,dt_beg=None,dt_end=None,
                 price_column=None,date_column=None,bars_per_day=1,options_model=None,rate_model=None,reference_symbol=None):
        self.price_column = VarModel.DEFAULT_PRICE_COLUMN if price_column is None else price_column
        self.date_column = VarModel.DEFAULT_DATE_COLUMN if date_column is None else date_column        
        self.reference_symbol = 'SPY' if reference_symbol is None else reference_symbol
        self.rate_model = rate_model if rate_model is not None else FixedRateModel()
        self.op_model = options_model if options_model is not None else opmod.BsModel
        self.df_portfolio = df_portfolio
        self.df_portfolio['underlying'] = self.df_portfolio.symbol.apply(lambda s: s.split('_')[0])
        self.bars_per_day = bars_per_day
        self.history_fetcher = history_fetcher
        if self.history_fetcher is None:
            self.history_fetcher = YahooFetcher()
        self.dt_end = dt_end if dt_end is not None else datetime.datetime.now()
        self.dt_beg = dt_beg if dt_beg is not None else self.dt_end - datetime.timedelta(60)
        self.history_dict = self.fetch_portfolio_history()
        self.reference_current_price = self.get_reference_index_current_price()
        self.df_std = self.compute_std() 
        self.df_corr = self.compute_corr_matrix()
        
    def fetch_portfolio_history(self):
        symbols = list(set(self.df_portfolio.underlying.as_matrix().reshape(-1)))
        history_dict = {}
        for symbol in set(symbols):
            history_dict[symbol] = self.history_fetcher.fetch_history(symbol, self.dt_beg, self.dt_end)
        return history_dict

    def get_reference_index_current_price(self):
        df_ref_prices = self.history_fetcher.fetch_history(self.reference_symbol, self.dt_beg, self.dt_end)
        return float(df_ref_prices.iloc[-1][self.price_column])
        
    def compute_std(self):
        df_price = self.get_history_matrix()
        cols = list(set(list(df_price.columns.values))-set([self.date_column]))
        bars_per_day = self.bars_per_day
        perc_of_day = 1/bars_per_day
        perc_of_year = perc_of_day/256
        std_series = df_price[cols].pct_change().iloc[1:].std()/perc_of_year**.5
        df_std = pd.DataFrame({'stdev':list(std_series.values),'underlying':list(std_series.index.values)})
        return df_std
    
    def get_history_matrix(self,price_column_to_use=None):
        pctu = price_column_to_use if price_column_to_use is not None else self.price_column
        df_price = None
        for symbol in self.history_dict.keys():
            df = self.history_dict[symbol][[self.date_column,pctu]]  
            col_dict = {pctu:symbol}
            df = df.rename(columns=col_dict)          
            if df_price is None:
                df_price = df.copy()
            else:
                df_price = df_price.merge(df,how='inner',on=self.date_column)
        return df_price
    
    def compute_corr_matrix(self):
        df_close = self.get_history_matrix()
        df_close = df_close.drop(columns=[self.date_column]) 
        df_corr = df_close.corr() 
        return df_corr  
    
    def get_current_prices(self):
        df_price_history = self.get_history_matrix()
        df_price_history = df_price_history.drop([self.date_column],axis=1)
        prices = df_price_history.iloc[-1].as_matrix()
        syms = df_price_history.columns.values
        df_prices = pd.DataFrame({'underlying':syms,self.price_column:prices})
        return df_prices
        
    def compute_var(self,var_days = 1,var_confidence=.99,spy_usual_std=.16):
        df_portfolio = self.df_portfolio
        df_prices = self.get_current_prices()
        df_std = self.df_std
        df_corr = self.df_corr
        df_positions_2 = df_portfolio.merge(df_prices,how='inner',on='underlying')
        df_positions_3 = df_positions_2.merge(df_std,how='inner',on='underlying')
        rate = self.rate_model.get_rate(None)
        
        def _delta(r):             
            m = opmod.model_from_symbol(r.symbol, r[self.price_column], vol=r.stdev, rate=rate,
                                        model=self.op_model, tzinfo=opmod.BaseModel.DEFAULT_TIMEZONE)
            delta = m.get_delta()
            return delta
        df_positions_3['delta'] = df_positions_3.apply(_delta,axis=1)

        def _gamma(r):             
            m = opmod.model_from_symbol(r.symbol, r[self.price_column], vol=r.stdev, rate=rate,
                                        model=self.op_model, tzinfo=opmod.BaseModel.DEFAULT_TIMEZONE)
            gamma = m.get_gamma()
            return gamma
        df_positions_3['gamma'] = df_positions_3.apply(_gamma,axis=1)

        def _unit_var(r):
            stdev = r[self.price_column] * r.stdev * norm.ppf(var_confidence) * (var_days/256)**.5 
            return (r.delta * stdev + .5 * r.gamma * stdev**2) / r[self.price_column]
        
#         df_positions_3['unit_var'] = df_positions_3.apply(lambda r: r[self.price_column] * r.stdev * norm.ppf(.99) * (1/256)**.5 / r[self.price_column],axis=1 )
        df_positions_3['unit_var'] = df_positions_3.apply(_unit_var,axis=1 )
        df_positions_3['position_var'] = df_positions_3.apply(lambda r: r.unit_var * r.position * r[self.price_column] ,axis=1 )
        # create an spy standard deviation that is the historical average
        cols_no_symbol = [c for c in df_positions_3.columns.values if c != 'symbol']
        df_underlying_positions = df_positions_3[cols_no_symbol].groupby('underlying',as_index=False).sum()
        port_variance = df_underlying_positions.position_var.astype(float).as_matrix().T @ df_corr.astype(float).as_matrix() @ df_underlying_positions.position_var.astype(float).as_matrix()
        
        port_var = port_variance**.5 
        # get sp500 equivilants
        spy_usual_var = self.reference_current_price * spy_usual_std *  norm.ppf(var_confidence) * (var_days/256)**.5 
        sp_dollar_equiv = port_var / spy_usual_var * self.reference_current_price
        return {'df_underlying_positions':df_underlying_positions,'df_positions_all':df_positions_3,'port_var':port_var,'sp_dollar_equiv':sp_dollar_equiv,'df_atm_price':df_prices,'df_std':df_std}

        
    
if __name__ == '__main__':
    libor = FixedRateModel().get_rate(None)
    print(libor)
    
    positions_tuple = [
        ('SPY_20190322_272_c',200),
        ('USO',1),
        ('GLD',--300),
        ('SPY',0),
        ('XLU',-200),
        ('XLE',200)
    ]
    
    symbols = [t[0] for t in positions_tuple]
    positions = [t[1] for t in positions_tuple]

    df_portfolio = pd.DataFrame({'symbol':symbols,'position':positions})[['symbol','position']]
    vm = VarModel(df_portfolio=df_portfolio)
    var_dict = vm.compute_var()
    port_var = var_dict['port_var']
    df_positions = var_dict['df_underlying_positions']
    sp_dollar_equiv = var_dict['sp_dollar_equiv']    
    print(f"portolio VaR: {round(port_var,2)}")
    print(f'Equivalent S&P position (in dollars): {round(sp_dollar_equiv,2)}')
    print(df_positions)
    print(vm.df_corr)
    print(vm.df_std)

    vm = VarModel(df_portfolio=df_portfolio,bars_per_day=8*2,history_fetcher=BarChartFetcher30Min())
    var_dict = vm.compute_var()
    port_var = var_dict['port_var']
    df_positions = var_dict['df_underlying_positions']
    sp_dollar_equiv = var_dict['sp_dollar_equiv']
    print(f'portolio VaR: {round(port_var,2)}')
    print(f'Equivalent S&P position (in dollars): {round(sp_dollar_equiv,2)}')
    print(df_positions)
    print(vm.df_corr)
    print(vm.df_std)

