#


import os
from pylivetrader.api import *
from logbook import Logger, StreamHandler
import sys
StreamHandler(sys.stdout).push_application()
log = Logger(__name__)
# -*- coding: utf-8 -*-
import pylivetrader.algorithm as algo
from zipline.pipeline import Pipeline, CustomFactor
from pipeline_live.data.alpaca.pricing import USEquityPricing
from pipeline_live.data.iex.fundamentals import IEXKeyStats
from pylivetrader.api import schedule_function
import numpy as np
from pipeline_live.data.iex.factors import AverageDollarVolume

def initialize(context):
    
    context.attach_pipeline(make_pipeline(), 'pipeline') 
    
    #Schedule Functions
    schedule_function(trade, date_rules.month_end() , time_rules.market_close(minutes=30))
    schedule_function(trade_bonds, date_rules.month_end(), time_rules.market_close(minutes=20))
    
    #This is for the trend following filter
    context.spy = symbol('SPY')
    context.TF_filter = False
    context.TF_lookback = 126
    context.function_bool = True
    
    schedule_function(func=initial_trade,  
                      date_rule=date_rules.every_day(),  
                      time_rule=time_rules.market_close(minutes=30))  
    
    #Set number of securities to buy and bonds fund (when we are out of stocks)
    context.Target_securities_to_buy = 20.0
    context.bonds = symbol('IEF')
    
    os.environ["IEX_TOKEN"] = "sk_74eb6a4ba7974d849625e034959efa11"
    
    #Other parameters
    context.top_n_roe_to_buy = 50 #First sort by ROE
    context.relative_momentum_lookback = 126 #Momentum lookback
    context.momentum_skip_days = 10
    context.top_n_relative_momentum_to_buy = 20 #Number to buy
    
def make_pipeline():
    # Base universe set to the Q500US
    universe = AverageDollarVolume(window_length=300).top(500)
    roic = IEXKeyStats.returnOnCapital.latest
    pipe = Pipeline(columns={'roic': roic},screen=universe)
    return pipe
def before_trading_start(context, data):
    
    context.output = context.pipeline_output('pipeline')
    context.security_list = context.output.index

def initial_trade(context, data):
    if context.function_bool == True:  
            trade(context,data)  
            context.function_bool = False
        
def trade(context, data):
    ############Trend Following Regime Filter############
    TF_hist = data.history(context.spy , "close", 140, "1d")
    TF_check = TF_hist.pct_change(context.TF_lookback).iloc[-1]
    if TF_check > 0.0:
        context.TF_filter = True
    else:
        context.TF_filter = False
    ############Trend Following Regime Filter End############
    
    #DataFrame of Prices for our 500 stocks
    prices = data.history(context.security_list,"close", 180, "1d")      
    #DF here is the output of our pipeline, contains 500 rows (for 500 stocks) and one column - ROE
    df = context.output  
    
    #Grab top 50 stocks with best ROE
    top_n_roic = df.nlargest(context.top_n_roic_to_buy, "roic")
    #Calculate the momentum of our top ROE stocks   
    #Grab stocks with best momentum    
    #top_n_by_momentum = top_n_roic.nsmallest(context.top_n_relative_momentum_to_buy, "mfi")
    
    quality_momentum = prices[top_n_roic.index][:-context.momentum_skip_days].pct_change(context.relative_momentum_lookback).iloc[-1]
    #Grab stocks with best momentum    
    top_n_by_momentum = quality_momentum.nlargest(context.top_n_relative_momentum_to_buy)
    
 #when mfi < 20 , thats buy signal, when the mfi crosses 80, thats sell signal
    for x in context.portfolio.positions:
        if (x.sid == context.bonds):
            pass
        elif x not in top_n_by_momentum:
            order_target_percent(x, 0)
            print(('GETTING OUT OF',x))
    
    for x in top_n_by_momentum.index:
        if x not in context.portfolio.positions and context.TF_filter==True:
            order_target_percent(x, (1.0 / context.Target_securities_to_buy))
            print(('GETTING IN',x))
            
            
            
def trade_bonds(context , data):
    amount_of_current_positions=0
    if context.portfolio.positions[context.bonds].amount == 0:
        amount_of_current_positions = len(context.portfolio.positions)
    if context.portfolio.positions[context.bonds].amount > 0:
        amount_of_current_positions = len(context.portfolio.positions) - 1
    percent_bonds_to_buy = (context.Target_securities_to_buy - amount_of_current_positions) * (1.0 / context.Target_securities_to_buy)
    order_target_percent(context.bonds , percent_bonds_to_buy)
    
class MFI(CustomFactor):  
    """  
    Money Flow Index  
    Volume Indicator  
    **Default Inputs:**  USEquityPricing.high, USEquityPricing.low, USEquityPricing.close, USEquityPricing.volume  
    **Default Window Length:** 15 (14 + 1-day for difference in prices)  
    http://www.fmlabs.com/reference/default.htm?url=MoneyFlowIndex.htm  
    """     
    inputs = [USEquityPricing.high, USEquityPricing.low, USEquityPricing.close, USEquityPricing.volume]  
    window_length = 15
    def compute(self, today, assets, out, high, low, close, vol):
        # calculate typical price  
        typical_price = (high + low + close) / 3.
        # calculate money flow of typical price  
        money_flow = typical_price * vol
        # get differences in daily typical prices  
        tprice_diff = (typical_price - np.roll(typical_price, 1, axis=0))[1:]
        # create masked arrays for positive and negative money flow  
        pos_money_flow = np.ma.masked_array(money_flow[1:], tprice_diff < 0, fill_value = 0.)  
        neg_money_flow = np.ma.masked_array(money_flow[1:], tprice_diff > 0, fill_value = 0.)
        # calculate money ratio  
        money_ratio = np.sum(pos_money_flow, axis=0) / np.sum(neg_money_flow, axis=0)
        # MFI  
        out[:] = 100. - (100. / (1. + money_ratio))
        
    
def handle_data(context, data):
    pass