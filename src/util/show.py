import matplotlib.pyplot as plt
import matplotlib.image as img
from matplotlib.patches import Rectangle
from PIL import Image

import sys

imdir = sys.argv[1]
annos = sys.argv[2]
shape = (1920,1080) # sys.argv[3]

from parser import read_frames

fs = read_frames(annos, shape)

for f in fs:
    print(f)
    im = img.imread(imdir+'/'+f.frameid)
    shape = im.shape
    fig, ax = plt.subplots()
    ax.imshow(im)
    for b in f.bboxes:
        w1 = b.w*shape[1]
        h1 = b.h*shape[0]
        x1 = b.x*shape[1]-w1/2
        y1 = b.y*shape[0]-h1/2
        ax.add_patch(Rectangle((x1, y1), w1, h1, linewidth=1, edgecolor='r', facecolor='none'))
    plt.show()
