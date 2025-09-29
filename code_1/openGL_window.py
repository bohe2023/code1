'''
Created on 2023/12/28

@author: AD2Gen2-19
'''
import glfw
import cv2
from OpenGL.GL import *
from OpenGL.GLU import *
from openGL_drawText import textinitliaze, render_text, render_text_start, render_text_end
from openGL_drawImage import imageInitliaze, drawRectangleWithImage, ImageResource, ResourceImageData
import math
from LayerManagerForViewer import SymbolType, FeatureType
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from GlobalVar import getLogger
#import numpy as np
#from PIL import ImageFont, ImageDraw, Image

W_INIT = 700
H_INIT = 700

@dataclass
class Point3D:
    x: float
    y: float
    z: float
    
    def copy(self):
        return Point3D(self.x,self.y,self.z)
    
@dataclass
class Rot:
    theta: float
    phi: float
    
    def copy(self):
        return Rot(self.theta,self.phi)

class Button:
    def __init__(self, drawSrc = None, callbackFunc = None, x = 0, y = 0, size = 0):
        self.drawSrc = drawSrc
        self.callbackFunc = callbackFunc
        self.posX = x
        self.posY = y
        self.size = size
        
    def click(self):
        if self.callbackFunc != None:
            self.callbackFunc()

def deg2rad(deg):
    return deg * math.pi / 180.0

def rad2deg(deg):
    return deg * 180.0 / math.pi 

def roti(phi):
    return [[1.0, 0.0, 0.0],
            [0.0, math.cos(phi), -math.sin(phi)],
            [0.0, math.sin(phi), math.cos(phi)]]

def rotj(phi):
    return [[math.cos(phi), 0.0, math.sin(phi)],
            [0.0, 1.0, 0.0],
            [-math.sin(phi), 0.0, math.cos(phi)]]

def rotk(phi):
    return [[math.cos(phi), -math.sin(phi), 0.0],
            [math.sin(phi), math.cos(phi), 0.0],
            [0.0, 0.0, 1.0]]

def rot(x, y, z, phi): #任意の軸に回転
    r = math.sqrt(x*x + y*y + z*z)
    x = x / r;    y = y / r;    z = z / r;
    return [[(x * x * (1 - math.cos(phi)) + math.cos(phi)),       (x * y * (1 - math.cos(phi)) + z * math.sin(phi)),    (x * z * (1 - math.cos(phi)) - y * math.sin(phi))],
            [(x * y * (1 - math.cos(phi)) - z * math.sin(phi)),   (y * y * (1 - math.cos(phi)) + math.cos(phi)),        (y * z * (1 - math.cos(phi)) + x * math.sin(phi))],
            [(x * z * (1 - math.cos(phi)) + y * math.sin(phi)),   (y * z * (1 - math.cos(phi)) - x * math.sin(phi)),    (z * z * (1 - math.cos(phi)) + math.cos(phi))]]

def dmat_mul(l, m, n, m1, m2):
    ret = [[0 for _ in range(n)] for _ in range(l)]
    for i in range(l):
        for j in range(n):
            for k in range(m):
                ret[i][j] += m1[i][k] * m2[k][j]
    return ret

def dmat_add(l, n, m1, m2):
    ret = [[0 for _ in range(n)] for _ in range(l)]
    for i in range(l):
        for j in range(n):
            ret[i][j] = m1[i][j] + m2[i][j]
    return ret

def dmat_sub(l, n, m1, m2):
    ret = [[0 for _ in range(n)] for _ in range(l)]
    for i in range(l):
        for j in range(n):
            ret[i][j] = m1[i][j] - m2[i][j]
    return ret

class TrackingMode(Enum):
    Off = 0
    XYZ = 1
    XYZRot = 2    

class OpenGLWindow():
    ObjectSizeRate_lonlat = 1000.0
    ObjectSizeRate_meter = 0.02
    
    # Color
    Color_DiffuseW = (1.0,1.0,1.0)
    Color_DiffuseBlack = (0.0,0.0,0.0)
    Color_DiffuseGray = (0.5,0.5,0.5)
    Color_DiffuseR = (1.0,0.0,0.0)
    Color_DiffuseG = (0.0,1.0,0.0)
    Color_DiffuseB = (0.0,0.0,1.0)
    Color_DiffuseSR = (1.0,0.5,0.5)
    Color_DiffuseSG = (0.5,1.0,0.5)
    Color_DiffuseSB = (0.5,0.5,1.0)
    
    # Object
    window = None
    video_capture = None
    prepareDataFunction = None
    buttonList = []
    drawTextList_top = []
    drawTextList_bottom = []
    lastCompileIndex = 0
    
    # View Control
    trackingMode = TrackingMode.XYZRot
    showSubWindow = False
    windowWidth = 0
    windowHeight = 0
    totalSubWindowCount = 0
    selectedSubWindowIndex = 0
    subWindowLeft = [0, 0, 0]
    subWindowWidth = [0, 0, 0]
    subWindowBotton = [0, 0, 0]
    subWindowHeight = [0, 0, 0]
    
    subWindowEye = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    subWindowView = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    subWindowCameraGyro = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    view_distance = 0.685
    view_rot = Rot(0.0, deg2rad(20))
    view_rot_old = None
    view_point = Point3D(0.0, 0.0, 0.0)
    view_point_old = None
    view_offset = None
    
    # Smooth 画面変換処理
    view_point_Smooth = None
    view_point_Smooth_old = None
    view_rot_Smooth = None
    view_rot_Smooth_old = None
    view_point_Smooth_old_forRotCalc = None
    view_Smooth_lastTime = None
    view_SmoothRot_lastTime = None
    view_Smooth_orderSpan = 0
    view_SmoothRot_orderSpan = 0
    
    eyeOffset = Point3D(0, 0, 0)
    eyeOffset_rot = Rot(0, 0)
    eyeFov = 60.0 # deg (from bottom to top) 
