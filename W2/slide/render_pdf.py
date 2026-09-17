from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from lxml import html, etree
from html import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, Preformatted, Flowable
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import NameObject
import json, re, base64, io
base=Path(__file__).resolve().parent
# Capture the PDF build time once, independently of the saved HTML's timestamp.
compiled_at=datetime.now(ZoneInfo('Asia/Taipei'))
compiled_label=f'Last compiled: {compiled_at:%Y-%m-%d %H:%M:%S} (Asia/Taipei)'
font_dir=Path('/Applications/quarto/share/formats/revealjs/reveal/dist/theme/fonts/source-sans-pro')
for n,f in [('SourceSans','regular'),('SourceSans-Semibold','semibold'),('SourceSans-Italic','italic'),('SourceSans-SemiboldItalic','semibolditalic')]:
 pdfmetrics.registerFont(TTFont(n,str(font_dir/f'source-sans-pro-{f}.ttf')))
for n,f in [('Mono','Courier New.ttf'),('CJK','Arial Unicode.ttf')]:
 pdfmetrics.registerFont(TTFont(n,'/System/Library/Fonts/Supplemental/'+f))
pdfmetrics.registerFontFamily('SourceSans',normal='SourceSans',bold='SourceSans-Semibold',italic='SourceSans-Italic',boldItalic='SourceSans-SemiboldItalic')
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
INK=colors.HexColor('#1f2a37'); SLATE=colors.HexColor('#314f4f'); BLUE=colors.HexColor('#0271bb')
GREEN=colors.HexColor('#7cae96'); MUTED=colors.HexColor('#5f6f7f'); LINE=colors.HexColor('#d9e3df')
W,H=1050,700; LEFT=48; CW=W-2*LEFT
TITLE_TOP=40; BODY_BOTTOM=78
root=html.fromstring((base/'week1.html').read_text(encoding='utf-8'))
sections=root.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," slides ")]/section')
def classes(e): return e.get('class','').split()
# These slides are authored in R so Thai shaping, fonts, and dependency arrows
# remain exactly as in their R-generated PDF assets. pypdf merges native pages.
companion_pages={
 'three-languages':('udpipe_example_pages.pdf',0),
 'thai-dependency':('udpipe_example_pages.pdf',1),
 'dependency-labels':('udpipe_dependency_labels.pdf',0),
 'token-dfm':('token_to_dfm_diagram.pdf',0),
}
companion_specs={
 'udpipe_example_pages.pdf':(2,'tokenization_th_ja_zh.R'),
 'udpipe_dependency_labels.pdf':(1,'udpipe_zh_en_th_dependencies.R'),
 'token_to_dfm_diagram.pdf':(1,'token_to_dfm_diagram.R'),
}
# Bounds of the saved vector bodies on their 1050 x 700 pages, measured from
# the top edge and excluding their headings and source lines.
companion_body_bounds={
 ('udpipe_example_pages.pdf',0):(138.,641.578125),
 ('udpipe_example_pages.pdf',1):(134.000198,638.226563),
 ('udpipe_dependency_labels.pdf',0):(138.,649.992188),
 ('token_to_dfm_diagram.pdf',0):(124.,634.730469),
}
inserted_pages={}
for idx,s in enumerate(sections):
 matches=[companion_pages[name] for name in classes(s) if name in companion_pages]
 if len(matches)>1:raise ValueError(f'Slide {idx+1} has conflicting companion slide classes')
 if matches:inserted_pages[idx]=matches[0]
