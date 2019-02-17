'''
Created on Feb 16, 2019

@author: bperlman1
'''
import argparse as ap
import sys
import os
if  not './' in sys.path:
    sys.path.append('./')
if  not '../' in sys.path:
    sys.path.append('../')
from dashrisk import pg_pandas as pg
from os import listdir
from os.path import isfile, join
import pandas_datareader.data as web
import pandas as pd
import datetime as dt
import time
from dashrisk import logger_init as li

STOCKS_DIR = f'./temp_folder/stocks'
DEFAULT_DAYS_TO_FETCH = 120

def is_business_day(date):
    return bool(len(pd.bdate_range(date, date)))

def get_last_business_day(date):
    d = date
    for _ in range(5):
        if is_business_day(d):
            return d
        d = d - dt.timedelta(1)
    return None

class HistoryBuilder():
    def __init__(self,dburl=None,databasename=None,
                 username=None,password=None,schema_name=None,yahoo_daily_table=None,
                 logger=None,initial_stock_list=None,days_to_fetch=DEFAULT_DAYS_TO_FETCH):
        self.logger = logger if dburl is not None else li.init_root_logger('logfile.log', 'INFO')
        self.dburl = dburl if dburl is not None else 'localhost'
        self.username = username if username is not None else ''
        self.password = password if password is not None else ''
        self.databasename = databasename if databasename is not None else 'testdb'
        self.schema_name = schema_name if schema_name is not None else 'test_schema'
        self.yahoo_daily_table = yahoo_daily_table if yahoo_daily_table is not None else 'yahoo_daily'
        self.pga = pg.PgPandas(databasename=self.databasename,username=self.username,password=self.password,dburl=self.dburl)
        self.full_table_name = self.schema_name + '.' + self.yahoo_daily_table
        self.action_dict = {
            'update':self.update_yahoo_daily,
            'build_from_scratch': self.build_from_scratch,
            'build_from_csvs':self.build_pg_from_csvs,
            'add_new_symbols':self.add_new_symbols
        }
        self.initial_stock_list = self.get_sp_stocks() if initial_stock_list is None else initial_stock_list
        self.days_to_fetch = days_to_fetch
        
    def write_hist_dict_to_csv(self,hist_dict):
        try:
            os.makedirs(STOCKS_DIR)
        except:
            pass
        for sym,df in hist_dict.items():
            csv_path = f'{STOCKS_DIR}/{sym}.csv'
            self.logger.info(f'writing {sym} to {csv_path}')
            df['Date'] = df.index
            df.index = range(len(df))
            df.to_csv(csv_path,index=False)
            
            
    def build_history_dict(self):
        symbols = self.initial_stock_list
        hist_dict = {}
        end_date = dt.datetime.now()
        beg_date = end_date - dt.timedelta(self.days_to_fetch)
        for sym in symbols:
            self.logger.info(f'processing {sym}')
            try:
                df =web.DataReader(sym, 'yahoo', beg_date, end_date)
            except:
                try:
                    df =web.DataReader(sym, 'yahoo', beg_date, end_date)
                except Exception as e:
                    self.logger.warn(str(e))
                    continue
            hist_dict[sym] = df
            time.sleep(.5)
        return hist_dict
    
    def get_yahoo_data(self,sym,beg_date,end_date):
        try:
            df =web.DataReader(sym, 'yahoo', beg_date, end_date)
            return df
        except:
            try:
                df =web.DataReader(sym, 'yahoo', beg_date, end_date)
                return df
            except Exception as e:
                self.logger.warn(str(e))
        return None
    
    def get_sp_stocks(self):
        url_constituents = 'https://datahub.io/core/s-and-p-500-companies/r/constituents.csv'
        spydr_short_names = ['SPY','XLE','XLU','XLK','XLB','XLP','XLY','XLI','XLC','XLV','XLF']
        commodity_etf_short_names = ['USO','UNG','DBC','DBA','GLD','USCI']
        currency_etf_short_names = ['FXY','FXE','FXB','FXF','FXC','FXA']
        sp = list(pd.read_csv(url_constituents).Symbol)
        ret = sp + spydr_short_names + commodity_etf_short_names + currency_etf_short_names
        return ret
    
    
    def build_pg_from_csvs(self,delete_table_before_building=True):
        pga2 = self.pga        
        if delete_table_before_building:
            pga2.exec_sql_raw(f"drop table if exists {self.full_table_name}")
        try:
            # always try to build the table in case it's the first time
            sql = f"""
            create table {self.full_table_name}(
                symbol text not null,
                date Date not null,
                open numeric not null,
                high numeric not null,
                low numeric not null,
                close numeric not null,
                adj_close numeric not null,
                volume integer not null,
                primary key(symbol,Date));
            """            
            pga2.exec_sql_raw(sql) 
        except:
            # ignore
            pass
        stk_files = [s+'.csv' for s in self.initial_stock_list] if self.initial_stock_list is not None else   [f for f in listdir(STOCKS_DIR) if isfile(join(STOCKS_DIR, f))] 
        for csv_name in stk_files:
            csv_path = f'{STOCKS_DIR}/{csv_name}'
            df = pd.read_csv(csv_path)
            sym = csv_name.replace('.csv','')            
#             df['symbol'] = sym
#             self.logger.info(f'writing {sym} to postgres')
#             df = df.rename(columns = {c:c.lower().replace(' ','_') for c in df.columns.values})
            try:
