#!/usr/bin/env python3
"""Reproducible seasonality curves. Requires pandas, numpy, matplotlib."""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

DEFAULTS = {'XAUUSD':('xauusd_daily.csv',2001,2025),'JCI':('jci_daily.csv',1984,2025),'EURUSD':('eurusd_daily.csv',1999,2025),'USD_INDEX':('usd_index_daily.csv',1971,2025)}
THEME={'XAUUSD':'#e5ae42','JCI':'#49c6b1','EURUSD':'#7d9cf7','USD_INDEX':'#ed8b77'}
plt.rcParams.update({'figure.facecolor':'#101622','axes.facecolor':'#161f2d','savefig.facecolor':'#101622','text.color':'#eaf0f8','axes.labelcolor':'#c8d4e3','xtick.color':'#aebdd0','ytick.color':'#aebdd0','axes.edgecolor':'#405067','font.family':'DejaVu Sans','font.size':10})

def read_prices(path):
    d=pd.read_csv(path); d.columns=[x.strip().title() for x in d.columns]
    if not {'Date','Open','Close'}.issubset(d.columns): raise ValueError('Need Date, Open, Close columns')
    d['Date']=pd.to_datetime(d['Date'],errors='coerce'); d['Open']=pd.to_numeric(d['Open'],errors='coerce'); d['Close']=pd.to_numeric(d['Close'],errors='coerce')
    d=d.dropna(subset=['Date','Open','Close']).query('Open > 0 and Close > 0').sort_values('Date').drop_duplicates('Date',keep='last')
    return d

def period_label(dt,horizon):
    if horizon=='quarterly': return f'Q{(dt.month-1)//3+1}'
    if horizon=='semiannual': return 'H1' if dt.month<=6 else 'H2'
    return 'Annual'

def key(dt,horizon):
    return (dt.year,period_label(dt,horizon))

def episodes(df,start,end,horizon):
    df=df[(df.Date.dt.year>=start)&(df.Date.dt.year<=end)].copy()
    df['yr']=df.Date.dt.year; df['slot']=df.Date.map(lambda d:period_label(d,horizon))
    out=[]
    for (year,slot),g in df.groupby(['yr','slot'],sort=True):
        # Verify full calendar slot within analysis window and minimum trading observations
        if len(g)<({'quarterly':35,'semiannual':75,'annual':160}[horizon]):continue
        g=g.sort_values('Date'); base=float(g.Open.iloc[0]); ret=(g.Close.to_numpy(dtype=float)/base-1)*100
        # Explicit 0 at episode open; x is normalized trading-session progress, 0..1.
        x=np.r_[0,np.arange(1,len(g)+1)/len(g)]; y=np.r_[0,ret]
        out.append({'year':int(year),'slot':slot,'x':x,'y':y,'n':len(g),'end':float(ret[-1])})
    return out

def sample_episode(ep,horizon):
    # Daily: each trading session; 2D: every second trading session; weekly: every fifth trading session.
    stride={'quarterly':1,'semiannual':2,'annual':5}[horizon]
    indices=list(range(0,len(ep['y']),stride))
    if indices[-1]!=len(ep['y'])-1:indices.append(len(ep['y'])-1)
    return ep['x'][indices],ep['y'][indices]

def aggregated(eps,horizon,asset):
    # Fixed common progress grid; interpolation needed because holiday calendars differ.
    # Quarter 64 points, half-year 65, year 53. Underlying sampling respects 1/2/5 sessions.
    grid=np.linspace(0,1,{'quarterly':64,'semiannual':65,'annual':53}[horizon]); stack=[]
    for ep in eps:
        x,y=sample_episode(ep,horizon)
        stack.append(np.interp(grid,x,y))
    a=np.array(stack)
    rows=[]
    for i,x in enumerate(grid):
        v=a[:,i]
        rows.append({'asset':asset,'horizon':horizon,'slot':eps[0]['slot'],'progress':x,'step':i,'n_years':len(eps),'mean_cumulative_pct':v.mean(),'median_cumulative_pct':np.median(v),'p25_cumulative_pct':np.percentile(v,25),'p75_cumulative_pct':np.percentile(v,75),'p10_cumulative_pct':np.percentile(v,10),'p90_cumulative_pct':np.percentile(v,90)})
    return pd.DataFrame(rows),a

def decorate(ax,title,subtitle,grid,horizon):
    ax.set_title(title,loc='left',fontweight='bold',fontsize=14,pad=19)
    ax.text(0,1.01,subtitle,transform=ax.transAxes,fontsize=8.5,color='#aabbd0')
    ax.axhline(0,color='#93a5ba',lw=.8,alpha=.7); ax.grid(alpha=.15,axis='y'); ax.set_xlim(0,1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:+.0f}%'))
    if horizon=='annual':
        ax.set_xticks(np.linspace(0,1,13)); ax.set_xticklabels(['Jan','','Mar','','May','','Jul','','Sep','','Nov','','Jan'],fontsize=8)
        for v in [.25,.5,.75]:ax.axvline(v,color='#93a5ba',lw=.7,alpha=.35,ls='--')
    else:
        ax.set_xticks(np.linspace(0,1,5));ax.set_xticklabels(['Start','25%','50%','75%','End'])
    for spine in ax.spines.values():spine.set_visible(False)

