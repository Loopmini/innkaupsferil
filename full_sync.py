"""One complete, cancellable pass through each supported public catalogue."""
from market_sync import SOURCES,run,load,atomic,now


def full_pass(root,stop):
    path=root/'data/full-sync.json'
    previous=load(root/'data/market-status.json',{}).get('sources',{})
    pending=list(SOURCES);starts={k:previous.get(k,{}).get('next_page',1) for k in pending}
    travelled={k:0 for k in pending};rounds={k:0 for k in pending}
    state={'running':True,'started_at':now(),'completed':[],'failed':{},'pending':pending.copy(),'current':None,'batches':0}
    atomic(path,state)
    try:
        while pending and not stop.is_set():
            key=pending.pop(0);state.update(current=key,pending=[key]+pending);atomic(path,state)
            before=load(root/'data/market-status.json',{}).get('sources',{}).get(key,{})
            result=run(root=root,selected=[key]);after=result['sources'][key]
            rounds[key]+=1;state['batches']+=1
            if after['status'] in ('error','blocked','not_connected'):
                state['failed'][key]=after.get('error',after.get('scope','Tenging ólokið'))
            else:
                done=True
                if 'cursor' in after and after.get('expected'):
                    total=after['expected'];delta=(after['cursor']-before.get('cursor',0))%total
                    travelled[key]+=delta or total
                    done=travelled[key]>=total
                elif 'next_page' in after:
                    done=after['next_page']==starts[key]
                if done:state['completed'].append(key)
                elif rounds[key]>=2000:state['failed'][key]='Hámark lota náðist; halda þarf áfram síðar.'
                else:pending.append(key)
            state.update(pending=pending.copy(),current=None);atomic(path,state)
        state['status']='stopped' if stop.is_set() else 'finished'
    except Exception as e:
        state['status']='error';state['error']=str(e)
    finally:
        state.update(running=False,finished_at=now(),current=None);atomic(path,state)
    return state
