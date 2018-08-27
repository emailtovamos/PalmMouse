#!/usr/bin/python
#-*- coding: utf-8 -*-

"""-------------------------------------------------------------------------
    Control de cursor, click derecho e izquierdo, mediante procesamiento de imágenes.

    author:		Yeison Cardona
    contact:		yeison.eng@gmail.com
    first release:	12/11/2012
    last release:	22/11/2012

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""

import pickle, time, os, threading
import win32api, win32con

try:
    import numpy as np
    from numpy import sqrt, arccos, rad2deg
except:
    print ("need Numpy for Python!!.")
    exit()

try: import cv2
except:
    print ("need OpenCV for Python!!.")
    exit()

#Chequear dependencia de OpenCV 2.4
if not cv2.__version__ >= "2.4":
    print ("OpenCV version to old!!.")
    print ("need version >= 2.4.")
    exit()

#Checkear dependencia de xdotool package
# try: os.system("xdotool --help")
# except:
#     print ("need xdotool dependence.")
#     exit()

########################################################################
class HandTracking:

    #----------------------------------------------------------------------
    def __init__(self):
        #self.debugMode = False
        self.debugMode = True

        #self.camera = cv2.VideoCapture(2)  #Cambiar para usar otra cámara

        self.camera = cv2.VideoCapture(0)

        #Resolusión a usar
        #self.camera.set(3,640)
        #self.camera.set(4,480)

        self.camera.set(3,1920)
        self.camera.set(4,1080)

        self.posPre = 0  #Para obtener la posisión relativa del «mouse»

        #Diccionario para almacenar nuestros datos
        self.Data = {"angles less 90" : 0,
                     "cursor" : (0, 0),
                     "hulls" : 0,
                     "defects" : 0,
                     "fingers": 0,
                     "fingers history": [0],
                     "area": 0,
		     "cuadro": 0,
                     }
        #Última actualización
        self.lastData = self.Data

        #Cargamos las variables de los filtros
        #Si se modifican durante la ejecución, se actualizarán en el fichero
        try:  self.Vars = pickle.load(open(".config", "r"))
        except:
            print ("Config file («.config») not found.")
            exit()

        #Ventanas independientes para los filtros
        cv2.namedWindow("Filters")
        cv2.createTrackbar("erode", "Filters", self.Vars["erode"], 255, self.onChange_erode)
        cv2.createTrackbar("dilate", "Filters", self.Vars["dilate"], 255, self.onChange_dilate)
        cv2.createTrackbar("smooth", "Filters", self.Vars["smooth"], 255, self.onChange_smooth)

        cv2.namedWindow("HSV Filters")
        cv2.createTrackbar("upper", "HSV Filters", self.Vars["upper"], 255, self.onChange_upper)
        cv2.createTrackbar("filterUpS", "HSV Filters", self.Vars["filterUpS"], 255, self.onChange_fuS)
        cv2.createTrackbar("filterUpV", "HSV Filters", self.Vars["filterUpV"], 255, self.onChange_fuV)
        cv2.createTrackbar("lower", "HSV Filters", self.Vars["lower"], 255, self.onChange_lower)
        cv2.createTrackbar("filterDownS", "HSV Filters", self.Vars["filterDownS"], 255, self.onChange_fdS)
        cv2.createTrackbar("filterDownV", "HSV Filters", self.Vars["filterDownV"], 255, self.onChange_fdV)

        self.areaThresh = 5000

        self.mPosX = 50
        self.mPosY = 300
        self.mSepX = 30
        self.mSepY = 20
        self.mSqH = 60
        self.mSqW = 110


        #Agregar texto
        self.addText = lambda image, text, point:cv2.putText(image,text, point, cv2.FONT_HERSHEY_PLAIN, 1.0,(255,255,255))

        #Siempre
        while True:
            self.run()  #Procese la imagen
            #self.interprete()  #Interprete eventos (clicks)
            #self.updateMousePos()  #Mueve el cursor
            if self.debugMode:
                if cv2.waitKey(1) & 0xFF == 27: break


    #----------------------------------------------------------------------
    def onChange_fuS(self, value):
        self.Vars["filterUpS"] = value
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_fdS(self, value):
        self.Vars["filterDownS"] = value
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_fuV(self, value):
        self.Vars["filterUpV"] = value
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_fdV(self, value):
        self.Vars["filterDownV"] = value
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_upper(self, value):
        self.Vars["upper"] = value
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_lower(self, value):
        self.Vars["lower"] = value
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_erode(self, value):
        self.Vars["erode"] = value + 1
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_dilate(self, value):
        self.Vars["dilate"] = value + 1
        pickle.dump(self.Vars, open(".config", "w"))

    #----------------------------------------------------------------------
    def onChange_smooth(self, value):
        self.Vars["smooth"] = value + 1
        pickle.dump(self.Vars, open(".config", "w"))


    #----------------------------------------------------------------------
    def run(self):
        cutX = 400
        cutY = 300
        ret, im = self.camera.read()
        im = cv2.flip(im, 1)

        im = im[cutY:cutY+480, cutX:cutX+640]
        self.imOrig = im.copy()
        self.imNoFilters = im.copy()

        mPosX = self.mPosX
        mPosY = self.mPosY
        mSepX = self.mSepX
        mSepY = self.mSepY
        mSqH = self.mSqH
        mSqW = self.mSqW

        #Aplica smooth
        im = cv2.blur(im, (self.Vars["smooth"], self.Vars["smooth"]))

        #Aplica filtro de color de piel
        filter_ = self.filterSkin(im)

        #Aplica erode
        filter_ = cv2.erode(filter_,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(self.Vars["erode"], self.Vars["erode"])))

        #Aplica dilate
        filter_ = cv2.dilate(filter_,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(self.Vars["dilate"], self.Vars["dilate"])))


        #Muestra la imagen binaria
        if self.debugMode: cv2.imshow("Filter Skin", filter_)

        #Obtiene contornos
        contours, hierarchy = cv2.findContours(filter_,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
        #if self.debugMode: cv2.imshow("Filter Skin", filter_)

        #Elimina «islas huérfanas» de área pequeña
        allIdex = []
        for index in range(len(contours)):
            area = cv2.contourArea(contours[index])
            if area < self.areaThresh: allIdex.append(index)
        allIdex.sort(reverse=True)
        for index in allIdex: contours.pop(index)

        #Si no hay contornos, termine aquí
        #if len(contours) == 0: return

        allIdex = []
        index_ = 0

        #Recorremos cada contorno
        for cnt in contours:
            self.Data["area"] = cv2.contourArea(cnt)

            tempIm = im.copy()
            tempIm = cv2.subtract(tempIm, im)

	    #Para hallar convexidades (dedos)
            hull = cv2.convexHull(cnt)
            self.last = None
            self.Data["hulls"] = 0

            for hu in hull:
                if self.last == None: cv2.circle(tempIm, tuple(hu[0]), 10, (0,0,255), 5)
                else:
                    distance = self.distance(self.last, tuple(hu[0]))
                    if distance > 40:  #Eliminar puntos demasiado juntos
                        self.Data["hulls"] += 1
                        #Círculos rojos
                        cv2.circle(tempIm, tuple(hu[0]), 10, (0,0,255), 5)
                self.last = tuple(hu[0])

            #Momento principal, que rigue el control del cursor
            M = cv2.moments(cnt)
            centroid_x = int(M['m10']/M['m00'])
            centroid_y = int(M['m01']/M['m00'])
            #cv2.circle(tempIm, (centroid_x, centroid_y), 20, (0,255,255), 10)
            cv2.circle(self.imOrig, (centroid_x, centroid_y), 20, (0,255,255), 10)


            self.Data["cursor"] = (centroid_x, centroid_y)
	    #self.moveMouseCuadro(self.Data["cuadro"])
            #Para hallar la convexidades (espacios entre dedos)
            hull = cv2.convexHull(cnt,returnPoints = False)
            angles = []
            defects = cv2.convexityDefects(cnt,hull)
            if defects == None: return

            self.Data["defects"] = 0
            for i in range(defects.shape[0]):
                s,e,f,d = defects[i,0]
                if d > 1000 :
                    start = tuple(cnt[s][0])
                    end = tuple(cnt[e][0])
                    far = tuple(cnt[f][0])
                    self.Data["defects"] += 1
                    cv2.circle(tempIm,far,5,[0,255,255],-1)  #Marcar lo defectos con puntos amarillos
                    #Líneas entre convexidades y defectos
                    cv2.line(tempIm, start, far, [255, 0, 0], 5)
                    cv2.line(tempIm, far, end, [255, 0, 0], 5)
                    #Obtener el ángulos que forman las líneas anteriores
                    angles.append(self.angle(far, start, end))

            #Filtran ángulos menores a 90.
            b = filter(lambda a:a<90, angles)

            #Se asume que si son menores de 90 grados, corresponde a un dedo.
            self.Data["angles less 90"] = len(b)
            self.Data["fingers"] = len(b) + 1

            #Para almacenar los últimos estados de los dedos.
            self.Data["fingers history"].append(len(b) + 1)

            if len(self.Data["fingers history"]) > 10: self.Data["fingers history"].pop(0)
            self.imOrig = cv2.add(self.imOrig, tempIm)

            index_ += 1


        #Rellenar el espacio filtrado de la piel menos las áreas pequeñas de un color verde :)
        cv2.drawContours(self.imOrig,contours,-1,(64,255,85),-1)

        #Visualizar el estado anctual de los datos.
        self.debug()
        if self.debugMode: cv2.imshow("\"Hulk\" Mode", self.imOrig)


    #----------------------------------------------------------------------
    def distance(self, cent1, cent2):
        """Retorna la distancia entre dos puntos."""
        x = abs(cent1[0] - cent2[0])
        y = abs(cent1[1] - cent2[1])
        d = sqrt(x**2+y**2)
        return d

    #----------------------------------------------------------------------
    def angle(self, cent, rect1, rect2):
        """Retorna el ángulo formado entre tres puntos."""
        v1 = (rect1[0] - cent[0], rect1[1] - cent[1])
        v2 = (rect2[0] - cent[0], rect2[1] - cent[1])
        dist = lambda a:sqrt(a[0] ** 2 + a[1] ** 2)
        angle = arccos((sum(map(lambda a, b:a*b, v1, v2))) / (dist(v1) * dist(v2)))
        angle = abs(rad2deg(angle))
        return angle

    #----------------------------------------------------------------------
    def filterSkin(self, im):
        """Aplica el filtro de piel."""
        UPPER = np.array([self.Vars["upper"], self.Vars["filterUpS"], self.Vars["filterUpV"]], np.uint8)
        LOWER = np.array([self.Vars["lower"], self.Vars["filterDownS"], self.Vars["filterDownV"]], np.uint8)
        hsv_im = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
        filter_im = cv2.inRange(hsv_im, LOWER, UPPER)
        return filter_im

    #----------------------------------------------------------------------
    def debug(self):
        """Imprime mensaje de depuración sobre el video."""
        yPos = 10
        if self.debugMode: self.addText(self.imOrig, "Debug", (yPos, 20))
        pos = 50
        for key in self.Data.keys():
            if self.debugMode: self.addText(self.imOrig, (key+": "+str(self.Data[key])), (yPos, pos))
            pos += 20

    #----------------------------------------------------------------------
    def updateMousePos(self):
        """Actualiza la posisión del cursor."""
        pos = self.Data["cursor"]
        posPre = self.posPre
        npos = np.subtract(pos, posPre)
        self.posPre = pos

        if self.Data["fingers"] in [1]:  #Sólo mueve el curson cuando hay un dedo extendido o el puño cerrado
            try: elf.t.__stop.set()
            except: pass
            #Thread para mover el cursor
            self.t = threading.Thread(target=self.moveMouse, args=(npos))
            self.t.start()

    #----------------------------------------------------------------------
    def interprete(self):
        """Interpreta los eventos."""
        cont = 3
        #Click Izquierdo, 5 dedos extendidos.
        if self.Data["fingers history"][:cont] == [5] * cont:
            # os.system("xdotool click 1")
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN,100,100,0,0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP,100,100,0,0)
            self.Data["fingers history"] = [0]  #Elimina el historial de estado de los dedos.
        #Click Izquierdo, 3 dedos extendidos.
        elif self.Data["fingers history"][:cont] == [3] * cont:
            # os.system("xdotool click 3")
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN,100,100,0,0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP,100,100,0,0)
            self.Data["fingers history"] = [0]

    #----------------------------------------------------------------------
    def moveMouse(self, x, y):
        """Mueve el cursor a una posisión relativa.

        Siempre de «invoca» desde un thread!!."""
        mini = 10
        mul = 2
        x *= mul
        y *= mul
        #Un movimiento fluido...
        posy = lambda n:(y/x) * n  #...genera la ecuación de la trayectoria...
        stepp = 10
        #... y la recorre en x cada 10px
        if x > 0:
            # for i in range(0, x, stepp): os.system("xdotool mousemove_relative -- %d %d" %(i, posy(i)))
            for i in range(0, x, stepp): win32api.SetCursorPos((i, posy(i)))
        if x < 0:
            # for i in range(x, 0, stepp): os.system("xdotool mousemove_relative -- %d %d" %(i, posy(i)))
            for i in range(0, x, stepp): win32api.SetCursorPos((i, posy(i)))
        time.sleep(0.2)  #Pausa para «suavizar» el movimiento

    #----------------------------------------------------------------------
    def moveMouseCuadro(self, cuadro):
        posX = [0,240,720,1200,240,720,1200]
        posY = [0,225,225,225,675,675,675]
        if cuadro >= 1 and cuadro <= 6:
        	# comm = "xdotool mousemove " + str(posX[cuadro]) + " " + str(posY[cuadro])
            win32api.SetCursorPos((posX[cuadro], posY[cuadro]))
        elif cuadro == 0:
        	comm = "xdotool mousemove " + str(1440) + " " + str(900)
            # win32api.SetCursorPos((1400, 900))

        # os.system(comm)


if __name__=='__main__':
    HandTracking()