#     eyeOffset = Point3D(-0.38, 0.02, 0.04)
#     eyeOffset_rot = Rot(-0.07, -0.09)
#     eyeFov = 28.5 # deg (from bottom to top)
    
    # Event control
    mousePressTime = None
    mouseReleaseTime = None
    lButtonDowned = False
    rButtonDowned = False
    shiftKeyPressed = False
    mouseClickPoint = (0, 0)
            
    @staticmethod
    def mouseMove(window, x, y):
        self = glfw.get_window_user_pointer(window)
        if self.lButtonDowned == False and self.rButtonDowned == False:
            return
        
        pos = self.modifyToWindowPoint((x, y))
    
        if (self.lButtonDowned):
            if (self.selectedSubWindowIndex == 0): self.dglViewRotate(pos)
        elif (self.rButtonDowned):
            if (self.selectedSubWindowIndex == 0): self.dglViewTranslate(pos)
     
    @staticmethod
    def mouseEvent(window, button, action, mods):
        self = glfw.get_window_user_pointer(window)
        pos = glfw.get_cursor_pos(window)
        self.selectedSubWindowIndex = self.getClickedSubWindowIndex(pos)
        if (self.selectedSubWindowIndex != 0): return
        pos = self.modifyToWindowPoint(pos)
        
        buttonIndex = self.getClickedButtonIndex(pos)
        if buttonIndex >= 0:
            if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
                self.buttonList[buttonIndex].click()
                self.lButtonDowned = False
                self.rButtonDowned = False
        else:
            if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
                self.lButtonDowned = True
                self.mousePressTime = datetime.now()
                self.mouseClickPoint = pos
                self.view_rot_old = self.view_rot.copy()
                self.view_point_old = self.view_point.copy()
                
            elif button == glfw.MOUSE_BUTTON_LEFT and action == glfw.RELEASE and self.lButtonDowned:
                self.lButtonDowned = False
                self.rButtonDowned = False
                if self.mousePressTime != None: mousePressElapsedTime = (datetime.now() - self.mousePressTime).total_seconds()
                else: mousePressElapsedTime = 0
                if self.mouseReleaseTime != None: mouseIntervalElapsedTime = (datetime.now() - self.mouseReleaseTime).total_seconds()
                else: mouseIntervalElapsedTime = 999
                if mousePressElapsedTime < 0.2 and mouseIntervalElapsedTime > 0.2:
                    self.dglViewRaytracingXYTranslate(pos)
                self.mousePressTime = None
                self.mouseReleaseTime = datetime.now()
                
            elif button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.PRESS:
                self.rButtonDowned = True
                self.mouseClickPoint = pos
                self.view_rot_old = self.view_rot.copy()
                self.view_point_old = self.view_point.copy()
                
            elif button == glfw.MOUSE_BUTTON_RIGHT and action == glfw.RELEASE and self.rButtonDowned:
                self.lButtonDowned = False
                self.rButtonDowned = False
    
    @staticmethod
    def mouseScroll(window, xoffset, yoffset):
        self = glfw.get_window_user_pointer(window)
        if (self.shiftKeyPressed): self.dglViewTranslate_FrontBack(True if yoffset > 0 else False)
        else: self.viewZoom(yoffset)
    
    def dglViewRotate(self, pos):
        self.view_rot.theta = (self.view_rot_old.theta + float(self.mouseClickPoint[0]-pos[0])/100.0)
        self.view_rot.phi = (self.view_rot_old.phi + float(self.mouseClickPoint[1]-pos[1])/250.0)
        if (self.view_rot.phi > math.pi/2-0.01): self.view_rot.phi = (math.pi/2-0.01)
        if (self.view_rot.phi < 0.01): self.view_rot.phi = 0.01
        #if (self.view_rot.phi < -math.pi/2+0.01): self.view_rot.phi = (-math.pi/2+0.01)
        
        if self.trackingMode == TrackingMode.XYZRot:
            self.trackingMode = TrackingMode.XYZ
            self.btn_tracking.drawSrc = ResourceImageData[ImageResource.AutoMov]
    
    def dglViewTranslate_FrontBack(self, frontDirect):
        dx = math.cos(self.view_rot.phi)*math.cos(self.view_rot.theta)
        dy = math.cos(self.view_rot.phi)*math.sin(self.view_rot.theta)
        dz = math.sin(self.view_rot.phi)
        if (frontDirect):
            self.view_point.x -= self.view_distance*dx/(10*OpenGLWindow.ObjectSizeRate_lonlat)
            self.view_point.y -= self.view_distance*dy/(10*OpenGLWindow.ObjectSizeRate_lonlat)
            self.view_point.z -= self.view_distance*dz/(10*OpenGLWindow.ObjectSizeRate_lonlat)
        else:
            self.view_point.x += self.view_distance*dx/(10*OpenGLWindow.ObjectSizeRate_lonlat)
            self.view_point.y += self.view_distance*dy/(10*OpenGLWindow.ObjectSizeRate_lonlat)
            self.view_point.z += self.view_distance*dz/(10*OpenGLWindow.ObjectSizeRate_lonlat)
    
    def dglViewTranslate(self, pos):
        #XYZ立体移動
