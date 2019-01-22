import cv2
import numpy as np
import time
import datetime
import schedule as sched
import uuid
import DatabaseConnect as db
from itertools import tee
import math

# The cutoff for threshold. A lower number means smaller changes between
# the average and current scene are more readily detected.
THRESHOLD_SENSITIVITY = 50
# The number of square pixels a blob must be before we consider it a
# candidate for tracking.
BLOB_SIZE = 30000
# The weighting to apply to "this" frame when averaging. A higher number
# here means that the average scene will pick up changes more readily,
# thus making the difference between average and current scenes smaller.
DEFAULT_AVERAGE_WEIGHT = 0.04
# The maximum distance a blob centroid is allowed to move in order to
# consider it a match to a previous scene's blob.
BLOB_LOCKON_DISTANCE_PX = 125
# The number of seconds a blob is allowed to sit around without having
# any new blobs matching it.
BLOB_TRACK_TIMEOUT = 0.1

# Constants for drawing on the frame.
LINE_THICKNESS = 1
CIRCLE_SIZE = 5
RESIZE_RATIO = 1.0

avg = None
tracked_blobs = []

inCount_goingToSM = 0
inCount_goingToCalmar = 0
inAllSpeeds_goingToSM = 0
inAllSpeeds_goingToCalmar = 0

avgSpeed_goingToSM = 0
avgSpeed_goingToCalmar = 0
trafficFlow_goingToSM = 0
trafficFlow_goingToCalmar = 0
density_goingToSM = 0
density_goingToCalmar = 0

timeNow = int(time.time())
dateTime = str(datetime.datetime.fromtimestamp(timeNow).strftime('%Y-%m-%d %H:%M:%S'))

def nothing():
    pass

vc = cv2.VideoCapture('7AM.avi')

db.create_table1_trafficRecordToSM()
db.create_table1_trafficRecordToCalmar()
db.create_table2_trafficDataToSM()
db.create_table2_trafficDataToCalmar()

def computation():

    global inCount_goingToSM
    global inCount_goingToCalmar
    global inAllSpeeds_goingToSM
    global inAllSpeeds_goingToCalmar

    try:
        avgSpeed_goingToSM = inAllSpeeds_goingToSM / inCount_goingToSM
        avgSpeed_goingToCalmar = inAllSpeeds_goingToCalmar / inCount_goingToCalmar
    except ZeroDivisionError:
        avgSpeed_goingToSM = 0
        avgSpeed_goingToCalmar = 0

    trafficFlow_goingToSM = inCount_goingToSM / 300  # vehicles per 5 minutes
    trafficFlow_goingToCalmar = inCount_goingToCalmar / 300  # vehicles per 5 minutes

    density_goingToSM = trafficFlow_goingToSM / 11  # vehicles per 11 meters.
    density_goingToCalmar = trafficFlow_goingToCalmar / 11  # vehicles per 11 meters.

    print("----------------------------------------------------------------------------------------------------------")
    print("Count (To SM) = ", inCount_goingToSM)
    print("Average Speed (To SM) = ", avgSpeed_goingToSM)
    print("Traffic Flow (To SM) = ", trafficFlow_goingToSM)
    print("Density (To SM) = ", density_goingToSM)

    print("Count (To Calmar) = ", inCount_goingToCalmar)
    print("Average Speed (To Calmar) = ", avgSpeed_goingToCalmar)
    print("Traffic Flow (To Calmar) = ", trafficFlow_goingToCalmar)
    print("Density (To Calmar) = ", density_goingToCalmar)

    print("Time = ", dateTime)
    print("---------------------------------------------------------------------    -------------------------------------")

    db.data_entry2_toSM(dateTime, inCount_goingToSM, avgSpeed_goingToSM, trafficFlow_goingToSM, density_goingToSM)
    db.data_entry2_toCalmar(dateTime, inCount_goingToCalmar, avgSpeed_goingToCalmar, trafficFlow_goingToCalmar, density_goingToCalmar)

    inCount_goingToSM = 0
    inCount_goingToCalmar = 0
    inAllSpeeds_goingToSM = 0
    inAllSpeeds_goingToCalmar = 0

