# znc-aka
A ZNC module to track users

### WARNING Before Upgrading to 3.x.

This version of AKA has been extensively modified from the last known 2.0.3 and 2.0.4 versions on the internet.

Read the CHANGELOG.md file for a full list of new features.

Due to the massive amount of changes to the database you will need to manually update the database in SQLite (while the module is unloaded) to support this version.

This will increase your database size about a little over 3x in size (2x for the update, 1x for the VACUUM) while running these commands. Make sure you have enough storage before attempting this. This might take awhile depending on hardware and size of the database.

    PRAGMA auto_vacuum=2;
    CREATE TABLE IF NOT EXISTS users_temp (id INTEGER PRIMARY KEY, network TEXT, nick TEXT, ident TEXT, host TEXT, channel TEXT, event TEXT, message TEXT, firstseen INTEGER, lastseen INTEGER, texts INTEGER, joins INTEGER, parts INTEGER, quits INTEGER, account TEXT, gecos TEXT, UNIQUE (network, nick, ident, host, channel));
    INSERT INTO users_temp (network,nick,ident,host,channel,message,firstseen,lastseen) select network,nick,ident,host,channel,message,time,time from users;
    ALTER TABLE users RENAME TO users_old;
    ALTER TABLE users_temp RENAME TO users;
    UPDATE users SET event = '0', texts = '0', joins = '0', parts = '0', quits = '0', account = '0', gecos = '0';

NOTE: Users `firstseen` and `lastseen` will be the same so you will not know the actual `firstseen` on all existing users.

If everything was successful you can delete the old database and use the VACUUM command for recovering free space.

    DROP TABLE users_old;
    VACUUM;

Done.

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
 * <a href="https://www.sqlite.org">sqlite3</a> 3.24.0 or newer for UPSERT.

## Installation
To install aka, place aka.py in your ZNC modules folder

## Loading
`/znc loadmod aka`

## Commands

`all <user>` Get all information on a user (nick, ident, or host)

`history <user>` Show history for a user (nick, ident, or host)

`users <#channel 1> [<#channel 2>] ... [<#channel #>]` Show common users between a list of channels

`channels <user 1> [<user 2>] ... [<user #>]` Show common channels between a list of users (nicks, idents, and/or hosts)

`seen <user> [<#channel>]` Display last time user (nick, ident, or host) was seen speaking

`geo <user>` Geolocates user (nick, ident, host, IP, or domain)

`who <scope>` Update userdata on all users in the scope (#channel, network, or all)

`process <scope>` Add all current users in the scope (#channel, network, or all) to the database

`rawquery <query>` Run raw sqlite3 query and return results

`about` Display information about aka

`stats` Print data stats for the current network. Also shows total database size.

`help` Print help from the module

### Wildcard Searches

All `<user>` searches support GLOB syntax. `*` will match any number of characters and `?` will match a single character. Can be combined and used at the start, middle, and end of the `<user>` block(s).

## Examples

Command entered into SQLite (note: do not this while the module is loaded):

    sqlite> .mode column
    sqlite> SELECT * FROM users WHERE network = 'libera' AND nick = 'kindone' and channel = '##kindone';
    id   network  nick     ident     host                    channel    event  message         firstseen   lastseen    texts  joins  parts  quits  account  gecos
    ---  -------  -------  -------   ----------------------  ---------  -----  --------------  ----------  ----------  -----  -----  -----  -----  -------  -----
    281  libera   kindone  ~kindone  idlerpg/player/kindone  ##kindone  quit   Quit: Leaving.  1694703000  1694703601  0      1      0      1      kindone  ...
    282  libera   kindone  kindone   idlerpg/player/kindone  ##kindone  join                   1694703977  1702319802  36     8      7      1      kindone  ...

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

## Contact

Issues/bugs should be submitted on the <a href="https://github.com/RealKindOne/znc-aka/issues">GitHub issues page</a>.

`KindOne` on `irc.libera.chat` `##kindone` (Highlight me so I can know you are in there.)



EOF