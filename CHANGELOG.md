# Changelog:

### Version 3.2.0

  * Added support tracking kicks/bans/quiets. (From 1.10.x)
  * Added `offenses` command. (From 1.10.x)
  * Added `RECORD_MODERATED` setting for enabling and disabling the two features above.


### Version 3.1.0

  * Added `OnKickMessage` for recording kicks.
  * Added `RECORD_WHOIS`, `RECORD_WHOWAS`, and `WHO_ON_JOIN`settings.
  * Added `purge` command for deleting old data.
  * Added `VACUUM_ON_LOAD` command for vacuuming the database.
  * Added `kicks` column for the numer of times the person has been kicked.

### Version 3.0.0

  * Added `event` column for recording the last type of event someone used; JOIN, NICK, NOTICE, PART, PRIVMSG, QUIT
  * Added `firstseen` column for the first time the person was seen.
  * Renamed `time` column into `lastseen` for the last time the person was seen. 
  * Added `texts` column for the number of lines of both PRIVMSG and NOTICE sent into a channel or query.
  * Added `joins` column for the number of times the person has joined a channel.
  * Added `parts` column for the number of times the person has parted a channel.
  * Added `quits` column for the number of times the person has quit from a channel.
  * Added `account` column for the NickServ account the person used.
  * Added `gecos` column for the GECOS/realname the person used.
  * Added `OnPart()`.
  * Added `OnQuit()`.
  * Replace `OnJoin()` with `OnJoinMessage()`.
  * Replace `OnNick()` with `OnNickMessage()`.
  * Replace `OnPart()` with `OnPartMessage()`.
  * Replace `OnQuit()` with `OnQuitMessage()`.
  * Replace `OnChanMsg()` with `OnChanTextMessage()`.
  * Replace `OnChanAction()` with `OnChanActionMessage()`.
  * Replace `OnPrivMsg()` with `OnPrivTextMessage()`.
  * Added `OnChanNoticeMessage()`.
  * Added `OnPrivNoticeMessage()`.
  * Added `OnPrivActionMessage()`.
  * Added `OnUserTextMessage()`.
  * Added `OnUserActionMessage()`.
  * Added `OnUserNoticeMessage()`.
  * Support /who #channel.
  * Record firstseen and lastseen for a user.
  * Use newer OnChan[Join|Part|Text|Notice]Message() code.
  * Record own events.
  * Support /whois and /whowas 
  * Use UPSERT for SQLite.
  * Updated `seen` command output to include information from new columns.


Original Authors:

https://github.com/AwwCookies

https://github.com/emagaliff