import os
import asyncio, base64, tempfile
from playwright.async_api import async_playwright
INIT = "window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle('Financeiro', {create:true}); };"
PUT = """async ([b64, name]) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro',{create:true});
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const h = await d.getFileHandle(name,{create:true}); const w = await h.createWritable(); await w.write(bin); await w.close(); }"""
b64 = lambda f: base64.b64encode(open(f,'rb').read()).decode()
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=os.environ.get('CHROME_PATH') or None, args=['--no-sandbox'], headless=True, viewport={'width':1440,'height':900})
        await ctx.add_init_script(INIT); errs=[]
        async def route(r):
            if 'jszip' in r.request.url: await r.fulfill(path='node_modules/jszip/dist/jszip.min.js', content_type='application/javascript')
            elif 'fonts' in r.request.url: await r.abort()
            else: await r.continue_()
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); await pg.route('**/*', route); await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(600)
        print('bands', await pg.evaluate("[-0.1,0.199,0.1994,0.1996,0.2,0.25,0.289,0.2894,0.2896,0.29,0.35].map(v=>pct(v)+'→'+mbBand(v)).join('  ')"))
        for f,n in [('tests/fixtures/Database.xlsx','Database.xlsx'),('tests/fixtures/Config.xlsx','Config.xlsx')]: await pg.evaluate(PUT,[b64(f),n])
        await pg.click('button[data-act="connect"]'); await pg.wait_for_selector('.dgrid', timeout=20000); await pg.wait_for_timeout(500)
        # coerência: todo chip com texto X% deve ter a cor da faixa
        bad = await pg.evaluate("""[...document.querySelectorAll('.chip.bad,.chip.warn,.chip.good,td.hneg,td.hatt,td.hpos')].map(e=>[e.className,e.textContent.trim()]).filter(([c,t])=>/^-?−?\\d+(,\\d)?%$/.test(t)).filter(([c,t])=>{const v=parseFloat(t.replace('−','-').replace(',','.'))/100; const b=mbBand(v); return !(c.includes(b)||c.includes({bad:'hneg',warn:'hatt',good:'hpos'}[b]));})""")
        print('inconsistent chips', bad[:5], len(bad))
        print('alerts', await pg.inner_text('.t-alerts .dleg'))
        await pg.locator('.t-heatmap').screenshot(path='tests/out/mb_heat.png')
        await pg.click('.dtab[data-i="1"]'); await pg.wait_for_timeout(300); await pg.locator('.t-table').first.screenshot(path='tests/out/mb_table.png')
        await pg.click('button[data-v="projetos"]'); await pg.wait_for_timeout(300); await pg.screenshot(path='tests/out/mb_proj.png')
        print('errors', errs); await ctx.close()
asyncio.run(main())
