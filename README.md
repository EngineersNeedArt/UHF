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

Trying to modernize **UHF**, I am trying to move over to MPV for playback in place of the deprecated OMXPlayer. A nice Python wrapper `python-mpv` (available from PyPy, listed in `requirements.txt`) is a module you will also need.

## Basics

The primary file is `uhf.py`. Near the top of the file is a hard-coded path (`CHANNEL_FILE_PATH`) for where the schedule file and/or playlist files live. You should set this path to point to your own "channel" directory.

The `main()` function in `uhf.py` opens and parses the file pointed at in `CHANNEL_FILE_PATH`. If the version property of the file is `UHF Channel - v1` then it runs in "schedule mode" — meaning it will expect a day to day, hour to hour schedule of video content to play. It will look at the current date and time of the machine it is running on and then scan the schedule looking for content that should be playing at that moment. It will attempt then to open the video content and start playback at the point in the video where it should be (according to the schedule).

If instead the version property is `UHF List - v1` then the app runs in "playlist mode" — the video content is played randomly, endlessly.

Even in *schedule mode* the app does take advantage of play-lists to fill dead air-time between scheduled programs. Say you have a movie scheduled to play at noon and another two hours later. If the first movie is 20 minutes short of two hours in length, there will be 20 minutes of "dead air" before the next show starts. The **UHF** schedule can indicate playlists of content to play at random during these dead air breaks. For that reason it is good to have a lot of short content in playlists to act as filler.

Additionally, if for some reason a file in the schedule cannot be found, opened or played, **UHF** will attempt to substitute filler content for the duration of the originally scheduled content.
