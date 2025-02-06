# znc-aka
A ZNC module to track users

### WARNING Before Upgrading to 3.x.

This version of AKA has been extensively modified from the last known 2.0.3 and 2.0.4 versions on the internet.

WARNING: This script will automatically update your database to the new format. Your database size will grow about a little over 3x in size (2x for the update, 1x for the VACUUM) while doing the first time upgrade. Make sure you have enough storage before attempting this. This might take awhile depending on hardware and size of the database.

Read the CHANGELOG.md file for a full list of new features.


## Table of Contents
- [Requirements](#requirements)
- [Installation](#installation)
- [Loading](#loading)
- [Commands](#commands)
- [Examples](#examples)
- [Notes](#notes)
- [Contact](#contact)

## Requirements
 * <a href="http://znc.in">ZNC</a>
 * <a href="https://www.python.org">Python 3</a>
 * <a href="http://wiki.znc.in/Modpython">modpython</a>
 * <a href="http://docs.python-requests.org/en/latest/">python3-requests</a>
 * <a href="https://www.sqlite.org">sqlite3</a> 3.24.0 or newer for `UPSERT`.

## Installation
To install aka, place aka.py in your ZNC modules folder

## Loading
`/znc loadmod aka`

## Commands

`history <user>` Show history for a user (nick, ident, or host)

`who <scope>` Update userdata on all users in the scope (#channel, network, or all)

`process <scope>` Add all current users in the scope (#channel, network, or all) to the database

`rawquery <query>` Run raw sqlite3 query and return results


### Aggregate Commands

`all <user>` Get all information on a user (nick, ident, or host)


### User Lookup commands

`users <#channel 1> [<#channel 2>] ... [<#channel #>]` Show common users between a list of channels

`channels <user 1> [<user 2>] ... [<user #>]` Show common channels between a list of users (nicks, idents, and/or hosts)

`geo <user>` Geolocates user (nick, ident, host, IP, or domain)


### Moderation History Commands

`offenses nick <nick>` Display kick/ban/quiet history for nick

`offenses host <host>` Display kick/ban/quiet history for host

`offenses in nick <#channel> <nick>` Display kick/ban/quiet history for nick in channel

`offenses in host <#channel> <host>` Display kick/ban/quiet history for host in channel


### User Information Commands

Note: This command can use `nick`, `ident`, or `host` for the `--type=`

`seen <user>` Display last time the (nick, ident, or host) was seen on the network.

`seen <user> <#channel>` Display last time the (nick, ident, or host) was seen in the channel.

`seen <user> --type=ident` Display the last seen user with that ident.

`seen <user> <#channel> --type=ident` Display the last user seen with that ident in the channel.


### Other Commands

`about` Display information about aka

`help` Print help from the module

`stats` Print data stats for the current network. Also shows total database size.


## Configuration

### Commands

`getconfig` Prints the current settings.

`config <FEATURE> TRUE|FALSE` Enable or disable a setting.


### Variables
                                                                                                                    
  * **ENABLE_PURGE** *(True/False)* Enable the PURGE command.
  * **RECORD_KICK** *(True/False)*  Record kicking in the "users" table.
  * **RECORD_MODERATED** *(True/False)* Record kicking, banning, and quieting in the "moderated" table.
  * **RECORD_WHOIS** *(True/False)* Record /whois output.
  * **RECORD_WHOWAS** *(True/False)* Record /whowas output.
  * **VACUUM_ON_LOAD** *(True/False)* Perform SQLite VACUUM command when module is loaded. This setting will reset itself to FALSE when finished.
  * **WHO_ON_JOIN** *(True/False)* Send a /who #channel when you join a channel on your client.

## Other Stuff

### Wildcard Searches

All `<user>` searches support GLOB syntax. `*` will match any number of characters and `?` will match a single character. Can be combined and used at the start, middle, and end of the `<user>` block(s).


## Examples

Command entered into SQLite (note: do not this while the module is loaded):

    sqlite> .mode column
    sqlite> SELECT * FROM users WHERE network = 'libera' AND nick = 'kindone' and channel = '##kindone';
    id   network  nick     ident     host                    channel    event  message         firstseen   lastseen    texts  joins kicks parts  quits  account  gecos
    ---  -------  -------  -------   ----------------------  ---------  -----  --------------  ----------  ----------  -----  ----- ----- -----  -----  -------  -----
    281  libera   kindone  ~kindone  idlerpg/player/kindone  ##kindone  quit   Quit: Leaving.  1694703000  1694703601  0      1     0     0      1      kindone  ...
    282  libera   kindone  kindone   idlerpg/player/kindone  ##kindone  join                   1694703977  1702319802  36     8     0     7      1      kindone  ...

`rawquery` responses are printed in `csv` format for IRC clients.

`rawquery` command sent in IRC client to show the 10 most active users in a channel. Sorted by number of texts send in a descending order. 

    <KindOne> rawquery SELECT texts,nick,ident,host FROM users WHERE network = 'libera' and channel = '#libera' ORDER BY texts DESC LIMIT 10;
    <*aka> (2350, 'aaaa', ~ident', 'aaaa.com')
    <*aka> (2040, 'bbbb', ~ident', 'bbbb.com')
    <*aka> (1650, 'cccc', ~ident', 'cccc.com')
    <*aka> (1577, 'dddd', ~ident', 'dddd.com')
    <*aka> (1410, 'eeee', ~ident', 'eeee.com')
    <*aka> (1373, 'ffff', ~ident', 'ffff.com')
    <*aka> (1226, 'gggg', ~ident', 'gggg.com')
    <*aka> (1202, 'hhhh', ~ident', 'hhhh.com')
    <*aka> (1031, 'iiii', ~ident', 'iiii.com')
    <*aka> (1005, 'jjjj', ~ident', 'jjjj.com')
    <*aka> 10 records retrieve

Seen command:

    <KindOne> seen chanserv
    <*aka> chanserv (chanserv@services.libera.chat) was last seen in query at 2023-12-10 22:55:25 doing notice: "End of #foobar FLAGS listing.".

History command:

    <KindOne> history nickserv
    <*aka> Looking up history for nickserv, please be patient...
    <*aka> Nick(s): alis, chanserv, memoserv, nickserv, saslserv
    <*aka> Ident(s): alis, chanserv, memoserv, nickserv, saslserv
    <*aka> Host(s): services.libera.chat
    <*aka> History for nickserv complete.


## Notes

The module creates a new row based on the `network`, `nick`, `ident`, `host`, and `channel` column. 
If any of those are different a new row is created for the user.
All data (nick,ident,host,channel,etc..) is stored in lowercase except for the `message`.
The `account` and `gecos` columns are overwritten with the most recent one that was seen.
Do NOT make a copy of the database while the module is loaded. You can easily get a corrupted copy if there is channel/query activity.


## Known Issues

You will get NULL `ident` and `host` entries for the kicked nick in the `OnKickMessage` if the uses does not exist in the database. The only way to 'fix' this is to /who #channel on each channel you join.

Do not do `/whois` or `/whowas` command at the same time on multiple networks. The module uses `global` variables, this causes cross-contamination.

Using `chghost` will not trigger the `OnQuitMessage` / `OnJoinMessage` event message.

## Contact

Issues/bugs should be submitted on the <a href="https://github.com/RealKindOne/znc-aka/issues">GitHub issues page</a>.

`KindOne` on `irc.libera.chat` `##kindone` (Highlight me so I can know you are in there.)



EOF