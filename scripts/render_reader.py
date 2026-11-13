#!/usr/bin/env python3
"""Render a source-ordered bilingual paper reader. Python standard library only."""
from pathlib import Path
import argparse,base64,hashlib,html,json,mimetypes,re

SKILL=Path(__file__).resolve().parents[1]
CATEGORIES={'thesis':'核心论点','concept':'关键概念','evidence':'实证证据','concession':'让步反驳','method':'方法说明'}
ENGLISH={'thesis':'Thesis','concept':'Concept','evidence':'Evidence','concession':'Concession','method':'Method'}
def esc(s):return html.escape(str(s),quote=True)
def identifier(s):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*',s):raise ValueError(f'Invalid id: {s}')
    return s

def validate(data):
    assert data.get('schema_version')==1,'schema_version must be 1'
    assert data['paper']['title'],'A paper title is required'
    assert data['items'],'No ordered content items'
    ids=set();last_page=0;rows=[]
    for item in data['items']:
        ident=identifier(item['id']);assert ident not in ids,f'Duplicate id: {ident}';ids.add(ident)
        assert item['type'] in ['section','chapter','paragraph','figure','references'],f'Unknown item type: {item["type"]}'
        if 'order_page' in item:
            page=item['order_page'];assert page>=last_page,f'Source order regressed at {ident}: {page} < {last_page}';last_page=page
        if item['type'] not in ['paragraph','figure']:continue
        rows.append(item)
        for field in ['en','zh','function','role','note']:
            assert item.get(field,'').strip(),f'{ident}: empty {field}'
        for field in ['function','role','note']:
            assert re.search(r'[\u3400-\u9fff]',item[field]),f'{ident}: annotation field {field} must be Chinese'
        assert item.get('pages'),f'{ident}: source pages required'
        for p in item['pages']:assert str(p) in data.get('images',{}).get('pages',{}),f'{ident}: missing source page {p}'
        if item['type']=='figure':assert str(item['image_key']) in data.get('images',{}).get('figures',{}),f'{ident}: missing figure image'
        for category,phrases in item.get('highlights',{}).items():
            assert category in CATEGORIES,f'{ident}: unknown highlight category {category}'
            for phrase in phrases:assert phrase.casefold() in item['en'].casefold(),f'{ident}: highlight not in source: {phrase}'
        selected=[(category,html.unescape(text).casefold()) for category,text in re.findall(r'<mark class="hl (\w+)"[^>]*>(.*?)</mark>',highlighter(item),re.S)]
        pairs=item.get('highlight_pairs',[])
        assert sorted(selected)==sorted((p['category'],p['en'].casefold()) for p in pairs),f'{ident}: every English highlight needs a matching Chinese alignment'
        for pair in pairs:
            assert pair['category'] in CATEGORIES and pair['en'],'Invalid paired highlight'
            for phrase in pair['zh']:
                assert phrase and phrase in item['zh'],f'{ident}: Chinese highlight not in translation: {phrase}'
        translation_highlighter(item)
    assert sum(i['type']=='references' for i in data['items'])==1,'Include one references item (empty entries permitted)'
    assert not ids.intersection({'top','main','argument','source','source-dialog','course'}),'Reserved DOM id used'
    return rows

def embed_image(value,base):
    if value.startswith('data:image/'):return value
    if re.match(r'https?://',value):raise ValueError('Download images first; output must have no remote image dependency')
    p=Path(value);p=p if p.is_absolute() else base/p
    mime=mimetypes.guess_type(p.name)[0] or 'image/jpeg'
    assert mime.startswith('image/'),f'Not an image: {p}'
    return 'data:'+mime+';base64,'+base64.b64encode(p.read_bytes()).decode('ascii')

def highlighter(item):
    text=item['en'];spans=[]
    def add(phrase,category):
        match=re.search(re.escape(phrase),text,re.I)
        if not match:return False
        start,end=match.span()
        if any(start<e and end>s for s,e,c in spans):return False
        spans.append((start,end,category));return True
    for category,phrases in item.get('highlights',{}).items():
        for phrase in phrases:add(phrase,category)
    for term in item.get('terms',[])[:2]:add(term,'concept')
    out=[];pos=0
    for start,end,category in sorted(spans):
        link=''
        for number,pair in enumerate(item.get('highlight_pairs',[]),1):
            if pair['category']==category and pair['en'].casefold()==text[start:end].casefold():link=f' data-alignment="{esc(item["id"])}-h{number}"';break
        out.extend([esc(text[pos:start]),f'<mark class="hl {category}"{link} title="{CATEGORIES[category]}">{esc(text[start:end])}</mark>']);pos=end
    out.append(esc(text[pos:]));return ''.join(out)

