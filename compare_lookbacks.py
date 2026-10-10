import argparse
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from seasonality_engine import read_prices, episodes, aggregated

p=argparse.ArgumentParser()
p.add_argument('--csv',default='input/xauusd_daily.csv');p.add_argument('--end-year',type=int,default=2025);p.add_argument('--windows',type=int,nargs='+',default=[5,10,15]);p.add_argument('--out',default='output')
a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
df=read_prices(a.csv); colors={5:'#eab65d',10:'#6dbed8',15:'#b58cff'}
allcurves=[]; allstats=[]; allsimilar=[]
for horizon,slots in [('quarterly',['Q1','Q2','Q3','Q4']),('semiannual',['H1','H2']),('annual',['Annual'])]:
    fig,axs=plt.subplots(2,2,figsize=(16,10)) if horizon=='quarterly' else plt.subplots(1,len(slots),figsize=(16,6))
    axs=np.asarray(axs).reshape(-1)
    for ax,slot in zip(axs,slots):
        curves_by_window={}
        for window in a.windows:
            start=a.end_year-window+1
            eps=[e for e in episodes(df,start,a.end_year,horizon) if e['slot']==slot]
            if len(eps)!=window: print('WARNING incomplete window',horizon,slot,window,len(eps))
            if not eps:continue
            agg,stack=aggregated(eps,horizon,'XAUUSD');agg['lookback_years']=window;agg['start_year']=start;agg['end_year']=a.end_year
            allcurves.append(agg);curves_by_window[window]=agg.mean_cumulative_pct.to_numpy()
            ends=np.array([e['end'] for e in eps]);allstats.append({'horizon':horizon,'slot':slot,'lookback_years':window,'start_year':start,'end_year':a.end_year,'n':len(ends),'bullish_pct':100*np.mean(ends>0),'mean_return_pct':ends.mean(),'median_return_pct':np.median(ends),'min_return_pct':ends.min(),'max_return_pct':ends.max()})
            c=colors.get(window,None);x=agg.progress.to_numpy()
            ax.plot(x,agg.mean_cumulative_pct.to_numpy(),color=c,lw=2.6,label=f'{window}Y mean ({start}–{a.end_year})')
            ax.plot(x,agg.median_cumulative_pct.to_numpy(),color=c,lw=1.05,ls='--',alpha=.8)
        for w1 in a.windows:
            for w2 in a.windows:
                if w1>=w2 or w1 not in curves_by_window or w2 not in curves_by_window:continue
                v1,v2=curves_by_window[w1],curves_by_window[w2]
                allsimilar.append({'horizon':horizon,'slot':slot,'window_a':w1,'window_b':w2,'shape_correlation':np.corrcoef(v1,v2)[0,1] if np.std(v1)>0 and np.std(v2)>0 else np.nan,'mean_absolute_curve_difference_pp':np.mean(abs(v1-v2)),'terminal_return_difference_pp':v1[-1]-v2[-1]})
        ax.set_title(slot,loc='left',fontsize=15,fontweight='bold',pad=15);ax.axhline(0,color='#a8b6c7',lw=.8,alpha=.65);ax.grid(axis='y',alpha=.15);ax.set_xlim(0,1)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'{v:+.0f}%'))
        if horizon=='annual':
            ax.set_xticks(np.linspace(0,1,5));ax.set_xticklabels(['Jan','Apr','Jul','Oct','Dec'])
        else:
            ax.set_xticks(np.linspace(0,1,5));ax.set_xticklabels(['Start','25%','50%','75%','End'])
        for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.075,.965,f'XAUUSD  /  {horizon.upper()} LOOKBACK SENSITIVITY',ha='left',va='top',fontsize=19,fontweight='bold')
    fig.text(.075,.890,f'Mean: solid   |   Median: dashed   |   End year: {a.end_year}   |   Lookbacks: '+', '.join(f'{w}Y' for w in a.windows),color='#b4c2d3',fontsize=10,ha='left',va='top')
    fig.legend(*axs[0].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.5,.005))
    fig.subplots_adjust(top=.755,bottom=.14,left=.075,right=.96,hspace=.40,wspace=.18)
    fig.savefig(out/f'xauusd_{horizon}_lookback_comparison.png',dpi=175);plt.close(fig)

pd.concat(allcurves,ignore_index=True).to_csv(out/'lookback_curves.csv',index=False)
pd.DataFrame(allstats).to_csv(out/'lookback_statistics.csv',index=False)
pd.DataFrame(allsimilar).to_csv(out/'lookback_shape_comparison.csv',index=False)
print(pd.DataFrame(allstats).to_string(index=False));print('\nShape comparison:');print(pd.DataFrame(allsimilar).to_string(index=False))
