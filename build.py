#!/usr/bin/env python3
"""Gera os arquivos do app a partir do código-fonte.

    src/template.html + src/core.js  ->  dist/index.html                 (JSZip via CDN)
                                     ->  dist/SafeHarbor_Financeiro.html  (JSZip embutido, funciona offline)

Uso: npm install && python3 build.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CDN_TAG = '<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js"></script>'
TITLE = '<title>Safe Harbor Financeiro</title>'


def main() -> None:
    template = (ROOT / 'src' / 'template.html').read_text(encoding='utf-8')
    core = (ROOT / 'src' / 'core.js').read_text(encoding='utf-8')
    assert '/*__CORE__*/' in template, 'marcador /*__CORE__*/ não encontrado no template'
    page = template.replace('/*__CORE__*/', core)

    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    (dist / 'index.html').write_text(page, encoding='utf-8')

    jszip_path = ROOT / 'node_modules' / 'jszip' / 'dist' / 'jszip.min.js'
    if not jszip_path.exists():
        raise SystemExit('JSZip não encontrado. Rode "npm install" antes do build.')
    jszip = jszip_path.read_text(encoding='utf-8').replace('</script', '<\\/script')
    assert CDN_TAG in page, 'tag do JSZip (CDN) não encontrada no template'
    local = page.replace(CDN_TAG, '<script>\n' + jszip + '\n</script>').replace(TITLE, '<title>Safe Harbor Financeiro (local)</title>')
    (dist / 'SafeHarbor_Financeiro.html').write_text(local, encoding='utf-8')

    for f in ('index.html', 'SafeHarbor_Financeiro.html'):
        print(f'dist/{f}: {(dist / f).stat().st_size / 1024:.0f} KB')


if __name__ == '__main__':
    main()