def remove_companion_heading(page):
 # The saved R pages contain their own heading and horizontal rule. Remove
 # just those drawing operations in memory, then use the shared slide header.
 # The source line is redrawn at the shared footer position. Body text,
 # multilingual font shaping, and vector diagrams remain intact.
 content=page.get_contents(); ops=content.operations
 if ops[0]!=( [1,0,0,-1,0,H], b'cm'):
  raise ValueError('Unexpected companion coordinate system')
 start=next(i for i,(_,op) in enumerate(ops) if op==b'BT')
 end=next(i for i in range(start+1,len(ops)) if ops[i][1]==b'ET')
 matrices=[args for args,op in ops[start:end] if op==b'Tm']
 if len(matrices)!=1 or not (40<=float(matrices[0][0])<=45 and float(matrices[0][4])==LEFT and 0<float(matrices[0][5])<100):
  raise ValueError('Unexpected companion heading; preserve the original asset')
 rules=[]
 for i in range(end+1,len(ops)-2):
  a,op=ops[i]; b,op2=ops[i+1]
  if (op==b'm' and op2==b'l' and ops[i+2][1]==b'S'
      and len(a)==len(b)==2 and float(a[0])==LEFT and float(b[0])==W-LEFT
      and float(a[1])==float(b[1]) and 100<=float(a[1])<=120):rules.append(i)
 if len(rules)!=1:raise ValueError('Expected one companion heading rule')
 removed=set(range(start,end+1))|set(range(rules[0],rules[0]+3))
 footer=False;footer_runs=0
 for i,(args,op) in enumerate(ops):
  if op==b'Tm':footer=float(args[5])>=650
  elif op in (b'Tj',b'TJ') and footer:
   removed.add(i);footer_runs+=1
  elif op==b'ET':footer=False
 if footer_runs!=1:raise ValueError('Expected one companion source line')
 content.operations=[op for i,op in enumerate(ops) if i not in removed]
 page[NameObject('/Contents')]=content

companions={}
for filename in {asset for asset,_ in inserted_pages.values()}:
 expected_pages,script=companion_specs[filename]
 companion_path=base.parent/'image'/filename
 if not companion_path.is_file():
  raise FileNotFoundError(f'Missing R-generated PDF asset: {companion_path}. Run Rscript {base.parent / "lab" / script} first.')
 companion=PdfReader(io.BytesIO(companion_path.read_bytes()))
 if len(companion.pages)!=expected_pages:
  raise ValueError(f'Expected {expected_pages} companion PDF pages, found {len(companion.pages)}: {companion_path}')
 for idx,page in enumerate(companion.pages,1):
  if tuple(float(v) for v in page.mediabox)!=(0.,0.,float(W),float(H)) or tuple(page.cropbox)!=tuple(page.mediabox) or page.rotation:
   raise ValueError(f'Companion page {idx} must be an unrotated {W} x {H} page with an unchanged crop box')
  remove_companion_heading(page)
 companions[filename]=companion
def txt(e): return ''.join(e.itertext()).strip()
def safe_text(t):
 return re.sub(r'[\u2e80-\u9fff\u3040-\u30ff\uff00-\uffef]+', lambda m: '<font name="CJK">'+m.group(0)+'</font>', escape(t).replace('₁₀', '<sub>10</sub>'))
def inline(e):
 out=safe_text(e.text or '')
 for c in e:
  tag=c.tag
  child=inline(c)
  if tag=='strong': child=f'<b><font color="#314f4f">{child}</font></b>'
  elif tag in ('em','i'): child=f'<i>{child}</i>'
  elif tag=='code': child=f'<font name="Mono" color="#075c75">{child}</font>'
  elif tag=='a' and c.get('href','').startswith('http'): child=f'<link href="{escape(c.get("href"),quote=True)}" color="#0271bb">{child}</link>'
  elif tag=='br': child='<br/>'
  elif tag in ('button','script'): child=''
  out+=child+safe_text(c.tail or '')
 return out

def style(size=28,**kw):
 d=dict(name='body',fontName='SourceSans',fontSize=size,leading=size*1.28,textColor=INK,spaceAfter=15)
 d.update(kw)
 return ParagraphStyle(**d)

class Code(Flowable):
 def __init__(self,text,width,size=20):
  Flowable.__init__(self); self.text=text; self.width=width; self.size=size
  self.lines=text.splitlines(); self.height=len(self.lines)*size*1.34+28
  longest=max((pdfmetrics.stringWidth(l,'Mono',size) for l in self.lines),default=0)
  if longest>width-36: raise ValueError(f'Code too wide: {longest}/{width}, {text}')
 def wrap(self,a,b): return self.width,self.height
 def draw(self):
  c=self.canv;c.setFillColor(colors.white);c.setStrokeColor(colors.HexColor('#d0d0d0'));c.setLineWidth(1)
  c.roundRect(0,0,self.width,self.height,3,fill=1,stroke=1)
  c.setFillColor(colors.HexColor('#00445d'));c.setFont('Mono',self.size)
  for i,l in enumerate(self.lines):
   x=16; y=self.height-20-self.size-i*self.size*1.34
   for segment in re.split(r'([\u2e80-\u9fff\u3040-\u30ff\uff00-\uffef]+)',l):
    font='CJK' if re.search(r'[\u2e80-\u9fff\u3040-\u30ff\uff00-\uffef]',segment) else 'Mono'
    c.setFont(font,self.size);c.drawString(x,y,segment);x+=pdfmetrics.stringWidth(segment,font,self.size)

