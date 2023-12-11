# Toxygen

Toxygen is powerful cross-platform [Tox](https://tox.chat/) client written in pure Python3.

### [Install](/docs/install.md) - [Contribute](/docs/contributing.md) - [Plugins](/docs/plugins.md) - [Compile](/docs/compile.md) - [Contact](/docs/contact.md)

### Supported OS: Linux and Windows

### Features:

- 1v1 messages
- File transfers
- Audio calls
- Video calls
- Group chats
- Plugins support
- Desktop sharing
- Chat history
- Emoticons
- Stickers
- Screenshots
- Name lookups (toxme.io support)
- Save file encryption
- Profile import and export
- Faux offline messaging
- Faux offline file transfers
- Inline images
- Message splitting
- Proxy support
- Avatars
- Multiprofile
- Multilingual
- Sound notifications
- Contact aliases
- Contact blocking
- Typing notifications
- Changing nospam
- File resuming
- Read receipts
- NGC groups

### Screenshots
*Toxygen on Ubuntu and Windows*
![Ubuntu](/docs/ubuntu.png)
![Windows](/docs/windows.png)

## Forked

This hard-forked from the dead https://github.com/toxygen-project/toxygen
```next_gen``` branch.
 
https://git.plastiras.org/emdee/toxygen_wrapper needs packaging
is making a dependency. Just download it and copy the two directories
```wrapper``` and ```wrapper_tests``` into ```toxygen/toxygen```.

See ToDo.md to the current ToDo list.

You can have a [weechat](https://github.com/weechat/qweechat)
console so that you can have IRC and jabber in a window as well as Tox.
There's a copy of qweechat in ```thirdparty/qweechat``` backported to
PyQt5 and integrated into toxygen. Follow the normal instructions for
adding a ```relay``` to [weechat](https://github.com/weechat/weechat)
```
/relay add ipv4.ssl.weechat 9001
/relay start ipv4.ssl.weechat
```
or
```
/relay add weechat 9000
/relay start weechat
```
and use the Plugins/Weechat Console to start weechat under Toxygen.
Then use the File/Connect menu item of the Console to connect to weechat.

Weechat has a Jabber plugin to enable XMPP:
```
/python load jabber.el
/help jabber
```
so you can have Tox, IRC and XMPP in the same application!

Work on Tox on this project is suspended until the
[MultiDevice](https://git.plastiras.org/emdee/tox_profile/wiki/MultiDevice-Announcements-POC) problem is solved. Fork me!

This will probably be ported to Qt6 using qtpy
https://github.com/spyder-ide/qtpy .

