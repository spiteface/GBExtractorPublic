#!/usr/bin/env python3

# GarageBand MIDI extractor gbextractor v2.0a 6th Feb 2021
# Copyright (C) 2020, 2021 MisplacedDevelopment 
# See LICENSE for license information (Apache 2)

# Comes with the following dependencies:
# bitstring (3.1.7) - Simple construction, analysis and modification of binary data. https://github.com/scott-griffiths/bitstring
# MIDIUtil (1.2.1) - A pure python library for creating multi-track MIDI files. https://github.com/MarkCWirt/MIDIUtil
# https://midiutil.readthedocs.io/en/1.2.1/class.html#classref

import xml.etree.ElementTree as ET
import os
import base64
import sys
from bitstring import ConstBitStream
import time
import string
from midiutil import MIDIFile

class MIDISection:
  def __init__(self, label, associatedMidiID, recordNumber):
    self.label = label
    self.associatedMidiID = associatedMidiID
    self.bHasMIDI = False
    self.midiData = None
    self.recordNumber = recordNumber

class MIDIEvent:
  def __init__(self, time, velocity, note, unknown):
    self.time = time
    self.note = note
    self.velocity = velocity
    self.trackUsed = 0
   
class TwoPartEvent:
  def __init__(self, time, valueA, valueB):
    self.time = time
    self.valueA = valueA
    self.valueB = valueB
         
def quitWithError(errorString):
  print(errorString)
  if bIsPythonista:
    console.hud_alert(errorString, 'error', 2)
  sys.exit(1)
  
def createKey(partA, partB):
  return "{}:{}".format(str(partA), str(partB))

def debugPrint(stringToPrint):
  if(bDebug): print(stringToPrint)
  
def readTwoPartEvent(bitStream):
  bitStream.read("bytes:3")
  eventTime = bitStream.read("uintle:32")
  bitStream.read("bytes:3")
  eventValueA = bitStream.read("uintle:8")
  eventValueB = bitStream.read("uintle:8")
  debugPrint("eventValueA {}({}) eventValueB {}({})".format(eventValueA, hex(eventValueA), eventValueB, hex(eventValueB)))
  bitStream.read("bytes:3")  
  return TwoPartEvent(eventTime, eventValueA, eventValueB)

def dumphex(dataLength, s):
  originalPosition = s.pos
  byteCounter = 0
  hexDump = ""
  for lineOffset in range(0, dataLength, 16):
    hexString = ""
    asciiString = ""
    
    bytesToRead = min(16, dataLength - lineOffset)
    
    for byte in s.readlist("{}*uint:8".format(bytesToRead)):      
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

WORKING_DIR = "GB_Extract_" + time.strftime("%Y%m%d-%H%M%S")
# These offsets are in bits!
TEMPO_OFFSET = 0x550 # 0xAA bytes
TIME_SIGNATURE_OFFSET = 0x7D0 # 0xFA bytes
TIME_SIGNATURE_OFFSET_2 = 0x1DB6
BASE_TIME = 0x9600
VALID_BLOCKS = [b"\x2e\x03\x41",
                b"\x3c\x03\x41", 
                b"\x64\x03\x41",
                b"\x2e\x03\x01"]

####################################
### User-configurable parameters ###
####################################

## Pitch ##

# Set to True to multiply all pitch bends by pitchBendMultiplier.  Use this with
# instruments such as the playable guitars which do not scale pitch bend values 
# correctly when saved.
bOverridePitchBend = False
pitchBendMultiplier = 24
# TODO: By default all instruments have the pitch bend override applied to them
# If this list is not empty then it is used to target this to specific instruments
# You can use a regular expression here.
pitchBendInstFilter = ["Grand Piano"]

## Track split ##

# If set to True then each note in a MIDI file will be assigned its own track
# number.  You can use this to split out drum stems to their own tracks, for example.
bUniqueTracks = False
# If you know that you only have n instruments in your kit then you can set this number
# to limit the number of tracks created.  If more notes are found than tracks then new notes are
# added in a round-robin way, starting again from track zero.  The theoretical max value
# is 128.
if(bUniqueTracks):
  trackLimit = 16