class SourceCrop(Flowable):
 def __init__(self,kind,width):
  Flowable.__init__(self); self.kind=kind;self.width=width
  self.image=ImageReader(str(base.parent/'image/welbers2017-table1-figure1.png'))
  iw,ih=self.image.getSize();self.img_h=width*ih/iw
  self.height=width*(526/1300 if kind=='table' else 390/1300)
  self.shift=0 if kind=='table' else width*536/1300
 def wrap(self,a,b):return self.width,self.height
 def draw(self):
  c=self.canv;c.saveState();p=c.beginPath();p.rect(0,0,self.width,self.height);c.clipPath(p,stroke=0)
  c.drawImage(self.image,0,self.height-self.img_h+self.shift,width=self.width,height=self.img_h,mask='auto')
  c.restoreState()

class SlideImage(Flowable):
 def __init__(self,element,width):
  Flowable.__init__(self)
  src=element.get('src') or element.get('data-src','')
  data=io.BytesIO(base64.b64decode(src.split(',',1)[1])) if src.startswith('data:image/') else str(base/src)
  self.image=ImageReader(data)
  iw,ih=self.image.getSize()
  self.width=width;self.height=width*ih/iw
 def wrap(self,a,b):return self.width,self.height
 def draw(self):self.canv.drawImage(self.image,0,0,width=self.width,height=self.height,mask='auto')

def make_table(e,width,size):
 rows=e.xpath('./thead/tr|./tbody/tr|./tr'); n=len(rows[0])
 # Use content-aware column widths for short identifiers and numerical cells.
 texts=[[txt(c) for c in r if c.tag in ('th','td')] for r in rows]
 if n==2: ratios=[.34,.66]
 elif n==3: ratios=[.27,.32,.41]
 else: ratios=[1/n]*n
 # Keep the longest software identifier intact in the R/Python overview.
 if texts[0]==['Stage','Example tools','Contribution']: ratios=[.24,.36,.40]
 if texts[0]==['Tool','What it lets you do']: ratios=[.18,.82]
 # Numeric tables get wider identifier column only where needed.
 if n==3 and all(all(re.fullmatch(r'[0-9.]+',v) for v in row[1:]) for row in texts[1:]): ratios=[.60,.20,.20]
 if n==4: ratios=[.14,.33,.15,.38]
 if n>=5: ratios=[1/n]*n
 if texts[0]==['ID','token','lemma','upos','head','dep_rel']:
  ratios=[.08,.20,.20,.16,.12,.24]
 data=[]
 for i,r in enumerate(rows):
  vals=[]
  for cell in r:
   if cell.tag not in ('td','th'):continue
   st=style(size,spaceAfter=0,fontName='SourceSans-Semibold' if cell.tag=='th' else 'SourceSans',textColor=SLATE if cell.tag=='th' else INK)
   vals.append(Paragraph(inline(cell),st))
  data.append(vals)
 t=Table(data,colWidths=[width*r for r in ratios],hAlign='LEFT')
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),7 if size<=21 else 10),('BOTTOMPADDING',(0,0),(-1,-1),7 if size<=21 else 10),('LINEABOVE',(0,0),(-1,0),2,colors.black),('LINEBELOW',(0,0),(-1,0),1,colors.black),('LINEBELOW',(0,-1),(-1,-1),2,colors.black)]))
 return t

