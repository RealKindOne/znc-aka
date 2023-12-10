znc-aka

A ZNC module to track users.


WARNING: The database format has been heavily modified.

If you are upgrading from a 2.0.x version you will need to run the following commands in SQLite, while the znc module is unloaded.
Note: This will make the database 2x larger. Make sure you have enough storage space.

"

CREATE TABLE IF NOT EXISTS users_temp (id INTEGER PRIMARY KEY, network TEXT, nick TEXT, ident TEXT, host TEXT, channel TEXT, event TEXT, message TEXT, firstseen INTEGER, lastseen INTEGER, texts INTEGER, joins INTEGER, parts INTEGER, quits INTEGER, account TEXT, gecos TEXT, UNIQUE (network, nick, ident, host, channel));
INSERT INTO users_temp (network,nick,ident,host,channel,message,firstseen,lastseen) select network,nick,ident,host,channel,message,time,time from users;
ALTER TABLE users RENAME TO users_old;
ALTER TABLE users_temp RENAME TO users;
UPDATE users SET event = '0', texts = '0', joins = '0', parts = '0', quits = '0', account = '0', gecos = '0';

"

If everything was successful you can delete the old database:

"

DROP TABLE users_old;

"





Original Authors:

https://github.com/AwwCookies

https://github.com/emagaliff