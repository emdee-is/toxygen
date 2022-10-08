# Toxygen ToDo List

## Fix history

The code is in there but it's not working.

## Fix Audio

The code is in there but it's not working.
I may have broken it trying to wire up the ability to
set the audio device from the command line.

## Fix Video

The code is in there but it's not working.
I may have broken it trying to wire up the ability to
set the audio device from the command line.

## Groups

1. peer_id There has been a change of API on a field named
   ```group.peer_id``` The code is broken in places because I have not
   seen the path to change from the old API ro the new one.

2. There is no way to delete a group in the UI

3. Distinguish between Frieds, Groups and Whispers in the UI.

## Plugin system

1. Needs better documentation and checking.

2. There's something broken in the way some of them plug into Qt menus.

3. Should the plugins be in toxygen or a separate repo?

## check toxygen_wrapper

1. I've broken out toxygen_wrapper to be standalone,
   https://git.plastiras.org/emdee/toxygen_wrapper but the tox.py
   needs each call double checking.




