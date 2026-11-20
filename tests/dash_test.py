import os
import asyncio, base64, tempfile, json
from playwright.async_api import async_playwright
INIT = "window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle('Financeiro', {create:true}); };"
PUT = """async ([b64, name]) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro',{create:true});
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const h = await d.getFileHandle(name,{create:true}); const w = await h.createWritable(); await w.write(bin); await w.close(); }"""
b64 = lambda f: base64.b64encode(open(f,'rb').read()).decode()
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=os.environ.get('CHROME_PATH') or None, args=['--no-sandbox'], headless=True, viewport={'width':1440,'height':900}, accept_downloads=True)
        await ctx.add_init_script(INIT); errs=[]
        async def route(r):
            if 'jszip' in r.request.url: await r.fulfill(path='node_modules/jszip/dist/jszip.min.js', content_type='application/javascript')
            elif 'fonts' in r.request.url: await r.abort()
            else: await r.continue_()
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
        await pg.route('**/*', route); await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        for f,n in [('tests/fixtures/Database.xlsx','Database.xlsx'),('tests/fixtures/Config.xlsx','Config.xlsx')]: await pg.evaluate(PUT,[b64(f),n])
        await pg.click('button[data-act="connect"]'); await pg.wait_for_selector('.dgrid', timeout=20000); await pg.wait_for_timeout(600)
        tabs = await pg.eval_on_selector_all('.dtab', 'e=>e.map(x=>x.textContent)'); print('tabs', tabs)
        for i in range(4):
            await pg.click(f'.dtab[data-i="{i}"]'); await pg.wait_for_timeout(300)
            n = await pg.locator('.dw').count(); bad = await pg.locator('.dw .errs').count()
            print(i, tabs[i], 'widgets', n, 'errors', bad, [t[:40] for t in await pg.eval_on_selector_all('.dw h2','e=>e.map(x=>x.textContent)')])
            await pg.screenshot(path=f'tests/out/d_{i}.png', full_page=True)
        await pg.click('.dtab[data-i="0"]'); await pg.wait_for_timeout(200)
        print('kpi', await pg.eval_on_selector_all('.t-kpi', 'e=>e.map(x=>x.innerText.replace(/\\n/g," | "))'))
        # período e comparação
        await pg.select_option('select[data-bind="f.period"]','ytd'); await pg.wait_for_timeout(300)
        print('ytd kpi', (await pg.inner_text('.t-kpi')).replace('\n',' | '))
        await pg.select_option('select[data-bind="f.period"]','mes'); await pg.wait_for_timeout(300)
        print('mes kpi', (await pg.inner_text('.t-kpi')).replace('\n',' | '))
        await pg.select_option('select[data-bind="f.period"]','ano'); await pg.wait_for_timeout(200)
        # drill: clicar na 1a barra do ranking
        await pg.locator('.t-rank rect.hit[data-act="dDrill"]').first.click(); await pg.wait_for_timeout(300)
        print('drill chips', await pg.inner_text('.dchips'))
        await pg.screenshot(path='tests/out/d_drill.png', full_page=False)
        await pg.click('button[data-act="dClrAll"]'); await pg.wait_for_timeout(200)
        # drill no mês
        await pg.locator('.t-trend rect.hit[data-act="dDrill"]').nth(2).click(); await pg.wait_for_timeout(300)
        print('month drill', await pg.evaluate('[S.f.period,S.f.month]')); await pg.select_option('select[data-bind="f.period"]','ano'); await pg.wait_for_timeout(200)
        # mais filtros
        await pg.click('button[data-act="dMoreF"]'); await pg.wait_for_timeout(200); await pg.select_option('select[data-bind="f.sen"]','Sênior'); await pg.wait_for_timeout(300)
        print('sen opts', await pg.eval_on_selector_all('select[data-bind="f.sen"] option','e=>e.map(x=>x.textContent)'), 'chips', await pg.inner_text('.dchips'))
        await pg.click('button[data-act="dClrAll"]'); await pg.wait_for_timeout(200)
        # edição
        await pg.click('button[data-act="dEdit"]'); await pg.wait_for_timeout(200)
        n0 = await pg.locator('.dw').count()
        await pg.click('.dgrid button.dadd'); await pg.wait_for_timeout(200); await pg.screenshot(path='tests/out/d_catalog.png')
        await pg.click('.cat-item[data-act="dAdd"][data-g="2"][data-j="4"]'); await pg.wait_for_timeout(300)
        await pg.click('.dgrid button.dadd'); await pg.wait_for_timeout(200); await pg.click('.cat-item[data-act="dAddType"][data-t="table"]'); await pg.wait_for_timeout(300)
        print('cfg modal open', await pg.locator('#mform').count())
        await pg.select_option('#mform select[name="dim"]','ist'); await pg.check('#mform input[name="metrics"][value="ader"]'); await pg.click('#mform button[type="submit"]'); await pg.wait_for_timeout(300)
        n1 = await pg.locator('.dw').count(); print('added', n0, '->', n1, 'last title', await pg.locator('.dw h2').last.inner_text())
        # tamanho
        await pg.locator('select[data-dsize]').last.select_option('6'); await pg.wait_for_timeout(200)
        print('size', await pg.evaluate('curBoard().widgets.at(-1).size'))
        # sort tabela
        ths = pg.locator('.dw').last.locator('th.sort'); await ths.nth(1).click(); await pg.wait_for_timeout(200); s1 = await pg.evaluate('[curBoard().widgets.at(-1).sortBy,curBoard().widgets.at(-1).sortDir]')
        await pg.locator('.dw').last.locator('th.sort').nth(1).click(); await pg.wait_for_timeout(200); s2 = await pg.evaluate('[curBoard().widgets.at(-1).sortBy,curBoard().widgets.at(-1).sortDir]')
        print('sort', s1, s2, (await pg.locator('.dw').last.locator('tbody tr').first.inner_text()).replace('\t',' | '))
        # busca
        await pg.locator('.dw').last.locator('.dsearch').fill('data'); await pg.wait_for_timeout(300)
        print('search rows', await pg.locator('.dw').last.locator('tbody tr').count(), 'focus kept', await pg.evaluate('document.activeElement.dataset.dq != null'))
        # mover / arrastar
        before = await pg.evaluate('curBoard().widgets.map(w=>w.metric||w.type)')
        await pg.locator('.drag').nth(0).drag_to(pg.locator('.dw').nth(2)); await pg.wait_for_timeout(300)
        after = await pg.evaluate('curBoard().widgets.map(w=>w.metric||w.type)'); print('drag', before[:4], '->', after[:4])
        await pg.locator('button[data-act="dMove"][data-d="1"]').first.click(); await pg.wait_for_timeout(200)
        # remover e desfazer
        c0 = await pg.locator('.dw').count(); await pg.locator('button[data-act="dDel"]').first.click(); await pg.wait_for_timeout(200); c1 = await pg.locator('.dw').count()
        await pg.click('button[data-act="dUndo"]'); await pg.wait_for_timeout(200); c2 = await pg.locator('.dw').count(); print('del/undo', c0, c1, c2)
        await pg.screenshot(path='tests/out/d_edit.png', full_page=True)
        # nova visão + persistência
        await pg.click('button[data-act="dBoardNew"]'); await pg.wait_for_timeout(200); await pg.fill('#mform input[name="bname"]','Comitê'); await pg.click('#mform button[type="submit"]'); await pg.wait_for_timeout(300)
        print('new board', await pg.eval_on_selector_all('.dtab','e=>e.map(x=>x.textContent)'), 'widgets', await pg.locator('.dw').count())
        await pg.click('button[data-act="dEdit"]'); await pg.wait_for_timeout(200)
        # export
        await pg.click('.dtab[data-i="0"]'); await pg.click('button[data-act="dEdit"]'); await pg.click('button[data-act="dBoardMenu"]'); await pg.wait_for_timeout(200)
        async with pg.expect_download() as dl: await pg.click('button[data-act="dExport"]')
        d = await dl.value; pth = await d.path(); lay = json.load(open(pth)); print('export boards', [b['name'] for b in lay['boards']])
        await pg.click('#mform button[data-act="close"]')
        await pg.reload(); await pg.wait_for_timeout(800)
        await pg.click('button[data-act="reconnect"]') if await pg.locator('button[data-act="reconnect"]').count() else None
        await pg.wait_for_selector('.dgrid', timeout=20000); await pg.wait_for_timeout(500)
        print('after reload tabs', await pg.eval_on_selector_all('.dtab','e=>e.map(x=>x.textContent)'))
        # tema escuro
        await pg.emulate_media(color_scheme='dark'); await pg.click('.dtab[data-i="0"]'); await pg.wait_for_timeout(300); await pg.screenshot(path='tests/out/d_dark.png', full_page=True)
        await pg.emulate_media(color_scheme='light')
        # leitura: dados não gravados
        print('changes', await pg.evaluate('S.changes.length'), 'lock', await pg.evaluate('S.lock && S.lock.mine'))
        print('errors', errs); await ctx.close()
asyncio.run(main())
