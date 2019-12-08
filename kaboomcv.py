import numpy as np
import cv2
import os
import time
import win32gui
from PIL import ImageGrab
import math

from directkeys import PressKey, ReleaseKey, Z, X, C, F2, F12

queryLoc = "./query/"
bombQ = queryLoc+"bomb3.png"
bucketQ = queryLoc+"bucket3.png"

#below is a frame converted to seconds, assuming the game runs at 60 fps
frameTime = .0167

def main():
	#get Kaboom! window
	hwnd = getWindow()

	#make window active
	win32gui.SetForegroundWindow(hwnd)
	time.sleep(.5)

	#reset game
	PressKey(F2)
	time.sleep(.5)
	ReleaseKey(F2)
	print "game start"

	while 1:
		PressKey(C)
		ReleaseKey(C)

		#win32gui.SetForegroundWindow(hwnd)

		#get the current game state
		frame = getFrame(hwnd)
		
		#get the x position of the lowest bomb
		bomb, bomb2 = getBombPos(frame)

		if bomb[0] <= 10:
			print "===BREAK===\n"
			continue

		#get the bucket's leftmost and rightmost positions
		bxLeft, bxRight, bucketLength = getBucketPos(frame)

		makeMove(bxLeft,bxRight, bomb, bomb2, bucketLength)

		drawGuides(frame, bxLeft, bxRight, 282, bomb, bomb2)

		cv2.imshow("frame",frame)
		if cv2.waitKey(10) & 0xFF == ord('q'):
			cv2.destroyAllWindows()
			break

		print
	return

def getWindow():
	toplist, winlist = [], []
	def enum_cb(hwnd, results):
	    winlist.append((hwnd, win32gui.GetWindowText(hwnd)))
	win32gui.EnumWindows(enum_cb, toplist)

	kaboom = [(hwnd, title) for hwnd, title in winlist if 'kaboom!' in title.lower()]
	# just grab the hwnd for first window matching kaboom
	kaboom = kaboom[0]
	hwnd = kaboom[0]

	return hwnd

def getFrame(hwnd):
	bbox = win32gui.GetWindowRect(hwnd)

	frame = np.array(ImageGrab.grab(bbox).crop((32,40,555,404)))
	frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
	return frame

def getBucketPos(frame):
	#get the bucket template and its dimensions
	template = cv2.imread(bucketQ)
	tempDim = np.shape(template)[:2]
	h,w = tempDim

	#perform template matching
	res = cv2.matchTemplate(frame, template, 1)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

	#get the bounding box
	top_left = min_loc
	bottom_right = (top_left[0] + w, top_left[1] + h)
	
	return top_left[0], bottom_right[0], w

def getBombPos(frame):
	#get the bomb template and its dimensions
	template = cv2.imread(bombQ)
	tempDim = np.shape(template)[:2]
	h,w = tempDim

	# run template matching, get minimum val
	res = cv2.matchTemplate(frame, template, cv2.TM_SQDIFF_NORMED)
	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

	# create threshold from min val, find where sqdiff is less than thresh
	min_thresh = (min_val + 1e-2) * 2
	match_locations = np.where(res<=min_thresh)

	# draw template match boxes and find bottom-most bomb
	lowestBombPos = (0,0)
	lowestBomb2Pos = (0,0)
	boxColor = (0,255,255)
	boxThickness = 1
	for (x, y) in zip(match_locations[1], match_locations[0]):
	    cv2.rectangle(frame, (x, y), (x+w, y+h), boxColor, boxThickness)
	    if lowestBombPos[1] < y:
	    	lowestBomb2Pos = lowestBombPos
	    	lowestBombPos = (x,y)

	lowestBombPos = list(lowestBombPos)
	lowestBomb2Pos = list(lowestBomb2Pos)

	#place x pos at middle of bomb
	lowestBombPos[0] = lowestBombPos[0] + (w/2)
	lowestBomb2Pos[0] = lowestBomb2Pos[0] + (w/2)

	#place y pos at bottom of bomb
	lowestBombPos[1] = lowestBombPos[1] + h
	lowestBomb2Pos[1] = lowestBomb2Pos[1] + h

	return lowestBombPos, lowestBomb2Pos

