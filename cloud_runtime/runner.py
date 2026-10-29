#!/usr/bin/env python3
"""Durable Linux execution of the four repositories without GitHub Actions."""
from __future__ import annotations
import argparse, concurrent.futures, fcntl, json, os, re, shutil, subprocess, sys, uuid
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
CAIRO=ZoneInfo('Africa/Cairo')
CREDENTIALS={'GEMINI_API_KEY','GEMINI_TEXT_API_KEY','GEMINI_TTS_API_KEY','BUFFER_API_KEY','BUFFER_CHANNEL_IDS','BUFFER_YOUTUBE_CHANNEL_ID','BUFFER_FACEBOOK_CHANNEL_ID','BUFFER_INSTAGRAM_CHANNEL_ID','BUFFER_TIKTOK_CHANNEL_ID','YT_CLIENT_ID','YT_CLIENT_SECRET','YT_REFRESH_TOKEN','YT_REFRESH_TOKEN_FALLBACK','GH_RELEASE_TOKEN','GITHUB_TOKEN'}
REPO_NAMES={'science':'science-discovery-shorts','horror':'arabic-horror-stories','history':'documented-history-stories','news':'ai-news-daily'}


def save(path:Path,data):
    path.parent.mkdir(parents=True,exist_ok=True);pending=path.with_suffix('.tmp');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2));pending.chmod(0o600);pending.replace(path)


def secrets(path:Path) -> dict[str,str]:
    if path.stat().st_mode & 0o077:raise ValueError('Secret files must be private to their owner (chmod 600)')
    data=json.loads(path.read_text())
    if not isinstance(data,dict) or any(k not in CREDENTIALS or not isinstance(v,str) for k,v in data.items()):raise ValueError('Secret JSON contains an unsupported name or non-string value')
    return data


def daily_window(config,now=None):
    local=(now or datetime.now(timezone.utc)).astimezone(CAIRO)
    return config.get('generation_hour_cairo',9)<=local.hour<=config.get('latest_start_hour_cairo',12)


def command(argv,repo,env,log):
    with log.open('ab') as handle:
        handle.write(('\nCOMMAND '+json.dumps([str(x) for x in argv])+'\n').encode())
        handle.flush();result=subprocess.run([str(x) for x in argv],cwd=repo,env=env,stdout=handle,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError('Repository stage failed; private stage log retained')


def execute(project,config,mode,decision,run_id,resume=False):
    profile=project['profile'];repo=Path(project['path']).resolve();root=Path(config['runtime_root']);journal=root/'journals'/f'{profile}.json';root.mkdir(parents=True,exist_ok=True)
    locks=root/'locks';locks.mkdir(exist_ok=True)
    with (locks/(profile+'.lock')).open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'profile':profile,'status':'already_running'}
        if not decision['run']:return {'profile':profile,'status':'approval_pending'}
        env=os.environ.copy()
        for name in CREDENTIALS:env.pop(name,None)
        bound=secrets(Path(project['secrets_file']));env.update(bound)
        if not (env.get('GEMINI_TEXT_API_KEY') or env.get('GEMINI_API_KEY')) or not (env.get('GEMINI_TTS_API_KEY') or env.get('GEMINI_API_KEY')):raise RuntimeError('Writing and original voice credentials are not bound on this host')
        env.update(PYTHONPATH=str(repo),PYTHONUNBUFFERED='1',GITHUB_RUN_ID=run_id,GITHUB_RUN_ATTEMPT='1',GITHUB_EVENT_NAME='external_schedule',GITHUB_REPOSITORY=project['repository'],CHROMIUM_PATH=config.get('chromium','/usr/bin/chromium'))
        prior=json.loads(journal.read_text()) if journal.exists() else {};slot=decision['slot']
        if mode=='review' and resume and prior.get('mode')=='review' and prior.get('status')!='complete':slot=prior['slot'];decision['slot']=slot
        if prior.get('slot')!=slot:
            old_slot=re.sub(r'[^A-Za-z0-9_-]','-',prior.get('slot','pre-native'))
            archive=root/'archive'/profile/(old_slot+'-'+uuid.uuid4().hex[:8]);archive.mkdir(parents=True,exist_ok=True)
            for name in ['delivery','output','chunks']:
                source=repo/'professional_motion'/name
                if source.is_symlink():raise ValueError('Generated working directories must not be symlinks')
                if source.exists():shutil.move(str(source),str(archive/name))
            prior={'slot':slot,'mode':mode,'completed':[],'attempt':0}
        if prior.get('stage')=='publish' and 'publish' not in prior.get('completed',[]):
            return {'profile':profile,'status':'failed','slot':slot,'stage':'publish','error_class':'PublicationReconciliationRequired'}
        if prior.get('status')=='complete':return {'profile':profile,'status':'already_complete','slot':slot}
        prior['attempt']=prior.get('attempt',0)+1;env['GITHUB_RUN_ATTEMPT']=str(prior['attempt']);prior['status']='running';prior['due']=decision['due'];save(journal,prior)
        logdir=root/'logs'/profile/slot;logdir.mkdir(parents=True,exist_ok=True);log=logdir/'run.log';log.touch(mode=0o600,exist_ok=True)
        python=config.get('python',sys.executable);node=config.get('node','node')
        stages=[('dependencies',[python,str(Path(__file__).with_name('preflight.py'))]),('prepare',[python,'-m','professional_motion.cli','prepare',profile,'--slot',slot]),('voice',[python,'-m','professional_motion.voice_job'])]
        try:
            for stage,argv in stages:
                if stage in prior['completed']:continue
                prior['stage']=stage;save(journal,prior);command(argv,repo,env,log);prior['completed'].append(stage);save(journal,prior)
            if 'render' not in prior['completed']:
                prior['stage']='render';save(journal,prior);parts=int(config.get('render_workers',2));out=repo/'professional_motion/output';chunks=repo/'professional_motion/chunks';out.mkdir(exist_ok=True);chunks.mkdir(exist_ok=True)
                def render(index):
                    name=f'chunk-{index}.mp4';target=chunks/name;metadata=chunks/(name+'.json')
                    if target.exists() and metadata.exists():return
                    command([node,'professional_motion/render.mjs','--part',str(index),'--parts',str(parts),'--output',name],repo,env,logdir/f'render-{index}.log')
                    shutil.move(str(out/name),str(target));shutil.move(str(out/(name+'.json')),str(metadata))
                with concurrent.futures.ThreadPoolExecutor(max_workers=parts) as pool:list(pool.map(render,range(parts)))
                command([python,'-m','professional_motion.merge_chunks'],repo,env,log);prior['completed'].append('render');save(journal,prior)
            if 'finish' not in prior['completed']:
                prior['stage']='finish';save(journal,prior);command([python,'-m','professional_motion.finish'],repo,env,log);command([python,'-m','professional_motion.cli','rendered',profile,'--slot',slot],repo,env,log);prior['completed'].append('finish');save(journal,prior)
            if decision['publish'] and 'publish' not in prior['completed']:
                prior['stage']='publish';save(journal,prior)
                command([python,str(Path(__file__).with_name('publish_static.py')),'--repo',repo,'--profile',profile,'--slot',slot,'--due',decision['due'],'--public-root',config['public_root'],'--media-base-url',config['media_base_url']],repo,env,log)
                prior['completed'].append('publish');save(journal,prior)
            prior['status']='complete';prior['stage']='done';save(journal,prior)
            return {'profile':profile,'status':'scheduled' if decision['publish'] else 'review_ready','slot':slot,'due':decision['due'],'video':str(repo/'professional_motion/output/professional-review.mp4')}
        except Exception as error:
            prior['status']='failed';prior['error_class']=type(error).__name__;save(journal,prior)
            return {'profile':profile,'status':'failed','slot':slot,'stage':prior.get('stage'),'error_class':type(error).__name__,'log':str(log)}


