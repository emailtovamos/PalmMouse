import numpy as np
import cv2, time
import win32api, win32con
import matplotlib.pyplot as plt
def movemouse(x,y):
    win32api.SetCursorPos((x,y))

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')

cap = cv2.VideoCapture(0)
iii=0

ret1, img1 = cap.read()
ret2, img2 = cap.read()
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


cv2.imshow('img',img1)
cv2.imshow('img2',img2)
k = cv2.waitKey(30) & 0xff
if k == 27:
    break

cap.release()
cv2.destroyAllWindows()
