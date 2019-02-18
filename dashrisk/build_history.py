'''
Created on Feb 16, 2019

Use the main in this module to build an history sql database, by instantiating an
  instance of HistoryBuilder.

Usage: (make sure your virtualenv has all the dependencies in ../requirements.txt)

1. Build database from scratch, using symbols from the SP 500, the sector spdr ETF's 
   and the commodity ETFs
$ python3 build_history.py --delete_schema True --fetch_from_yahoo True --build_table True

2. Update the existing symbols in the database
$ python3 build_history.py --update_table  True

3. Delete the existing table, and recreate it
$ python3 build_history.py --delete_table --True --fetch_from_yahoo True --build_table True


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
    def __init__(self,
                 delete_schema=False,
                 delete_table=False,
                 fetch_from_yahoo=False,
                 build_table=False,
                 update_table=True,
                 beg_date=None,
                 end_date=None,
                 dburl=None,
                 databasename=None,
                 username=None,
                 password=None,
                 schema_name=None,
                 yahoo_daily_table=None,
                 initial_symbol_list=None,
                 days_to_fetch=DEFAULT_DAYS_TO_FETCH,
                 logger=None):
        self.delete_schema = delete_schema
        self.delete_table = delete_table
        self.fetch_from_yahoo = fetch_from_yahoo
        self.build_table = build_table
        self.update_table = update_table
        self.beg_date = beg_date
        self.end_date = end_date
        self.logger = logger if dburl is not None else li.init_root_logger('logfile.log', 'INFO')
        self.dburl = dburl if dburl is not None else 'localhost'
        self.username = username if username is not None else ''
        self.password = password if password is not None else ''
        self.databasename = databasename if databasename is not None else 'testdb'
        self.schema_name = schema_name if schema_name is not None else 'test_schema'
        self.yahoo_daily_table = yahoo_daily_table if yahoo_daily_table is not None else 'yahoo_daily'
        self.pga = pg.PgPandas(databasename=self.databasename,username=self.username,password=self.password,dburl=self.dburl)
        self.full_table_name = self.schema_name + '.' + self.yahoo_daily_table
        self.initial_symbol_list = self.get_sp_stocks() if initial_symbol_list is None else initial_symbol_list
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
        symbols = self.initial_symbol_list
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
    
    
    def build_pg_from_csvs(self,delete_table_before_building=False):
#         pga2 = self.pga        
#         if delete_table_before_building:
#             pga2.exec_sql_raw(f"drop table if exists {self.full_table_name}")
#         try:
#             # try creating the schema, just in case
#             pga2.exec_sql_raw(f"create schema {self.schema_name};")
#         except:
#             pass
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
            self.pga.exec_sql_raw(sql) 
        except:
            # ignore
            pass
        stk_files = [s+'.csv' for s in self.initial_symbol_list] if self.initial_symbol_list is not None else   [f for f in listdir(STOCKS_DIR) if isfile(join(STOCKS_DIR, f))] 
        for csv_name in stk_files:
            csv_path = f'{STOCKS_DIR}/{csv_name}'
            try:
                df = pd.read_csv(csv_path)
                sym = csv_name.replace('.csv','')            
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
            df_to_write = df_this_stock.copy()
            if len(df_already_there) > 0:
                df_to_write = df_this_stock[~df_this_stock.date.isin(df_already_there.date)]
            if len(df_to_write)<1:
                self.logger.warn(f'write_symbol_to_pg: no new data to write for symbol {symbol}')
                return
            self.logger.info(f'writing {symbol} to database')
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
        df = df.rename(columns = {c:c.lower().replace(' ','_') for c in df.columns.values})
        if 'date' not in df.columns.values and df.index.name.lower()=='date':
            df['date'] = df.index
            df.index = range(len(df))
        return df
    
    def pg_to_yahoo(self,df_in):
        df = df_in.copy()
        df.index = df.date
        df = df.rename(columns = {c:c[0].upper()+c[1:].replace('_',' ') for c in df.columns.values})
        df = df.rename(columns={'Adj close':'Adj Close'})
        return df        
    
#     def build_from_scratch(self):
#         hist_dict = self.build_history_dict()
#         self.write_hist_dict_to_csv(hist_dict)
#         self.build_pg_from_csvs()
#       
#     def build_from_csvs(self):
#         self.build_pg_from_csvs()
#     
#     def add_new_symbols(self):
#         hist_dict = self.build_history_dict()
#         self.write_hist_dict_to_csv(hist_dict)
#         self.build_pg_from_csvs(delete_table_before_building=False)
#     
#     def do_action(self,action):
#         self.action_dict[action]()
        
        
    def delete_pg_table(self):
        self.pga.exec_sql_raw(f"drop table if exists {self.full_table_name}")
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
        self.pga.exec_sql_raw(sql) 
    
    def execute(self):
        if self.delete_table:
            self.delete_pg_table()

        if self.delete_schema:
            self.pga.exec_sql_raw(f"DROP SCHEMA IF EXISTS  {self.schema_name};")
            self.pga.exec_sql_raw(f"create schema {self.schema_name};")
        
            
        if self.fetch_from_yahoo:
            hist_dict = self.build_history_dict()
            self.write_hist_dict_to_csv(hist_dict=hist_dict)
        if self.build_table:
            self.build_pg_from_csvs()
        if self.update_table:
            self.update_yahoo_daily(self.beg_date, self.end_date)


if __name__ == '__main__':
    logger = li.init_root_logger('logger.log','INFO') 
    start_time = dt.datetime.now()
    logger.info(f'starting at {start_time}')
    parser = ap.ArgumentParser()
#     parser.add_argument('--action',type=str,help='update (default), build_from_scratch, build_from_csvs, add_new_symbols',
#                         default='update')


    parser.add_argument('--delete_schema',type=bool,
                    help='delete schema (default=False)',
                    default=False)
    parser.add_argument('--delete_table',type=bool,
                    help='delete_table schema (default=False)',
                    default=False)
    parser.add_argument('--fetch_from_yahoo',type=bool,
                    help='fetch_from_yahoo schema (default=False)',
                    default=False)
    parser.add_argument('--build_table',type=bool,
                    help='build_table schema (default=False)',
                    default=False)
    parser.add_argument('--update_table',type=bool,
                    help='update_table schema (default=False)',
                    default=False)
    parser.add_argument('--beg_date_yyyymmddhhmmss',type=str,
                    help='yyyymmdd or yyyymmddhhmmss string that is converted to beginning datetime.dateime object for yahoo fetches (default datetime.datetime.now - datetime.timedelta(days_to_fetch)',
                    nargs='?')
    parser.add_argument('--end_date_yyyymmddhhmmss',type=str,
                    help='yyyymmdd or yyyymmddhhmmss string that is converted to ending datetime.dateime object for yahoo fetches (default datetime.datetime.now)',
                    nargs='?')
    parser.add_argument('--dburl',type=str,
                    help='database url (None will be localhost)',
                    nargs='?')
    parser.add_argument('--databasename',type=str,
                    help='databasename (None will be maindb)',
                    nargs='?')
    parser.add_argument('--username',type=str,
                    help='username (None will be postgres)',
                    nargs='?')
    parser.add_argument('--password',type=str,
                    help='password (None will be blank)',
                    nargs='?')
    parser.add_argument('--schema_name',type=str,
                    help='schema name for table (None will be test_schema)',
                    nargs='?')
    parser.add_argument('--yahoo_daily_table',type=str,
                    help='table name for table (None will be yahoo_daily)',
                    nargs='?')
    parser.add_argument('--initial_symbol_list',type=str,
                    help='comma separated list of symbols, like SPY,AAPL,XLE (default is list of SP500 stocks and main sector and commodity etfs)',
                    nargs='?')
    parser.add_argument('--days_to_fetch',type=str,
                    help=f"number of days of history to fetch (None will be {DEFAULT_DAYS_TO_FETCH})",
                    default=DEFAULT_DAYS_TO_FETCH)
    args = parser.parse_args()

    days_to_fetch = args.days_to_fetch
    end_date = dt.datetime.now() 
    if args.end_date_yyyymmddhhmmss is not None:
        yyyy = args.end_date_yyyymmddhhmmss[0:4]
        month = args.end_date_yyyymmddhhmmss[4:6]
        day = args.end_date_yyyymmddhhmmss[6:8]
        #dt.datetime.max.time()        
        hour = args.end_date_yyyymmddhhmmss[8:10] if len(args.end_date_yyyymmddhhmmss)>8 else 23
        minute = args.end_date_yyyymmddhhmmss[10:12] if len(args.end_date_yyyymmddhhmmss)>10 else 1
        second =  args.end_date_yyyymmddhhmmss[12:14] if len(args.end_date_yyyymmddhhmmss)>12 else 1
        end_date = dt.datetime(yyyy,month,day,hour,minute,second)
    beg_date = end_date  - dt.timedelta(days_to_fetch) 
    
    if args.beg_date_yyyymmddhhmmss is not None:
        yyyy = args.beg_date_yyyymmddhhmmss[0:4]
        month = args.beg_date_yyyymmddhhmmss[4:6]
        day = args.beg_date_yyyymmddhhmmss[6:8]
        #dt.datetime.max.time()        
        hour = args.beg_date_yyyymmddhhmmss[8:10] if len(args.beg_date_yyyymmddhhmmss)>8 else 23
        minute = args.beg_date_yyyymmddhhmmss[10:12] if len(args.beg_date_yyyymmddhhmmss)>10 else 1
        second =  args.beg_date_yyyymmddhhmmss[12:14] if len(args.beg_date_yyyymmddhhmmss)>12 else 1
        beg_date = dt.datetime(yyyy,month,day,hour,minute,second)
    
    hb = HistoryBuilder(
        args.delete_schema, args.delete_table, 
        args.fetch_from_yahoo, args.build_table, args.update_table, 
        beg_date, end_date, args.dburl, 
        args.databasename, args.username, args.password, 
        args.schema_name, args.yahoo_daily_table, args.initial_symbol_list, 
        args.days_to_fetch, logger)
    
    hb.execute()
    end_time = dt.datetime.now()
    logger.info(f'ending at {end_time}')
    elapsed_time = end_time - start_time
    logger.info(f'elapsed time {elapsed_time}')
        
    