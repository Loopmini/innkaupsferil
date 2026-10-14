"""One complete, cancellable pass through each supported public catalogue."""
from market_sync import SOURCES,run,load,atomic,now


def full_pass(root,stop,selected=None,force=False):
    path=root/'data/full-sync.json'
    previous=load(root/'data/market-status.json',{}).get('sources',{})
    pending=list(SOURCES) if selected is None else list(dict.fromkeys(selected));
    if not pending or any(k not in SOURCES for k in pending):raise ValueError("Veldu að minnsta kosti einn þekktan birgi.")
    from sync_priority import plan
    pending,skipped,_=plan(SOURCES,previous,pending,force)
    client_cache={}
    sitemap_cache={} # Reuse indexes only within this pass; the next run fetches fresh indexes.
    starts={k:previous.get(k,{}).get('next_page',1) for k in pending}
    travelled={k:0 for k in pending};rounds={k:0 for k in pending}
    state={'skipped':skipped,'selected':pending.copy(),'concurrency':4,'running':True,'started_at':now(),'completed':[],'failed':{},'pending':pending.copy(),'current':None,'batches':0,'counts':{}}
    atomic(path,state)
    try:
        while pending and not stop.is_set():
            batch=pending[:4];pending=pending[4:]
            state.update(current=batch,pending=batch+pending);atomic(path,state)
            previous=load(root/'data/market-status.json',{}).get('sources',{})
            # run owns the single writer lock and uses four source workers.
            result=run(root=root,selected=batch,sitemap_cache=sitemap_cache,client_cache=client_cache,force=force)
            for key in batch:
                before=previous.get(key,{});after=result['sources'][key]
                rounds[key]+=1;state['batches']+=1
                count=state['counts'].setdefault(key,{'new_products':0,'changed_products':0,'batches':0})
                count['batches']+=1
                count['scanned']=count.get('scanned',0)+after.get('checked_this_run',0)
                for field in ('new_products','changed_products'):count[field]+=result.get('runtime',{}).get(key,{}).get(field,0)
                if key in result.get('skipped',{}):
                    state['skipped'][key]=result['skipped'][key];continue
                if after['status'] in ('error','blocked','not_connected'):
                    state['failed'][key]=after.get('error',after.get('scope','Tenging ólokið'))
                else:
                    done=True
                    if after.get('coverage_complete'):done=True
                    elif 'cursor' in after and after.get('expected'):
                        total=after['expected'];delta=(after['cursor']-before.get('cursor',0))%total
                        travelled[key]+=delta or total
                        done=travelled[key]>=total
                    elif 'next_page' in after:
                        done=after['next_page']==starts[key]
                    if done and after.get('errors'):state['failed'][key]='Síður mistókust; umferð ekki staðfest fullunnin.'
                    elif done:state['completed'].append(key)
                    elif rounds[key]>=2000:state['failed'][key]='Hámark lota náðist; halda þarf áfram síðar.'
                    else:pending.append(key)
            state.update(pending=pending.copy(),current=None);atomic(path,state)
        state['status']='stopped' if stop.is_set() else 'finished'
    except Exception as e:
        state['status']='error';state['error']=str(e)
    finally:
        state.update(running=False,finished_at=now(),current=None);atomic(path,state)
    return state