def flow(e,width=CW,size=28):
 out=[]; tag=e.tag; cl=classes(e)
 if tag in ('aside','script','h2') or 'notes' in cl or 'source' in cl: return out
 if tag=='img': return [SlideImage(e,width),Spacer(1,14)]
 if tag=='p' and e.find('img') is not None:return flow(e.find('img'),width,size)
 if tag=='p': return [Paragraph(inline(e),style(size))]
 if tag in ('ul','ol'):
  for i,li in enumerate(e):
   if li.tag!='li':continue
   prefix=f'{i+1}. ' if tag=='ol' else '• '
   out.append(Paragraph(escape(prefix)+inline(li),style(size,leftIndent=22,firstLineIndent=-22,spaceAfter=14)))
  return out
 if tag=='h3': return [Paragraph(inline(e),style(size,fontName='SourceSans-Semibold',textColor=SLATE,spaceAfter=18))]
 if tag=='pre': return [Code(txt(e),width,20 if size>=25 else 18),Spacer(1,16)]
 if tag=='table': return [make_table(e,width,min(size,23)),Spacer(1,22)]
 if 'source-crop' in cl: return [SourceCrop('table' if 'table-crop' in cl else 'figure',width*.94 if 'table-crop' in cl else width),Spacer(1,20)]
 if 'columns' in cl:
  columns=[c for c in e if 'column' in classes(c)]
  cells=[sum((flow(n,(width-36)/2,size) for n in col),[]) for col in columns]
  t=Table([[cells[0],'',cells[1]]],colWidths=[(width-36)/2,36,(width-36)/2]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
  return [t,Spacer(1,20)]
 if 'key' in cl:
  paragraphs=[Paragraph(inline(child),style(min(size+1,29),textColor=SLATE,spaceAfter=0)) for child in e]
  box=Table([[paragraphs]],colWidths=[width],hAlign='LEFT')
  box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f4f8f6')),('LINEBEFORE',(0,0),(0,-1),6,GREEN),('LEFTPADDING',(0,0),(-1,-1),20),('RIGHTPADDING',(0,0),(-1,-1),20),('TOPPADDING',(0,0),(-1,-1),14),('BOTTOMPADDING',(0,0),(-1,-1),14)]))
  return [Spacer(1,8),box,Spacer(1,15)]
 if 'small' in cl:size=min(size,23)
 if 'tight' in cl:size=min(size,21)
 if 'mathline' in cl:size=min(size+2,30)
 for c in e:out.extend(flow(c,width,size))
 return out

def height(items): return sum(f.wrap(CW,H)[1]+f.getSpaceBefore()+f.getSpaceAfter() for f in items)

def draw_items(c,items,y):
 for f in items:
  y-=f.getSpaceBefore();w,h=f.wrap(CW,H);f.drawOn(c,LEFT,y-h);y-=h+f.getSpaceAfter()
 return y

def heading_paragraph(section):
 p=Paragraph(inline(section.find('h2')),style(45,fontName='SourceSans-Semibold',textColor=SLATE,leading=49.5,spaceAfter=0))
 _,th=p.wrap(CW,130)
 return p,th

def draw_heading(c,p,th):
 top=H-TITLE_TOP
 p.drawOn(c,LEFT,top-th)
 ruley=top-th-12
 c.setStrokeColor(LINE);c.setLineWidth(2);c.line(LEFT,ruley,W-LEFT,ruley)
 return ruley-24

def draw_source(c,section):
 source=section.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," source ")]')
 if source:
  sp=Paragraph(inline(source[0]),style(13,textColor=MUTED,leading=17,spaceAfter=0))
  _,sh=sp.wrap(CW-70,60);sp.drawOn(c,LEFT,30)

