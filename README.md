subslider
=========

A script to fix out of sync subtitles.

Note
----

This is the original Python project for subslider. If you're looking for the
quickest way to sync your subtitles without having to download anything, look
for the more recent Javascript version, called [subslider.js][1]

[1]: https://github.com/micheleb/subslider.js

How to use it
-------------

The easiest way to use subslider is to play the video and reach the first dialog. When you find it, take a look at the
exact time at which it starts. Let's say the first dialog happens at 1:23,450. Then, you can simply call
```Shell
python subslider.py -s 1:23,450 MySubFile.srt
```

You will be shown the first 10 lines in the .srt file, from which you can choose which one is the one that should start
at 1:23,450. Most of the times it's going to be the first, but sometimes subtitle authors put in their tags, and maybe
the name of the video you're watching, so you don't want to synchronize those.

The script will update the original .srt file, so that you can simply reload it on your player to see if it helped.

The original .srt file is copied to a file with a _orig suffix, so MySubFile.srt would be copied to MySubFile_orig.srt.

More options
------------

Type
```Shell
python subslider.py -h
```

for a list of all available options.