def translation_highlighter(item):
    text=item['zh'];spans=[]
    for number,pair in enumerate(item.get('highlight_pairs',[]),1):
        for phrase in pair['zh']:
            # The first occurrence is deliberate. Use a longer phrase to disambiguate
            # repeated translated terms, rather than silently coloring a different one.
            start=text.find(phrase);assert start>=0,f'{item["id"]}: missing Chinese phrase {phrase}'
            end=start+len(phrase)
            assert not any(start<e and end>s for s,e,c,n in spans),f'{item["id"]}: overlapping Chinese alignment: {phrase}'
            spans.append((start,end,pair['category'],number))
    out=[];pos=0
    for start,end,category,number in sorted(spans):
        link=f'{item["id"]}-h{number}'
        out.extend([esc(text[pos:start]),f'<mark class="hl {category}" data-alignment="{esc(link)}" title="{CATEGORIES[category]} · 与英文对应">{esc(text[start:end])}</mark>']);pos=end
    out.append(esc(text[pos:]));return ''.join(out)

def annotate(item):
    return f'''<aside class="annotation" lang="zh-CN" aria-label="{esc(item['id'])}的中文论证批注"><div class="note-id">论证批注 <span>{esc(item['id'])}</span></div><dl><dt>段落功能</dt><dd>{esc(item['function'])}</dd><dt>逻辑角色</dt><dd>{esc(item['role'])}</dd><dt>论证技巧与潜在漏洞</dt><dd>{esc(item['note'])}</dd></dl></aside>'''

def render_row(item):
    ident=item['id'];isfigure=item['type']=='figure';category=item.get('category','evidence');assert category in {*CATEGORIES,'neutral'}
    refs=' '.join(f'<button class="source-ref" data-page="{int(p)}" aria-label="查看原PDF第{int(p)}页">PDF p.{int(p)}</button>' for p in item['pages'])
    image=''
    if isfigure:
        key=esc(item['image_key']);title=esc(item['title']);page=item.get('image_page',item['order_page'])
        image=f'''<figure class="figure-panel"><button class="figure-open" data-figure="{key}" data-title="{title}" aria-label="放大{title}"><img data-image="figures:{key}" loading="lazy" width="1080" height="1350" alt="{title}，原论文图版"><span>点击放大源图 ↗</span></button><figcaption>源图：合并PDF第{int(page)}页</figcaption></figure>'''
    row=f'''<article class="pair {category}" id="{ident}" data-search="{ident}" data-order-page="{int(item['order_page'])}"><div class="bilingual"><div class="paragraph-meta"><a class="paragraph-id" href="#{ident}">{ident}</a><span>{'原图与图注' if isfigure else '原文'} · EN / 中</span><span class="source-links">{refs}</span></div>{image}<p class="original" lang="en">{highlighter(item)}</p><div class="translation" lang="zh-CN"><span class="translation-label">中文意译</span><p>{translation_highlighter(item)}</p></div></div>{annotate(item)}</article>'''
    heading=''
    if item.get('subheading'):heading=f'<h3 class="record-heading">{esc(item["subheading"])}</h3>'
    if isfigure:return f'<div class="inline-figure"><h3 class="record-heading figure-title">{esc(item["title"])}</h3>{row}</div>'
    return heading+row