#                 pga2.write_df_to_postgres_using_metadata(df=df,table_name=self.full_table_name)
                self.write_symbol_to_pg(sym,df)
            except Exception as e:
                self.logger.warn(str(e))
    
    def add_symbol_to_pg(self,symbol,dt_beg,dt_end):
        df = self.get_yahoo_data(symbol,dt_beg,dt_end)
        self.write_symbol_to_pg(symbol, df)

    def write_symbol_to_pg(self,symbol,df):
        if len(df)>0:
            df['symbol'] = symbol
            df_this_stock = self.yahoo_to_pg(df)
            df_already_there = self.pga.get_sql(f"select date from {self.full_table_name} where symbol='{symbol}'")
            df_to_write = df_this_stock[~df_this_stock.date.isin(df_already_there.date)]
            if len(df_to_write)<1:
                self.logger.warn(f'write_symbol_to_pg: no new data to write for symbol {symbol}')
                return
            self.pga.write_df_to_postgres_using_metadata(df=df_to_write,table_name=self.full_table_name)
        else:
            raise ValueError(f'cannot find Yahoo data for {symbol}')        
    
    def update_yahoo_daily(self,dt_beg=None,dt_end=None):
        '''
        Update existing symbols in database with new days data
        :param dt_beg:
        :param dt_end:
        '''
        pga2 = self.pga
        sql_get = f"""
        select symbol,max(date) max_date, min(date) min_date from {self.full_table_name}
        group by symbol
        """
                
        df_last_dates = pga2.get_sql(sql_get)
        for i in range(len(df_last_dates)):
            r  = df_last_dates.iloc[i]
            
            end_date = dt_end if dt_end is not None else dt.datetime.now()
            end_date = get_last_business_day(end_date)                
            beg_date = dt_beg if dt_beg is not None else end_date - dt.timedelta(self.days_to_fetch)
            db_min_date = dt.datetime.combine(r.min_date, dt.datetime.min.time())
            db_max_date = dt.datetime.combine(r.max_date, dt.datetime.max.time())
            if (db_min_date - beg_date).days <= 4: # account for weekends + or long holiday
                # move the begin date up because you already have this data
                beg_date = db_max_date + dt.timedelta(1)   
            if beg_date >= end_date:
                self.logger.info(f'{r.symbol} nothing to update')
                continue   
            if end_date <= db_max_date:
                self.logger.info(f'{r.symbol} nothing to update')
                continue   
            try:
                self.add_symbol_to_pg(r.symbol, beg_date, end_date)
                self.logger.info(f'{r.symbol} updated')
            except Exception as e:
                self.logger.warn(str(e))
                continue
            
#         
#             df_this_stock = self.get_yahoo_data(r.symbol,beg_date,end_date)
#             if df_this_stock is None or len(df_this_stock)<1:
#                 self.logger.info(f'{r.symbol} nothing to update')
#                 continue
#             df_this_stock['symbol'] = r.symbol
#             df_this_stock = self.yahoo_to_pg(df_this_stock)
#             df_this_stock = df_this_stock[~df_this_stock.date.isin(set(df_last_dates.date))]
#             if len(df_this_stock)>0:
#                 try:
#                     pga2.write_df_to_postgres_using_metadata(df=df_this_stock,table_name=self.full_table_name)
#                 except Exception as e:
#                     self.logger.warn(str(e))
#                     self.logger.info(f'{r.symbol} nothing to update')
#                     continue
#                 self.logger.info(f'{r.symbol} updated')
#             else:
#                 self.logger.info(f'{r.symbol} nothing to update')

    def get_pg_data(self,symbol,dt_beg,dt_end):
        sql_dt_beg = dt_beg.strftime('%Y-%m-%d')
        sql_dt_end = dt_end.strftime('%Y-%m-%d')
        
        sql_get = f"""
        select * from {self.full_table_name}
        where symbol='{symbol}' and date>='{sql_dt_beg}' and date<='{sql_dt_end}'
        """        
        df = self.pga.get_sql(sql_get)
#         df = self.pg_to_yahoo(df)
        return df
    
    def yahoo_to_pg(self,df_in):
        df = df_in.copy()
        df['date'] = df.index
        df.index = range(len(df))
        df = df.rename(columns = {c:c.lower().replace(' ','_') for c in df.columns.values})
        return df
    
    def pg_to_yahoo(self,df_in):
        df = df_in.copy()
        df.index = df.date
        df = df.rename(columns = {c:c[0].upper()+c[1:].replace('_',' ') for c in df.columns.values})
        df = df.rename(columns={'Adj close':'Adj Close'})
        return df        
    
    def build_from_scratch(self):
        hist_dict = self.build_history_dict()
        self.write_hist_dict_to_csv(hist_dict)
        self.build_pg_from_csvs()
      
    def build_from_csvs(self):
        self.build_pg_from_csvs()
    
    def add_new_symbols(self):
        hist_dict = self.build_history_dict()
        self.write_hist_dict_to_csv(hist_dict)
        self.build_pg_from_csvs(delete_table_before_building=False)
    
    def do_action(self,action):
        self.action_dict[action]()
        


if __name__ == '__main__':
    start_time = dt.datetime.now()
    print(start_time)
    parser = ap.ArgumentParser()
    parser.add_argument('--action',type=str,help='update (default), build_from_scratch, build_from_csvs, add_new_symbols',
                        default='update')
    parser.add_argument('--initial_stock_list',type=str,help='a comma separated list of stock names.  If blank, use SP500 constituents',
                        nargs='?')
    args = parser.parse_args()
    action = args.action
    isl = args.initial_stock_list
    if isl is not None:
        isl = isl.split(',')
    hb = HistoryBuilder(initial_stock_list=isl)
    hb.do_action(action)
    end_time = dt.datetime.now()
    print(start_time)
    print(end_time - start_time)
        
    