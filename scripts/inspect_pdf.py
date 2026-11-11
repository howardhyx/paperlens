#!/usr/bin/env python3
"""Extract source text/line positions and optional page previews without guessing reading order."""
from pathlib import Path
import argparse,json

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf',type=Path);parser.add_argument('directory',type=Path)
    parser.add_argument('--render',action='store_true');parser.add_argument('--dpi',type=int,default=110)
    parser.add_argument('--pages',help='Optional comma-separated one-based pages, for example 1,2,5')
    args=parser.parse_args()
    import pdfplumber
    selected={int(n) for n in args.pages.split(',')} if args.pages else None
    args.directory.mkdir(parents=True,exist_ok=True)
    result=[];thumbs=[];ocr=[]
    with pdfplumber.open(args.pdf) as doc:
        for number,page in enumerate(doc.pages,1):
            if selected is not None and number not in selected:continue
            text=page.extract_text() or ''
            lines=[{'text':line['text'],'bbox':[round(line[k],2) for k in ['x0','top','x1','bottom']]} for line in page.extract_text_lines()]
            words=[{k:word[k] for k in ['text','x0','x1','top','bottom']} for word in page.extract_words()]
            item={'page':number,'width':page.width,'height':page.height,'text':text,'lines':lines,'words':words}
            if len(text.strip())<120:ocr.append(number)
            (args.directory/f'page-{number:03}.txt').write_text(text,encoding='utf8')
            if args.render:
                from PIL import Image,ImageDraw
                image=page.to_image(resolution=args.dpi).original.convert('RGB')
                image.save(args.directory/f'page-{number:03}.jpg',quality=86,optimize=True)
                item['image']=f'page-{number:03}.jpg'
                image.thumbnail((220,300));tile=Image.new('RGB',(240,330),'#e5e5df');tile.paste(image,((240-image.width)//2,24));ImageDraw.Draw(tile).text((10,7),f'PDF {number}',fill='#10263e');thumbs.append(tile)
            result.append(item)
        total=len(doc.pages)
    (args.directory/'pages.json').write_text(json.dumps({'source':str(args.pdf.resolve()),'page_count':total,'pages':result,'sparse_text_pages':ocr},ensure_ascii=False,indent=2),encoding='utf8')
    if args.render:
        from PIL import Image
        for start in range(0,len(thumbs),12):
            batch=thumbs[start:start+12];sheet=Image.new('RGB',(960,330*((len(batch)+3)//4)),'white')
            for i,tile in enumerate(batch):sheet.paste(tile,((i%4)*240,(i//4)*330))
            sheet.save(args.directory/f'contact-{start//12+1:02}.jpg',quality=88)
    print(json.dumps({'pdf_pages':total,'inspected':len(result),'sparse_text_pages':ocr,'note':'Sparse text may indicate a figure-only page or a scan; inspect its image before deciding whether OCR is needed.'},ensure_ascii=False))

if __name__=='__main__':main()
