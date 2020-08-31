#!/usr/bin/env python3

# GarageBand drum extractor gbextractor v1.0 29 Aug 2020
# Copyright (C) 2020 MisplacedDevelopment 
# See LICENSE for license information (Apache 2)

# Comes with the following dependencies:
# bitstring (3.1.7) - Simple construction, analysis and modification of binary data. https://github.com/scott-griffiths/bitstring
# MIDIUtil (1.2.1) - A pure python library for creating multi-track MIDI files. https://github.com/MarkCWirt/MIDIUtil

import xml.etree.ElementTree as ET
import dialogs
import os
import base64
import sys
import console
from enum import Enum
from bitstring import ConstBitStream
import time
import string
from midiutil import MIDIFile

bWriteToFile = False
bDebug = False
recordHash = dict()

WORKING_DIR = "GB_Extract_" + time.strftime("%Y%m%d-%H%M%S")
TEMPO_OFFSET = 0x550
TIME_SIGNATURE_OFFSET = 0x7D0
BASE_TIME = 0x9600
VALID_BLOCKS = [b"\x2e\x03\x41",
                b"\x3c\x03\x41", 
                b"\x64\x03\x41"]

MIDIEventType = Enum('MIDIEventType', 'NOTE_ON NOTE_OFF')

canBePrinted = bytes(string.ascii_letters + string.digits + string.punctuation, 'ascii')

class MIDISection:
  def __init__(self, label, associatedMidiID, recordNumber):
    self.label = label.decode("utf-8")
    self.associatedMidiID = associatedMidiID
    self.bHasMIDI = False
    self.midiData = None
    self.recordNumber = recordNumber

class MIDIEvent:
  def __init__(self, type, time, velocity, note, articulation, offMode):
    self.type = type
    self.time = time
    self.note = note
    self.velocity = velocity
    self.time = time
    
def quitWithError(errorString):
  print(errorString)
  console.hud_alert(errorString, 'error', 2)
  sys.exit(1)

def dumphex(dataLength, s):
  originalPosition = s.pos
  byteCounter = 0
  hexDump = ""
  for lineOffset in range(0, dataLength, 16):
    hexString = ""
    asciiString = ""
    for byte in s.readlist("16*uint:8"):      
      if(byte in canBePrinted):
        asciiString += chr(byte)
      else:
        asciiString += "."
        
      hexString += "{:02X} ".format(byte)
      
      byteCounter += 1
      if (byteCounter == dataLength):
        break        
    hexDump += "0x{:08X} | {:48}| {:16} |\n".format(lineOffset, hexString, asciiString)
  s.pos = originalPosition
  print(hexDump)
  

if bDebug: print("Creating working directory {} in {}".format(WORKING_DIR, os.getcwd()))

try:
  os.mkdir(WORKING_DIR)
except OSError:
  quitWithError("ERROR: Could not create working directory")

os.chdir(WORKING_DIR)

# Should we redirect stdout to a log file?
if bWriteToFile:
  origStdout = sys.stdout
  newStdout = open("GB_Extract_Log.txt", 'w')
  sys.stdout = newStdout

# Show iOS file picker to select GB file
fp = dialogs.pick_document(types=["public.item"])

if (fp != None):
  pathToGBFile = os.path.join(fp, "projectData")
else:
  quitWithError("ERROR: No file selected.")
  
if os.path.exists(pathToGBFile):
  parseDataFile = ET.parse(pathToGBFile)
  xmlRoot = parseDataFile.getroot()
else:
  quitWithError("ERROR: File does not exist: {}".format(pathToGBFile))

# Decode the base64 data in the projectData file
nsData = xmlRoot.find(".//*[key='NS.data']/data")
encodedText = nsData.text
try:
  decodedData = base64.b64decode(encodedText)
  with open("decoded.bin","wb") as fp:
    fp.write(decodedData)
except Exception as ex:
  print(str(ex))
  quitWithError("ERROR: Failed to decode data")

# Open the decoded binary file for parsing
s = ConstBitStream(filename='decoded.bin')
s.pos = 0

if bDebug: dumphex(256, s)

# Pull out the tempo
s.pos = TEMPO_OFFSET
preciseBPM = s.read('uintle:24')
songTempo = preciseBPM/10000
if bDebug: print("Tempo BPM is {}".format(songTempo))

