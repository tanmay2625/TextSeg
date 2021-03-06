import cv2
import sys
import numpy as np
from math import ceil
import math
import glob
import timeit

def getVerticalProjectionProfile(image, header_position=0):
    height = image.shape[0]
    width = image.shape[1]
    x = [[0 for i in range(image.shape[1])] for j in range(image.shape[0])]

    for i in range(header_position+1, height):
        for j in range(width):
            if image[i][j] == 0:
                x[i][j] = 1

    vertical_projection = np.sum(x, axis=0)

    return vertical_projection


def getHorizontalProjectionProfile(image):

     # Convert black spots to ones
    height = image.shape[0]
    width = image.shape[1]
    x = [[0 for i in range(image.shape[1])] for j in range(image.shape[0])]

    for i in range(height):
        for j in range(width):
            if image[i][j] == 0:
                x[i][j] = 1

    horizontal_projection = np.sum(x, axis=1)

    return horizontal_projection


def cropROI(image):
    height = image.shape[0]
    width = image.shape[1]
    horizontal_projection = getHorizontalProjectionProfile(image)
    verticle_projection = getVerticalProjectionProfile(image)
    start_x = -1
    end_x = width
    start_y = -1
    end_y = height
    for i in range(width):
        if verticle_projection[i]:
            
            if(i): start_x = i-1
            else: start_x=i
            break
    for i in range(width-1, 0, -1):
        if verticle_projection[i]:
            if(width-1-i):end_x = i+1
            else: end_x= width-1
            break
    for i in range(height):
        if horizontal_projection[i]:
            if(i):start_y = i-1
            else: start_y=i
            break
    for i in range(height-1, 0, -1):
        if horizontal_projection[i]:
            if(height-1-i):end_y = i+1
            else: height=i
            break
    image = image[start_y:end_y, start_x:end_x]
    return image


def find_si(i, pi):
    slope = (pi-i)/(N-1)
    ans = 0
    cur = 0
    for j in range(N):
        y = i+slope*j
        fp = y-math.floor(y)
        y = int(y)
        if fp >= 0.5:
            y += 1
        if(y >= M):
            break
        if img[j][y] == 0:
            cur += 1
        else:
            ans = max(ans, cur)
            cur = 0
    ans = max(ans, cur)
    if ans<N/3:ans=0
    return ((ans/N)*64) # this change is done so that it adapts irresptive of resolution change


def find_gamma(i, pi, prev_pi):
    if pi == prev_pi+1:
        return 0
    if i==W: return 0
    slope = (pi-i)/(N-1)
    ans = 0
    for j in range(N):
        y = i+slope*j
        fp = y-int(y)
        y = int(y)
        if fp >= 0.5:
            y += 1
        if(y >= M):
            break
        if img[j][y] == 0:
            ans += 1
    return -ans


def avg_pi(centr, i):

    new_img = img[:, int(max(centr - sig/2, 0)): int(min(M, centr + sig/2))]
    new_img = 255 - new_img
    contours, _ = cv2.findContours(new_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    one_part = 360/16
    cnt = np.zeros(8, dtype=int)
    for cont in contours:
        first = cont[0][0]
        l = len(cont)
        for i in range(1, l):
            angle = (math.atan2(cont[i][0][1]-first[1],cont[i][0][0]-first[0])) * (180/math.pi)
            if(angle < 0):
                angle += 180
            cnt[int(math.floor(angle/one_part)) % 8] += 1
    slope_here=(((2*cnt[1]+2*cnt[2]+cnt[3])-(cnt[5]+2*cnt[6]+2*cnt[7])) /
                 ((cnt[1]+2*cnt[2]+2*cnt[3])+2*cnt[4]+(2*cnt[5]+2*cnt[6]+cnt[7])))
    if slope_here==0 : return pi
    out = i + N/slope_here
    if(math.isnan(out)): return pi ;
    if(sum(cnt)<N/2): return pi
    return out


def find_ci(i, pi):
    if len(avg_slope_at)==0 :return 0 #function disabled
    # use trial and error
    return -1 * abs(avg_pi(min(i, pi)+abs(i-pi)/2, i) - pi)


def find_f(i, pi, prev_pi):
    return ws*find_si(i, pi)+wc*find_ci(i, pi)+wn*find_gamma(i, pi, prev_pi)

cnttt=0
for input_img in glob.glob('./tests/*'):
    print(cnttt,input_img)
    img = cv2.imread(input_img)

    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    (thresh, img) = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    img = cropROI(img)
    cur_h = img.shape[0]
    ratio =128/cur_h
    dim = (int(img.shape[1]*ratio), int(img.shape[0]*ratio))
    img = cv2.resize(img, dim, interpolation=cv2.INTER_LINEAR)
    (thresh, img) = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    N = img.shape[0]
    M = img.shape[1]
    W = 2*N
    img= cv2.copyMakeBorder(img,0,0,W,W,cv2.BORDER_CONSTANT,value=255)
    N = img.shape[0]
    M = img.shape[1]
    print(N, M)
    W = 2*N

    ws = 0.75
    wc = 0   #avg slant factor
    wn = 0.25
    sig = 11* (N/64)
    avg_slope_at=[]
    
    #sigma is large here because the resolution of image is high , we can adjust it to a lower value by lowering resoltion

    g = [[0 for i in range(M)] for j in range(M)]
    b = [[0 for i in range(M)] for j in range(M)]
    for pi in range(min(2*W+1,M)):g[W][pi]=ws*find_si(W,pi)+wc*find_ci(W,pi)
    for i in range(1+W,M):
        print(i)
        for pi in range(max(i-W,0),min(i+W+1,M)):
            g[i][pi]=-100000000000000
            for k in range(3):
                cur=g[i-1][pi-k]+find_f(i,pi,pi-k)
                if cur>g[i][pi]:
                    g[i][pi]=cur
                    b[i][pi]=pi-k
                elif cur==g[i][pi]:
                    b[i][pi]= pi-1



    opt=[]
    for i in range(M):opt.append(0)
    for i in range(W): opt[i]=i
    opt[M-1]=M-1
    for i in range(M-1,W,-1):
        opt[i-1]=b[i][opt[i]]
    new_img=img.copy()
    for x in range(W,M):
        for y in range(N):
            i=x
            pi=opt[i]
            xx= i+((pi-i)/(N-1))*y
            fp=xx-int(xx)
            xx=int(xx)
            if fp>=0.5:xx+=1
            new_img[y][x]=img[y][xx]
    vis = np.concatenate((img, new_img), axis=0)

    cv2.imwrite('./results/result'+str(cnttt)+'.jpg',vis)
    
    cnttt+=1
