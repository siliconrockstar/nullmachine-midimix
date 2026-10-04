# name=Nullmachine Midimix

# this script is FOSS, no rights reserved

# incoming numbers are midi function, note number, note velocity
# note numbers for the midimix buttons are 1-24, this doc was amazingly helpful
# https://docs.google.com/document/d/1zeRPklp_Mo_XzJZUKu2i-p1VgfBoUWF0JKZ5CzX8aB0/edit
# to turn a light on or off send 144, the original incoming NT, and 127 (on) or 0 (off)

# mixer indices
# k/s - 8
# all bass - 12
# all mid - 16
# all hi - 20
# all guitar - 24
# all texture - 27
# all vox - 32

import midi # FL
import device # FL
import mixer # FL
import math # python

# a list of mixer track indexes, and the channel to route them to so they end up in master
# keys are 0 indexed, and the MidiMix buttons are in groups of three, so you can figure
# out which midiMix column you're in with math.floor((event.data1-1) / 3)
trackList = [ [3,8], [7,8], [12,28], [16,28], [20,28], [24,28], [27,28], [32,36] ];

queueSendTrackNumber = 35

# takes incoming midi data, looks at trackList, returns data describing an FL mixer track
#
# @return trackNumber, queueSendTrackNumber, masterSendTrackNumber, isTrackMuted, isTrackSolo, isTrackRoutedToQueue, isTrackRoutedToMaster
def getTrackData(event):
    
    print('Device name:',device.getName())
    
    print('Midi data from device:',event.midiId, event.midiChan, event.data1, event.data2)
    
    trackListIndex = math.floor((event.data1-1) / 3)
    print('Track list index:',trackListIndex)
  
    trackNumber = trackList[trackListIndex][0]
    print('Track number:', trackNumber)
  
    trackMasterSendTrackNumber = trackList[trackListIndex][1]
    print('Track master send track number:', trackMasterSendTrackNumber)
  
    isTrackMuted = mixer.isTrackMuted(trackNumber)
    print('Is track muted?',isTrackMuted)
  
    isTrackSolo = mixer.isTrackSolo(trackNumber)
    print('Is track solo?',isTrackSolo)
  
    isTrackRoutedToQueue = mixer.getRouteSendActive(trackNumber, queueSendTrackNumber)
    print('Is track routed to queue?', isTrackRoutedToQueue)
  
    isTrackRoutedToMaster = mixer.getRouteSendActive(trackNumber, trackMasterSendTrackNumber)
    print('Is track routed to master?', isTrackRoutedToMaster)

    return [trackNumber, trackMasterSendTrackNumber, isTrackMuted, isTrackSolo, isTrackRoutedToQueue, isTrackRoutedToMaster]
  

# mute button was pressed - this actually routes/unroutes the track to queue
def muteTrack(trackData, event):
    print('Mute button pressed')
    
    if (trackData[4] == 0):
        print('Track not routed to queue, sending to queue')
        mixer.setRouteTo(trackData[0], queueSendTrackNumber, 1)
        mixer.afterRoutingChanged()
        lightOn(event.data1)
    if (trackData[4] == 1):
        print('Track already queued, unsending')
        mixer.setRouteTo(trackData[0], queueSendTrackNumber, 0)
        lightOff(event.data1)
        mixer.afterRoutingChanged()


# solo button was pressed - this actually does toggle solo
def soloTrack(trackData, event):
    print('Solo button pressed')
       
    # toggle solo for the track
    mixer.soloTrack(trackData[0])
    
    # remember, isTrackSolo is the state *before* you toggled it above, set light status appropriately
    if (trackData[3] == 1):
        # turn off *all* solo lights, in case you had a track solo'd and solo'd another
        # this is an ugly kludge but good enough for our purposes I guess, still has an edge
        # case failure where solo lights stay on until you specifically turn off the soloed track
        # but just don't be a dumbass and it won't be a problem lol
        lightOff(2)
        lightOff(5)
        lightOff(8)
        lightOff(11)
        lightOff(14)
        lightOff(17)
        lightOff(20)
        lightOff(23) 
    else:
        lightOn(event.data1)
    

# rec arm button was pressed - in reality this routes/unroutes the track to master (but the real track number may vary based on trackList)
def armTrack(trackData, event):
    print('Rec Arm button pressed')
    
    if (trackData[5] == 0):
        print('Track not routed to master, sending to master')
        mixer.setRouteTo(trackData[0], trackData[1], 1)
        mixer.afterRoutingChanged()
        lightOn(event.data1)
    if (trackData[5] == 1):
        print('Track already master, unsending')
        mixer.setRouteTo(trackData[0], trackData[1], 0)
        lightOff(event.data1)
        mixer.afterRoutingChanged()


# turns a light on based on NT
def lightOn(note):
    print('Turning on light',note)
    device.midiOutMsg(144, 0, note, 127)


# turns a light off based on NT
def lightOff(note):
    print('Turning off light',note)
    device.midiOutMsg(144, 0, note, 0)  








# init the starting MidiMix light states, based on FL mixer track states
#
# 1,4,7... mute buttons that send to queue
# 2,5,8... solo buttons that solo
# 3,6,9... rec arm buttons that send to master
def OnInit():
    print('onInit called')
    
    for n in range(0,8): # 0-7
        print('checking trackList', n);  # first is track number, second is master out number, queue out number is constant
        
        # check mute button / is track sent to queue
        if (mixer.getRouteSendActive(trackList[n][0], queueSendTrackNumber)): # track is routed to queue
            lightOn((3 * n) + 1)
        else:
            lightOff((3 * n) +1)
        
        # check solo button / is track solo'data
        if (mixer.isTrackSolo(trackList[n][0])): # track is solo'd
            lightOn((3 * n) + 2)
        else:
            lightOff((3 * n) + 2)
            
        # rec arm / send to master
        if (mixer.getRouteSendActive(trackList[n][0], trackList[n][1])): # track is routed to master
            lightOn((3 * n) + 3)
        else:
            lightOff((3 * n) + 3)

    
# handle incoming midi messages
def OnMidiMsg(event):

    # disregard data from the knobs, and button releases
    if (event.midiId != 144 or event.data1 > 24):
        event.handled = False;
        return;
	
    trackData = getTrackData(event)
    print('trackData:',trackData)
  
    # figure out if it was a mute, solo, or rec arm button press. Buttons are in threes, so use modulus
    # 0 = mute, 1 = solo, 2 = rec arm
    offset = (event.data1 - 1) % 3;
    print('Button type (0 = mute, 1 = solo, 2 = rec arm):',offset)
  
    # not the prettiest but Python is weird with switches apparently
    if (offset == 0):
        muteTrack(trackData, event) # this actually routes to queue track
    elif (offset == 1):
        soloTrack(trackData, event) # this actually *does* solo the track
    elif (offset == 2):
        armTrack(trackData, event) # this actually routes to master track
    else:
        # you shouldn't ever end up here :/
        print('ERROR: event was not handled properly')
	
    event.handled = True;
    print()
    return



