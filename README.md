# GBExtractor

Extract drummer patterns from GarageBand to MIDI, natively on iOS.

Tested on an iPad 7th gen with iOS 13 and latest GB, as of Aug 29th 2020.  It might work elsewhere.

The following drum sources should be parseable (Accoustic and Electronic):

1. Virtual Drummers
1. Smart Drums
1. "Tappity-tap the screen" Drums
1. Beat Sequencer

Song tempo is preserved.

One MIDI file per "part" of drum data is created.  This means that there may be multiple MIDI files created per GB track.  Hopefully the naming of the MIDI files should indicate some kind of ordering but you can always rename the parts to make it clearer.

### Notes

1. Only note on, velocity and note duration data is preserved.  Other MIDI control data is ignored.
1. The basic nature of the parsing may cause some note effects to go missing and may be most obvious with electronic drums.  The pattern however should be still be usable and to me this is the valuable part.
1. You may need to manually remap some of the notes in order to match them to the correct parts of the instrument in your DAW.
1. If you see a "file missing" type of error then try running the script again as this seems to be a transient issue.
1. The script has not been tested with Mac GB files, although I have no reason to think the format would be different.

## Usage instructions

1. Install http://omz-software.com/pythonista/ from the iOS app store.  Yes it costs money and there may be other lower cost/free options but that is what I use.  There is not a lot of code that would need to be changed to get this running on the desktop so that might be an option for you.
1. Grab gbextractor.py script
1. Load the script into Pythonista. **IMPORTANT** You must copy to and run the script from the Pythonista folder, i.e. somewhere under iCloud Drive/Pythonista 3, otherwise you will not have permission to write the MIDI data.
1. Install packages "bitstring" and "MIDIUtil", e.g. "pip install packageName" from https://github.com/ywangd/stash
1. Run the script.  You will be presented with an iOS file picker which you should use to select your GarageBand project file.
1. With luck, the script will complete with "File processing complete"
1. A directory will be created in the same directory as the gbextractor.py script containing MIDI representations of the drum tracks that were found in the GB project.

## Troubleshooting

The use-case for this script is to harness GB as a tool to create some beat patterns and then extract them for use elsewhere.  The code has therefore had minimal testing on real projects containing non-drum tracks and so there will surely be cases where the parsing code hits some unexpected data since it has to try and parse everything to get to the drum parts.  To increase your chances of a successful parse, create a project containing just the drum parts that you want.  Try duplicating your project and in the duplicate delete all other tracks other than the drum tracks.

If you do hit problems then the script has some debug capability.  By default this is turned off but you can enable it by changing the `bDebug` variable to `True`.  This will dump some possibly useful data to the console in Pythonista.  You may also set the `bWriteToFile` variable to `True` in order to write this debug information to a file which will be written to the same working directory as the MIDI files.

Normally, fixing problems will entail changing the code in the `while` loop to skip over unknown data.

## Ideas for future extensions

* Per instrument stem output, e.g. separate MIDI file for kick drums.
* Make script usable with either Pythonista or desktop Python
* Let user choose how to remap GB note values
* Allow a single MIDI file to contain multiple sections as they appear in GB rather than splitting them up into separate files
* Add general MIDI support