#         m0 = rot(math.sin(self.view_rot.theta),-math.cos(self.view_rot.theta),0,self.view_rot.phi)
#         m1 = rotk(self.view_rot.theta)
#         m2 = dmat_mul(3,3,3,m0,m1)
#     
#         n = [[self.view_distance], [0], [0]]
#         v0 = dmat_mul(3,3,1,m2,n)
#     
#         dx = ((self.mouseClickPoint[0]-pos[0])*self.view_distance/(OpenGLWindow.ObjectSizeRate_lonlat))
#         dy = -((self.mouseClickPoint[1]-pos[1])*self.view_distance/(OpenGLWindow.ObjectSizeRate_lonlat))
#         
#         n = [[self.view_distance], [dx], [dy]]
#         v1 = dmat_mul(3,3,1,m2,n)
#     
#         self.view_point.x = (self.view_point_old.x + (v1[0][0] - v0[0][0]))
#         self.view_point.y = (self.view_point_old.y + (v1[1][0] - v0[1][0]))
#         self.view_point.z = (self.view_point_old.z - (v1[2][0] - v0[2][0]))

        #XY平面移動
        dx = ((self.mouseClickPoint[0]-pos[0])*self.view_distance/(OpenGLWindow.ObjectSizeRate_lonlat))
        dy = -((self.mouseClickPoint[1]-pos[1])*self.view_distance/(OpenGLWindow.ObjectSizeRate_lonlat))
        
        m = rotk(self.view_rot.theta)
        n = [[dy], [dx], [0]]
        v = dmat_mul(3,3,1,m,n)
        
        self.view_point.x = (self.view_point_old.x + v[0][0])
        self.view_point.y = (self.view_point_old.y + v[1][0])
        
        if self.trackingMode == TrackingMode.XYZRot or self.trackingMode == TrackingMode.XYZ:
            self.trackingMode = TrackingMode.Off
            self.btn_tracking.drawSrc = ResourceImageData[ImageResource.AutoOff]
        
    def dglViewRaytracingXYTranslate(self, pos):
        whRate = self.subWindowWidth[0] / self.subWindowHeight[0]
        deltaTheta = deg2rad(whRate * self.eyeFov/2 * ((pos[0] / (self.subWindowWidth[0]/2)) - 1))
        deltaPhi = deg2rad(self.eyeFov/2 * ((pos[1] / (self.subWindowHeight[0]/2)) - 1))
        phi = math.fabs(self.view_rot_old.phi)
        theta = self.view_rot_old.theta
          
        dx = -(math.sin(phi) * (math.tan(deg2rad(90) - phi + deltaPhi) - math.tan(deg2rad(90) - phi)))
        dy = math.sin(phi) * math.tan(deltaTheta) / math.cos(deg2rad(90) - phi + deltaPhi) 
        
        Rz = rotk(theta)
        n = [[dx], [dy], [0]]
        v = dmat_mul(3,3,1,Rz,n)

        self.view_point.x = self.view_point_old.x + v[0][0] * self.view_distance
        self.view_point.y = self.view_point_old.y + v[1][0] * self.view_distance
        
        if self.trackingMode == TrackingMode.XYZRot or self.trackingMode == TrackingMode.XYZ:
            self.trackingMode = TrackingMode.Off
            self.btn_tracking.drawSrc = ResourceImageData[ImageResource.AutoOff]
    
    def viewZoom(self, zDelta):
        self.view_distance *= math.pow(1.3,-zDelta/5.0)
        #if self.view_distance < 50.0: self.view_distance = 50.0 
    
    @staticmethod
    def keyboard(window, key, scancode, action, mods):
        self = glfw.get_window_user_pointer(window)
        if key == glfw.KEY_LEFT_SHIFT and action == glfw.PRESS:
            self.shiftKeyPressed = True
        elif key == glfw.KEY_LEFT_SHIFT and action == glfw.RELEASE:
            self.shiftKeyPressed = False
            