def get_frame():
    " Grabs a frame from the video capture and resizes it. "
    rval, frame = vc.read()
    if rval:
        (h, w) = frame.shape[:2]
        frame = cv2.resize(frame, (int(w * RESIZE_RATIO), int(h * RESIZE_RATIO)), interpolation=cv2.INTER_CUBIC)
    return rval, frame

def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def calculateDistance(x1, y1, x2, y2):
    dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return dist

sched.every(5).minutes.do(computation)

print("Time Now = ", dateTime)

while True:
    grabbed, frame = get_frame()
    frame1 = frame

    if not grabbed:
        break

    if sched:
        sched.run_pending()

    fps = vc.get(cv2.CAP_PROP_FPS)
    frameCount = vc.get(cv2.CAP_PROP_FRAME_COUNT)
    vidTime = frameCount / fps

    frame_time = time.time()

    hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    (_, _, grayFrame) = cv2.split(hsvFrame)

    grayFrame = cv2.GaussianBlur(grayFrame, (21, 21), 1)
    #cv2.imshow("grayFrame", grayFrame)

    if avg is None:
        avg = grayFrame.copy().astype("float")
        continue

    cv2.accumulateWeighted(grayFrame, avg, DEFAULT_AVERAGE_WEIGHT)
    #cv2.imshow("average", cv2.convertScaleAbs(avg))

    differenceFrame = cv2.absdiff(grayFrame, cv2.convertScaleAbs(avg))
    #cv2.imshow("difference", differenceFrame)

    retval, thresholdImage = cv2.threshold(differenceFrame, THRESHOLD_SENSITIVITY, 255, cv2.THRESH_BINARY)
    #cv2.imshow("thresholdImage", thresholdImage)

    kernel1 = np.ones((15, 15), np.uint8)
    kernel2 = np.ones((5, 5), np.uint8)

    dilate = cv2.dilate(thresholdImage, kernel1, iterations=1)
    erode = cv2.erode(dilate, kernel2, iterations=1)

    #cv2.imshow("Dilated", dilate)
    #cv2.imshow("Eroded",erode)

    frame,contours, hierarchy = cv2.findContours(erode, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    blobs = filter(lambda c: cv2.contourArea(c) > BLOB_SIZE, contours)

    if blobs:
        for c in blobs:
            (x, y, w, h) = cv2.boundingRect(c)
            center = (int(x + w / 2), int(y + h / 2))

            cv2.rectangle(frame1, (x, y), (x + w, y + h), (255, 255, 255), LINE_THICKNESS)

            closest_blob = None
            if tracked_blobs:
                closest_blobs = sorted(tracked_blobs, key=lambda b: cv2.norm(b['trail'][0], center))

                for close_blob in closest_blobs:
                    distance = cv2.norm(center, close_blob['trail'][0])

                    if distance < BLOB_LOCKON_DISTANCE_PX:
                        expected_dir = close_blob['dir']
                        if expected_dir == 'left' and close_blob['trail'][0][0] < center[0]:
                            continue
                        elif expected_dir == 'right' and close_blob['trail'][0][0] > center[0]:
                            continue
                        else:
                            closest_blob = close_blob
                            break
                if closest_blob:
                    prev_center = closest_blob['trail'][0]
                    if center[0] < prev_center[0]:
                        closest_blob['dir'] = 'left'
                        closest_blob['bumper_x'] = x
                    else:
                        closest_blob['dir'] = 'right'
                        closest_blob['bumper_x'] = x + w

                    closest_blob['trail'].insert(0, center)
                    closest_blob['last_seen'] = frame_time

            if not closest_blob:
                b = dict(
                    id=str(uuid.uuid4())[:8],
                    first_seen=vc.get(cv2.CAP_PROP_POS_FRAMES),
                    last_seen=frame_time,
                    dir=None,
                    bumper_x=None,
                    trail=[center],
                )
                tracked_blobs.append(b)
    if tracked_blobs:

        for i in range(len(tracked_blobs) - 1, -1, -1):
            if frame_time - tracked_blobs[i]['last_seen'] > BLOB_TRACK_TIMEOUT:
                print("--------------------------------------------------DATA--------------------------------------------------------")

                #print("Vehicle ID = {}".format(tracked_blobs[i]['id']))

                timeNow = int(time.time())
                dateTime = str(datetime.datetime.fromtimestamp(timeNow).strftime('%Y-%m-%d %H:%M:%S'))

                firstSeenTime = tracked_blobs[i]['first_seen']
                currentFirstTimeSeen = (frameCount - firstSeenTime) / fps
                realCurrentFirstTimeSeen = vidTime - currentFirstTimeSeen
                #print("First Seen Time = ", realCurrentFirstTimeSeen)

                currentTimeFrame = vc.get(cv2.CAP_PROP_POS_FRAMES)
                #print("Current Last Seen Frame = ",currentTimeFrame)

                currentLastTimeSeen = (frameCount - currentTimeFrame) / fps
                realCurrentLastTimeSeen = vidTime - currentLastTimeSeen
                #print("Last Seen Time = ",realCurrentLastTimeSeen)

                #print("Trail = ", tracked_blobs[i]['trail'])
                #print("First Trail = ", tracked_blobs[i]['trail'][0][0])
                #print("Second Trail = ", tracked_blobs[i]['trail'][-1])

                distance = calculateDistance(tracked_blobs[i]['trail'][0][0], tracked_blobs[i]['trail'][0][1], tracked_blobs[i]['trail'][-1][0], tracked_blobs[i]['trail'][-1][1])
                # Distance is equivalent to 1 centimeter per pixel
                meters = distance * .01
                vehicleTimeSpent = realCurrentLastTimeSeen - realCurrentFirstTimeSeen
                speedMperSec = meters / vehicleTimeSpent #DISTANCE over TIME
                speed = (speedMperSec * 18)/5
                #print("Distance Travelled in Meters = ", meters)
                #print("Time Taken of the Vehicle = ", vehicleTimeSpent)
                #print("Speed of the Vehicle M/Sec= ", speedMperSec)
                #print("Speed of the Vehicle KM/Hr= ", speed)

                if tracked_blobs[i]['dir'] == 'left':   #GOING TO SM
                    if meters <= 2:
                        del tracked_blobs[i]
                    else:
                        inAllSpeeds_goingToSM += speed
                        inCount_goingToSM = inCount_goingToSM + 1

                        db.data_entry1_toSM(tracked_blobs[i]['id'], dateTime, meters, speed)
                        del tracked_blobs[i]
                else:   #GOING TO CALMAR
                    if meters <= 3:
                        del tracked_blobs[i]
                    else:
                        inAllSpeeds_goingToCalmar += speed
                        inCount_goingToCalmar = inCount_goingToCalmar + 1

                        db.data_entry1_toCalmar(tracked_blobs[i]['id'], dateTime, meters, speed)
                        print("Distance Travelled in Meters = ", meters)
                        del tracked_blobs[i]

                print("Count (To SM): ", inCount_goingToSM)
                print("Count (To Calmar): ", inCount_goingToCalmar)

    for blob in tracked_blobs:
        for (a, b) in pairwise(blob['trail']):
            cv2.circle(frame1, a, 3, (255, 0, 0), LINE_THICKNESS)
            if blob['dir'] == 'left':
                cv2.line(frame1, a, b, (255, 255, 0), LINE_THICKNESS)
            else:
                cv2.line(frame1, a, b, (0, 255, 255), LINE_THICKNESS)

    cv2.imshow('orig', frame1)
    #cv2.imshow("preview", frame)

    key = cv2.waitKey(1)
    if key == 27:  # exit on ESC
        break

print("--------------------------------------------------VIDEO INFORMATION--------------------------------------------------------")
print("FPS = ",fps)
print("FRAME COUNT = ",frameCount)
print("Length of Video = ",vidTime)
print("Time = ", dateTime)

db.closingDatabase()
cv2.destroyAllWindows()
