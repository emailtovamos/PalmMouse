import numpy as np
import cv2, time
import win32api, win32con
import matplotlib.pyplot as plt
def movemouse(x,y):
    win32api.SetCursorPos((x,y))
    # win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
    # win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)
    # win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN,x,y,0,0)
    # win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP,x,y,0,0)
def savitzky_golay(y, window_size, order, deriv=0, rate=1):

     import numpy as np
     from math import factorial

     try:
         window_size = np.abs(np.int(window_size))
         order = np.abs(np.int(order))
     except ValueError as msg:
         raise ValueError("window_size and order have to be of type int")
     if window_size % 2 != 1 or window_size < 1:
         raise TypeError("window_size size must be a positive odd number")
     if window_size < order + 2:
         raise TypeError("window_size is too small for the polynomials order")
     order_range = range(order+1)
     half_window = (window_size -1) // 2
     # precompute coefficients
     b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
     m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
     # pad the signal at the extremes with
     # values taken from the signal itself
     firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
     lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
     y = np.concatenate((firstvals, y, lastvals))
     return np.convolve( m[::-1], y, mode='valid')


# x = np.linspace(0,2*np.pi,100)
# y = np.sin(x) + np.random.random(100) * 0.2
# yhat = savitzky_golay(y, 51, 3) # window size 51, polynomial order 3
#
# plt.plot(x,y)
# plt.plot(x,yhat, color='red')
# print(type(y))
# plt.show()

# multiple cascades: https://github.com/Itseez/opencv/tree/master/data/haarcascades

#https://github.com/Itseez/opencv/blob/master/data/haarcascades/haarcascade_frontalface_default.xml
palm_cascade = cv2.CascadeClassifier('palm.xml')


cap = cv2.VideoCapture(0)
iii=0
while 1:
    ret, img = cap.read()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = palm_cascade.detectMultiScale(gray, 1.3, 5)
    yy=[]
    xx=[]
    for ii in range(15):
        for (x,y,w,h) in faces:
            cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
            yy.append(y)
            xx.append(x)
            # movemouse(x*3,y*3)
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = img[y:y+h, x:x+w]
            # print(y)
            # print(x)


    # yhat = savitzky_golay(yy, 51, 3)

    avg=(np.average(yy))
    avg1=(np.average(xx))

    try:
        avgy=int(avg)
        avgx=int(avg1)
        movemouse(avgx*3,avgy*3)
    except ValueError:
        # avgy=yy[-1]
        try:
            avgy=faces[0]
            avgx=faces[1]
            movemouse(avgx*3,avgy*3)
        except:
            pass
    iii=iii+1
    # print(iii)



    # print(avgy)
    # print(avgx)
        # print(yy)

        # if yy != [] and xx!= []:
        #     yhat = savitzky_golay(yy, 51, 3)
        #     xhat = savitzky_golay(xx, 51, 3)
        #     movemouse(int(np.average(xhat)),int(np.average(yhat)) )
    # yhat = savitzky_golay(yy, 51, 3)
    # movemouse(x*3,int(np.average(yhat)*3) )


    cv2.imshow('img',img)
    k = cv2.waitKey(30) & 0xff
    if k == 27:
        break

cap.release()
cv2.destroyAllWindows()