# Pull out the time signature 
s.pos = TIME_SIGNATURE_OFFSET
numerator = s.read('uintle:8')
denominator = s.read('uintle:8')
if bDebug: print("Time signature is {}/{}".format(numerator, 2**denominator))

# Generate an ordered list of offsets pointing to bits of the 
# binary data that we are interested in
offset_list = list(s.findall('0x71537645', bytealigned = True)) #qSvE
offset_list.extend(list(s.findall('0x7165534D', bytealigned = True))) #qeSM
#   offset_list.extend(list(s.findall('0x6B617254', bytealigned = True)))
#   offset_list.extend(list(s.findall('0x74536e49', bytealigned = True)))
#   offset_list.extend(list(s.findall('0x74537854', bytealigned = True)))
sorted_offset_list = sorted(offset_list)

for thisOffset in sorted_offset_list:
  s.pos = thisOffset
  
  if bDebug:
    print("Byte offset {}".format(thisOffset))
    dumphex(64, s)
  
  recordType, recordSubType, recordNumber, recordMidiID, dataLength = s.readlist("pad:32, uintle:16, uintle:32, uintle:32, uintle:32, 2*pad:32, pad:16, uintle:32, pad:32")
  
  # We are now at the start of the data so save this position for later...
  dataStart = s.pos
  
  if bDebug:
    print("Data length is: {} Type is: {} Record no: {} MIDI ID: {}".format(dataLength, recordType, recordNumber, recordMidiID))
    dumphex(dataLength, s)

  # Test for a MIDI block header
  blockType = s.read("bytes:3")

  if bDebug: print("BlockType is {}".format(blockType.hex()))
  
  # Is this a section header?
  if(recordType == 2 and
    (blockType in VALID_BLOCKS)):
    associatedMidiID, sectionNameLength = s.readlist("pad:40, uintle:32, pad:32, uintle:16")
    # Create a key from the record + associated midi ID
    hashKey = "{}:{}".format(str(recordNumber), str(associatedMidiID))
    sectionName = s.read("bytes:{}".format(str(sectionNameLength)))
    
    if bDebug: print("Section name is {}, hash key is {}".format(sectionName, hashKey))
      
    existingRecord = recordHash.get(hashKey)
    # Validation - The key should be unique
    if(existingRecord != None):
      quitWithError("ERROR: Found second record for key {}".format(hashKey))

    midiSection = MIDISection(sectionName, associatedMidiID, recordNumber)
    recordHash[hashKey] = midiSection
  elif(recordType == 1): # MIDI data block
    hashKey = str(recordNumber) + ":" + str(recordMidiID)
    if bDebug: print("Hash key is {}".format(hashKey))
    # Have we seen a section header with this MIDI ID?
    midiSection = recordHash.get(hashKey)
    if(midiSection != None):
      if bDebug: print("Found MIDI data for section {}".format(midiSection.label))
      # Create a new MIDIFile object to store the notes for this MIDI section
      midiFileData = MIDIFile(numTracks=1, eventtime_is_ticks=True)
      midiFileData.addTempo(0, 0, songTempo)
      trackName = midiSection.label + "-" + str(recordNumber) + "_" + str(recordMidiID)
      midiFileData.addTrackName(0, 0, trackName)
      
      s.pos = dataStart
      midiEvent = None
      lastMIDIEvent = None
      # Optionally set this to None to use the first note time as the base time
      baseTime = BASE_TIME
      while True:
        # Read in the next command byte
        midiCmd = s.read('uintle:8')
        if bDebug: print('Command is {} ({})'.format(midiCmd, hex(midiCmd)))

        if(midiCmd >= 0x90 and midiCmd <= 0x9F): # Note ON event
          # 0x00000000 | 90 00 00 00 00 96 00 00 00 00 00 7D 24 00 00 00 | ...........}$...
          # 0x00000010 | 80 00 00 00 00 00 00 89 00 00 00 00 F0 00 00 00 | ................

          # If we have a midiEvent that has not been written yet then
          # this implies we have not seen the duration command, which
          # is unexpected
          if(midiEvent != None):
            quitWithError("ERROR: Outstanding MIDI event not written")

          # Record the midiEvent based on the set of bytes read in for this note ON 
          midiEvent = MIDIEvent(MIDIEventType.NOTE_ON, *s.readlist('pad:24, uintle:32, pad:24, uintle:8, uintle:8, pad:8, uintle:16, uintle:16, pad:40'))
        elif (midiCmd == 0x89): # Set note duration event
          # 0x00000580 | 40 00 00 00 00 00 00 89 00 00 00 00 F0 00 00 00 | @...............
          # 0x00000590 | 00 00 00 00 00 00 00 A7 00 00 00 00 00 00 00 00 | ................
          # 0x000005A0 | 90 00 00 00 53 BD 00 00 00 00 00 73 24 00 00 00 | ....S......s$...

          # An 0x89 event should follow a note on event, we should therefore have
          # an outstanding midiEvent
          if(midiEvent != None):
            s.read("pad:32")
            # Duration spans at least 3, probably 4 bytes.  We'll go for 4 for now!
            midiEvent.duration = s.read("uintle:32")

            if(baseTime == None):
              baseTime = midiEvent.time
              
            bAddNote = True
            
            # Try and work around bug https://github.com/MarkCWirt/MIDIUtil/issues/24
            if(lastMIDIEvent != None):
              if(lastMIDIEvent.note == midiEvent.note and
                 lastMIDIEvent.time == midiEvent.time):
                 bAddNote = False

            if(bAddNote):
              midiFileData.addNote(0, 0, midiEvent.note, midiEvent.time - baseTime, midiEvent.duration, midiEvent.velocity)
              if bDebug: print(midiEvent.__dict__)
              lastMIDIEvent = midiEvent
              
            midiEvent = None
            midiSection.bHasMIDI = True
          else:
            # We seem to have found a set duration command without having seen a note-on event
            quitWithError("ERROR: No MIDI event to write")
        elif (midiCmd == 0xA8 or midiCmd == 0xA7):
          # Don't know what this command is for...
          # 0x00000740 | 08 00 03 03 00 00 00 A8 00 00 00 00 01 00 1C 00 | ................
          # 0x00000750 | 90 00 00 00 10 B3 00 00 00 00 00 7B 24 00 00 00 | ...........{$...
          s.read("bytes:8")
        elif (midiCmd >= 0x70 and midiCmd <= 0x7F):
          # 0x7x appears to be some kind of state reset at the start of a block, possibly for looping purposes
          s.read("bytes:31")
        elif (midiCmd == 0xF1):
          if bDebug: print("End of buffer")
          break
        elif ((midiCmd >= 0x30 and midiCmd <= 0x3F) or 
               midiCmd == 0x60 or 
               midiCmd == 0x11 or 
               midiCmd == 0x12):
          # These tend to be at the start of blocks we are not interested in
          if bDebug: print("Unknown bytes: {}".format(hex(midiCmd)))
          break
        elif (midiCmd >= 0x00 and midiCmd <= 0x0F):
          # There is sometimes a run of usually null bytes after 0x89.  I don't know what they are
          # for so skip over them
          if bDebug: print("Inter-cmd bytes {}".format(hex(midiCmd)))
          s.read('bytes:6')
        else:
          # Not seen this command byte before so dump some context for debugging
          # purposes then exit
          s.pos -= (64 * 8)
          dumphex(68, s)
          quitWithError("Unrecognised command: {}".format(midiCmd))
          break # Unreachable

        # Check we have not exceeded the length of the data in this block
        bufferUsed = s.pos - dataStart
        totalBufferSize = (dataLength * 8)
        if bDebug: print("Buffer used so far: {} out of: {}".format(bufferUsed, totalBufferSize))
        if(bufferUsed > totalBufferSize):
          quitWithError("ERROR: Went past end of buffer.")
      
      if (midiSection.bHasMIDI):
        midiSection.midiData = midiFileData

for k,v in recordHash.items():
  if bDebug: print("Key {} with value {} ".format(k, v.label))
  midiFileData = v.midiData
  if(midiFileData != None):
    filename = "{}-{}_{}.mid".format(v.label, str(v.recordNumber), str(v.associatedMidiID))
    with open(filename, "wb") as output_file:
      print("Writing MIDI to {}".format(filename))
      midiFileData.writeFile(output_file)

if bWriteToFile:
  newStdout.close()
  sys.stdout = origStdout

console.hud_alert("File processing complete",'success', 1)