def health(config):
    problems=[];projects=[]
    for project in config['projects']:
        repo=Path(project['path']);p={'profile':project['profile'],'repository_present':(repo/'professional_motion/cli.py').exists(),'native_pipeline_present':(repo/'professional_motion/merge_chunks.py').exists(),'secret_file_present':Path(project['secrets_file']).exists()}
        p['ready']=all(p[k] for k in ['repository_present','native_pipeline_present','secret_file_present']);projects.append(p)
        if not p['ready']:problems.append(project['profile']+' is not provisioned')
    for binary in [config.get('python',sys.executable),config.get('node','node'),config.get('chromium','/usr/bin/chromium'),'ffmpeg']:
        if not shutil.which(binary):problems.append('Missing executable: '+binary)
    durable_init=Path('/proc/1/comm').read_text().strip()=='systemd' if Path('/proc/1/comm').exists() else False
    return {'ready':not problems,'durable_systemd_host_observed':durable_init,'projects':projects,'problems':problems,'secret_values_included':False}


def main():
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('action',choices=['health','run']);parser.add_argument('--mode',choices=['review','daily'],default='review');parser.add_argument('--profiles',nargs='*',choices=list(REPO_NAMES));parser.add_argument('--resume',action='store_true');args=parser.parse_args();config=json.loads(args.config.read_text())
    if args.action=='health':report=health(config);print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['ready'] else 2
    if args.mode=='daily' and not daily_window(config):print(json.dumps({'status':'outside_generation_window','no_posts_sent':True}));return 0
    run_id='external-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8];projects=[p for p in config['projects'] if not args.profiles or p['profile'] in args.profiles];plans=[]
    # Resolve every project's due slot before sequential/parallel work starts.
    for project in projects:
        repo=Path(project['path']).resolve();env=os.environ.copy();env.update(PYTHONPATH=str(repo),GITHUB_EVENT_NAME='external_schedule',GITHUB_RUN_ID=run_id)
        raw=subprocess.check_output([config.get('python',sys.executable),'-m','professional_motion.cli','decision',project['profile'],'--mode',args.mode],cwd=repo,env=env)
        decision=json.loads(raw.decode().splitlines()[-1]);plans.append((project,decision))
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(config.get('max_parallel_projects',1))) as pool:
        futures=[pool.submit(execute,p,config,args.mode,d,run_id,args.resume) for p,d in plans]
        reports=[]
        for future in futures:
            try:reports.append(future.result())
            except Exception as error:reports.append({'status':'failed','error_class':type(error).__name__})
    print(json.dumps({'results':reports,'github_actions_used':False},ensure_ascii=False,indent=2));return 1 if any(r['status']=='failed' for r in reports) else 0

if __name__=='__main__':raise SystemExit(main())
