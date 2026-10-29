#!/usr/bin/env python3
"""Local dependency imports and browser/WebGL check; no model/API calls."""
import importlib,json,os,platform,shutil,subprocess,sys
from pathlib import Path

def main():
    problems=[]
    for name in ['requests','PIL','numpy','av','faster_whisper','ctranslate2','torch','stable_whisper','scipy','num2words']:
        try:importlib.import_module(name)
        except Exception as error:problems.append({'dependency':name,'error_class':type(error).__name__})
    for binary in ['ffmpeg','ffprobe','node',os.getenv('CHROMIUM_PATH','/usr/bin/chromium')]:
        if not shutil.which(binary):problems.append({'binary':binary,'error_class':'MissingExecutable'})
    browser='''import {chromium} from 'playwright-core';const b=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});try{const p=await b.newPage();await p.setContent('<canvas></canvas>');if(!await p.evaluate(()=>!!document.querySelector('canvas').getContext('webgl2')))throw Error('WebGL2 unavailable');}finally{await b.close();}'''
    try:subprocess.run(['node','--input-type=module','-e',browser],cwd=Path('professional_motion'),check=True,timeout=90,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except Exception as error:problems.append({'dependency':'playwright-chromium-webgl2','error_class':type(error).__name__})
    print(json.dumps({'ready':not problems,'architecture':platform.machine(),'problems':problems,'paid_api_calls':0}))
    return 1 if problems else 0
if __name__=='__main__':raise SystemExit(main())
