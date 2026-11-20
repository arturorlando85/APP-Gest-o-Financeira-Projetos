import os
import asyncio, base64, tempfile
from playwright.async_api import async_playwright
INIT = "window.showDirectoryPicker = async () => { const root = await navigator.storage.getDirectory(); return await root.getDirectoryHandle('Financeiro', {create:true}); };"
PUT = """async ([b64, name]) => { const root = await navigator.storage.getDirectory(); const d = await root.getDirectoryHandle('Financeiro',{create:true});
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); const h = await d.getFileHandle(name,{create:true}); const w = await h.createWritable(); await w.write(bin); await w.close(); }"""
b64 = lambda f: base64.b64encode(open(f,'rb').read()).decode()
V = "() => [document.querySelector('#mform [name=\"R$/H\"]').value, document.querySelector('#mform [name=\"Custo Profissional\"]').value]"
OPTS = lambda n: f"() => [...document.querySelectorAll('#mform [name=\"{n}\"] option')].map(o=>o.textContent).filter(Boolean)"
async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(tempfile.mkdtemp(), executable_path=os.environ.get('CHROME_PATH') or None, args=['--no-sandbox'], headless=True, viewport={'width':1440,'height':900})
        await ctx.add_init_script(INIT); errs=[]
        async def route(r):
            if 'jszip' in r.request.url: await r.fulfill(path='node_modules/jszip/dist/jszip.min.js', content_type='application/javascript')
            elif 'fonts' in r.request.url: await r.abort()
            else: await r.continue_()
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); await pg.route('**/*', route); await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(600)
        await pg.screenshot(path='tests/out/pf_welcome.png'); print('welcome upload?', await pg.locator('#file, #drop').count())
        await pg.evaluate("localStorage.setItem('sh-editor-name','Orlando')")
        for f,n in [('tests/fixtures/Database.xlsx','Database.xlsx'),('tests/fixtures/Config.xlsx','Config.xlsx')]: await pg.evaluate(PUT,[b64(f),n])
        await pg.click('button[data-act="connect"]'); await pg.wait_for_selector('.dgrid', timeout=20000); await pg.click('button[data-act="lockAcquire"]'); await pg.wait_for_timeout(2500)
        await pg.click('button[data-v="projetos"]'); await pg.wait_for_timeout(200)
        await pg.locator('tr.click[data-act="open"]').first.click(); await pg.wait_for_timeout(300)
        await pg.click('button[data-act="newAlloc"]'); await pg.wait_for_timeout(300)
        print('A open: papel', await pg.evaluate(OPTS('Papel')), '| sen', await pg.evaluate(OPTS('Senioridade')), '| vals', await pg.evaluate(V))
        await pg.fill('[name="Profissional"]','Digitando'); await pg.evaluate("toast('aviso'); render(); lockTick()"); await pg.wait_for_timeout(300)
        print('A2 input kept after toast+render', await pg.evaluate("document.querySelector('#mform [name=Profissional]').value"))
        await pg.fill('[name="Mês de Execução"]','2026-12')
        await pg.select_option('[name="iStudio"]','AI_Cockpit'); await pg.wait_for_timeout(150)
        print('B AI_Cockpit papel', await pg.evaluate(OPTS('Papel')))
        await pg.select_option('[name="Papel"]','Customer Success Manager'); await pg.wait_for_timeout(150)
        print('  sen', await pg.evaluate(OPTS('Senioridade')))
        await pg.select_option('[name="Senioridade"]','Senior'); await pg.wait_for_timeout(200)
        print('  vals', await pg.evaluate(V), '| hint', (await pg.inner_text('#rc-hint')).replace('\n',' ')[:220])
        await pg.screenshot(path='tests/out/pf_form.png')
        # mês 2027 reaplica (valores ainda automáticos)
        await pg.fill('[name="Mês de Execução"]','2027-02'); await pg.dispatch_event('[name="Mês de Execução"]','change'); await pg.wait_for_timeout(200)
        print('C 2027 vals', await pg.evaluate(V))
        # valor manual e troca de mês: mantém manual
        await pg.fill('[name="R$/H"]','300'); await pg.dispatch_event('[name="R$/H"]','change'); await pg.fill('[name="Mês de Execução"]','2026-11'); await pg.dispatch_event('[name="Mês de Execução"]','change'); await pg.wait_for_timeout(200)
        print('D manual kept', await pg.evaluate(V), '|', (await pg.inner_text('#rc-hint')).split('\n')[1][:80])
        # troca de perfil: reaplica
        await pg.select_option('[name="Senioridade"]','Especialista'); await pg.wait_for_timeout(200); print('E Especialista', await pg.evaluate(V))
        # troca iStudio: papel fora da lista → reseta seleção
        await pg.select_option('[name="iStudio"]','Data_AI'); await pg.wait_for_timeout(200)
        print('F Data_AI papel sel', await pg.evaluate("document.querySelector('#mform [name=Papel]').value"), 'opts', len(await pg.evaluate(OPTS('Papel'))), 'sen disabled', await pg.evaluate("document.querySelector('#mform [name=Senioridade]').disabled"))
        # iStudio sem tabela
        others = await pg.evaluate("[...document.querySelectorAll('#mform [name=iStudio] optgroup:nth-of-type(2) option')].map(o=>o.value)")
        print('G sem tabela:', others[:6], '| ist opts', await pg.evaluate(OPTS('iStudio')))
        if others:
            await pg.select_option('[name="iStudio"]', others[0]); await pg.wait_for_timeout(200)
            print('  papel tag', await pg.evaluate("document.querySelector('#mform [name=Papel]').tagName"), '| hint', (await pg.inner_text('#rc-hint'))[:90])
        # salvar uma alocação completa
        await pg.select_option('[name="iStudio"]','Cloud_DevSecOps'); await pg.select_option('[name="Papel"]','DevOps'); await pg.wait_for_timeout(100)
        sens = await pg.evaluate(OPTS('Senioridade')); await pg.select_option('[name="Senioridade"]', sens[1]); await pg.wait_for_timeout(150)
        await pg.fill('[name="Profissional"]','Teste Perfil'); await pg.fill('[name="Horas Executadas"]','100'); await pg.fill('[name="Horas Provisionadas"]','100')
        vals = await pg.evaluate(V); print('  pre-submit', await pg.evaluate("[...new FormData(document.getElementById('mform'))].filter(x=>['iStudio','Papel','Senioridade'].includes(x[0]))"), sens); await pg.click('#mform button[type=submit]'); await pg.wait_for_timeout(400); print('  errs', await pg.locator('#mform .errs').all_inner_texts())
        a = await pg.evaluate("(()=>{const a=S.m.allocations.find(x=>x.fields['Profissional']==='Teste Perfil');return a&&[a.fields.iStudio,a.fields.Papel,a.fields.Senioridade,a.fields['R$/H'],a.fields['Custo Profissional']]})()")
        print('H saved', a, 'form', vals, 'modal closed', await pg.locator('#mform').count()==0)
        # editar alocação legada (iStudio com outra grafia)
        lid = await pg.evaluate("(()=>{const a=S.m.allocations.find(x=>x.fields.iStudio==='Cloud & DevSecOps');S.projId=S.m.projects.find(p=>p.name===a.project&&S.m.clients.find(c=>c.sheet===a.sheet&&c.name===p.client)).id;S.view='projeto';S.teamMonth='all';render();return a.id})()")
        await pg.wait_for_timeout(300); await pg.locator(f'[data-act="editAlloc"][data-id="{lid}"]').first.click(); await pg.wait_for_timeout(300)
        print('I legacy ist', await pg.evaluate("document.querySelector('#mform [name=iStudio]').value"), '| papel opts', len(await pg.evaluate(OPTS('Papel'))), '| papel', await pg.evaluate("document.querySelector('#mform [name=Papel]').value"), '| sen', await pg.evaluate("document.querySelector('#mform [name=Senioridade]').value"), '| vals unchanged', await pg.evaluate(V), await pg.evaluate(f"(()=>{{const a=S.m.allocations.find(x=>x.id==='{lid}');return [a.fields['R$/H'],a.fields['Custo Profissional']]}})()"))
        await pg.screenshot(path='tests/out/pf_legacy.png')
        print('errors', errs); await ctx.close()
asyncio.run(main())
