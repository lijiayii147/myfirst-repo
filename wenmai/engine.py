"""Deterministic structure analysis; no untrained cultural recognition claims."""
from collections import deque
from io import BytesIO
import base64
import hashlib
import html
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, UnidentifiedImageError

MAX_SIDE = 384
MAX_PIXELS = 16_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def mask_image(image):
    image = ImageOps.exif_transpose(image).convert('RGBA')
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    # Transparency means background, never an artificial black silhouette.
    background = Image.new('RGBA', image.size, 'white')
    background.alpha_composite(image)
    gray = np.array(background.convert('L'))
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    weight = np.cumsum(hist)
    moment = np.cumsum(hist * np.arange(256))
    total = weight[-1]
    denom = weight * (total-weight)
    score = np.divide((moment[-1]*weight-moment*total)**2, denom,
                      out=np.zeros(256), where=denom > 0)
    threshold = int(np.argmax(score))
    if int(gray.max())-int(gray.min()) < 8:
        raise ValueError('图像没有足够的前景与背景对比，请上传清晰的平面纹样。')
    mask = gray <= threshold
    # Assume the border majority represents the background.
    border = np.concatenate((mask[0], mask[-1], mask[:, 0], mask[:, -1]))
    if border.mean() > .5:
        mask = ~mask
    if mask.sum() < 4 or mask.mean() > .95:
        raise ValueError('未找到有效纹样，请裁剪后重试。')
    return mask, threshold


def components(mask):
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    found = []
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        queue = deque([(int(y), int(x))]); seen[y, x] = True
        x0=x1=int(x); y0=y1=int(y); area=0
        while queue:
            cy,cx=queue.popleft(); area+=1
            x0=min(x0,cx); x1=max(x1,cx); y0=min(y0,cy); y1=max(y1,cy)
            for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                if 0<=ny<h and 0<=nx<w and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx]=True; queue.append((ny,nx))
        if area >= 3:
            found.append({'id':f'element_{len(found)+1}','bbox':[x0,y0,x1+1,y1+1],
                          'area_px':area,'label':'未标注元素'})
    return sorted(found,key=lambda c:-c['area_px'])


def analyze(image):
    mask, threshold = mask_image(image)
    h,w=mask.shape
    nodes=components(mask)
    symmetry=lambda other: round(float(np.logical_and(mask,other).sum()/max(1,np.logical_or(mask,other).sum())),4)
    return mask, {'width':w,'height':h,'threshold':threshold,'foreground_ratio':round(float(mask.mean()),4),
                  'components':len(nodes),'mirror_x_iou':symmetry(np.fliplr(mask)),
                  'mirror_y_iou':symmetry(np.flipud(mask)),
                  'graph':{'nodes':nodes[:120], 'edges':[],
                           'status':'几何连通域，不代表已识别文化母题；连接语义待人工标注'},
                  'cultural_identification':'unknown',
                  'note':'不从图像自动断定地域、年代或寓意。'}


def paths(mask):
    # Lossless binary row-run vectorization. This is editable, not optimized CNC output.
    parts=[]
    for y,row in enumerate(mask):
        padded=np.pad(row.astype(int),(1,1)); diff=np.diff(padded)
        for a,b in zip(np.where(diff==1)[0],np.where(diff==-1)[0]):
            parts.append(f'M{a},{y}h{b-a}v1h-{b-a}z')
    return ''.join(parts)


def svg(mask, color='#b92535', title='Wenmai generated design'):
    h,w=mask.shape
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">'
            f'<title>{html.escape(title)}</title><path fill="{color}" d="{paths(mask)}"/>'
            '<metadata>AI-assisted geometric co-creation; no historical attribution inferred.</metadata></svg>')


def render(mask,color='#b92535'):
    h,w=mask.shape
    image=Image.new('RGB',(w,h),'#fffaf1')
    rgb=Image.new('RGB',(w,h),color)
    image.paste(rgb,mask=Image.fromarray(mask.astype('uint8')*255))
    return image


def png_bytes(image):
    b=BytesIO();image.save(b,format='PNG');return b.getvalue()


def data_url(image):
    return 'data:image/png;base64,'+base64.b64encode(png_bytes(image)).decode()


