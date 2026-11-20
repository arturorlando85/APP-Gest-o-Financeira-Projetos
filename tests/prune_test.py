import os
import asyncio, base64, tempfile
from playwright.async_api import async_playwright
INIT = "window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle('Financeiro', {create:true}); };"
PUT = """async ([b64, name]) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro',{create:true});
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const h = await d.getFileHandle(name,{create:true}); const w = await h.createWritable(); await w.write(bin); await w.close(); }"""
MK = """async (names) => { const root = await navigator.storage.getDirectory(); const d = await (await root.getDirectoryHandle('Financeiro',{create:true})).getDirectoryHandle('_backups_safeharbor',{create:true});
  for (const n of names) { const h = await d.getFileHandle(n,{create:true}); const w = await h.createWritable(); await w.write('x'); await w.close(); } }"""
LS = """async () => { const root = await navigator.storage.getDirectory(); const d = await (await root.getDirectoryHandle('Financeiro')).getDirectoryHandle('_backups_safeharbor'); const o=[]; for await (const [n] of d.entries()) o.push(n); return o.sort(); }"""
b64 = lambda f: base64.b64encode(open(f,'rb').read()).decode()
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=os.environ.get('CHROME_PATH') or None, args=['--no-sandbox'], headless=True)
        await ctx.add_init_script(INIT); errs=[]
        async def route(r):
            if 'jszip' in r.request.url: await r.fulfill(path='node_modules/jszip/dist/jszip.min.js', content_type='application/javascript')
            elif 'fonts' in r.request.url: await r.abort()
            else: await r.continue_()
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); await pg.route('**/*', route); await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        for f,n in [('tests/fixtures/Database.xlsx','Database.xlsx'),('tests/fixtures/Config.xlsx','Config.xlsx')]: await pg.evaluate(PUT,[b64(f),n])
        await pg.evaluate(MK, ['Database_backup_20261101_0900.xlsx','Database_backup_20261110_0900.xlsx','Database_backup_20261116_0900.xlsx','Config_backup_20261101_0900.xlsx','Config_backup_20261105_0900.xlsx','Database_backup_20261117_1500.xlsx'])
        print('antes ', await pg.evaluate(LS))
        await pg.click('button[data-act="connect"]'); await pg.wait_for_selector('.kpis', timeout=20000); await pg.wait_for_timeout(1500)
        print('depois', await pg.evaluate(LS), await pg.evaluate("S.lastPrune && S.lastPrune.n"))
        print('errors', errs); await ctx.close()
asyncio.run(main())
