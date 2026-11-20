import os
import asyncio, base64, tempfile
from playwright.async_api import async_playwright
INIT = "window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle('Financeiro', {create:true}); };"
PUT = """async ([b64, name]) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro',{create:true});
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const h = await d.getFileHandle(name,{create:true}); const w = await h.createWritable(); await w.write(bin); await w.close(); }"""
GET = """async (name) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro'); const f = await (await d.getFileHandle(name)).getFile(); const u = new Uint8Array(await f.arrayBuffer()); let s=''; for (let i=0;i<u.length;i+=32768) s+=String.fromCharCode.apply(null,u.subarray(i,i+32768)); return btoa(s); }"""
LS = """async () => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro'); const out=[]; for await (const [n,h] of d.entries()) { if (h.kind==='file') out.push(n); else for await (const [n2] of h.entries()) out.push(n+'/'+n2); } return out.sort(); }"""
b64 = lambda f: base64.b64encode(open(f,'rb').read()).decode()
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=os.environ.get('CHROME_PATH') or None, args=['--no-sandbox'], headless=True, viewport={'width':1440,'height':950})
        await ctx.add_init_script(INIT); errs=[]
        async def route(r):
            if 'jszip' in r.request.url: await r.fulfill(path='node_modules/jszip/dist/jszip.min.js', content_type='application/javascript')
            elif 'fonts' in r.request.url: await r.abort()
            else: await r.continue_()
        async def newpage():
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); await pg.route('**/*', route); await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(900); await pg.evaluate("localStorage.setItem('sh-editor-name','Teste')"); return pg
        A = await newpage()
        for f,n in [('tests/fixtures/Database.xlsx','Database.xlsx'),('tests/fixtures/Config.xlsx','Config.xlsx'),('serve_c.xlsx','Safeharbor_antigo.xlsx')]: await A.evaluate(PUT,[b64(f),n])
        await A.screenshot(path='tests/out/f_welcome.png')
        await A.click('button[data-act="connect"]'); await A.wait_for_selector('.dgrid', timeout=20000); await A.wait_for_timeout(400)
        print('1 opened', await A.evaluate("[S.src.name, S.src.cfgName, document.querySelectorAll('.modal').length, !!S.m.config, S.m.taxes.ISSQN, lvl()]"), 'nav', await A.evaluate("[...document.querySelectorAll('.nav')].map(n=>n.textContent.trim())"))
        await A.click('button[data-act="lockAcquire"]'); await A.wait_for_timeout(2500)
        # novo cliente + projeto isento + profissional com ratecard
        await A.click('button[data-v="projetos"]'); await A.click('button[data-act="newProject"]')
        await A.select_option('[name="client"]','__new'); await A.fill('[name="newClient"]','Banco Novo'); await A.fill('[name="name"]','Squad Pix'); await A.select_option('[name="trib"]','Isento')
        await A.click('#mform button[type=submit]'); await A.wait_for_timeout(300)
        await A.click('button[data-act="newAlloc"]'); await A.fill('[name="Profissional"]','Ana'); await A.fill('[name="Mês de Execução"]','2026-12')
        await A.select_option('[name="iStudio"]','Cloud_DevSecOps'); await A.select_option('[name="Papel"]','Cloud Architect'); await A.select_option('[name="Senioridade"]','Pleno'); await A.wait_for_timeout(200)
        print('2 ratecard hint:', (await A.inner_text('#rc-hint')).replace('\n',' ')[:200])
        await A.fill('[name="Horas Executadas"]','160')
        print('  filled', await A.evaluate("[document.querySelector('#mform [name=\"R$/H\"]').value, document.querySelector('#mform [name=\"Custo Profissional\"]').value]"))
        await A.screenshot(path='tests/out/f_alloc.png')
        await A.click('#mform button[type=submit]'); await A.wait_for_timeout(7000)
        print('3 save:', await A.inner_text('#savestate'), await A.evaluate(LS))
        open('tests/out/fin_db.xlsx','wb').write(base64.b64decode(await A.evaluate(GET,'Database.xlsx'))); open('tests/out/fin_cfg.xlsx','wb').write(base64.b64decode(await A.evaluate(GET,'Config.xlsx')))
        # alguém muda o ISSQN no Config pelo Excel
        await A.wait_for_timeout(1100); await A.evaluate(PUT,[b64('tests/fixtures/Config_alt.xlsx'),'Config.xlsx']); await A.evaluate("checkExternal()"); await A.wait_for_timeout(2500)
        print('4 after external Config change: ISSQN', await A.evaluate("S.m.taxes.ISSQN"), 'modal', await A.evaluate("S.modal && S.modal.kind"))
        # reabrir: sem escolher arquivo
        B = await newpage(); await B.screenshot(path='tests/out/f_reopen.png')
        await B.click('button[data-act="reconnect"]'); await B.wait_for_selector('.dgrid', timeout=20000); await B.wait_for_timeout(500)
        print('5 reopen', await B.evaluate("[S.src.name, S.src.cfgName, !!S.m.projects.find(p=>p.name==='Squad Pix'), document.querySelectorAll('.modal').length]"))
        U = await newpage(); await U.evaluate("S.m=null;S.src=null;S.stored=null;render()"); print('6 sem upload:', await U.locator('#file, #drop').count(), await U.eval_on_selector_all('.welcome button','e=>e.map(x=>x.textContent)'))
        print('errors', errs); await ctx.close()
asyncio.run(main())
