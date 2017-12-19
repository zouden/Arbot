import requests
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter
import ccxt
def get_euro_rate():
    ## get fiat exchange rates in EUR
    r=requests.get('https://api.fixer.io/latest?base=EUR')
    return r.json()['rates']

def get_kraken_to_btcmarkets():
    #compare prices for EUR and AUD markets on Kraken and BTCmarkets
    #returns a dataframe of timestamp, token, profit
    
    # find all the AUD markets on btcmarkets
    btcmarkets = ccxt.btcmarkets()
    btcmarkets.load_markets()
    for name, marketdata in btcmarkets.markets.items():
        if marketdata['quote'] == 'AUD':
            marketdata.update(btcmarkets.fetch_ticker(name)['info'])
    btcmarketsdf = pd.DataFrame(btcmarkets.markets).T.query('quote == "AUD"')
    # Now do the same thing on Kraken
    kraken = ccxt.kraken()
    #here we can actually get all markets and all tickers in just 2 calls
    krakendf = pd.DataFrame(kraken.load_markets()).T
    #we are mainly interested in the bid price since we just need to make the highest bid
    krakenbids = pd.Series({name: tickerdata['bid'] for name, tickerdata in kraken.fetch_tickers().items()})
    krakendf['bid']=krakenbids
    # only look at euro ones
    krakendf = krakendf.query('quote=="EUR" and active==True and darkpool==False')
    #withdrawal_fees = {'BTC':0.001}
    ## Okay how can we sell these tokens at btcmarkets?
    df = pd.merge(btcmarketsdf, krakendf, on='base')
    rates = get_euro_rate()
    df['eurobid'] = df.bestBid / rates['AUD']
    df['profit'] = (df.eurobid / df.bid) * (1 - df.taker_y) * (1 - df.taker_x) - 1
    df = df.sort_values('profit', ascending=False)
    #assign all these results the same timestamp because they are close enough
    df.timestamp = pd.to_datetime(df.timestamp.max(),unit='s')
    return df[['timestamp','instrument','profit']]

def print_results_table(results): 
    #just a small table of current profits as a text output
    for row in results.itertuples():
        print(f'{row.instrument} {row.profit:0.2%}')
    print(f'({results.iloc[0].instrument}<>{results.iloc[-1].instrument}) {results.iloc[0].profit-results.iloc[-1].profit:0.2%}')
#%%
def save_results(results):
    #append results to a flat file
    with open('results.txt','a') as outfile:
        results.to_csv(outfile, header=False, index=False)
#%%
def chart_results():
    #read results from flat file and make a chart
    sns.set_style('darkgrid')
    sns.set_context('talk')
    rdf = pd.read_csv('results.txt', header=None, names=['timestamp','instrument','profit'])
    rdf = rdf.pivot(index='timestamp',columns='instrument',values='profit')
    rdf.index = pd.DatetimeIndex(rdf.index)
    #sort the columns so the current-highest-profit one is first
    rdf = rdf[rdf.iloc[-1].sort_values(ascending=False).index]
    #name the columns with the current profit value
    rdf.columns = [f'{name} {profit:0.2%}' for name, profit in rdf.iloc[-1].iteritems()]
    ax = rdf.plot(figsize=(12,8), title='Arbitrage Kraken to BTC Markets')
    ax.yaxis.set_major_formatter(FuncFormatter('{0:.1%}'.format))
    fig = ax.get_figure()
    fig.savefig('chart.png')
    return ax
#%%
## This code should run every 5 minutes or so
results = get_kraken_to_btcmarkets()
print_results_table(results)
save_results(results)
chart_results();
