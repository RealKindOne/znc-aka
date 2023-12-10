znc-aka

A ZNC module to track users.


WARNING: COMPATABILITY CHANGES.

 - Using UPSERT that was added in SQLite 3.24.0 (2018-06-04)
 - Renamed 'time' column into 'firstseen'. The name is technically wrong for
   all existing users in the db since it is actually their 'lastseen'.
 - Added 'lastseen' column.


Original Authors:

https://github.com/AwwCookies

https://github.com/emagaliff