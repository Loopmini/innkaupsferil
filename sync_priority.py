"""Persistent scan rounds: completed suppliers wait for reachable incomplete ones."""
import hashlib,json
from datetime import datetime,timezone

LIMITED={'iskraft'}
def complete(state):
 if state.get('status') in ('blocked','error','not_connected') or state.get('errors'):return False
 if 'coverage_complete' in state:return state['coverage_complete'] is True
 # Migration only for a completed full API response, never loaded/sitemap ratios.
 return state.get('status')=='ok'

def plan(keys,statuses,selected=None,force=False):
 requested=list(keys) if selected is None else list(dict.fromkeys(selected))
 if force:return requested,{},False
 available=[k for k in keys if k not in LIMITED and statuses.get(k,{}).get('status') not in ('blocked','error','not_connected')]
 unfinished=[k for k in available if not complete(statuses.get(k,{}))]
 skipped={};chosen=[]
 for k in requested:
  s=statuses.get(k,{})
  if k in LIMITED:skipped[k]='Heildartenging ólokið; nota sérstaka endurtilraun.'
  elif s.get('status') in ('blocked','error','not_connected'):skipped[k]='Tenging bíður sérstakrar endurtilraunar.'
  elif unfinished and complete(s):skipped[k]='Umferð lokið; bíður eftir öðrum aðgengilegum birgjum.'
  else:chosen.append(k)
 return sorted(chosen,key=lambda k:(complete(statuses.get(k,{})),statuses.get(k,{}).get('coverage_fraction',0))),skipped,bool(available and not unfinished)

def checkpoint(previous,current):
 """Only successful unique scan units count; errors can never produce 100%."""
 if current.get('status') not in ('ok','partial'):
  return {**current,**{k:v for k,v in previous.items() if k.startswith('coverage_')},'coverage_complete':False}
 total=current.get('coverage_total');units=current.get('coverage_units')
 if units is None:
  if current.get('status')=='ok' and not current.get('errors'):current['coverage_complete']=True
  return current
 same=previous.get('coverage_index')==current.get('coverage_index')
 seen=set(previous.get('coverage_seen',[]) if same else [])|set(units)
 current.update(coverage_seen=sorted(seen),coverage_done=len(seen),coverage_fraction=min(1,len(seen)/total) if total else 0,
                coverage_complete=bool(total and len(seen)>=total and not current.get('errors')))
 current.pop('coverage_units',None)
 return current

def index_id(values):return hashlib.sha256(json.dumps(values,ensure_ascii=False).encode()).hexdigest()