pdf=base/'week1.pdf'
rendered=io.BytesIO()
c=canvas.Canvas(rendered,pagesize=(W,H));c.setTitle(txt(root.xpath('//section[@id="title-slide"]/h1')[0]));c.setAuthor('Yen-Chieh Liao')
log=[]
companion_transforms={}
for idx,s in enumerate(sections,1):
 if idx-1 in inserted_pages:
  # Use the same heading as every content slide, above the saved R body.
  p,th=heading_paragraph(s);body_top=draw_heading(c,p,th)
  asset,asset_page=inserted_pages[idx-1]
  original_top,original_bottom=companion_body_bounds[(asset,asset_page)]
  available=body_top-BODY_BOTTOM
  scale=min(1.,available/(original_bottom-original_top))
  used=scale*(original_bottom-original_top)
  gap=(available-used)/2
  target_top=body_top-gap
  companion_transforms[idx-1]=Transformation().scale(scale).translate(
   tx=LEFT*(1-scale),ty=target_top-scale*(H-original_top))
  draw_source(c,s)
  log.append({'page':idx,'title':txt(s.find('h2')),'companion_asset':asset,'companion_page':asset_page+1,'body_scale':scale,'top_gap':gap,'bottom_gap':gap})
 elif s.get('id')=='title-slide':
  # Match the course title slide while preserving the text authored in Quarto.
  title=s.find('h1')
  subtitle=s.xpath('./p[contains(concat(" ",normalize-space(@class)," ")," subtitle ")]')
  author=s.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," quarto-title-author-name ")]')
  date=s.xpath('./p[contains(concat(" ",normalize-space(@class)," ")," date ")]')
  lecture_date=''.join(date[0].xpath('./text()')).strip()
  tx=.115*W;tw=.77*W
  for text,top,size,leading,font,color in [
   (txt(title),.24*H,52.2,56.376,'SourceSans-Semibold',SLATE),
   (txt(subtitle[0]),.445*H,33.84,44.0,'SourceSans-Semibold',GREEN),
   (txt(author[0]),.635*H,28.08,35.1,'SourceSans-Semibold',INK),
   (lecture_date,.702*H,28.08,35.1,'SourceSans-Semibold',INK),
   (compiled_label,.702*H+35.1+12,18,23.4,'SourceSans',MUTED),
  ]:
   p=Paragraph(safe_text(text),style(size,fontName=font,textColor=color,leading=leading,spaceAfter=0))
   _,ph=p.wrap(tw,160);p.drawOn(c,tx,H-top-ph)
  c.setStrokeColor(LINE);c.setLineWidth(2);c.line(tx,H-.585*H,W-tx,H-.585*H)
  c.drawImage(str(base.parent/'image/ntu-logo.png'),W-tx-220,H-.616*H-102,width=220,height=102,mask='auto')
 else:
  title=txt(s.find('h2'));p,th=heading_paragraph(s)
  # Most slides use the course's 28pt body. Dense tables and code may use a
  # restrained compact tier. The title always starts at the same position,
  # and the body is centered within the safe area above the citation.
  for body_size in (28,26,24,23,22):
   items=[]
   for node in s:items.extend(flow(node,size=body_size))
   used=height(items)
   group_height=th+12+24+used
   if group_height<=H-TITLE_TOP-BODY_BOTTOM:break
  else:raise ValueError(f'Overflow {idx} {title}: {group_height}, {H-TITLE_TOP-BODY_BOTTOM} available')
  body_top=draw_heading(c,p,th)
  gap=(body_top-BODY_BOTTOM-used)/2
  y=body_top-gap
  bottom=draw_items(c,items,y)
  if gap<0 or abs((bottom-BODY_BOTTOM)-gap)>.01:
   raise ValueError(f'Unbalanced body on slide {idx}')
  log.append({'page':idx,'title':title,'body_size':body_size,'content_bottom':round(bottom,1),'top_gap':gap,'bottom_gap':bottom-BODY_BOTTOM})
  draw_source(c,s)
 c.setFont('SourceSans',12);c.setFillColor(BLUE);c.drawRightString(W-16,16,str(idx))
 c.showPage()
c.save()
if inserted_pages:
 generated=PdfReader(rendered)
 writer=PdfWriter()
 for idx,page in enumerate(generated.pages):
  if idx in inserted_pages:
   asset,asset_page=inserted_pages[idx]
   page.merge_transformed_page(companions[asset].pages[asset_page],companion_transforms[idx],over=False)
  writer.add_page(page)
 if generated.metadata:writer.add_metadata(dict(generated.metadata))
 merged=io.BytesIO();writer.write(merged)
 output=merged.getvalue()
else:output=rendered.getvalue()
# Leave the previous deliverable intact until rendering and merging succeed.
temporary=pdf.with_suffix('.pdf.tmp')
temporary.write_bytes(output);temporary.replace(pdf)
# Content-fit checks above reject overflowing pages before delivery.
print(f'Created {len(sections)} pages: {pdf}')