#         elif key == glfw.KEY_A and action == glfw.PRESS:
#             self.eyeOffset.x += 0.01
#         elif key == glfw.KEY_Z and action == glfw.PRESS:
#             self.eyeOffset.x -= 0.01
#         elif key == glfw.KEY_S and action == glfw.PRESS:
#             self.eyeOffset.y += 0.01
#         elif key == glfw.KEY_X and action == glfw.PRESS:
#             self.eyeOffset.y -= 0.01
#         elif key == glfw.KEY_D and action == glfw.PRESS:
#             self.eyeOffset.z += 0.01
#         elif key == glfw.KEY_C and action == glfw.PRESS:
#             self.eyeOffset.z -= 0.01
#         elif key == glfw.KEY_F and action == glfw.PRESS:
#             self.eyeFov += 0.5
#         elif key == glfw.KEY_V and action == glfw.PRESS:
#             self.eyeFov -= 0.5
            
    @staticmethod
    def resize(window, w, h):
        self = glfw.get_window_user_pointer(window)
        # for iconify on Windows
        if h==0:
            return
        self.windowWidth = w
        self.windowHeight = h
    
    def drawCoordinate(self, windowIndex):
        glEnable(GL_LINE_STIPPLE)
        glLineStipple(5,0x5555)
        
        glLineWidth(4)
        for i in range(0,3):
            if windowIndex == 0:
                size = 0.01
                if i == 0: (x,y,z) = (self.view_point.x, self.view_point.y, self.view_point.z)
                else: break
            else:
                size = 0.5
                if i == 0: (x,y,z) = (self.view_point.x, self.view_point.y, self.view_point.z)
                elif i == 1: (x,y,z) = (self.subWindowEye[0][0], self.subWindowEye[0][1], self.subWindowEye[0][2])
                elif i == 2: (x,y,z) = (self.subWindowView[0][0], self.subWindowView[0][1], self.subWindowView[0][2])
            
            glColor3fv(OpenGLWindow.Color_DiffuseR)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseR)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x+size, y, z)
            glEnd()
            glColor3fv(OpenGLWindow.Color_DiffuseG)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseG)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x, y+size, z)
            glEnd()
            glColor3fv(OpenGLWindow.Color_DiffuseB)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseB)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x, y, z+size)
            glEnd()

        glLineWidth(2)
        glColor3fv(OpenGLWindow.Color_DiffuseSB)
        glBegin(GL_LINE_LOOP)
        for j in range(360):
            x = self.view_point.x + OpenGLWindow.ObjectSizeRate_lonlat * 0.0223 * math.cos(deg2rad(j)) # 2km
            y = self.view_point.y + OpenGLWindow.ObjectSizeRate_lonlat * 0.0223 * math.sin(deg2rad(j))
            z = 0
            glVertex3f(x,y,z)
        glEnd()
        
        if windowIndex == 2:
            glLineWidth(2)
            glColor3fv(OpenGLWindow.Color_DiffuseSB)
            glBegin(GL_LINE_LOOP)
            for j in range(360):
                x = self.view_point.x + OpenGLWindow.ObjectSizeRate_lonlat * 0.065 * math.cos(deg2rad(j)) # 7km
                y = self.view_point.y + OpenGLWindow.ObjectSizeRate_lonlat * 0.065 * math.sin(deg2rad(j))
                z = 0
                glVertex3f(x,y,z)
            glEnd()
        
        if windowIndex != 0:
            (x,y,z) = (self.subWindowEye[0][0], self.subWindowEye[0][1], self.subWindowEye[0][2])
            
            glColor3fv(OpenGLWindow.Color_DiffuseGray)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseR)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(self.subWindowView[0][0], self.subWindowView[0][1], self.subWindowView[0][2])
            glEnd()
            
            n = [[self.subWindowView[0][0]-self.subWindowEye[0][0]], [self.subWindowView[0][1]-self.subWindowEye[0][1]], [self.subWindowView[0][2]-self.subWindowEye[0][2]]]
            Rz = rotk(deg2rad(self.eyeFov/2))
            mat = dmat_mul(3,3,1,Rz,n)

            glColor3fv(OpenGLWindow.Color_DiffuseGray)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseR)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x+mat[0][0], y+mat[1][0], z+mat[2][0])
            glEnd()
            
            Ryx = rot(n[0][0], n[1][0], n[2][0], deg2rad(90))
            mat = dmat_mul(3,3,1,Ryx,mat)

            glColor3fv(OpenGLWindow.Color_DiffuseGray)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseR)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x+mat[0][0], y+mat[1][0], z+mat[2][0])
            glEnd()
            
            Rz = rotk(deg2rad(-self.eyeFov/2))
            mat = dmat_mul(3,3,1,Rz,n)

            glColor3fv(OpenGLWindow.Color_DiffuseGray)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseR)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x+mat[0][0], y+mat[1][0], z+mat[2][0])
            glEnd()
            
            mat = dmat_mul(3,3,1,Ryx,mat)

            glColor3fv(OpenGLWindow.Color_DiffuseGray)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, OpenGLWindow.Color_DiffuseR)
            glBegin(GL_LINES)
            glVertex3f(x, y, z)
            glVertex3f(x+mat[0][0], y+mat[1][0], z+mat[2][0])
            glEnd()
        
        glDisable(GL_LINE_STIPPLE)
    
    def display(self):
        ####### 視点スムーズ処理 #######
        if (self.trackingMode == TrackingMode.XYZRot or self.trackingMode == TrackingMode.XYZ) and self.view_Smooth_orderSpan > 0:
            currentElapsedTime = (datetime.now() - self.view_Smooth_lastTime).total_seconds()
            timeRate = currentElapsedTime / self.view_Smooth_orderSpan
            if (timeRate > 1.5): timeRate = 1.5
            self.view_point.x = self.view_point_Smooth_old.x * (1-timeRate) + self.view_point_Smooth.x * (timeRate)
            self.view_point.y = self.view_point_Smooth_old.y * (1-timeRate) + self.view_point_Smooth.y * (timeRate)
            self.view_point.z = self.view_point_Smooth_old.z * (1-timeRate) + self.view_point_Smooth.z * (timeRate)
                
            if self.trackingMode == TrackingMode.XYZRot and self.view_SmoothRot_orderSpan > 0:
                currentElapsedTime_rot = (datetime.now() - self.view_SmoothRot_lastTime).total_seconds()
                timeRate_rot = currentElapsedTime_rot / self.view_SmoothRot_orderSpan
                if (timeRate_rot > 1): timeRate_rot = 1
                self.view_rot.theta = self.view_rot_Smooth_old.theta * (1-timeRate_rot) + self.view_rot_Smooth.theta * (timeRate_rot)
                self.view_rot.phi = self.view_rot_Smooth_old.phi * (1-timeRate_rot) + self.view_rot_Smooth.phi * (timeRate_rot)
        
        if (self.showSubWindow):
            self.totalSubWindowCount = 3
            
            subWindowSize_H = int(self.windowHeight / 2)
            subWindowSize_W = int(subWindowSize_H / 1.8)
            
            self.subWindowWidth[0] = self.windowWidth - subWindowSize_W
            self.subWindowHeight[0] = int(self.windowHeight)
            self.subWindowLeft[0] = 0
            self.subWindowBotton[0] = 0
            
            self.subWindowWidth[1] = subWindowSize_W
            self.subWindowHeight[1] = subWindowSize_H
            self.subWindowLeft[1] = self.windowWidth - subWindowSize_W
            self.subWindowBotton[1] = subWindowSize_H

            self.subWindowWidth[2] = subWindowSize_W
            self.subWindowHeight[2] = subWindowSize_H
            self.subWindowLeft[2] = self.windowWidth - subWindowSize_W
            self.subWindowBotton[2] = 0

        else:
            self.totalSubWindowCount = 1
    
            self.subWindowWidth[0] = self.windowWidth
            self.subWindowHeight[0] = self.windowHeight
            self.subWindowLeft[0] = 0
            self.subWindowBotton[0] = 0
    
        for i in range(self.totalSubWindowCount-1, -1, -1):
            glViewport(self.subWindowLeft[i],self.subWindowBotton[i],self.subWindowWidth[i],self.subWindowHeight[i])
            glPushMatrix()
            
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
                  
            if i == 0:
                # Rz(the) * Ry(-phi) * Rx(0) * [[dis], [0] , [0]] result
