# znc-aka
A ZNC module to track users

### WARNING Before Upgrading to 3.x.

This version of AKA has been extensively modified from the last known 2.0.3 and 2.0.4 versions on the internet.

Read the CHANGELOG.md file for a full list of new features.

Due to the massive amount of changes to the database you will need to manually update the database in SQLite, (while the module is unloaded) to support this version.

This will increase your database size by about 2x. Make sure you have enough storage.

    PRAGMA auto_vacuum=2;
    CREATE TABLE IF NOT EXISTS users_temp (id INTEGER PRIMARY KEY, network TEXT, nick TEXT, ident TEXT, host TEXT, channel TEXT, event TEXT, message TEXT, firstseen INTEGER, lastseen INTEGER, texts INTEGER, joins INTEGER, parts INTEGER, quits INTEGER, account TEXT, gecos TEXT, UNIQUE (network, nick, ident, host, channel));
    INSERT INTO users_temp (network,nick,ident,host,channel,message,firstseen,lastseen) select network,nick,ident,host,channel,message,time,time from users;
    ALTER TABLE users RENAME TO users_old;
    ALTER TABLE users_temp RENAME TO users;
    UPDATE users SET event = '0', texts = '0', joins = '0', parts = '0', quits = '0', account = '0', gecos = '0';


If everything was successful you can delete the old database and use the VACUUM command for recovering free space.

    DROP TABLE users_old;
    VACUUM;

Done.

## Table of Contents
- [Requirements](#requirements)
- [Installation](#installation)
- [Loading](#loading)
- [Commands](#commands)
- [Contact](#contact)

## Requirements
 * <a href="http://znc.in">ZNC</a>
 * <a href="https://www.python.org">Python 3</a>
 * <a href="http://wiki.znc.in/Modpython">modpython</a>
 * <a href="http://docs.python-requests.org/en/latest/">python3-requests</a>
 * <a href="https://www.sqlite.org">sqlite3</a> 3.24.0 or newer.

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


## Contact

Issues/bugs should be submitted on the <a href="https://github.com/RealKindOne/znc-aka/issues">GitHub issues page</a>.

`KindOne` on `irc.libera.chat` `##kindone`