def plot_horizon(asset,horizon,ep,output):
    slots={'quarterly':['Q1','Q2','Q3','Q4'],'semiannual':['H1','H2'],'annual':['Annual']}[horizon]
    fig,axes=plt.subplots(2,2,figsize=(16,10)) if horizon=='quarterly' else plt.subplots(1,len(slots),figsize=(16,6))
    axes=np.array(axes).flatten(); allcurves=[]; stats=[]; color=THEME.get(asset,'#62b6f5')
    for ax,slot in zip(axes,slots):
        group=[e for e in ep if e['slot']==slot]
        if not group:ax.text(.5,.5,'No complete episodes',ha='center');continue
        agg,stack=aggregated(group,horizon,asset);allcurves.append(agg)
        x=agg.progress.to_numpy(); mean=agg.mean_cumulative_pct.to_numpy();median=agg.median_cumulative_pct.to_numpy()
        for curve in stack:ax.plot(x,curve,color='#8c9bad',lw=.65,alpha=.15,zorder=1)
        ax.fill_between(x,agg.p25_cumulative_pct.to_numpy(),agg.p75_cumulative_pct.to_numpy(),color=color,alpha=.20,label='25th–75th percentile',zorder=2)
        ax.plot(x,mean,color=color,lw=2.6,label='Mean',zorder=3)
        ax.plot(x,median,color='#f6f8fb',lw=1.6,ls='--',label='Median',zorder=4)
        ends=np.array([e['end'] for e in group]); stats.append({'asset':asset,'horizon':horizon,'slot':slot,'n_years':len(group),'bullish_count':int((ends>0).sum()),'bullish_pct':100*(ends>0).mean(),'mean_return_pct':ends.mean(),'median_return_pct':np.median(ends),'mean_positive_pct':ends[ends>0].mean() if (ends>0).any() else np.nan,'mean_negative_pct':ends[ends<0].mean() if (ends<0).any() else np.nan,'min_pct':ends.min(),'max_pct':ends.max()})
        decorate(ax,slot,f'{len(group)} years   |   bullish {(ends>0).mean()*100:.1f}%   |   mean {ends.mean():+.2f}%',x,horizon)
    fig.suptitle(f'{asset.replace("_"," ")}  /  {horizon.upper()} SEASONALITY',fontsize=21,fontweight='bold',x=.06,ha='left',y=.995)
    fig.text(.06,.947,{'quarterly':'DAILY sampling  •  Each quarter starts at 0%','semiannual':'2 TRADING-DAY sampling  •  Each semester starts at 0%','annual':'WEEKLY (5 trading-session) sampling  •  Each year starts at 0%'}[horizon],color='#b0c1d3',fontsize=10)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,.006))
    fig.subplots_adjust(top=.86,bottom=.11,left=.075,right=.96,hspace=.36,wspace=.19)
    fig.savefig(output/f'{asset.lower()}_{horizon}_seasonality.png',dpi=170);plt.close(fig)
    return allcurves,stats

def main():
    p=argparse.ArgumentParser();p.add_argument('--input-dir',default='input');p.add_argument('--out',default='output');p.add_argument('--asset',default='all',help='all, XAUUSD, JCI, EURUSD, USD_INDEX');args=p.parse_args()
    inp=Path(args.input_dir);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assets=list(DEFAULTS) if args.asset.lower()=='all' else [args.asset.upper()]
    curves=[];stats=[];episodes_table=[]
    for asset in assets:
        filename,start,end=DEFAULTS[asset];data=read_prices(inp/filename)
        for horizon in ('quarterly','semiannual','annual'):
            eps=episodes(data,start,end,horizon)
            for e in eps:episodes_table.append({'asset':asset,'horizon':horizon,'year':e['year'],'slot':e['slot'],'trading_sessions':e['n'],'period_return_pct':e['end']})
            c,s=plot_horizon(asset,horizon,eps,out);curves.extend(c);stats.extend(s)
        print(f'{asset}: {start}-{end} complete calendar years, charts generated')
    pd.concat(curves,ignore_index=True).to_csv(out/'seasonal_curves.csv',index=False)
    pd.DataFrame(stats).to_csv(out/'seasonal_statistics.csv',index=False)
    pd.DataFrame(episodes_table).to_csv(out/'seasonal_episodes.csv',index=False)
    if len(assets)==1: return
    # Comparison of annual seasonal curves
    fig,ax=plt.subplots(figsize=(15,7))
    for asset in assets:
        d=pd.concat([c for c in curves if c.asset.iloc[0]==asset and c.horizon.iloc[0]=='annual'])
        ax.plot(d.progress,d.mean_cumulative_pct,label=f'{asset} ({int(d.n_years.iloc[0])} years)',lw=2.3,color=THEME[asset])
    ax.axhline(0,color='#9bafc5',lw=.8);ax.grid(alpha=.15);ax.legend(frameon=False,ncol=2)
    ax.set_xticks(np.linspace(0,1,13));ax.set_xticklabels(['Jan','','Mar','','May','','Jul','','Sep','','Nov','','Jan']);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,p:f'{v:+.0f}%'))
    ax.set_title('ANNUAL SEASONALITY  /  CROSS-ASSET COMPARISON',loc='left',fontweight='bold',fontsize=18,pad=22)
    ax.text(0,1.01,'Mean cumulative return from annual open  |  5-trading-session sampling  |  different historical windows',transform=ax.transAxes,color='#b0c1d3',fontsize=9)
    fig.subplots_adjust(left=.08,right=.97,top=.85,bottom=.11);fig.savefig(out/'annual_cross_asset_comparison.png',dpi=170);plt.close(fig)
if __name__=='__main__':main()
