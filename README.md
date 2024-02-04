**NOT READY FOR PRIME TIME. I'M MAKING IT PUBLIC AS-IS SINCE I'VE HAD SOME PEOPLE INTERESTED IN IT - WARTS AND ALL.**

<p align="center">
<img width=206 src="https://github.com/EngineersNeedArt/channelZ/blob/cab68924e3866708accc4d49367ba8c88f54d778/documentation/UHF_logo.png" alt="ChannelZ logo.">
</p>

Take a Raspberry Pi and turn your hoard of (offline) video content into your own personal TV channel.

Like a TV channel the app is driven by a schedule — programs come on at specified times of the day. Like TV there is no pause, no rewind or skip, no streaming on demand. Like TV you either plan to watch when the program you want to see comes on or, perhaps more fun, you come across a show serendipitously.

Unlike a TV channel the content is local — your own collection of video files. No internet required. Unlike TV there are of course no commercials.

A random play-list works for some content (and the **UHF** app supports that as well) but I like the schedule nature of having horror films come on in the evening and kid's programs on Saturday morning.

**UHF** is written in Python to run on a Raspberry Pi. You point it at a schedule (a single JSON file or a suite of files) or a playlist (also a JSON file) and it starts playing video content fullscreen.

In "playlist mode" it reads the JSON file containing a list of file paths to the content you wish to show. It shuffles the list, plays through the video content then re-shuffles and repeats — forever. Having a collection of woodworking or shop videos culled from YouTube playing continuously in your garage workshop might be one use-case.

To use the "Schedule mode" requires a good deal more effort on your part in order to create the schedule. But if that appeals to you (as it did me) **UHF** will ingest the schedule and play your content when you intended.

If, like television, you schedule programs to start on the hour/half-hour you will likely find there is a lot fo "dead air time". **UHF** can use the playlist-like mode to fill this dead time with random short content that you provide.

## Installation

When I began development of **UHF** I was on a device running the Buster version of Raspbian. I had early success using OMXPlayer to playback video on the Pi and so developed **UHF** with OMXPlayer as the video framework. A nice Python wrapper `omxplayer-wrapper` (available from PyPy, listed in `requirements.txt`) is a module you will also need.

Note: OMXPlayer itself is already installed on Buster but has been deprecated since. I intend to experiment with VLC (the recommended replacement for OMXPlayer) but as the code stands today, you will probably want to stick with Buster.

For displaying static images **UHF** uses `feh`. Here is the Terminal command to install `feh`:

`sudo apt-get install feh`

## Basics

The primary file is `uhf.py`. Near the top of the file is a hard-coded path (`CHANNEL_FILE_PATH`) for where the schedule file and/or playlist files live. You should set this path to point to your own "channel" directory.