#             self.subWindowEye[0][0] = self.view_distance*math.cos(self.view_rot.phi)*math.cos(self.view_rot.theta) + self.view_point.x
#             self.subWindowEye[0][1] = self.view_distance*math.cos(self.view_rot.phi)*math.sin(self.view_rot.theta) + self.view_point.y
#             self.subWindowEye[0][2] = self.view_distance*math.sin(self.view_rot.phi) + self.view_point.z

                Ry = rotj(-(self.view_rot.phi + self.eyeOffset_rot.phi))
                Rz = rotk(self.view_rot.theta + self.eyeOffset_rot.theta)
                Rzy = dmat_mul(3,3,3,Rz,Ry)
                
                n = [[self.view_distance + self.eyeOffset.x], [self.eyeOffset.y], [self.eyeOffset.z]]
                mat = dmat_mul(3,3,1,Rzy,n)
                self.subWindowEye[i][0] = mat[0][0] + self.view_point.x
                self.subWindowEye[i][1] = mat[1][0] + self.view_point.y
                self.subWindowEye[i][2] = mat[2][0] + self.view_point.z
                
                n = [[self.eyeOffset.x], [self.eyeOffset.y], [self.eyeOffset.z]]
                mat = dmat_mul(3,3,1,Rzy,n)
                self.subWindowView[i][0] = mat[0][0] + self.view_point.x
                self.subWindowView[i][1] = mat[1][0] + self.view_point.y
                self.subWindowView[i][2] = mat[2][0] + self.view_point.z
                
                self.subWindowCameraGyro[i][0] = 0
                self.subWindowCameraGyro[i][1] = 0
                self.subWindowCameraGyro[i][2] = 1
                
                #glOrtho(-self.subWindowWidth[i]*self.view_distance/1200, self.subWindowWidth[i]*self.view_distance/1200, -self.subWindowHeight[i]*self.view_distance/1200, self.subWindowHeight[i]*self.view_distance/1200, -10000.0, 10000.0)
                gluPerspective(self.eyeFov, (self.subWindowWidth[i])/(self.subWindowHeight[i]), 0.0, 1.0)
                #glFrustum(-1, 1, -1, 1, 0.1, 100)
            
            elif i == 1:
                render_text_start(self.subWindowWidth[i], self.subWindowHeight[i])
                render_text('(2km range)', 20, 20, 0.4, self.Color_DiffuseW)
                render_text_end()
                self.subWindowEye[i][0] = self.subWindowView[0][0]
                self.subWindowEye[i][1] = self.subWindowView[0][1]
                self.subWindowEye[i][2] = self.subWindowView[0][2] + 70
                 
                self.subWindowView[i][0] = self.subWindowView[0][0]
                self.subWindowView[i][1] = self.subWindowView[0][1]
                self.subWindowView[i][2] = self.subWindowView[0][2]
                 
                self.subWindowCameraGyro[i][0] = 0
                self.subWindowCameraGyro[i][1] = 1
                self.subWindowCameraGyro[i][2] = 0
 
                gluPerspective(self.eyeFov, (self.subWindowWidth[i])/(self.subWindowHeight[i]), 0.0, 1.0)
                 
            elif i == 2:
                render_text_start(self.subWindowWidth[i], self.subWindowHeight[i])
                render_text('(7km range)', 20, 20, 0.4, self.Color_DiffuseW)
                render_text_end()
                self.subWindowEye[i][0] = self.subWindowView[0][0]
                self.subWindowEye[i][1] = self.subWindowView[0][1]
                self.subWindowEye[i][2] = self.subWindowView[0][2] + 210
                 
                self.subWindowView[i][0] = self.subWindowView[0][0]
                self.subWindowView[i][1] = self.subWindowView[0][1]
                self.subWindowView[i][2] = self.subWindowView[0][2]
                 
                self.subWindowCameraGyro[i][0] = 0
                self.subWindowCameraGyro[i][1] = 1
                self.subWindowCameraGyro[i][2] = 0
                 
                gluPerspective(self.eyeFov, (self.subWindowWidth[i])/(self.subWindowHeight[i]), 0.0, 1.0)   
               
            # Debug for Vision AR
#             elif i == 1:
#                 self.subWindowEye[i][0] = self.subWindowView[0][0]
#                 self.subWindowEye[i][1] = self.subWindowView[0][1] + self.view_distance
#                 self.subWindowEye[i][2] = self.subWindowView[0][2]
#                 
#                 self.subWindowView[i][0] = self.subWindowView[0][0]
#                 self.subWindowView[i][1] = self.subWindowView[0][1]
#                 self.subWindowView[i][2] = self.subWindowView[0][2]
#                 
#                 self.subWindowCameraGyro[i][0] = 0
#                 self.subWindowCameraGyro[i][1] = 0
#                 self.subWindowCameraGyro[i][2] = 1
# 
#                 if self.view_distance > 100:
#                     glOrtho(-self.view_distance, self.view_distance, -self.view_distance, self.view_distance, -self.view_distance, self.view_distance)
#                 else:                
#                     glOrtho(-self.view_distance, self.view_distance, -self.view_distance, self.view_distance, -100, 100)
#                 
#             elif i == 2:
#                 self.subWindowEye[i][0] = self.subWindowView[0][0]
#                 self.subWindowEye[i][1] = self.subWindowView[0][1]
#                 self.subWindowEye[i][2] = self.subWindowView[0][2] + self.view_distance
#                 
#                 self.subWindowView[i][0] = self.subWindowView[0][0]
#                 self.subWindowView[i][1] = self.subWindowView[0][1]
#                 self.subWindowView[i][2] = self.subWindowView[0][2]
#                 
#                 self.subWindowCameraGyro[i][0] = -1
#                 self.subWindowCameraGyro[i][1] = 0
#                 self.subWindowCameraGyro[i][2] = 0
#                 
#                 if self.view_distance > 100:
#                     glOrtho(-self.view_distance, self.view_distance, -self.view_distance, self.view_distance, -self.view_distance, self.view_distance)
#                 else:                
#                     glOrtho(-self.view_distance, self.view_distance, -self.view_distance, self.view_distance, -100, 100)
                
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

                #動画出力
                #print('offset = {}, offsetR = {}, fov = {}, viewR = {}, distance = {}'.format(self.eyeOffset, self.eyeOffset_rot, self.eyeFov, self.view_rot, self.view_distance))
#                 if self.video_capture != None:
#                     #self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 16*30)
#                     success, frame = self.video_capture.read()
#                     if success:
#                         frame = cv2.resize(frame, (self.subWindowWidth[i], self.subWindowHeight[i]))
#                         frame = cv2.flip(frame, 0)
#                         frame= cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
#                         glDrawPixels(frame.shape[1], frame.shape[0], GL_RGB,GL_UNSIGNED_BYTE, frame)
            
            gluLookAt( self.subWindowEye[i][0], self.subWindowEye[i][1], self.subWindowEye[i][2],
                       self.subWindowView[i][0], self.subWindowView[i][1], self.subWindowView[i][2],
                       self.subWindowCameraGyro[i][0], self.subWindowCameraGyro[i][1], self.subWindowCameraGyro[i][2])
                    
            ####### drawCoordinate 描画 #######
            self.drawCoordinate(i)
            
            ####### レイヤー描画 #######
            self.drawLayerFeatures()
            if self.additionalDrawFunction != None:
                self.additionalDrawFunction(self)
        
            glPopMatrix()
    
        #Text出力
        self.displayText(self.subWindowWidth[0], self.subWindowHeight[0])
        #ボタン出力
        self.displayButton(self.subWindowWidth[0], self.subWindowHeight[0])
        
        glFlush()
                        
    def displayText(self, width, height):
        windowScale = (width / 1024.0) * 0.6
        if windowScale < 1: windowScale = 1
        render_text_start(width, height)
