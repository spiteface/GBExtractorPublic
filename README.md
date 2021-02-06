# GBExtractor

Extract music sections from GarageBand as MIDI, natively on iOS.

### Features:
* Note on/off supported for all instruments, including all types of smart instrument
* Time signature and tempo are preserved
* Understands a variety of MIDI meta-data such MIDI CC and pitch wheel changes.
* GB multi-take sections are supported - use GB to jam short clips of MIDI and then export to a clip launcher such as LK.
* Optionally export drum sections as one track per drum part to allow for multi-stem processing.  Features automatic naming of each stem with the appropriate instrument for ease of use in your sequencer (limited DAW support for this option),

### Testing
I have tested most instruments with this tool and I can get note data from all of those tested, subject to the limitations discussed later.

The script has not been tested with Mac GB files, although I have no reason to think the format would be different.

Tested on an iPad Air 2020 with iOS 14.4 and latest GB, as of Feb 6th 2020.

## Usage instructions

1. Install http://omz-software.com/pythonista/ from the iOS app store.  This is not free and there may be other lower cost/free options but this is what the tool was developed and tested with.  Alternatively, find a desktop machine with Python 3 installed.  The v1.x version of the script was tested to run using Python 3.7 but I have not repeated this testing with v2.x of the tool. The free and powerful app iSH may also work but I have not tried this: [How to install Python in iSH](https://www.reddit.com/r/ish/comments/jjq8nc/how_to_install_apk_and_python/)
1. Download the gbextractor.py script from this site, or clone the project on iOS using [Working Copy](https://workingcopyapp.com)
1. (Pythonista only) Load the script into Pythonista. **IMPORTANT** You must copy to and run the script from the Pythonista folder, i.e. somewhere under iCloud Drive/Pythonista 3, otherwise you will not have permission to write the MIDI data.
1. Install packages "bitstring" and "MIDIUtil", e.g. "pip install packageName", see [this page](https://github.com/ywangd/stash) for how to do this.
1. Before running the script, ensure that GB does not have the project open otherwise you will not be able to open it via the tool.
1. Run the script.  On Pythonista you will be presented with an iOS file picker which you should use to select your GarageBand project file.  Outside of Pythonista you should provide a single argument to the script which is the GB project directory, e.g. ```python3.7 ~/gbextractor.py ~/MySong.band```
1. With luck, the script will complete with "File processing complete"
1. A directory will be created containing MIDI representations of the music sections that were found in the GB project.  For Pythonista, this will be in the same iCloud directory as the gbextractor.py script and if run outside of iOS then the directory will be created in the current working directory.

One MIDI file per section of GB data is created.  This means that there may be multiple MIDI files created per GB track.  The naming of the MIDI files should suggest some kind of ordering but you can rename the sections to make it clearer.

### Playing back MIDI in GB
The easiest way I have found of playing back MIDI into GB after it has been extracted is to use [AudioBus](https://audiob.us) to create a virtual port and then point the MIDI sequencer at that.  If GB is running and the appropriate instrument is open then you should hear the MIDI playing though GB, subject to the restrictions discussed in the [Limitations] section.

## Drum stems
If you prefer to process certain parts of a drum kit separately, e.g. by adding compression to a kick drum, then you may benefit from the ability of the tool to assign every note to a separate track.  By default all notes are added to a single track but if the `bUniqueTracks` Boolean is set to `True` then every note will be assigned to a unique track.

For ease of implementation, 16 tracks are created in the MIDI file upfront by default when using unique tracks.  Many DAWs ignore any empty tracks but some, e.g. ZenBeats will unfortunately load all of them.

You can modify the `trackLimit` variable if you know exactly how many stems you need.  One idea is to run the tool once with a high value for `trackLimit` to find out how many tracks you will need and then run it again with the correct number.  If `trackLimit` is set too low and there are more notes than stems then they will be added in a round-robin manner and so each stem may contain multiple notes.  Splitting notes in this semi-random manner could offer creative options.

### Note map
When using drum stems then it can be helpful to have an idea of what instrument each track represents.  If the `bUniqueTracks` Boolean is set to `True` then `trackMap` is used to map MIDI notes to an instrument name.  This name is then used to name the track and should make it much easier to identify the instrument in your sequencer.  You should note that depending on the instrument then the note names may not be correct.  For example, a siren sound in the drum sequencer may be labelled something like a Tom when exported but would sound as expected if played back in to GB.

I have only found a couple of DAW/sequencers that use the track names - Xequence 2 and MTS Studio.  The longer term plan is to offer the option to split stems to separate MIDI files which will offer more flexibility.
 
## Limitations [Limitations]
The following are known limitations:

### Pitch bends
Pitch bend information is stored as it is found in the GB project file.  This is recorded correctly when the keyboard interface is used to bend the pitch using the pitch wheel.  If however the data was recorded using an on-screen instrument then the pitch information is not scaled to the -8192 +8191 pitch range.  When this exported MIDI data is played back then the pitch bend may be hardly perceptible.

If there is scaling information stored with the project then I have not found it yet.  As a workaround there is a `bOverridePitchBend` Boolean which when set to `True` will use the value of the `pitchBendMultiplier` variable to automatically scale *all* pitch bend values found in that run of the tool.  The default of 24 appears correct for the guitar instrument but may need adjustment for other instruments.

### On screen controls
Many instruments have buttons which can be depressed or dials which can be turned to change the live sound of the instrument that is playing.  The tool will extract the most common of these (pitch bend, modulation) but most others are ignored.  This means that if you record a piece which requires these interactions then you will lose them on playback.  I have identified a lot of them in the project data but I have not yet worked out how (or if) is possible to send them back in to GB.

## Troubleshooting and further research
If you do hit problems or want to research the file format further then the script has some debug capability.  By default this is turned off but you can enable it by changing the `bDebug` variable to `True`.  This will dump some possibly useful data to the console in Pythonista.  You may also set the `bWriteToFile` variable to `True` in order to write this debug information to a file which will be written to the same working directory as the MIDI files.

Normally, fixing problems will entail changing the code in the `while` loop to skip over unknown data.

If you see a "file missing" type of error then try running the script again as this seems to be a transient issue.

## Ideas for future extensions
* Split stems to separate files.
* Use only the necessary number of tracks for stems.
* Let user choose how to remap GB note values.  For example, remap drum notes as they are written to the MIDI so that they work with a drum kit that expects different note values.  There are already ways of doing this in realtime on iOS, e.g. StreamByter or Mozaic.
* Automatically scale pitch bend based on the instrument.
* Allow a single MIDI file to contain multiple sections as they appear in GB rather than splitting them up into separate files

## Change history

* v2.0 Added support for extracting all MIDI
* v1.1 Script can be run outside of Pythonista using Python 3.x (tested with 3.7)
* v1.0 Initial release