else:
  trackLimit = 1
# If bRenameTracks set to True then split tracks are given custom names based on the note->name mapping below,
# otherwise the note number is used as part of the track name. 
# TODO: Make this automatic based on the instrument as different instruments have slightly
# different mappings
# TODO: Use a list to target splitting to specific instruments/tracks
bRenameTracks = True
trackMap = {35:'Kick',
            36:'Kick2',
            37:'Sidestick',
            38:'Snare',
            39:'Clap',
            32:'RimShot',
            40:'Rimshot',
            41:'TomFloorLo',
            42:'HiHatClosed',
            43:'TomFloorHi',
            31:'PedalHiHat',
            33:'PedalHiHat',
            44:'PedalHiHat',
            45:'TomLo',
            46:'HiHatOpen',
            47:'TomLoMid',
            48:'TomHiMid',
            49:'Crash',
            50:'TomHi',
            51:'Ride',
            52:'RideChina',
            53:'RideBell',
            54:'Tambourine',
            55:'Splash',
            56:'Cowbell',
            57:'Crash2',
            58:'Vibraslap',
            59:'Ride2',
            60:'BongoHi',
            61:'BongoLo',
            62:'CongaMuteHi',
            63:'CongaOpenHi',
            64:'CongaLo',
            65:'TimbaleHi',
            66:'TimbaleLo',
            67:'AgogoHi',
            68:'AgogoLo',
            69:'Cabasa',
            70:'Maracas',
            71:'WhistleShort',
            72:'WhistleLong',
            73:'GuiroShort',
            74:'GuiroLong',
            75:'Claves',
            76:'WoodBlockHi',
            77:'WoodBlockLo',
            78:'CuicaMute',
            79:'CuicaOpen',
            80:'TriangleMute',
            81:'TriangleOpen'
            }

## MIDI start time ##

# Set this to None if you want to remove all space before the first note so that
# the MIDI starts exactly with the first note.
baseTime = BASE_TIME
      
## Debugging ##

# Turn debugging on or off
bDebug = False
# Choose whether to redirect stdout to a log file.  You would normally want to do this
# on iOS
bWriteToFile = False
# If this is set then the whole binary is dumped as hex text at the end of processing
bDumpFile = False

########################################
### END User-configurable parameters ###
########################################

# INTERNAL NOTE: Here is the instrument identifier, still need to find where the
# difference between keyboard and touch interface is kept...
#0x00000070 | 00 00 A0 06 20 49 6E 73 74 20 31 00 6C 20 53 74 | .....Inst.1.l.St |
#0x00000080 | 72 69 70 29 00 00 00 00 00 00 00 00 00 00 00 00 | rip)............ |
#0x00000090 | 00 00 00 00 4C 10 00 00 00 00 08 09 00 00 06 00 | ....L........... | <- 4C = instrument, e.g. CF = pipa
#0x000000A0 | 49 6E 73 74 20 31 2A 00 00 FF 00 01 00 00 00 00 | Inst.1*......... |

trackCounter = 0
trackDict = dict()
recordHash = dict()

try:
  import dialogs
  import console
  bIsPythonista = True
  debugPrint("Running inside of Pythonista")
except:
  bIsPythonista = False
  debugPrint("Running outside of Pythonista")

canBePrinted = bytes(string.ascii_letters + string.digits + string.punctuation, 'ascii')

debugPrint("Creating working directory {} in {}".format(WORKING_DIR, os.getcwd()))

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

if bIsPythonista: 
  # Show iOS file picker to select GB file
  fp = dialogs.pick_document(types=["public.item"])
else:
  if(len(sys.argv) == 2):
    fp = sys.argv[1]
  else:
    quitWithError("ERROR: Expects a single argument which is the path to the GB project.band directory")

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

if bDebug: dumphex(0x800, s)