#                 textImage = np.zeros((self.windowHeight,self.windowWidth,3), np.uint8)
#                 textImage = Image.fromarray(textImage)
#                 fontDraw = ImageDraw.Draw(textImage)
        linePosY = 0
        for (txt, size, color) in self.drawTextList_top:
            if txt == '': continue
            linePosY += 50 * size * windowScale
#                     fontDraw.text((20, int(linePosY)), txt, font=self.font, fill=(int(color[0]*255), int(color[1]*255), int(color[2]*255)))
#                     textImage = cv2.putText(
#                       img = textImage,
#                       text = txt,
#                       org = (20, int(linePosY)),
#                       fontFace = cv2.FONT_HERSHEY_SIMPLEX,
#                       fontScale = size*1.5,
#                       color = (color[0]*255, color[1]*255, color[2]*255),
#                       thickness = 1
#                     )
            render_text(txt, 20, linePosY, size * windowScale, color)
        linePosY = height
        for (txt, size, color) in reversed(self.drawTextList_bottom):
            if txt == '': continue
            linePosY -= 50 * size * windowScale
#                     fontDraw.text((20, int(linePosY)), txt, font=self.font, fill=(int(color[0]*255), int(color[1]*255), int(color[2]*255)))
#                     textImage = cv2.putText(
#                       img = textImage,
#                       text = txt,
#                       org = (20, int(linePosY)),
#                       fontFace = cv2.FONT_HERSHEY_SIMPLEX,
#                       fontScale = size*1.5,
#                       color = (color[0]*255, color[1]*255, color[2]*255),
#                       thickness = 1
#                     )
            render_text(txt, 20, linePosY, size * windowScale, color)
            
        render_text_end()
#                 textImage = np.array(textImage)
#                 textImage = cv2.flip(textImage, 0)
#                 glRasterPos2f(-1, -1)
#                 glDrawPixels(textImage.shape[1], textImage.shape[0], GL_RGB,GL_UNSIGNED_BYTE, textImage)    

    def displayButton(self, width, height):
        glPushMatrix()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        buttonSize = 80
        margin = 20
        buttonCnt = len(self.buttonList)
        posX = width - buttonSize - margin
        posY = height - (height - buttonSize*buttonCnt - margin*(buttonCnt-1)) / 2 - buttonSize
        
        for button in self.buttonList:
            button.posX = posX
            button.posY = posY
            button.size = buttonSize
            drawSrc = button.drawSrc
            drawRectangleWithImage(posX, posY, buttonSize, buttonSize, width, height, drawSrc)
            posY -= margin + buttonSize
        
        glPopMatrix()
    
    def getClickedButtonIndex(self, pos):
        for i in range(len(self.buttonList)):
            posX = self.buttonList[i].posX
            posY = self.buttonList[i].posY
            buttonSize = self.buttonList[i].size
            if (posX <= pos[0]) and (pos[0] < (posX + buttonSize)) and (posY <= pos[1]) and (pos[1] < (posY + buttonSize)):
                return i
        return -1
    
    def getClickedSubWindowIndex(self, pos):
        for i in range(self.totalSubWindowCount):
            if (self.subWindowLeft[i] <= pos[0]) and (pos[0] < (self.subWindowLeft[i] + self.subWindowWidth[i])) and (self.subWindowBotton[i] <= pos[1]) and (pos[1] < (self.subWindowBotton[i] + self.subWindowHeight[i])):
                return i
        return -1
    
    def modifyToWindowPoint(self, pos):
        pos_x = pos[0]
        pos_y = self.windowHeight - pos[1]
        return (pos_x, pos_y)
        
    def setViewTargetLonLatZ(self, lon, lat, z):
        rate = OpenGLWindow.ObjectSizeRate_lonlat
        rate_z = OpenGLWindow.ObjectSizeRate_meter
        
        if self.view_offset == None:
            self.view_offset = Point3D(lon, lat, 0)
        newPosition = Point3D((lon-self.view_offset.x) * rate, (lat-self.view_offset.y) * rate, z * rate_z)

        if self.view_Smooth_lastTime == None:
            self.view_Smooth_orderSpan = 0
            self.view_Smooth_lastTime = datetime.now()
        else:
            deltaTime = (datetime.now() - self.view_Smooth_lastTime).total_seconds()
            if deltaTime > 1.0:
                self.view_Smooth_orderSpan = deltaTime
                self.view_Smooth_lastTime = datetime.now()
                self.view_point_Smooth_old = self.view_point.copy()
                self.view_point_Smooth = newPosition.copy()
        
        if self.view_SmoothRot_lastTime == None:
            self.view_SmoothRot_orderSpan = 0
            self.view_SmoothRot_lastTime = datetime.now()
            self.view_point_Smooth_old_forRotCalc = newPosition.copy()
        else:
            deltaTime = (datetime.now() - self.view_SmoothRot_lastTime).total_seconds()
            distance = (self.view_point_Smooth_old_forRotCalc.x - newPosition.x) ** 2 + (self.view_point_Smooth_old_forRotCalc.y - newPosition.y) ** 2
            if deltaTime > 2.0 and distance > 0.00001:
                self.view_SmoothRot_orderSpan = deltaTime
                self.view_SmoothRot_lastTime = datetime.now()
                self.view_rot_Smooth_old = self.view_rot.copy()
                self.view_rot_Smooth = Rot(math.atan2(self.view_point_Smooth_old_forRotCalc.y - newPosition.y,
                                                      self.view_point_Smooth_old_forRotCalc.x - newPosition.x),
                                        deg2rad(20))
                while self.view_rot_Smooth.theta < self.view_rot_Smooth_old.theta - math.pi:
                    self.view_rot_Smooth.theta += math.pi * 2
                while self.view_rot_Smooth.theta > self.view_rot_Smooth_old.theta + math.pi:
                    self.view_rot_Smooth.theta -= math.pi * 2
                self.view_point_Smooth_old_forRotCalc = newPosition.copy()
    
    def __init__(self, title, prepareDataFunction = None, additionalDrawFunction = None, drawTask = None, layerManager = None):
        # GLFW初期化
        if not glfw.init():
            return
    
        logger = getLogger()
        # ウィンドウを作成
        window = glfw.create_window(W_INIT, H_INIT, title, None, None)
        if not window:
            glfw.terminate()
            logger.logPrintWithConsol('Failed to create window')
            return
    
        # コンテキストを作成します
        self.window = window
        self.prepareDataFunction = prepareDataFunction
        self.additionalDrawFunction = additionalDrawFunction
        self.drawTask = drawTask
        self.layerManager = layerManager
        glfw.make_context_current(window)
        glfw.set_window_user_pointer(window, self)
        glfw.set_window_size_callback(window, OpenGLWindow.resize)
        glfw.set_mouse_button_callback(window, OpenGLWindow.mouseEvent)
        glfw.set_cursor_pos_callback(window, OpenGLWindow.mouseMove)
        glfw.set_scroll_callback(window, OpenGLWindow.mouseScroll)
        glfw.set_key_callback(window, OpenGLWindow.keyboard)
        
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        
        # OpenGLのバージョン等を表示します
        logger.logPrintWithConsol('Vendor : {}'.format(glGetString(GL_VENDOR)))
        logger.logPrintWithConsol('GPU : {}'.format(glGetString(GL_RENDERER)))
        logger.logPrintWithConsol('OpenGL version : {}'.format(glGetString(GL_VERSION)))    
        logger.logPrintWithConsol("OpenCV version : {}".format(cv2.__version__))
    
