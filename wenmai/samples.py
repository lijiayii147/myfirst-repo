"""Original procedural motif silhouettes for demonstration ONLY, not heritage data."""
import math
import random
from PIL import Image,ImageDraw

LABELS=['花卉','鸟','鱼','几何']


def sample(label,seed,size=160):
    rng=random.Random(seed);image=Image.new('RGB',(size,size),'white');d=ImageDraw.Draw(image)
    c=size/2;scale=rng.uniform(.82,1.05);shift=rng.uniform(-5,5)
    def box(x0,y0,x1,y1):return tuple(int(c+(v-c)*scale+shift) for v in (x0,y0,x1,y1))
    if label=='花卉':
        petals=rng.choice([5,6,7,8]);radius=rng.uniform(31,39);petal=rng.uniform(16,23)
        for i in range(petals):
            a=2*math.pi*i/petals;cx=c+radius*math.cos(a);cy=c+radius*math.sin(a)
            d.ellipse(box(cx-petal,cy-petal,cx+petal,cy+petal),fill='black')
        d.ellipse(box(52,52,108,108),fill='black');d.ellipse(box(70,70,90,90),fill='white')
    elif label=='鱼':
        d.ellipse(box(35,48,125,108),fill='black')
        d.polygon([box(18,35,18,35)[:2],box(57,78,57,78)[:2],box(18,122,18,122)[:2]],fill='black')
        d.ellipse(box(104,65,113,74),fill='white')
        for x in [64,79,94]:d.arc(box(x-8,57,x+12,100),90,270,fill='white',width=2)
    elif label=='鸟':
        d.ellipse(box(49,61,115,111),fill='black');d.ellipse(box(101,34,133,66),fill='black')
        d.polygon([box(125,43,125,43)[:2],box(147,51,147,51)[:2],box(125,57,125,57)[:2]],fill='black')
        d.polygon([box(55,77,55,77)[:2],box(16,49,16,49)[:2],box(29,100,29,100)[:2]],fill='black')
        d.line(box(76,104,70,136),fill='black',width=4);d.line(box(94,104,100,136),fill='black',width=4)
        d.ellipse(box(118,43,123,48),fill='white')
    elif label=='几何':
        step=rng.choice([23,27,30])
        for y in range(25,135,step):
            for x in range(25,135,step):
                if rng.random()>.10:d.rectangle(box(x,y,x+14,y+14),fill='black')
    else:raise ValueError('unknown synthetic label')
    if rng.random()<.5:image=image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return image