def render_items(items):
    out=[];open_section=False
    for item in items:
        typ=item['type'];ident=item['id']
        if typ in ['section','chapter','references'] and open_section:out.append('</section>');open_section=False
        if typ=='chapter':out.append(f'<div class="chapter-banner" id="{ident}"><span>{esc(item.get("kicker",""))}</span><h2>{esc(item["title"])}</h2><p>{esc(item.get("description",""))}</p></div>')
        elif typ=='section':
            out.append(f'<section class="reading-section" id="{ident}" aria-labelledby="heading-{ident}"><header class="section-heading"><span class="eyebrow">{esc(item.get("kicker",""))}</span><h2 id="heading-{ident}">{esc(item["title"])}</h2><p class="section-original" lang="en">{esc(item.get("subtitle",""))}</p><p class="section-description">{esc(item.get("description",""))}</p></header>');open_section=True
        elif typ in ['paragraph','figure']:out.append(render_row(item))
        elif typ=='references':
            entries=item.get('entries',[]);bibliography=''.join(f'<li id="ref-{n+1}" lang="en">{esc(entry)}</li>' for n,entry in enumerate(entries))
            note=annotate(item) if all(item.get(k,'').strip() for k in ['function','role','note']) else ''
            description=f'<p class="section-description">{esc(item["description"])}</p>' if item.get('description') else ''
            bibliography=f'<details class="reference-details"><summary>展开全部{len(entries)}条参考文献</summary><ol class="references">{bibliography}</ol></details>'
            content=f'<div class="refs-header"><div>{bibliography}</div>{note}</div>' if note else bibliography
            out.append(f'<section id="{ident}" class="reading-section"><header class="section-heading"><h2>参考文献</h2>{description}</header>{content}</section>')
    if open_section:out.append('</section>')
    return '\n'.join(out)

def render_overview(arg):
    out=['<section id="argument" class="overview"><header class="overview-heading"><h2>全文论证结构总览</h2></header>']
    out.append(f'<div class="thesis-statement"><span class="eyebrow">作者核心主张 · 一句话</span><p>{esc(arg["thesis"])}</p></div><div class="logic-chain">')
    colors=['concept','thesis','evidence','concession','thesis']
    for index,step in enumerate(arg['chain']):
        href=identifier(step['target'])
        out.append(f'<div class="logic-step" style="--cat:var(--{colors[index%5]})"><small>{index+1:02d}</small><h3>{esc(step["label"])}</h3><p>{esc(step["text"])}</p><a href="#{href}">查看依据 ↗</a></div>')
    out.append('</div>')
    if arg.get('matrix'):
        out.append('<div class="matrix-wrap"><table class="matrix"><caption>主张与证据的对应关系</caption><thead><tr><th>论证环节</th><th>现有证据支持什么</th><th>仍未解决什么</th></tr></thead><tbody>')
        for entry in arg['matrix']:out.append('<tr>'+''.join(f'<td>{esc(entry[key])}</td>' for key in ['claim','supports','limits'])+'</tr>')
        out.append('</tbody></table></div>')
    out.append('<div class="strength-weakness">')
    for key,label,cls in [('strongest','最强处',''),('weakest','最弱处','weak')]:
        value=arg[key];out.append(f'<article class="assessment {cls}"><span class="eyebrow">{label}</span><h3>{esc(value["title"])}</h3><p>{esc(value["text"])}</p></article>')
    out.append('</div></section>');return ''.join(out)