#         self.font = ImageFont.truetype('res/font/meiryo.ttc', 20)
        textinitliaze()
        imageInitliaze()
        self.buttonList = []
        if self.trackingMode == TrackingMode.XYZRot:
            self.btn_tracking = Button(ResourceImageData[ImageResource.AutoRotMov], self.clickOnTrackingButton)
        elif self.trackingMode == TrackingMode.XYZ:
            self.btn_tracking = Button(ResourceImageData[ImageResource.AutoMov], self.clickOnTrackingButton)
        else:
            self.btn_tracking = Button(ResourceImageData[ImageResource.AutoOff], self.clickOnTrackingButton)
        self.buttonList.append(self.btn_tracking)
        self.buttonList.append(Button(ResourceImageData[ImageResource.ZoomIn], self.clickOnZoomIn))
        self.buttonList.append(Button(ResourceImageData[ImageResource.ZoomOut], self.clickOnZoomOut))
        self.buttonList.append(Button(ResourceImageData[ImageResource.CurPos], self.clickOnCurPos))
        if self.showSubWindow:
            self.btn_subView = Button(ResourceImageData[ImageResource.SubViewOn], self.clickOnSubViewButton)
        else:
            self.btn_subView = Button(ResourceImageData[ImageResource.SubViewOff], self.clickOnSubViewButton)
        self.buttonList.append(self.btn_subView)

        OpenGLWindow.resize(window, W_INIT, H_INIT)
    
    def clickOnTrackingButton(self):
        if self.trackingMode == TrackingMode.XYZRot:
            self.trackingMode = TrackingMode.Off
            self.btn_tracking.drawSrc = ResourceImageData[ImageResource.AutoOff]
        elif self.trackingMode == TrackingMode.XYZ:
            self.trackingMode = TrackingMode.XYZRot
            self.btn_tracking.drawSrc = ResourceImageData[ImageResource.AutoRotMov]
        else:
            self.trackingMode = TrackingMode.XYZ
            self.btn_tracking.drawSrc = ResourceImageData[ImageResource.AutoMov]
    
    def clickOnZoomIn(self):
        self.viewZoom(5)
        
    def clickOnZoomOut(self):
        self.viewZoom(-5)
        
    def clickOnCurPos(self):
        if self.view_point_Smooth != None:
            self.view_point = self.view_point_Smooth.copy()
        
    def clickOnSubViewButton(self):
        if self.showSubWindow:
            self.showSubWindow = False
            self.btn_subView.drawSrc = ResourceImageData[ImageResource.SubViewOff]
        else:
            self.showSubWindow = True
            self.btn_subView.drawSrc = ResourceImageData[ImageResource.SubViewOn]
    
    def loadVedioFile(self, path):
        self.video_capture = cv2.VideoCapture(path)
        if not self.video_capture.isOpened():
            logger = getLogger()
            logger.logPrintWithConsol('Can not open video file')
        
    def drawText(self, lineNo, txt, size, color):
        while len(self.drawTextList_top) <= lineNo:
            self.drawTextList_top.append(('', 0, None))
        self.drawTextList_top[lineNo] = (txt, size, color)
        
    def getText(self, lineNo):
        if len(self.drawTextList_top) > lineNo:
            return self.drawTextList_top[lineNo][0]
        else:
            return ''
                
    def drawText_bottom(self, lineNo, txt, size, color):
        while len(self.drawTextList_bottom) <= lineNo:
            self.drawTextList_bottom.append(('', 0, None))
        self.drawTextList_bottom[lineNo] = (txt, size, color)
        
    def getText_bottom(self, lineNo):
        if len(self.drawTextList_bottom) > lineNo:
            return self.drawTextList_bottom[lineNo][0]
        else:
            return ''
    
    def applySymbol(self, symbol):
        glColor3fv((symbol.color.r / 255, symbol.color.g / 255, symbol.color.b / 255))
        glLineWidth(symbol.width * 2)

    def drawLayerFeatures(self):
#         compileCallTotalTime = 0
#         compileCallCount = 0
#         createCompileTotalTime = 0
#         createCompileCount = 0
        if self.layerManager == None:
            return
        
        for _, layers in self.layerManager.layerList.items():
            for layer in layers:
                layer = layer[0]
                    
                compileList = layer.glCompile
