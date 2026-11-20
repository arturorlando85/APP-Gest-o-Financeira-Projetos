import os
import asyncio, base64, tempfile
from playwright.async_api import async_playwright
INIT = "window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle('Financeiro', {create:true}); };"
PUT = """async ([b64, name]) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro',{create:true});
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const h = await d.getFileHandle(name,{create:true}); const w = await h.createWritable(); await w.write(bin); await w.close(); }"""
LOCK = """async () => { try { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro'); return JSON.parse(await (await (await d.getFileHandle('_safeharbor.lock')).getFile()).text()); } catch(e) { return null } }"""
b64 = lambda f: base64.b64encode(open(f,'rb').read()).decode()
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=os.environ.get('CHROME_PATH') or None, args=['--no-sandbox'], headless=True, viewport={'width':1440,'height':800})
        await ctx.add_init_script(INIT); errs=[]
        async def route(r):
            if 'jszip' in r.request.url: await r.fulfill(path='node_modules/jszip/dist/jszip.min.js', content_type='application/javascript')
            elif 'fonts' in r.request.url: await r.abort()
            else: await r.continue_()
        async def newpage(name):
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); await pg.route('**/*', route); await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
            await pg.evaluate("n => localStorage.setItem('sh-editor-name', n)", name); return pg
        A = await newpage('Ana')
        for f,n in [('tests/fixtures/Database.xlsx','Database.xlsx'),('tests/fixtures/Config.xlsx','Config.xlsx')]: await A.evaluate(PUT,[b64(f),n])
        await A.click('button[data-act="connect"]'); await A.wait_for_selector('.dgrid', timeout=20000); await A.wait_for_timeout(800)
        print('0 A ao abrir:', await A.evaluate("[S.lock.mine, lvl(), document.querySelectorAll('[data-act=newProject]').length]"), (await A.inner_text('.lockbar')).replace('\n',' '), '| lock file:', await A.evaluate(LOCK))
        await A.screenshot(path='tests/out/l_open.png')
        await A.click('button[data-act="lockAcquire"]'); await A.wait_for_timeout(2500)
        print('1 A:', await A.evaluate("[S.lock.mine, lvl()]"), (await A.inner_text('.lockbar')).replace('\n',' '), '| lock file holder:', (await A.evaluate(LOCK))['holder'])
        B = await newpage('Bruno'); await B.click('button[data-act="reconnect"]'); await B.wait_for_selector('.dgrid', timeout=20000); await B.wait_for_timeout(1500)
        print('2 B:', await B.evaluate("[S.lock.mine, lvl(), document.querySelectorAll('[data-act=newProject]').length]"), (await B.inner_text('.lockbar')).replace('\n',' '))
        await B.screenshot(path='tests/out/l_ro.png')
        # B pede; A recebe e libera; B assume
        await B.click('button[data-act="lockRequest"]'); await B.wait_for_timeout(300)
        await A.evaluate("lockTick()"); await A.wait_for_timeout(500)
        print('3 A vê pedido:', (await A.inner_text('.lockbar')).replace('\n',' '))
        await A.screenshot(path='tests/out/l_req.png')
        await A.click('button[data-act="lockRelease"]'); await A.wait_for_timeout(500)
        await B.evaluate("lockTick()"); await B.wait_for_timeout(2500)
        print('4 B assumiu:', await B.evaluate("[S.lock.mine, lvl()]"), '| A:', await A.evaluate("lockTick().then(()=>[S.lock.mine, lvl()])"))
        # A tenta gravar sem trava (guarda de gravação)
        await A.evaluate("S.changes.push({desc:'teste',at:new Date().toISOString()}); saveNow()"); await A.wait_for_timeout(800)
        print('5 A sem trava ao gravar:', await A.evaluate("[S.save.state, S.save.err]"))
        # trava velha (Bruno fechou o navegador sem liberar)
        await B.evaluate("""(async()=>{const d=S.src.dir; const l=await readLock(d); l.heartbeat=new Date(Date.now()-5*60e3).toISOString(); await writeLock(d,l);})()""")
        await A.evaluate("S.changes=[]; lockTick()"); await A.wait_for_timeout(300); print('6 A vê trava expirada:', await A.evaluate("[S.lock.free, S.lock.mine]"))
        await A.click('button[data-act="lockAcquire"]'); await A.wait_for_timeout(2500); print('  A assumiu:', await A.evaluate("S.lock.mine"))
        # inatividade
        await A.evaluate("S.lastAct = Date.now() - 11*60e3; lockTick()"); await A.wait_for_timeout(1500)
        print('7 A após 11 min parado:', await A.evaluate("[S.lock.mine, S.lock.free]"), 'lock file:', await A.evaluate(LOCK))
        print('errors', errs); await ctx.close()
asyncio.run(main())
