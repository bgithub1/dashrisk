'''
Created on Feb 5, 2019

Options models to create prices and greeks

@author: bperlman1
'''

import numpy as np
import pandas as pd
from scipy import stats as ss
import copy
import datetime
import pytz
from future.backports.datetime import tzinfo

class BlackScholesBasic(object):
    def __init__(self, *args, **kwargs):
        object.__init__(self, *args, **kwargs)
        
    #Black and Scholes
    def d1(self,S0, K, r, sigma, T):
        return (np.log(S0/K) + (r + sigma**2 / 2) * T)/(sigma * np.sqrt(T))
     
    def d2(self,S0, K, r, sigma, T):
        return self.d1(S0, K, r, sigma, T) - sigma * np.sqrt(T)
     
    def opt_price(self,callput,S0, K, r, sigma, T):
        if callput.lower()=="c":
            return S0 * ss.norm.cdf(self.d1(S0, K, r, sigma, T)) - K * np.exp(-r * T) * ss.norm.cdf(self.d2(S0, K, r, sigma, T))
        else:
            return K * np.exp(-r * T) * ss.norm.cdf(-self.d2(S0, K, r, sigma, T)) - S0 * ss.norm.cdf(-self.d1(S0, K, r, sigma, T))

    def delta(self,callput,S0, K, r, sigma, T):
        if callput.lower()!="c":
            return ss.norm.cdf(self.d1(S0, K, r, sigma, T))-1
        else:
            return ss.norm.cdf(self.d1(S0, K, r, sigma, T))


class BaseModel():
    REFERENCE_VOL = .2
    ONE_DAY_SCAL = (1/365.0)**.5
    ATM_PERCENT_CHANGE_PER_VOL = (.001/(REFERENCE_VOL))
    VOL_PERCENT_CHANGE = .01
    INTEREST_TO_CHANGE = .001
    DEFAULT_TIMEZONE = pytz.timezone('US/Eastern')
    
    def __init__(self,expiry_datetime,strike,c_p,atm_price,input_vol,rate,carry=None,time_zone=None):
        self.strike = strike
        self.c_p = c_p
        self.atm_price = atm_price
        self.input_vol = input_vol
        self.rate = rate
        self.carry=carry
        self.time_zone= BaseModel.DEFAULT_TIMEZONE if time_zone is None else time_zone
        dt_now = datetime.datetime.now().replace(tzinfo=BaseModel.DEFAULT_TIMEZONE)
        days = (dt_now- expiry_datetime).days
        if days < 1:
            days = 1
        self.dte = days/365.0   
            
    def get_option_price(self):
        bs = BlackScholesBasic()
        op = bs.opt_price(
                          self.c_p, 
                          self.atm_price, 
                          self.strike, 
                          self.rate, 
                          self.input_vol, 
                          self.dte
        )
        return op
    
    def clone(self):
        return copy.deepcopy(self) 
    
         
    def get_delta(self):
        op = self.get_option_price()         
        
        perc_to_move =  self.input_vol *  BaseModel.ATM_PERCENT_CHANGE_PER_VOL 
        model_up = self.clone()     
        price_move =  self.atm_price * perc_to_move  
        model_up.atm_price = self.atm_price + price_move 
        op_up = model_up.get_option_price() 
        model_down = self.clone()        
        model_down.atm_price = self.atm_price - price_move 
        op_down = model_down.get_option_price() 
        d = ((op-op_down) - (op - op_up)) / (2*price_move)
        return d
    
    def get_gamma(self):
        op = self.get_delta()
        perc_to_move =  self.input_vol *  BaseModel.ATM_PERCENT_CHANGE_PER_VOL 
        model_up = self.clone()     
        price_move =  self.atm_price * perc_to_move  
        model_up.atm_price = self.atm_price + price_move 
        op_up = model_up.get_delta() 
        model_down = self.clone()        
        model_down.atm_price = self.atm_price - price_move 
        op_down = model_down.get_delta() 
        d = ((op-op_down) - (op - op_up)) / (2*price_move)
        return d
        
    def get_vega(self):
        op = self.get_option_price()         
        vol_perc_to_move = BaseModel.VOL_PERCENT_CHANGE
        model_up = self.clone()     
        model_up.input_vol =  self.input_vol + vol_perc_to_move  
        op_up = model_up.get_option_price() 
        model_down = self.clone()        
        model_down.input_vol =  self.input_vol - vol_perc_to_move  
        op_down = model_down.get_option_price() 
        v = ((op-op_down) - (op - op_up)) / (2)
        return v
        
    def get_theta(self):
        op = self.get_option_price()         
        dte_change = 1/365.0
        model_down = self.clone()        
        model_down.dte =  self.dte - dte_change  
        op_down = model_down.get_option_price() 
        t = op-op_down
        return t

    def get_rho(self):
        op = self.get_option_price()         
        int_to_move = BaseModel.INTEREST_TO_CHANGE
        model_up = self.clone()     
        model_up.rate =  self.rate + int_to_move  
        op_up = model_up.get_option_price() 
        model_down = self.clone()        
        model_down.rate =  self.rate - int_to_move  
        op_down = model_down.get_option_price() 
        r = ((op-op_down) - (op - op_up)) / (2) * .01/BaseModel.INTEREST_TO_CHANGE
        return r


class BsModel(BaseModel):
    def __init__(self,expiry_datetime,strike,c_p,atm_price,input_vol,rate,carry=None,time_zone=None):
        super(BsModel,self).__init__(expiry_datetime,strike,c_p,atm_price,input_vol,rate,carry,time_zone)
    def get_delta(self):
        bs = BlackScholesBasic()
        return bs.delta(self.c_p, self.atm_price, self.strike, self.rate, self.input_vol, self.dte)



if __name__=='__main__':
    pc = 'c'
    s = 100
    k = 100
    vol = .2
    r = .03
    car = 0
    expiry_date = datetime.datetime.now().replace(tzinfo=BaseModel.DEFAULT_TIMEZONE) - datetime.timedelta(30)
    m = BaseModel(expiry_date,s,pc,k,vol,r,car)
    p = m.get_option_price()
    d = m.get_delta()
    g = m.get_gamma()
    v = m.get_vega()
    t = m.get_theta()
    rh = m.get_rho()
    print(p,d,g,v,t,rh)
    
    m = BaseModel(expiry_date,s,pc,k,vol,r-.01,car)
    p = m.get_option_price()
    print(p)
    m = BaseModel(expiry_date,s,pc,k,vol,r+.01,car)
    p = m.get_option_price()
    print(p)
    
    
        