#                 compileListCount = len(compileList)
#                 compileCallCount += compileListCount
#                 startTime = datetime.now()
                for compileID in compileList:
                    if compileID > self.lastCompileIndex-3000: glCallList(compileID)          
#                 compileID = 1
#                 while compileID < self.lastCompileIndex:
#                     glCallList(compileID)
#                     compileID += 1                    
#                 endTime = datetime.now()
#                 compileCallTotalTime += (endTime - startTime).total_seconds()*1000
                
                featureList = layer.getFeatures()
                featureCount = len(featureList)
                if featureCount == 0: continue
#                 createCompileCount += featureCount
                
#                 startTime = datetime.now()
                rate = OpenGLWindow.ObjectSizeRate_lonlat
                rate_z = OpenGLWindow.ObjectSizeRate_meter
                compileID = glGenLists(1)
                self.lastCompileIndex = compileID
                glNewList(compileID, GL_COMPILE)
                            
                # 通常の描画処理
                for feature in featureList:
                    if feature.type == FeatureType.COMMAND:
                        if feature.getAttributes()[0] == 'deleteFeatures':
                            layer.glCompile.clear()
                            continue
                    
                    symbol = None
                    if layer.category != None:
                        order = layer.getFeatureCategoryValue(feature)
                        if order in layer.category.symbolList:
                            symbol = layer.category.symbolList[order]
                    else:
                        symbol = layer.symbol
                    
                    if symbol != None:
                        self.applySymbol(symbol)
                        
                    if self.view_offset == None:
                        if len(feature.geometryList) > 0 and len(feature.geometryList[0].pointList) > 0:
                            point = feature.geometryList[0].pointList[0]
                            self.view_offset = Point3D(point.lon, point.lat, 0)
                        
                    if layer.symbol.symbolType == SymbolType.LINE:
                        for geometry in feature.geometryList:
                            if feature.type == FeatureType.SingleDashedPaintLine:
                                glEnable(GL_LINE_STIPPLE)
                                glLineStipple(20,0x5555)
                                glBegin(GL_LINE_STRIP)
                                for point in geometry.pointList:
                                    #print((point.lon, point.lat, point.z))
                                    glVertex3f((point.lon-self.view_offset.x)*rate, (point.lat-self.view_offset.y)*rate, (point.z-self.view_offset.z)*rate_z)
                                glEnd()
                                glDisable(GL_LINE_STIPPLE)
                            else:    
                                glBegin(GL_LINE_STRIP)
                                for point in geometry.pointList:
                                    #print((point.lon, point.lat, point.z))
                                    glVertex3f((point.lon-self.view_offset.x)*rate, (point.lat-self.view_offset.y)*rate, (point.z-self.view_offset.z)*rate_z)
                                glEnd()
                            
                glEndList()
                layer.clearFeatures()
                layer.glCompile.add(compileID)
                 
#                 endTime = datetime.now()
#                 createCompileTotalTime += (endTime - startTime).total_seconds()*1000
                 
#         render_text(self.window, self.windowWidth, self.windowHeight, '-> call({}) {:,.1f} ms'.format(compileCallCount ,compileCallTotalTime), self.windowWidth-200, 60, 0.4, self.Color_DiffuseGray)
#         render_text(self.window, self.windowWidth, self.windowHeight, '-> make({}) {:,.1f} ms'.format(createCompileCount, createCompileTotalTime), self.windowWidth-200, 80, 0.4, self.Color_DiffuseGray)
        
    def drawTriangle(self, lon, lat, z, bearing, color):
        rate = OpenGLWindow.ObjectSizeRate_lonlat
        rate_z = OpenGLWindow.ObjectSizeRate_meter
        
        Rz = rotk(bearing)
        p1 = dmat_mul(3,3,1,Rz,[[-0.000012], [ 0.00001], [0]])
        p2 = dmat_mul(3,3,1,Rz,[[-0.000012], [-0.00001], [0]])
        p3 = dmat_mul(3,3,1,Rz,[[ 0.000020], [ 0      ], [0]])
                
        #glLineWidth(2)
        glBegin(GL_TRIANGLES)
        glColor3f(color[0], color[1], color[2])
        glVertex3f((p1[0][0]+lon-self.view_offset.x)*rate, (p1[1][0]+lat-self.view_offset.y)*rate, (z-self.view_offset.z)*rate_z)
        glVertex3f((p2[0][0]+lon-self.view_offset.x)*rate, (p2[1][0]+lat-self.view_offset.y)*rate, (z-self.view_offset.z)*rate_z)
        glVertex3f((p3[0][0]+lon-self.view_offset.x)*rate, (p3[1][0]+lat-self.view_offset.y)*rate, (z-self.view_offset.z)*rate_z)
        glEnd()
    
    def mainLoop(self):
        while not glfw.window_should_close(self.window):
            # バッファを指定色で初期化
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glClearColor(0,0,0,1)
            
            #データ読み込み
#             displayStartTime = datetime.now()
            if self.prepareDataFunction != None:
                self.prepareDataFunction(self, self.drawTask, self.layerManager)
#             displayEndTime = datetime.now()
#             render_text(self.window, self.windowWidth, self.windowHeight, 
#                     'feature {:,.1f} ms'.format((displayEndTime - displayStartTime).total_seconds()*1000), 
#                     self.windowWidth-200, 20, 0.4, self.Color_DiffuseGray)
            
            #描画
            displayStartTime = datetime.now()
            self.display()
            displayEndTime = datetime.now()
            render_text_start(self.windowWidth, self.windowHeight)
            render_text('drawing {:,.1f} ms'.format((displayEndTime - displayStartTime).total_seconds()*1000), 
                    self.windowWidth-200, 20, 0.4, self.Color_DiffuseGray)
            render_text_end()
                
            # バッファを入れ替えて画面を更新
            glfw.swap_buffers(self.window)
        
            # イベントを受け付けます
            glfw.poll_events() #delay無し
            #glfw.wait_events_timeout(1e-3) #delayあり
            #glfw.wait_events() #イベントあるまで待つ
            
        # ウィンドウを破棄してGLFWを終了します
        glfw.destroy_window(self.window)
        glfw.terminate()
        