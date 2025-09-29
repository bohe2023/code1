'''
Created on 2024/04/02
'''
import glfw
import cv2
from OpenGL.GL import *
from OpenGL.GLU import *
from enum import Enum

ResourceImageData = {}
class ImageResource(Enum):
    ZoomIn = 0
    ZoomOut = 1
    CurPos = 2
    AutoRotMov = 3
    AutoMov = 4
    AutoOff = 5
    SubViewOn = 6
    SubViewOff = 7
    
def loadImage(path):
    image = cv2.imread(path)
    image = cv2.flip(image, 0)
    image = cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    return image
    
def imageInitliaze():
    ResourceImageData[ImageResource.ZoomIn] = loadImage("res/image/zoomIn.png")
    ResourceImageData[ImageResource.ZoomOut] = loadImage("res/image/zoomOut.png")
    ResourceImageData[ImageResource.CurPos] = loadImage("res/image/curPos.png")
    ResourceImageData[ImageResource.AutoOff] = loadImage("res/image/AutoOff.png")
    ResourceImageData[ImageResource.AutoMov] = loadImage("res/image/AutoMov.png")
    ResourceImageData[ImageResource.AutoRotMov] = loadImage("res/image/AutoRotMov.png")
    ResourceImageData[ImageResource.SubViewOn] = loadImage("res/image/subViewOn.png")
    ResourceImageData[ImageResource.SubViewOff] = loadImage("res/image/subViewOff.png")

def drawRectangleWithImage(x, y, width, height, windowWidth, windowHeight, img_data):
    img_data = cv2.resize(img_data, (width, height))
    glRasterPos2f((x*2 / windowWidth) - 1, (y*2 / windowHeight) - 1)
    glDrawPixels(img_data.shape[1], img_data.shape[0], GL_RGB,GL_UNSIGNED_BYTE, img_data)
            
    

    