# Pull out the tempo, offset is number of BITS
s.pos = TEMPO_OFFSET
preciseBPM = s.read('uintle:24')
songTempo = preciseBPM/10000
debugPrint("Tempo BPM is {} ({})".format(songTempo, hex(preciseBPM)))

# Pull out the time signature 
s.pos = TIME_SIGNATURE_OFFSET
numerator = s.read('uintle:8')
denominator = s.read('uintle:8')
debugPrint("Time signature is {}/{}".format(numerator, 2**denominator))

# Generate an ordered list of offsets pointing to bits of the 
# binary data that we are interested in
offset_list = list(s.findall('0x71537645', bytealigned = True)) #qSvE
offset_list.extend(list(s.findall('0x7165534D', bytealigned = True))) #qeSM

#offset_list.extend(list(s.findall('0x6B617254', bytealigned = True)))
#offset_list.extend(list(s.findall('0x74536e49', bytealigned = True)))
#offset_list.extend(list(s.findall('0x74537854', bytealigned = True)))
#offset_list.extend(list(s.findall('0x69766e45', bytealigned = True)))
sorted_offset_list = sorted(offset_list)

for thisOffset in sorted_offset_list:
  s.pos = thisOffset
  
  if bDebug:
    debugPrint("Byte offset {}".format(thisOffset))
    dumphex(64, s)
  
  recordType, recordSubType, recordNumber, recordMidiID, dataLength = s.readlist("pad:32, uintle:16, uintle:32, uintle:32, uintle:32, 2*pad:32, pad:16, uintle:32, pad:32")
  
  # We are now at the start of the data so save this position for later...
  dataStart = s.pos
  
  if bDebug:
    debugPrint("Data length is: {} Type is: {} Record no: {} MIDI ID: {}".format(dataLength, recordType, recordNumber, recordMidiID))
    if(recordType == 1 or recordType == 5): dumphex(dataLength, s)

  # Test for a MIDI block header
  blockType = s.read("bytes:3")

  debugPrint("BlockType is {}".format(blockType.hex()))
  
  # Is this a section header?
  if(recordType == 2 and
    (blockType in VALID_BLOCKS)):
    associatedMidiID, sectionNameLength = s.readlist("pad:40, uintle:32, pad:32, uintle:16")
    # Create a key from the record + associated midi ID
    hashKey = createKey(str(recordNumber), str(associatedMidiID))
    origSectionName = s.read("bytes:{}".format(str(sectionNameLength))).decode("utf-8")
    
    # Strip out filename unfriendly characters
    sectionName = "".join(thisChar for thisChar in origSectionName if (thisChar.isalnum() or thisChar in "._- "))
    
    debugPrint("Section name is {} (orig {}), hash key is {}".format(sectionName, origSectionName, hashKey))
      
    existingRecord = recordHash.get(hashKey)
    # Validation - The key should be unique
    if(existingRecord != None):
      quitWithError("ERROR: Found second record for key {}".format(hashKey))

    midiSection = MIDISection(sectionName, associatedMidiID, recordNumber)
    recordHash[hashKey] = midiSection
  elif(recordType == 1): # MIDI data block
    hashKey = createKey(str(recordNumber), str(recordMidiID))    
    debugPrint("Hash key is {}".format(hashKey))    
    # Have we seen a section header with this MIDI ID?
    midiSection = recordHash.get(hashKey)
    if(midiSection != None):
      debugPrint("Found MIDI data for section {}".format(midiSection.label))
        
      # Create a new MIDIFile object to store the notes for this MIDI section
      midiFileData = MIDIFile(numTracks=trackLimit, ticks_per_quarternote=960, eventtime_is_ticks=True)
      midiFileData.addTimeSignature(0, 0, numerator, denominator, clocks_per_tick = 24, notes_per_quarter=8)
      midiFileData.addTempo(0, 0, songTempo)
      midiFileData.addTrackName(0, 0, midiSection.label + "-" + str(recordNumber) + "_" + str(recordMidiID))
      
      trackCounter = 0
      trackDict = dict()
      midiEvent = None
      lastMIDIEvent = None
            
      s.pos = dataStart     
      
      while True:
        # Read in the next command byte
        midiCmd = s.read('uintle:8')
        debugPrint('Command is {} ({})'.format(midiCmd, hex(midiCmd)))
        
        midiChl = midiCmd & 0x0F
        
        if(midiCmd >= 0x90 and midiCmd <= 0x9F): # Note on/off event
          # 0x00000000 | 90 00 00 00 00 96 00 00 00 00 00 7D 24 00 00 00 | ...........}$...
          # 0x00000010 | 80 00 00 00 00 00 00 89 00 00 00 00 F0 00 00 00 | ................
          
          midiEvent = MIDIEvent(*s.readlist('pad:24, uintle:32, pad:24, uintle:8, uintle:8, uintle:24'))
          s.read("bytes:7")
          
          midiCmd = s.read('uintle:8')
          if(midiCmd >= 0x80 and midiCmd <= 0x8F): # Note Off event then set note duration event
            # 0x00000580 | 40 00 00 00 00 00 00 89 00 00 00 00 F0 00 00 00 | @...............
            # 0x00000590 | 00 00 00 00 00 00 00 A7 00 00 00 00 00 00 00 00 | ................
            # 0x000005A0 | 90 00 00 00 53 BD 00 00 00 00 00 73 24 00 00 00 | ....S......s$...

            extendedBytes = s.read("uintle:32")
            # Duration spans at least 3, probably 4 bytes.  We'll go for 4 for now!
            midiEvent.duration = s.read("uintle:32")
            
            if(baseTime == None):
              baseTime = midiEvent.time
               
            bAddNote = True
    
            # Try and work around duplicate note bug https://github.com/MarkCWirt/MIDIUtil/issues/24
            if(lastMIDIEvent != None):
              if(lastMIDIEvent.note == midiEvent.note and
                 lastMIDIEvent.time == midiEvent.time):
                 bAddNote = False
                  
            if(bAddNote):
              # Default track zero
              trackToUse = 0
              if(bUniqueTracks):
                trackToUse = trackDict.get(midiEvent.note)
                if(trackToUse == None):
                  trackToUse = trackCounter
                  trackDict[midiEvent.note] = trackToUse
                  noteName = None
                  
                  # Track name appended with mapped instrument name or MIDI note number
                  if(bRenameTracks):
                    noteName = trackMap.get(midiEvent.note)
                  
                  if(noteName == None):
                    noteName = str(midiEvent.note)
                    
                  trackName = noteName + "_" + midiSection.label + "-" + str(recordNumber) + "_" + str(recordMidiID) + "_" + noteName
                  midiFileData.addTrackName(trackToUse, 0, trackName)
                  trackCounter += 1
                  
                  if(trackCounter >= trackLimit):
                    debugPrint("Resetting track counter")
                    trackCounter = 0
                    
                  debugPrint("trackToUse {} {}".format(trackToUse, trackName))
                        
              midiFileData.addNote(trackToUse, midiChl, midiEvent.note, midiEvent.time - baseTime, midiEvent.duration, midiEvent.velocity)
              debugPrint(midiEvent.__dict__)
              midiEvent.trackUsed = trackToUse
              lastMIDIEvent = midiEvent
              midiSection.bHasMIDI = True
                          
            if(extendedBytes > 0):
              debugPrint('Found extended bytes {} '.format(hex(extendedBytes)))
              
          else: # Did not find expected 0x8x before note duration data
            quitWithError('ERROR: Unknown command {} ({})'.format(midiCmd, hex(midiCmd)))
        elif ((midiCmd >= 0x00 and midiCmd <= 0x0A) or midiCmd == 0xFF): # internal commands/screen elements?
          # 00 00 00 00 00 00 01 B5 00 00 00 00 00 00 00 00. button on? 01 on 02 off
          s.read('bytes:6')
          midiCmd = s.read('uintle:8')
          if (midiCmd != 0xA8 and midiCmd != 0xA7 and midiCmd != 0xB5):
            debugPrint('WARN: Unknown command {} ({})'.format(midiCmd, hex(midiCmd)))            
          s.read('bytes:8')
        elif (midiCmd >= 0x20 and midiCmd <= 0x2F): # cc bank change ?
          # 20 3D 01 00 00 00 00 A8 00 00 00 00 A5 83 00 00
          s.read("bytes:15")
        elif (midiCmd == 0x40): # cc sustain ?
          # 40 2F 01 00 00 00 00 A8 00 00 00 00 A2 83 00 00
          s.read("bytes:15")
        elif (midiCmd >= 0x50 and midiCmd <= 0x5F): # cc general purpose controller, synth knobs 0x00-0x0b pads CA-CD
          # 50 40 00 00 00 96 00 00 10 58 39 0E 00 01 00 01 # knob top left synth 00 
          # 50 40 00 00 00 96 00 00 45 B6 D3 0C 01 01 00 01 # knob bottom left 01
          # 50 40 00 00 00 96 00 00 00 00 00 7F 02 01 00 01 # knob top right 02
          # 50 40 00 00 00 96 00 00 00 00 00 00 07 01 00 01 # knob bottom right 07
          
          if (midiCmd >= 0x51 and midiCmd <= 0x5F): # I do not think this is actually per-channel so validate this
            quitWithError("Unexpected 0x5x command {} ({})".format(midiCmd, hex(midiCmd)))
          
          thisEvent = readTwoPartEvent(s)
          
          # It feels like program change, e.g. patch change in synth is implemented like this but GB does not respond
          # so disabling this for now.
          if(False and thisEvent.valueB & 0xC0 == 0xC0):
            ctrlChl = thisEvent.valueB & 0x0F
            debugPrint("Adding program change")
            midiFileData.addProgramChange(0, ctrlChl, thisEvent.time - baseTime, thisEvent.valueA)
        
        elif (midiCmd >= 0x70 and midiCmd <= 0x7F): # can be triggered by manually adding and moving percussion with smart drums while recording
          # 70 00 00 00 00 96 00 00 00 00 00 01 36 00 00 00
          # 09 00 02 06 00 00 00 A8 00 00 00 00 21 00 09 00
          debugPrint("0x7x MIDI command {} ({})".format(midiCmd, hex(midiCmd)))            
          s.read("bytes:31")
        elif (midiCmd >= 0x80 and midiCmd <= 0x8F): # Do not know what this is. Seen with synth, not a note-off though as it uses the same bytes each time.
          # 80 AE 01 00 00 00 00 A8 00 00 00 00 A5 83 00 00
          s.read("bytes:15")
        elif (midiCmd >= 0xA0 and midiCmd <= 0xAF): # polyphonic key pressure unsupported in MIDIUtil API :(
          # A0 11 01 00 00 00 00 A8 00 00 00 00 A5 83 00 00
          debugPrint("Polyphonic key pressure (unsupported) {}({})".format(midiCmd, hex(midiCmd)))
          s.read("bytes:15")
        elif (midiCmd >= 0xB0 and midiCmd <= 0xBF): # MIDI CC
          # B0 40 00 00 5D 9D 00 00 00 00 00 00 40 00 00 01 cc sustain off 00 40 ch 0 40 is cc val
          # B0 40 00 00 5D 9D 00 00 00 00 00 7F 40 00 00 01 cc sus on 7F 40 ch 0
          # 0 (to 63) is off. 127 (to 64) is on.
          # B0 40 00 00 40 9A 00 00 00 00 00 00 01 00 00 01 cc mod wheel zero
          
          thisEvent = readTwoPartEvent(s)
          midiFileData.addControllerEvent(0, midiChl, thisEvent.time - baseTime, thisEvent.valueB, thisEvent.valueA)
          midiSection.bHasMIDI = True
        elif (midiCmd >= 0xC0 and midiCmd <= 0xCF): # Should be program change but don't think it is 
          # C0 03 01 00 00 00 00 A8 00 00 00 00 A5 83 00 00
          s.read("bytes:15")
        elif (midiCmd >= 0xD0 and midiCmd <= 0xDF): # channel pressure
          # D3 40 00 00 81 A1 00 00 00 00 00 00 00 00 00 01 channel pressure 0
          # D5 40 00 00 C4 BA 00 00 00 00 00 1F 1F 00 00 01 channel pressure 1F
          
          thisEvent = readTwoPartEvent(s)
          
          if(thisEvent.valueA != thisEvent.valueB):
            quitWithError("Pressure value A ({}) != Pressure value B ({})".format(thisEvent.valueA, thisEvent.valueB))

          # This method does not appear to be documented but is in the MIDIUtil unit tests and the
          # changelog says it was added in 1.2.1          
          midiFileData.addChannelPressure(0, midiChl, thisEvent.time - baseTime, thisEvent.valueA)
          midiSection.bHasMIDI = True       
        elif (midiCmd >= 0xE0 and midiCmd <= 0xEF): # pitch bend
          # E8 40 00 00 19 A0 00 00 00 00 00 40 17 00 00 01 pitch bend ch 8 val 40 17
          # E4 40 00 00 41 9A 00 00 00 00 00 40 00 00 00 01 pitch bend 0
          
          thisEvent = readTwoPartEvent(s)
          
          pb = 0
          pb = (pb << 7) + (thisEvent.valueA & 0x7F)
          pb = (pb << 7) + (thisEvent.valueB & 0x7F)
          pitchWheelValue = -8192 + pb

          if(bOverridePitchBend):
            pitchWheelValue *= pitchBendMultiplier
            # Correct any overshoot
            if(pitchWheelValue < -8192): pitchWheelValue = -8192
            if(pitchWheelValue > 8191): pitchWheelValue = 8191
            debugPrint("Adjusted pitchWheelValue is: {}({})".format(pitchWheelValue, hex(pitchWheelValue)))

          midiFileData.addPitchWheelEvent(0, midiChl, thisEvent.time - baseTime, pitchWheelValue)
          midiSection.bHasMIDI = True
        elif (midiCmd == 0xF1):
          debugPrint("Found end of buffer")
          break
        elif ((midiCmd >= 0x30 and midiCmd <= 0x3F) or
               midiCmd == 0x60 or 
               midiCmd == 0x11 or 
               midiCmd == 0x12):
          # These tend to be at the start of blocks we are not interested in
          debugPrint("Unknown bytes: {}".format(hex(midiCmd)))
          break
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
        debugPrint("Buffer used so far: {} out of: {}".format(bufferUsed, totalBufferSize))
        
        if(bufferUsed > totalBufferSize):
          quitWithError("ERROR: Went past end of buffer.")
          
        if(bufferUsed == totalBufferSize):
          debugPrint("Used full buffer")
          break
      
      if (midiSection.bHasMIDI):
        midiSection.midiData = midiFileData

for k,v in recordHash.items():
  debugPrint("Key {} with value {} ".format(k, v.label))
  midiFileData = v.midiData
  if(midiFileData != None):
    filename = "{}-{}_{}.mid".format(v.label, str(v.recordNumber), str(v.associatedMidiID))
    # 'with open' means Python will automatically close the file
    with open(filename, "wb") as output_file:
      print("Writing MIDI to {}".format(filename))
      midiFileData.writeFile(output_file)
      
if(bDumpFile):
  s.pos = 0
  fileSize = os.path.getsize('decoded.bin')
  debugPrint("fileSize is {}".format(fileSize))
  dumphex(fileSize, s)

if bWriteToFile:
  newStdout.close()
  sys.stdout = origStdout

if bIsPythonista:
  console.hud_alert("File processing complete",'success', 1)
else:
  print("File processing complete")