def render(data,base):
    rows=validate(data);paper=data['paper'];title=paper['title'];figures=[r for r in rows if r['type']=='figure'];pagecount=len(data.get('images',{}).get('pages',{}))
    images={'pages':{},'figures':{},'figure_pages':{}}
    for group in ['pages','figures']:
        images[group]={str(k):embed_image(v,base) for k,v in data.get('images',{}).get(group,{}).items()}
    for figure in figures:images['figure_pages'][str(figure['image_key'])]=figure.get('image_page',figure['order_page'])
    fontcss=[]
    for family,name,weights in [('Lora','lora',[(0,400),(2,600),(3,700)]),('IBM Plex Sans','plex',[(0,400),(1,500),(2,600)])]:
        for index,weight in weights:
            font=SKILL/f'assets/fonts/{name}-{index}.ttf';encoded=base64.b64encode(font.read_bytes()).decode('ascii')
            fontcss.append(f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;font-display:swap;src:url(data:font/ttf;base64,{encoded}) format('truetype')}}")
    legends=''.join(f'<button data-category="{key}" aria-pressed="true" style="--cat:var(--{key})" title="{CATEGORIES[key]} / {ENGLISH[key]}"><i class="swatch"></i><span class="legend-label">{CATEGORIES[key]}<span class="legend-en"> / {ENGLISH[key]}</span></span></button>' for key in CATEGORIES)
    course=paper.get('course') or '课程信息：点击填写课程名称'
    doi=paper.get('doi','');doihtml=''
    if doi:doihtml=f'<br><a href="https://doi.org/{esc(doi)}" target="_blank" rel="noopener">DOI: {esc(doi)} ↗</a>'
    header=f'''<header class="masthead"><div class="wrap"><div class="masthead-top"><span class="course" id="course" contenteditable="true" role="textbox" aria-label="课程信息，可点击填写" spellcheck="false">{esc(course)}</span></div><div class="hero"><div><h1 lang="en">{esc(title)}</h1><p class="zh-title">{esc(paper.get('title_zh',''))}</p><p class="citation">{esc(paper.get('authors',''))}<br>{esc(paper.get('citation',''))}{doihtml}</p></div></div></div></header>'''
    nav=''.join(f'<a href="#{item["id"]}">{esc(item["nav_label"])}</a>' for item in data['items'] if item.get('nav_label'))+'<a href="#argument">论证总览</a><a href="#source">原页核对</a>'
    options=''.join(f'<option value="{i["id"]}">{esc(i.get("title",i["id"]))}</option>' for i in data['items'] if i['type'] in ['chapter','section','figure','references'])
    material_notes=[line for line in data.get('coverage',[]) if line.strip()]
    coverage=('<details class="coverage"><summary>材料说明</summary><ul>'+''.join(f'<li>{esc(line)}</li>' for line in material_notes)+'</ul></details>') if material_notes else ''
    thumbs=''.join(f'<button class="page-thumb" data-page="{int(p)}"><img data-image="pages:{int(p)}" loading="lazy" width="230" height="310" alt="原PDF第{int(p)}页预览"><span>PDF {int(p):02d}</span></button>' for p in sorted(images['pages'],key=int))
    archive=f'<section id="source" class="source-archive"><details><summary>原页核对 · 展开{pagecount}页PDF图像</summary><p class="archive-note">点击缩略图查看原页，左右箭头翻页，Esc关闭。正文中的“PDF p.”直接打开对应页。</p><div class="page-grid">{thumbs}</div></details></section>'
    slots={'TITLE':esc(title),'STORAGE_KEY':'paper-reader-'+hashlib.sha256(title.encode()).hexdigest()[:16],'HEADER':header,'LEGEND':legends,'NAV':nav,'OPTIONS':options,'CONTENT':render_items(data['items']),'OVERVIEW':render_overview(data['argument']),'COVERAGE':coverage,'SOURCE':archive,'IMAGES':json.dumps(images,separators=(',',':')).replace('</','<\\/'),'FONTS':'\n'.join(fontcss),'CSS':(SKILL/'assets/reader.css').read_text(encoding='utf8'),'JS':(SKILL/'assets/reader.js').read_text(encoding='utf8')}
    output=(SKILL/'assets/shell.html').read_text(encoding='utf8')
    for key,value in slots.items():output=output.replace('@@'+key+'@@',value)
    assert not re.search(r'@@[A-Z_]+@@',output),'Unfilled template slot'
    licenses='\n\n'.join(p.read_text(encoding='utf8') for p in sorted((SKILL/'assets/fonts').glob('*OFL.txt')))
    output=output.replace('</body>','<script type="text/plain" id="font-licenses">'+licenses.replace('</','<\\/')+'</script></body>')
    report={'pairs':len(rows),'paragraphs':sum(r['type']=='paragraph' for r in rows),'figures':len(figures),'pages':pagecount,'annotations_language':'zh-CN','aligned_highlights':sum(len(r.get('highlight_pairs',[])) for r in rows),'ordered_ids':[r['id'] for r in rows],'source_order_pages':[r['order_page'] for r in rows],'external_asset_dependencies':0}
    return output,report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--report',type=Path);args=parser.parse_args()
    data=json.loads(args.input.read_text(encoding='utf8'));output,report=render(data,args.input.resolve().parent)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(output,encoding='utf8')
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'output':str(args.output.resolve()),'bytes':args.output.stat().st_size,**{k:v for k,v in report.items() if k not in ['ordered_ids','source_order_pages']}},ensure_ascii=False))

if __name__=='__main__':main()
