# Toxygen ToDo List

## Bugs

1. There is an agravating bug  where new messages are not put in the
   current window, and a messages waiting indicator appears. You have
   to focus out of the window and then back in the window.



## Fix history

The code is in there but it's not working.

## Fix Audio

The code is in there but it's not working. It looks like audio input
is working but not output. The code is all in there; I may have broken
it trying to wire up the ability to set the audio device from the
command line.

## Fix Video

The code is in there but it's not working.  I may have broken it
trying to wire up the ability to set the video device from the command
line.

## Groups

1. peer_id There has been a change of API on a field named
   ```group.peer_id``` The code is broken in places because I have not
   seen the path to change from the old API ro the new one.


## Plugin system

1. Needs better documentation and checking.

2. There's something broken in the way some of them plug into Qt menus.

3. Should the plugins be in toxygen or a separate repo?

4. There needs to be a uniform way for plugins to wire into callbacks.

## check toxygen_wrapper

1. I've broken out toxygen_wrapper to be standalone,
   https://git.plastiras.org/emdee/toxygen_wrapper but the tox.py
   needs each call double checking.

2. https://git.plastiras.org/emdee/toxygen_wrapper needs packaging
   and making a dependency.