def drawGuides(frame, bxLeft, bxRight, h, bomb, bomb2):
	frameDim = np.shape(frame)[:2]

	#draw lines surrounding bucket
	lineColor = (255,0,0)
	lineThickness = 2
	cv2.line(frame, (bxLeft, 0), (bxLeft, frameDim[0]), lineColor, lineThickness)
	cv2.line(frame, (bxRight, 0), (bxRight, frameDim[0]), lineColor, lineThickness)

	#draw line at box height
	lineColor = (255,0,0)
	lineThickness = 1
	cv2.line(frame, (0, h), (frameDim[1], h), lineColor, lineThickness)

	#draw line showing the x position of the bottom-most bomb
	bombX = bomb[0]
	lineColor = (0,0,255)
	lineThickness = 1
	cv2.line(frame, (bombX, 0), (bombX, frameDim[0]), lineColor, lineThickness)

	#draw line showing the y position of the bottom-most bomb
	bombY = bomb[1]
	lineColor = (0,0,255)
	lineThickness = 1
	cv2.line(frame, (0, bombY), (frameDim[1], bombY), lineColor, lineThickness)

	bomb2X = bomb2[0]
	bomb2Y = bomb2[1]

	#only occurs if there's 1 bomb on the screen
	if bomb2X <= 10:
		return

	#draw line showing the x position of the second bottom-most bomb
	lineColor = (255,0,255)
	lineThickness = 1
	cv2.line(frame, (bomb2X, 0), (bomb2X, frameDim[0]), lineColor, lineThickness)

	#draw line showing the y position of the second bottom-most bomb
	lineColor = (255,0,255)
	lineThickness = 1
	cv2.line(frame, (0, bomb2Y), (frameDim[1], bomb2Y), lineColor, lineThickness)

	return

def makeMove(bxLeft, bxRight, bomb, bomb2, bucketLength):
	print "bxLeft:%d\tbxRight:%d\tbomb:%s\tbomb2:%s"%(bxLeft, bxRight, bomb,bomb2)

	#bucket at height 282
	h = 282

	step = 0.5
	stepInc = 0.75

	#if the bottom-most bomb is nearly below 282
	#and the second bottom-most is in the same direction
	#we should go to second instead

	if (bxLeft > bomb[0]):
		if (bomb2[0] > 10):
			pos = determineSecondBomb(bxLeft, bomb, bomb2, 290, "left")
		else:
			print "no second bomb"
			pos = bomb[0]

		stepCount = bxLeft
		while (stepCount > pos):
			stepCount -= bucketLength
			step += stepInc

		heldTime = frameTime * step
		PressKey(Z)
		time.sleep(frameTime * step)
		ReleaseKey(Z)

		print "left\tstep = %f\theldTime = %f"%(step,heldTime)

	elif (bxRight < bomb[0]):
		if (bomb2[0] > 10):
			pos = determineSecondBomb(bxRight, bomb, bomb2, h, "right")
		else:
			print "no second bomb"
			pos = bomb[0]

		stepCount = bxRight
		while (stepCount < pos):
			stepCount += bucketLength
			step += stepInc

		heldTime = frameTime * step
		PressKey(X)
		time.sleep(heldTime)
		ReleaseKey(X)

		print "right\tstep = %f\theldTime = %f"%(step,heldTime)

	else:
		print "remain"

	return

def determineSecondBomb(bx, b1, b2, h, dir):
	#Note: Things > the height are below the bucket

	if (b1[1] >= h):
		if dir == "left":
			if (bx > b2[0]):
				print "using bomb2"
				return b2[0]
			else:
				print "using bomb1"
				return b1[0]

		if dir == "right":
			if (bx < b2[0]):
				print "using bomb2"
				return b2[0]
			else:
				print "using bomb1"
				return b1[0]
	
	print "using bomb1"
	return b1[0]

if __name__ == "__main__":
	main()