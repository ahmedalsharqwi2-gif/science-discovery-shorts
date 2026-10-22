import asyncio, subprocess, time
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 server=subprocess.Popen(['python','-m','http.server','8765'],stdout=subprocess.DEVNULL)
 try:
  await asyncio.sleep(2)
  async with async_playwright() as p:
   browser=await p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox','--enable-webgl','--use-gl=angle','--use-angle=swiftshader','--ignore-gpu-blocklist'])
   page=await browser.new_page(viewport={'width':540,'height':960})
   page.on('pageerror',lambda e: print('JS ERROR:',e))
   await page.goto('http://127.0.0.1:8765',wait_until='load')
   await page.wait_for_function('typeof window.renderTime==="function"',timeout=30000)
   proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-vcodec','png','-r','24','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','21','battle-3d-proof.mp4'],stdin=subprocess.PIPE)
   for i in range(120):
    await page.evaluate('(t)=>window.renderTime(t)',i/24)
    proc.stdin.write(await page.screenshot(type='png'))
    if i==48: await page.screenshot(path='battle-3d-proof.jpg')
   proc.stdin.close()
   if proc.wait()!=0:raise RuntimeError('ffmpeg failed')
   await browser.close()
 finally:server.terminate()
asyncio.run(main())
