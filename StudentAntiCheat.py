import os
import argparse
import cv2
import time
import colorsys
import numpy as np
import moviepy
from moviepy.editor import *


NETWORK_W = 608
NETWORK_H = 608

######## CLI Argparser ########
parser = argparse.ArgumentParser(description='Command options for Student-AntiCheat Tool')

parser.add_argument('--p','--path', type=str ,
                    help='Required: Path To the Video',
                    required=True,metavar='')
parser.add_argument('--n','--name', type=str,
                    help='Required: Name of Student to check for exam.  Please add students image in faces Folder with appropriate name.(Specify in double " " quotes)',
                    required=True,metavar='')
parser.add_argument('--f','--fps', type=int ,
                    help='Target FPS to render at(Low Numbers result in faster rendering), \nDefault = 4',
                    default = 4,metavar='')
parser.add_argument('--m','--phone',action='store_true',
                    help='Specify this flag for Cell Phone cheating Detection. WARNING Uses YoloV4 algorithm and impacts performance Heavily')
parser.add_argument('--s','--save',action = 'store_true',
                    help='Specify this flag to save video file to OutPut Folder')
parser.add_argument('--v','--verbose',action = 'store_true',
                    help='Specify this flag to get Verbose output')

args = parser.parse_args()

if not os.path.exists(args.p):
    raise argparse.ArgumentTypeError('Video path does not exist. Please Specify correct path')

if len(os.listdir('Faces')) == 0:
    raise Exception('No Face files detected in Faces folder. Please populate the directory.')

def getFrame(sec): 
    vidcap.set(cv2.CAP_PROP_POS_MSEC,sec*1000) 
    hasFrames,image = vidcap.read() 
    return hasFrames,image 

##### Clear Temp folder if save flag Enabled
if args.s:
    for file in os.listdir('TempVideoFrames'):
        os.remove(os.path.join('TempVideoFrames',file))


#### Importing Heavy utils later after argparse checks #########
import antiCheatUtils as aUtils
import face_recognition as faceRec


labels = aUtils.read_labels("models/yolo/coco_classes.txt")
#class_threshold = 0.6
colors = aUtils.generate_colors(labels)
 
########### GET Face Data from Faces Folder for Face Recognition ############
faceDir = 'Faces'
faceImages = []
faceNames = []
faceEncodingsKnown = []
fileNames = os.listdir(faceDir)
for fn in fileNames:
    if fn[-3:]  in ['png','jpg']:
        faceIm = faceRec.load_image_file(faceDir + '/' +fn)
        faceEnc = faceRec.face_encodings(faceIm)[0]
        faceImages.append(faceIm)
        faceEncodingsKnown.append(faceEnc)
        faceName = fn[:-4]
        faceNames.append(faceName)
    
print('Faces Found in Faces Directory')
print(*faceNames)

vidcap = cv2.VideoCapture(args.p)
nameToCheck = args.n
sec = 0
fps = int(args.f)
frameSec = aUtils.getFrameSec(fps)   #interval to skip in video to match the given fps
success,img = getFrame(sec) ### get Frame after x sec interval to match given fps

absentFramesTotal,phoneFramesTotal = 0,0 
fc = 0 

print('Press (q) To abort')
tic = time.time()
while success:
    fc+=1
    img,absentFramesTotal = aUtils.faceRecInference(faceEncodingsKnown,faceNames,img,absentFramesTotal,nameToCheck)
    if args.m:
        img, width,height = aUtils.load_image_pixels(img, (608,608))
        img,phoneFramesTotal = aUtils.Inference(img,width,height,colors,labels,phoneFramesTotal)
        img = cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    cv2.imshow('feed',img)
    sec = sec + frameSec 
    sec = round(sec, 2)
    if args.v:
        print(f'Processing Frame number: {fc}')
        if args.m:
            print(f'Number of frames where phone was detected: {phoneFramesTotal}')
        print(f'Number of Frames where Student was missing: {absentFramesTotal}')
        print('-------------------------------------------------------------')
    if args.s:
        if args.m:
            ########## Multiplying normalized image by 255 before saving ##############
            img = img*255
        cv2.imwrite(os.path.join('TempVideoFrames','frame'+str(fc)+'.png'),img)
    success,img = getFrame(sec)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
toc = time.time()

cv2.destroyAllWindows()
vidcap.release()
print('Time Taken To Finish Rendering', round((toc-tic)/60,2),'min')

####### Save Video from saved images to output directory if Save flag specified ####
if args.s:
    print('Saving Frames to Video')
    readDir= r'TempVideoFrames'
    imli = [str(os.path.join(readDir,'frame'+str(fc)+'.png')) for fc in range(1,len(os.listdir(readDir)) +1)]
    clip = ImageSequenceClip(imli, fps=fps)
    clip.write_videofile("Output/"+args.n+".mp4",fps=fps)
    print('Save Complete to /Output')


print('Total frames in capture: ',fc)

print('Total number of Frames where the student was missing: ',absentFramesTotal)
print('Percent of time where the student was present',round(((fc-absentFramesTotal)/fc)*100,2))
if args.m:
    print('Total number of Phone Frames : ',phoneFramesTotal)
    print('Percent of time when cellphone use was detected: ', round((phoneFramesTotal/fc)*100,2))
