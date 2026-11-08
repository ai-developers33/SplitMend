"""Scientific figure from exhaustive neighborhood analysis, not model output."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
cases=json.loads((ROOT/"results/illustrative_case_explanations.json").read_text())
plt.rcParams.update({"font.size":10,"svg.fonttype":"none","axes.spines.top":False,"axes.spines.right":False})
fig,axes=plt.subplots(1,2,figsize=(10.5,4.6))
for ax,item,title,unit,aggregate in zip(axes,cases,["HAR70+","Sleep-EDF Telemetry"],["5-second windows","30-second epochs"],[4.29,1.37]):
    values=sorted((int(k),v) for k,v in item["best_feasible_cost_at_each_distance_from_greedy"].items())
    x=np.arange(max(k for k,v in values)+1)
    mapping=dict(values)
    y=[mapping.get(int(k),np.nan) for k in x]
    ax.axvspan(-.15,2.15,color="#e2e8f0",alpha=.8,label="Single / pair changes")
    ax.plot(x,y,"o-",color="#075985",linewidth=1.5,markersize=5,label="Best feasible cost at distance k")
    ax.axhline(item["greedy_movement"],color="#64748b",linestyle="--",linewidth=1.2,label="Tested greedy result")
    optimum=min(values,key=lambda pair:pair[1])
    ax.scatter(*optimum,color="#15803d",marker="D",s=60,zorder=5,label="Global minimum")
    ax.set_title(f"{title}\nSelected-case saving: {item['reduction_percent']:.2f}%\nAggregate over valid pairs: {aggregate:.2f}%",fontsize=11)
    ax.set(xlabel="Participant memberships changed from greedy (k)",ylabel=f"Moved {unit}")
    ax.set_xticks(range(0,max(x)+1));ax.grid(axis="y",alpha=.15)
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,loc="lower center",ncol=2,frameon=False,fontsize=9,bbox_to_anchor=(.5,.015))
fig.suptitle("Two post-hoc illustrations of local-search limits",fontsize=13,y=.98)
fig.subplots_adjust(left=.085,right=.98,bottom=.26,top=.74,wspace=.29)
for extension in ["png","svg"]:fig.savefig(ROOT/"results"/("illustrative_neighborhoods."+extension),dpi=180,facecolor="white")
plt.close(fig)