def demo_image():
    # Original procedural geometry. Not a museum object or an authentic Yuxian motif.
    image=Image.new('RGB',(320,320),'white');d=ImageDraw.Draw(image)
    for angle in range(0,360,45):
        a=math.radians(angle);cx=160+70*math.cos(a);cy=160+70*math.sin(a)
        d.line((160,160,cx,cy),fill='black',width=16)
        d.ellipse((cx-28,cy-28,cx+28,cy+28),fill='black')
    d.ellipse((124,124,196,196),fill='black')
    return image


def check(mask, width_mm, min_width_mm, margin_mm):
    if not (20<=width_mm<=1000 and 0<=min_width_mm<=10 and 0<=margin_mm<width_mm/2):
        raise ValueError('物理尺寸或加工参数超出范围。')
    h,w=mask.shape;mm_per_px=width_mm/w
    margin_px=int(math.ceil(margin_mm/mm_per_px))
    zone=mask.copy()
    if margin_px:
        zone[margin_px:max(margin_px,h-margin_px),margin_px:max(margin_px,w-margin_px)]=False
    else:zone[:]=False
    # Morphological opening identifies features vulnerable at the requested scale.
    diameter=max(1,int(math.ceil(min_width_mm/mm_per_px)))
    k=min(31,diameter if diameter%2 else diameter+1)
    img=Image.fromarray(mask.astype('uint8')*255)
    opened=np.array(img.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k)))>0 if k>1 else mask
    fragile=mask & ~opened
    nodes=components(mask)
    issues=[]
    if zone.any():issues.append({'type':'safe_zone','pixels':int(zone.sum()),'message':'前景越出指定安全区'})
    if fragile.any():issues.append({'type':'thin_feature_estimate','pixels':int(fragile.sum()),'message':'存在低于指定尺度的候选细节；形态学估计，需工艺复核'})
    if len(nodes)>1:issues.append({'type':'disconnected','count':len(nodes),'message':'存在多个独立连通域；是否需要桥接由实际工艺决定'})
    if diameter>31:issues.append({'type':'resolution','message':'线宽阈值超出本原型检查分辨率，不能判定通过'})
    return {'issues':issues,'digital_status':'needs_review' if issues else 'digital_checks_passed',
            'production_ready':False,'mm_per_px':round(mm_per_px,5),
            'assumptions':'四邻域连通；二值化形态学尺度估计；未进行实体打样',
            'fragile_pixels':int(fragile.sum()),'margin_violation_pixels':int(zone.sum())}


def create_design(mask,mode,layout,color,repair,width_mm,min_width_mm,margin_mm):
    if mode not in ('traditional','contemporary'):raise ValueError('未知创作模式')
    if layout not in ('single','repeat','mirror'):raise ValueError('未知布局')
    changes=[]
    if mode=='traditional' and layout!='single':
        raise ValueError('传统表达模式锁定主体布局；如需重组请选择当代共创。')
    before=mask.copy(); result=mask.copy()
    if repair:
        # Modest local fill; never invent bridges between culturally distinct nodes.
        dilated=Image.fromarray(result.astype('uint8')*255).filter(ImageFilter.MaxFilter(3))
        closed=dilated.filter(ImageFilter.MinFilter(3))
        if mode=='traditional':raise ValueError('传统表达锁定结构，不允许自动修复；请切换当代共创。')
        result=np.array(closed)>0;changes.append('执行一次3×3闭运算填补局部小缺口；未自动桥接独立元素')
    locked_iou=float((before & result).sum()/max(1,(before | result).sum()))
    if layout=='repeat':
        result=np.tile(result,(2,2));changes.append('将原单元排成2×2重复布局；不宣称无缝连续纹')
    elif layout=='mirror':
        result=np.concatenate((result,np.fliplr(result)),axis=1);changes.append('以原单元和水平镜像构成并置布局')
    else:changes.append('保留单元布局')
    changes.append(f'使用用户选择色彩 {color}；不推断历史配色')
    report=check(result,width_mm,min_width_mm,margin_mm)
    return result, {'changes':changes,'source_unit_iou':round(locked_iou,5),
                    'checks':report,'method':'deterministic_structure_composition',
                    'diffusion_model_used':False}
