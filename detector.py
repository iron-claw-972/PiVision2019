import cv2 as cv
import numpy as np
import time
import math
import sys
import context
import random
from networktables import NetworkTables

class Detector:
    LOWER_BLUE = np.array([46,0,222])
    UPPER_BLUE = np.array([95,171,255])

    def __init__(self):
        self.scaleFactor = .25
        self.criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        self.objp = np.float32([(-5.936, .501, 0),(-4, 0, 0),(-5.377, -5.325, 0),(-7.313, -4.824, 0),
                (5.936, .501, 0),(4, 0, 0),(5.377, -5.325, 0),(7.313, -4.824, 0)])

        self.objp = self.sort_points(self.objp)

        self.axis = np.float32([[0,0,0], [1,0,0], [0,1,0], [0,0,-1]]).reshape(-1,3)

        self.rvecs = [[0], [0], [0]]
        self.tvecs = [[0], [0], [0]]

        self.ip = 'roborio-972-frc.local'
        NetworkTables.initialize(server=self.ip)
        self.sd = NetworkTables.getTable("SmartDashboard")

        #self.sd.putString("raspberrypi ip", (([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")] or [[(s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) + ["no IP found"])[0])

        # Load previously saved data with np.load('B.npz') as X:
        with np.load('calibration640_480.npz') as X:
            self.mtx, self.dist, _, _ = [X[i] for i in ('mtx','dist','rvecs','tvecs')]
            context.dist = self.dist
            context.mtx = self.mtx

    @staticmethod
    def sortFunc(inputVal):
        return math.sqrt((inputVal[0] + 10) * (inputVal[0] + 10) + (inputVal[1] + 10) * (inputVal[1] + 10))

    @staticmethod
    def sort_points(points):
        # sort by y
        sorted = points[points[:,1].argsort()]

        # split
        top, bottom = np.split(sorted, 2)

        # sort both by x
        top = top[top[:,0].argsort()]
        bottom = bottom[bottom[:,0].argsort()]

        return np.concatenate((top, bottom), axis=0)

    @staticmethod
    def distFunc(a, b):
        return math.sqrt((a[0]-b[0])*(a[0]-b[0])+(a[1]-b[1])*(a[1]-b[1]))

    @staticmethod
    def white_balance(img):
        result = cv.cvtColor(img, cv.COLOR_BGR2LAB)
        avg_a = np.average(result[:, :, 1])
        avg_b = np.average(result[:, :, 2])
        result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
        result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
        result = cv.cvtColor(result, cv.COLOR_LAB2BGR)
        return result

    @staticmethod
    def draw(img, corners, imgpts):
        corner = tuple(corners[0].ravel())
        img = cv.line(img, corner, tuple(imgpts[0].ravel()), (255,0,0), 3)
        img = cv.line(img, corner, tuple(imgpts[1].ravel()), (0,255,0), 3)
        img = cv.line(img, corner, tuple(imgpts[2].ravel()), (0,0,255), 3)
        return img

    @staticmethod
    def almostEqual(a, b, delta):
        return abs(a-b) < abs(np.average([a,b]) * delta)


    def detectCorners(self, img):
        # TODO does it help?
        #img = white_balance(img)

        #cv.medianBlur(img, 5, img)

        # Threshold the HSV image to get only blue colors
        hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)
        mask = cv.inRange(hsv, self.LOWER_BLUE, self.UPPER_BLUE)
        img = cv.bitwise_and(img,img, mask= mask)

        # Taking a matrix of size 5 as the kernel
        kernel = np.ones((3,3), np.uint8)
        mask = cv.erode(mask, kernel, iterations=1)
        mask = cv.dilate(mask, kernel, iterations=1)
        img = cv.bitwise_and(img, img, mask=mask)

        contours,h = cv.findContours(mask, cv.RETR_LIST, cv.CHAIN_APPROX_SIMPLE)

        pntSet = []
        diagnostic_img = img.copy()

        for cnt in contours:
            cv.drawContours(diagnostic_img, [cnt], 0, (0,255,0), 3)
            approx = cnt

            approx = cv.convexHull(approx)

            epsilon = 0.05 * cv.arcLength(approx, True)
            # TODO arcLength should be sufficient to eliminate tiny contours

            if(epsilon < 3):
                epsilon = 3

            approx = cv.approxPolyDP(approx, epsilon, True)

            if len(approx) != 4:
                for pnt in approx:
                    cv.circle(diagnostic_img, tuple(pnt[0]), 0, (255, 255, 0), thickness=5) #Light Blue
                # print("len(approx) %d" % len(approx))
                continue

            sorted_box = self.sort_points(approx[:,0,:])

            # Points are sorted in the order of ABDC, A being top left, D bottom left
            boxAB = self.distFunc(sorted_box[0], sorted_box[1])
            boxAD = self.distFunc(sorted_box[0], sorted_box[2])
            boxBC = self.distFunc(sorted_box[1], sorted_box[3])
            boxDC = self.distFunc(sorted_box[2], sorted_box[3])

            boxR = boxAD / (boxAB + 1)
            # print("boxR %f" % boxR)

            area = cv.contourArea(approx)
            # print("area %f" % area)

            if(not(
                boxR > 2 and
                boxR < 5 and
                area > 500 and
                #area < 30000 and
                self.almostEqual(boxAB, boxDC, 0.3) and # allow 30% difference for opposite sides
                self.almostEqual(boxAD, boxBC, 0.3)
                )):
                for pnt in approx:
                    cv.circle(diagnostic_img, tuple(pnt[0]), 0, (255, 100, 100), thickness=5) #Dark Blue
                continue

            for pnt in approx:
                pntSet.append(tuple(pnt[0]))
                cv.circle(diagnostic_img, tuple(pnt[0]), 0, (255, 0, 255), thickness=5)

        return diagnostic_img, np.float32(pntSet)

    def solve(self, img):
        # img = cv.resize(img, (0,0), fx=scaleFactor, fy=scaleFactor)
        diagnostic_img, corners = self.detectCorners(img)

        self.sd.putNumber("piCount", random.randint(1, 999))

        if len(corners) != 8:
            #print('no can do')
            return None, None, None, diagnostic_img

        # print("corners")
        # print(corners)
        corners = self.sort_points(corners)

        i = 0
        for pnt in corners:
            cv.putText(img, "%s" % i, (pnt[0], pnt[1]), cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            i += 1

        # print("objp: %s" % self.objp)
        # print("corners: %s" % corners)
        # print("mtx: %s" % self.mtx)
        # print("dist: %s" % self.dist)

        ret, rvecs, tvecs = cv.solvePnP(self.objp, corners, self.mtx, self.dist)
        cv.putText(img, 'X: %s' % round(tvecs[0][0], 3), (50, 50), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv.putText(img, 'Y: %s' % round(tvecs[1][0], 3), (50, 100), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        cv.putText(img, 'Z: %s' % round(tvecs[2][0], 3), (50, 150), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        self.sd.putNumber("visionX", tvecs[0][0])
        self.sd.putNumber("visionY", tvecs[1][0])
        self.sd.putNumber("visionZ", tvecs[2][0])
        self.sd.putNumber("visionRX", rvecs[0][0])
        self.sd.putNumber("visionRY", rvecs[1][0])
        self.sd.putNumber("visionRZ", rvecs[2][0])
        self.sd.putNumber("visionCount", random.randint(1,999))

        context.rvecs = rvecs
        context.tvecs = tvecs
        context.last_detection = time.time()
        return ret, rvecs, tvecs, img
