#  znc-aka: A ZNC module to track users
#  Copyright (C) 2016 Evan Magaliff
#  Copyright (C) 2023 KindOne
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#  Original Authors: Evan (MuffinMedic), Aww (AwwCookies)                 #
#  New modifications: (irc.libera.chat KindOne) (GitHub: RealKindOne)     #
#  Desc: A ZNC module to track users                                      #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #


# WARNING:
# The database format has been extensively modified.
# If you are updating from a 2.0.x versions you must
# run the SQLite commands in the README.md file before
# you load this module.

version = '3.0.0'
updated = "Dec 10, 2023"

import znc
import os
import datetime
import time
import re
import sqlite3
import requests

DEFAULT_CONFIG = {
    "RECORD_WHOIS":   True,   # Record /whois output.
    "RECORD_WHOWAS":  True,   # Record /whowas output.
    "WHO_ON_JOIN":    True   # Send a /who #channel when you join a channel on your client.
}
class aka(znc.Module):
    module_types = [znc.CModInfo.UserModule]
    description = "Tracks users, allowing tracing and history viewing of nicks, hosts, and channels"
    #wiki_page = "aka"

    HELP_COMMANDS = (
        ('all'        , ''                                                  , 'Get all information on a user (nick, ident, or host)'),
        ('history'    , '<user> [--type=type]'                              , 'Show history for a user'),
        ('users'      , '<#channel1> [<#channel2>] ... [<channel #>]'       , 'Show common users between a list of channel(s)'),
        ('channels'   , '<user1> [<user2>] ... [<user #>] [--type=type]'    , 'Show common channels between a list of user(s) (nicks, idents, or hosts, including mixed)'),
        ('seen'       , '<user> [<#channel>] [--type=type]'                 , 'Display last time user was seen speaking'),
        ('geo'        , '<user> [--type=type]'                              , 'Geolocates user (nick, ident, host, IP, or domain)'),
        ('who'        , '<scope>'                                           , 'Update userdata on all users in the scope (#channel, network, or all)'),
        ('process'    , '<scope>'                                           , 'Add all current users in the scope (#channel, network, or all) to the database'),
        ('rawquery'   , '<query>'                                           , 'Run raw sqlite3 query and return results'),
        ('about'      , ''                                                  , 'Display information about aka'),
        ('stats'      , ''                                                  , 'Print data stats for the current network'),
        ('config'     , '<variable> <value>'                                , 'Set configuration variables.')
        ('getconfig'  , ''                                                  , 'Print the current configuration.')
        ('help'       , ''                                                  , 'Print help for using the module'),
        ('NOTE'       ,  'User Types'                                       , 'Valid user types are nick, ident, and host.'),
        ('NOTE'       ,  'Wildcard Searches'                                , '<user> supports * and ? GLOB wildcard syntax (combinable at start, middle, and end).')
    )

    def OnLoad(self, args, message):
        self.USER = self.GetUser().GetUserName()
        self.db_setup()
        self.configure()
        return True

    def OnJoinMessage(self, msg):
        channel = str(msg.GetChan().GetName()).replace("'","''")
        gecos   = str(msg.GetParam(2)).replace("'","''")
        self.process_join(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, 'join', msg.GetParam(1), gecos)

    def OnPartMessage(self, msg):
        channel  = str(msg.GetChan().GetName()).replace("'","''")
        partmsg  = str(msg.GetReason()).replace("'","''")
        if msg.GetTag('account'):
            self.process_part_account(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, 'part', partmsg, msg.GetTag('account'))
        else:
            self.process_part(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, 'part', partmsg)

    def OnQuitMessage(self, msg, vChans):
        quitmsg  = str(msg.GetReason()).replace("'","''")
        if msg.GetTag('account'):
            for chan in vChans:
                channel = str(chan.GetName().replace("'","''"))
                self.process_quit_account(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, 'quit', quitmsg, msg.GetTag('account'))
        else:
            for chan in vChans:
                channel = str(chan.GetName().replace("'","''"))
                self.process_quit(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, 'quit', quitmsg)

    # OnUser..() events will set the 'joins' column at '1' if sent to a query. Don't need to create a separate self.process_ ... for this.
    def OnUserTextMessage(self, msg):
        nick  = self.GetNetwork().GetCurNick()
        ident = self.GetNetwork().GetIRCNick().GetIdent()
        host  = self.GetNetwork().GetIRCNick().GetHost()
        priv  = msg.GetParam(1)
        self.process_message(self.GetNetwork().GetName(), nick, ident, host, msg.GetParam(0), 'privmsg', priv)

    def OnUserActionMessage(self, msg):
        nick  = self.GetNetwork().GetCurNick()
        ident = self.GetNetwork().GetIRCNick().GetIdent()
        host  = self.GetNetwork().GetIRCNick().GetHost()
        priv  = msg.GetParam(1)
        self.process_message(self.GetNetwork().GetName(), nick, ident, host, msg.GetParam(0), 'privmsg', '* ' + priv)

    def OnUserNoticeMessage(self, msg):
        nick  = self.GetNetwork().GetCurNick()
        ident = self.GetNetwork().GetIRCNick().GetIdent()
        host  = self.GetNetwork().GetIRCNick().GetHost()
        priv  = msg.GetParam(1)
        self.process_message(self.GetNetwork().GetName(), nick, ident, host, msg.GetParam(0), 'notice', priv)

    def OnNickMessage(self, msg, vChans):
        if msg.GetTag('account'):
            for chan in vChans:
                channel = str(chan.GetName().replace("'","''"))
                self.process_nick_change_new_account(self.GetNetwork().GetName(), msg.GetOldNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, msg.GetNewNick(), msg.GetTag('account'))
                self.process_nick_change_old_account(self.GetNetwork().GetName(), msg.GetNewNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, msg.GetOldNick(), msg.GetTag('account'))
        else:
            for chan in vChans:
                channel = str(chan.GetName().replace("'","''"))
                self.process_nick_change_new(self.GetNetwork().GetName(), msg.GetOldNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, msg.GetNewNick())
                self.process_nick_change_old(self.GetNetwork().GetName(), msg.GetNewNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), channel, msg.GetOldNick())

    def OnChanActionMessage(self, msg):
        self.process_message(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), msg.GetChan().GetName(), 'privmsg' , '* ' + msg.GetText())

    def OnChanNoticeMessage(self, msg):
        self.process_message(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), msg.GetChan().GetName(), 'notice', msg.GetText())

    def OnChanTextMessage(self, msg):
        self.process_message(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), msg.GetChan().GetName(), 'privmsg', msg.GetText())

    # Assume everything is PRIVMSG
    def OnPrivActionMessage(self, msg):
        self.process_message(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), 'query', 'privmsg', '* ' + msg.GetText())

    def OnPrivNoticeMessage(self, msg):
        # Don't log server notices.
        if (msg.GetNick().GetIdent() == ''): return
        self.process_message(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), 'query', 'notice', msg.GetText())

    def OnPrivTextMessage(self, msg):
        self.process_message(self.GetNetwork().GetName(), msg.GetNick().GetNick(), msg.GetNick().GetIdent(), msg.GetNick().GetHost(), 'query', 'privmsg', msg.GetText())

    def OnUserJoinMessage(self, msg):
        if self.nv['WHO_ON_JOIN'] == "TRUE":
            self.PutIRC("WHO %s" % msg.GetTarget())

    def OnNumericMessage(self, msg):

        #                      0      1        2      3       4  5
        # :do.foobar.com 311 KindOne KindOne ~ident 10.10.1.2 * :...
        if (msg.GetCode() == 311):
            global whois_nick
            global whois_ident
            global whois_host
            global whois_gecos
            global whois_account
            # User might not be logged in. '0' the account name.
            whois_account = '0'
            whois_nick  = msg.GetParam(1)
            whois_ident = msg.GetParam(2)
            whois_host  = msg.GetParam(3)
            whois_gecos = str(msg.GetParam(5)).replace("'","''")

        if (msg.GetCode() == 314):
            global whowas_nick
            global whowas_ident
            global whowas_host
            global whowas_gecos
            global whowas_account
            # User might not be logged in. '0' the account name.
            whowas_account = '0'
            whowas_nick  = msg.GetParam(1)
            whowas_ident = msg.GetParam(2)
            whowas_host  = msg.GetParam(3)
            whowas_gecos = str(msg.GetParam(5)).replace("'","''")
            if self.nv['RECORD_WHOWAS'] == "TRUE":
                self.process_whowas(self.GetNetwork().GetName(), whowas_nick, whowas_ident, whowas_host, whowas_account, whowas_gecos)

        # End of /whois
        # :do.foobar.com 318 KindOne KindOne :End of /WHOIS list.
        if (msg.GetCode() == 318):
            if self.nv['RECORD_WHOIS'] == "TRUE":
                self.process_whois(self.GetNetwork().GetName(), whois_nick, whois_ident, whois_host, whois_account, whois_gecos)

        # Account
        # :do.foobar.com 330 KindOne KindOne kindone :is logged in as
        if (msg.GetCode() == 330):
            whois_account  = msg.GetParam(2)
            whowas_account = msg.GetParam(2)

        # End of /whowas
        if (msg.GetCode() == 369):
            if self.nv['RECORD_WHOWAS'] == "TRUE":
                self.process_whowas(self.GetNetwork().GetName(), whowas_nick, whowas_ident, whowas_host, whowas_account, whowas_gecos)

        # /who #channel
        #                            0       1      2               3          4               5
        # :sodium.libera.chat 352 KindOne #channel ident some.fake.host.com sodium.libera.chat NICK H*@ :0 ...
        if (msg.GetCode() == 352):
          nick  = msg.GetParam(5)
          ident = msg.GetParam(2)
          host  = msg.GetParam(3)
          chan  = str(msg.GetParam(1)).replace("'","''")
          gecos = str(msg.GetParam(7)).replace("'","''")
          self.process_user_who(self.GetNetwork().GetName(), nick, ident, host, chan, gecos)
        # /cap req userhost-in-names
        # TODO - Figure out how to remove op/voice status.
        #if (msg.GetCode() == 353):
        #  if (msg.GetParam(1) == '='):
        #    self.PutModule(msg.GetParam(3))

        # mIRC /ialfill #channel
        # WHO #channel %acdfhlnrstu,995
        #                           0     1     2        3          4                  5           6
        # :sodium.libera.chat 354 KindOne 995 #channel ident some.fake.host.com sodium.libera.chat NICK H 0 2867 ACCOUNT :GECOS
        if (msg.GetCode() == 354):
          if (msg.GetParam(1) == '995'):
            nick  = msg.GetParam(6)
            ident = msg.GetParam(3)
            host  = msg.GetParam(4)
            chan  = str(msg.GetParam(2)).replace("'","''")
            account  = msg.GetParam(10)
            gecos = str(msg.GetParam(11)).replace("'","''")
            self.process_user_mirc_who(self.GetNetwork().GetName(), nick, ident, host, chan, account, gecos)


        # TODO - Deal with accountname.
        # TODO - Deal with QUIT event.
        #                           0       1       2
        # :sodium.libera.chat 396 KindOne new.vhost :is now...
        if (msg.GetCode() == 396):

            nick  = msg.GetParam(0)
            ident = self.GetNetwork().GetIRCNick().GetIdent()
            host  = msg.GetParam(1)
            gecos = self.GetNetwork().GetRealName()
            account = '0'
            for channel in self.GetNetwork().GetChans():
                self.process_chan_join(self.GetNetwork().GetName(), nick, ident, host, channel.GetName(), 'join', account, gecos)

    def process_user_who(self, network, nick, ident, host, channel, gecos):
        gecos = str(gecos).replace("'","''")
        channel = str(channel).replace("'","''")
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, gecos) \
            VALUES (?, ?, ?, ?, ?, '/who', '', strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '0', '0', ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set gecos = EXCLUDED.gecos, lastseen = strftime('%s', 'now');", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), gecos.lower()))
        self.conn.commit()

    def process_user_mirc_who(self, network, nick, ident, host, channel, account, gecos):
        gecos = str(gecos).replace("'","''")
        channel = str(channel).replace("'","''")
        #           n  n  i  h  c   event   t      first                  last             text     j    p   q    a  g
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account, gecos) \
            VALUES (?, ?, ?, ?, ?, '/who', '', strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '0', '0', ?, ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set gecos = EXCLUDED.gecos, account = EXCLUDED.account, lastseen = strftime('%s', 'now');", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), account.lower(), gecos.lower()))
        self.conn.commit()

    def process_join(self, network, nick, ident, host, channel, event, account, gecos):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account, gecos) \
            VALUES (?, ?, ?, ?, ?, ?, '', strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '0', '0', ?, ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set message = '', event = EXCLUDED.event, lastseen = strftime('%s', 'now'), joins = joins + 1, account = EXCLUDED.account, gecos = EXCLUDED.gecos;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), event, account.lower(), gecos.lower()))
        self.conn.commit()

    def process_part(self, network, nick, ident, host, channel, event, message):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits) \
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '1', '0') ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set event = EXCLUDED.event, message = EXCLUDED.message, lastseen = strftime('%s', 'now'), parts = parts + 1 ;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), event, message))
        self.conn.commit()

    def process_part_account(self, network, nick, ident, host, channel, event, message, account):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account) \
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '1', '0', ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set event = EXCLUDED.event, message = EXCLUDED.message, account = EXCLUDED.account, lastseen = strftime('%s', 'now'), parts = parts + 1 ;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), event, message, account.lower()))
        self.conn.commit()

    def process_quit(self, network, nick, ident, host, channel, event, message):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits) \
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '0', '1') ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set event = EXCLUDED.event, message = EXCLUDED.message, lastseen = strftime('%s', 'now'), quits = quits + 1 ;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), event, message))
        self.conn.commit()

    def process_quit_account(self, network, nick, ident, host, channel, event, message, account):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account) \
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '1', '0', '1', ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set event = EXCLUDED.event, message = EXCLUDED.message, lastseen = strftime('%s', 'now'), account = EXCLUDED.account, quits = quits + 1 ;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), event, message, account.lower()))
        self.conn.commit()

    def process_nick_change_new(self, network, nick, ident, host, channel, message):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits) \
            VALUES (?, ?, ?, ?, ?, 'nick', ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '0', '0', '0') ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set message = EXCLUDED.message, lastseen = strftime('%s', 'now'), event = EXCLUDED.event;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), message.lower()))
        self.conn.commit()

    def process_nick_change_old(self, network, nick, ident, host, channel, message):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits) \
            VALUES (?, ?, ?, ?, ?, 'nicked', ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '0', '0', '0') ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set message = EXCLUDED.message, lastseen = strftime('%s', 'now'), event = EXCLUDED.event;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), message.lower()))
        self.conn.commit()

    def process_nick_change_new_account(self, network, nick, ident, host, channel, message, account):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account) \
            VALUES (?, ?, ?, ?, ?, 'nick', ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '0', '0', '0', ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set message = EXCLUDED.message, lastseen = strftime('%s', 'now'), event = EXCLUDED.event, account = EXCLUDED.account;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), message.lower(), account.lower()))
        self.conn.commit()

    def process_nick_change_old_account(self, network, nick, ident, host, channel, message, account):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account) \
            VALUES (?, ?, ?, ?, ?, 'nicked', ?, strftime('%s', 'now'), strftime('%s', 'now'), '0', '0', '0', '0', ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set message = EXCLUDED.message, lastseen = strftime('%s', 'now'), event = EXCLUDED.event, account = EXCLUDED.account;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), message.lower(), account.lower()))
        self.conn.commit()

    # Channel messages and notices:
    # Private messages and notices:
    # NOTES:
    # A query will get a '1' in the joins column. Don't bother creating a second process_message for query windows.
    def process_message(self, network, nick, ident, host, channel, event, message):
        channel = str(channel).replace("'","''")
        message = str(message).replace("'","''")
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits) \
            VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now'), '1', '1', '0', '0') ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set event = EXCLUDED.event, message = EXCLUDED.message, lastseen = strftime('%s', 'now'), texts = texts + 1;", \
            (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower(), event, message))
        self.conn.commit()

    def process_user(self, network, nick, ident, host, channel):
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, firstseen, lastseen) VALUES (?, ?, ?, ?, ?, strftime('%s', 'now'), strftime('%s', 'now')) ON CONFLICT(network,nick,ident,host,channel) DO UPDATE set lastseen = strftime('%s', 'now') ;", (network.lower(), nick.lower(), ident.lower(), host.lower(), channel.lower()))
        self.conn.commit()

    def process_whois(self, network, whois_nick, whois_ident, whois_host, whois_account, whois_gecos):
        gecos = str(whois_gecos).replace("'","''")
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account, gecos) \
            VALUES (?, ?, ?, ?, '/whois', '', '', strftime('%s', 'now'), strftime('%s', 'now'), '0', '0', '0', '0', ?, ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set account = EXCLUDED.account ,gecos = EXCLUDED.gecos, lastseen = strftime('%s', 'now');", \
            (network.lower(), whois_nick.lower(), whois_ident.lower(), whois_host.lower(), whois_account.lower(), whois_gecos.lower()))
        self.conn.commit()

    def process_whowas(self, network, whowas_nick, whowas_ident, whowas_host, whowas_account, whowas_gecos):
        gecos = str(whowas_gecos).replace("'","''")
        self.cur.execute("INSERT INTO users (network, nick, ident, host, channel, event, message, firstseen, lastseen, texts, joins, parts, quits, account, gecos) \
            VALUES (?, ?, ?, ?, '/whowas', '', '', strftime('%s', 'now'), strftime('%s', 'now'), '0', '0', '0', '0', ?, ?) ON CONFLICT(network,nick,ident,host,channel) \
            DO UPDATE set account = EXCLUDED.account ,gecos = EXCLUDED.gecos;", \
            (network.lower(), whowas_nick.lower(), whowas_ident.lower(), whowas_host.lower(), whowas_account.lower(), whowas_gecos.lower()))
        self.conn.commit()

    def cmd_process(self, scope):
        self.PutModule("Processing {}.".format(scope))
        if scope == 'all':
            nets = self.GetUser().GetNetworks()
            for net in nets:
                chans = net.GetChans()
                for chan in chans:
                    nicks = chan.GetNicks()
                    for nick in nicks.items():
                        self.process_user(net.GetName(), nick[1].GetNick(), nick[1].GetIdent(), nick[1].GetHost(), chan.GetName())
        elif scope == 'network':
            chans = self.GetNetwork().GetChans()
            for chan in chans:
                nicks = chan.GetNicks()
                for nick in nicks.items():
                    self.process_user(self.GetNetwork().GetName(), nick[1].GetNick(), nick[1].GetIdent(), nick[1].GetHost(), chan.GetName())
        else:
            nicks = self.GetNetwork().FindChan(scope).GetNicks()
            for nick in nicks.items():
                self.process_user(self.GetNetwork().GetName(), nick[1].GetNick(), nick[1].GetIdent(), nick[1].GetHost(), scope)
        self.PutModule("{} processed.".format(scope))

    def cmd_history(self, type, user, deep):
        user_query = self.generate_user_query(type, user)
        self.PutModule("Looking up \x02history\x02 for \x02{}\x02, please be patient...".format(user.lower()))
        self.cur.execute("SELECT DISTINCT nick, host FROM users WHERE network = '{0}' AND ({1});".format(self.GetNetwork().GetName().lower(), re.sub(r'([\[\]])', '[\\1]', user_query)))
        data = self.cur.fetchall()
        nicks = set(); idents = set(); hosts = set();
        if len(data) > 0:
            for row in data:
                nicks.add("nick = '" + row[0] + "' OR"); hosts.add("host = '" + row[1] + "' OR");
            self.cur.execute("SELECT DISTINCT nick, ident, host FROM users WHERE network = '{}' AND ({} {})".format(self.GetNetwork().GetName().lower(), ' '.join(nicks), ' '.join(hosts)[:-3]))
            data = self.cur.fetchall()
            nicks.clear(); hosts.clear()
            for row in data:
                if deep:
                    nicks.add(row[0]); idents.add(row[1]); hosts.add(row[2]);
                    self.cur.execute("SELECT DISTINCT nick, ident, host FROM users WHERE network = '{0}' AND (nick GLOB '{1}' OR ident GLOB '{2}' OR host GLOB '{3}');".format(self.GetNetwork().GetName().lower(), re.sub(r'([\[\]])', '[\\1]', row[0]), re.sub(r'([\[\]])', '[\\1]', row[1]), re.sub(r'([\[\]])', '[\\1]', row[2])))
                    data_inner = self.cur.fetchall()
                    for row_inner in data_inner:
                        nicks.add(row_inner[0]); idents.add(row_inner[1]); hosts.add(row_inner[2]);
                else:
                    nicks.add(row[0]); idents.add(row[1]); hosts.add(row[2]);
            self.display_results(nicks, idents, hosts)
            self.PutModule("History for {} \x02complete\x02.".format(user.lower()))
        else:
            self.PutModule("No history found for \x02{}\x02".format(user.lower()))

    def display_results(self, nicks, idents, hosts):
        nicks = sorted(list(nicks)); idents = sorted(list(idents)); hosts = sorted(list(hosts));
        size = 100
        index = 0
        while(index < len(nicks)):
            self.PutModule("\x02Nick(s):\x02 " + ', '.join(nicks[index:index+size]))
            index += size
        index = 0
        while(index < len(idents)):
            self.PutModule("\x02Ident(s):\x02 " + ', '.join(idents[index:index+size]))
            index += size
        index = 0
        while(index < len(hosts)):
            self.PutModule("\x02Host(s):\x02 " + ', '.join(hosts[index:index+size]))
            index += size

    def cmd_seen(self, type, user, channel):
        user_query = self.generate_user_query(type, user)
        if channel:
            self.cur.execute("SELECT nick, ident, host, channel, event, message, MAX(lastseen)) FROM (SELECT * from users WHERE message IS NOT NULL) WHERE network = '{0}' AND channel = '{1}' AND ({2});".format(self.GetNetwork().GetName().lower(), channel.lower(), re.sub(r'([\[\]])', '[\\1]', user_query)))

        else:
            self.cur.execute("SELECT nick, ident, host, channel, event, message, MAX(lastseen)) FROM (SELECT * from users WHERE message IS NOT NULL) \
                 WHERE network = '{0}' AND ({1});".format(self.GetNetwork().GetName().lower(), re.sub(r'([\[\]])', '[\\1]', user_query)))
        data = self.cur.fetchone()
        try:
            self.PutModule("\x02{}\x02 ({}@{}) was last seen in \x02{}\x02 at \x02{}\x02 doing \x02{}\x02: \"{}\"."\
                .format(data[0], data[1], data[2],data[3], datetime.datetime.fromtimestamp(int(data[6])).strftime('%Y-%m-%d %H:%M:%S'), data[4], data[5]))
        except:
            if channel:
                self.PutModule("\x02{}\x02 has \x02\x034not\x03\x02 been seen in \x02{}\x02.".format(user.lower(), channel.lower()))
            else:
                self.PutModule("\x02{}\x02 has \x02\x034not\x03\x02 been seen.".format(user.lower()))

    def cmd_users(self, type, user):
        user_query = self.generate_user_query(type, user)
        self.cur.execute("SELECT DISTINCT nick, host, ident FROM users WHERE network = '{0}' AND ({1});".format(self.GetNetwork().GetName().lower(), re.sub(r'([\[\]])', '[\\1]', user_query)))
        data = self.cur.fetchall()
        chans = set()
        for row in data:
            chans.add(row[0])
        self.PutModule("\x02{}\x02 has been seen in \x02channels\x02: {}".format(user.lower(), ', '.join(sorted(chans))))

    def cmd_channels(self, type, users):
        chan_lists = []
        for user in users:
            user_query = self.generate_user_query(type, user)
            chans = []
            self.cur.execute("SELECT DISTINCT channel FROM users WHERE network = '{0}' AND ({1});".format(self.GetNetwork().GetName().lower(), re.sub(r'([\[\]])', '[\\1]', user_query)))
            data = self.cur.fetchall()
            for row in data:
                chans.append(row[0])
            chan_lists.append(chans)
        shared_chans = set(chan_lists[0])
        for chan in chan_lists[1:]:
            shared_chans.intersection_update(chan)
        self.PutModule("Common \x02channels\x02 for \x02{}:\x02 {}".format(', '.join(users), ', '.join(sorted(shared_chans))))

    def cmd_users(self, channels):
        nick_lists = []; ident_lists = []; host_lists = [];
        for channel in channels:
            nicks = []; idents = []; hosts = [];
            self.cur.execute("SELECT DISTINCT nick, ident, host FROM users WHERE network = '{}' AND channel = '{}';".format(self.GetNetwork().GetName().lower(), channel.lower()))
            data = self.cur.fetchall()
            for row in data:
                nicks.append(row[0]); idents.append(row[1]); hosts.append(row[2]);
            nick_lists.append(nicks); ident_lists.append(idents); host_lists.append(hosts);
        nicks = set(nick_lists[0]); idents = set(ident_lists[0]); hosts = set(host_lists[0]);
        for nick in nick_lists[1:]:
            nicks.intersection_update(nick)
        for ident in ident_lists[1:]:
            idents.intersection_update(ident)
        for host in host_lists[1:]:
            hosts.intersection_update(host)
        self.PutModule("Common \x02users\x02 for \x02{}:\x02".format(', '.join(channels)))
        self.display_results(nicks, idents, hosts)

    def cmd_compare_users(self, type, users):
        self.PutModule("Users compared.")

    def cmd_geo(self, type, user):
        user_query = self.generate_user_query(type, user)

        ipv4 = '(?:[0-9]{1,3}(\.|\-)){3}[0-9]{1,3}'
        ipv6 = '^((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4}))*::((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4}))*|((?:[0-9A-Fa-f]{1,4}))((?::[0-9A-Fa-f]{1,4})){7}$'
        rdns = '^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$'

        if (re.search(ipv6, str(user)) or re.search(ipv4, str(user)) or (re.search(rdns, str(user)) and '.' in str(user))):
            host = user

        self.cur.execute("SELECT host, nick, ident FROM users WHERE network = '{0}' AND ({1}) ORDER BY time DESC;".format(self.GetNetwork().GetName().lower(), re.sub(r'([\[\]])', '[\\1]', user_query)))
        data = self.cur.fetchall()
        for row in data:
            if (re.search(ipv6, str(row[0])) or re.search(ipv4, str(row[0])) or (re.search(rdns, str(row[0])) and '.' in str(row[0]))):
                host = row[0]
                nick = row[1]
                ident = row[2]
                break
        try:
            if re.search(ipv4, str(host)):
                ip = re.sub('[^\w.]',".",((re.search(ipv4, str(host))).group(0)))
            elif re.search(ipv6, str(host)) or re.search(rdns, str(host)):
                ip = str(host)
            url = 'http://ip-api.com/json/' + ip + '?fields=country,regionName,city,lat,lon,timezone,mobile,proxy,query,reverse,status,message'
            loc = requests.get(url)
            loc_json = loc.json()

            if loc_json["status"] != "fail":
                try:
                    user = "\x02{}\x02 ({}@{})".format(nick.lower(), ident.lower(), host.lower())
                except:
                    user = "\x02{}\x02 (no matching user)".format(user.lower())
                self.PutModule("{} is located in \x02{}, {}, {}\x02 ({}, {}) / Timezone: {} / Proxy: {} / Mobile: {} / IP: {} / rDNS: {}".format(user, loc_json["city"], loc_json["regionName"], loc_json["country"], loc_json["lat"], loc_json["lon"], loc_json["timezone"], loc_json["proxy"], loc_json["mobile"], loc_json["query"], loc_json["reverse"]))
            else:
                self.PutModule("\x02\x034Unable to geolocate\x03\x02 user \x02{}\x02. (Reason: {})".format(user.lower(), loc_json["message"]))
        except:
            self.PutModule("\x02\x034No valid host\x03\x02 for user \x02{}\x02".format(user.lower()))

    def generate_user_query(self, type, user):
        if type:
            query = "{0} GLOB '{1}'".format(type, user.lower())
        else:
            query = "nick GLOB '{0}' OR ident GLOB '{0}' OR host GLOB '{0}'".format(user.lower())
        return query

    def cmd_stats(self):
        self.cur.execute("SELECT COUNT(DISTINCT nick), COUNT(DISTINCT ident), COUNT(DISTINCT host), COUNT(DISTINCT channel), COUNT(*) FROM users WHERE network = '{0}';".format(self.GetNetwork().GetName().lower()))
        data = self.cur.fetchone()
        self.PutModule("\x02Nick(s):\x02 {}".format(data[0]))
        self.PutModule("\x02Ident(s):\x02 {}".format(data[1]))
        self.PutModule("\x02Host(s):\x02 {}".format(data[2]))
        self.PutModule("\x02Channel(s):\x02 {}".format(data[3]))
        self.PutModule("\x02Size:\x02 {} MB".format(os.path.getsize(self.GetSavePath() + "/aka.db") >> 20))
        self.PutModule("\x02Total Records:\x02 {}".format(data[4]))

    def cmd_who(self, scope):
        if scope == 'all':
            nets = self.GetUser().GetNetworks()
            for net in nets:
                chans = net.GetChans()
                for chan in chans:
                    self.PutIRC("WHO %s" % chan.GetName())
        elif scope == 'network':
            chans = self.GetNetwork().GetChans()
            for chan in chans:
                self.PutIRC("WHO %s" % chan.GetName())
        else:
           self.PutIRC("WHO %s" % scope)
        self.PutModule("{} WHO updates triggered. Please wait several minutes for ZNC to receive the updated data from the IRC server(s) and then run \x02process\x02 to add these updates to the database".format(scope))

    def cmd_about(self):
        self.PutModule("\x02aka")
        self.PutModule("\x02Description:\x02 {}".format(self.description))
        self.PutModule("\x02Version:\x02 {}".format(version))
        self.PutModule("\x02Updated:\x02 {}".format(updated))
        #self.PutModule("\x02Documenation:\x02 http://wiki.znc.in/Aka")
        self.PutModule("\x02Source:\x02 https://github.com/RealKindOne/znc-aka")

    def cmd_rawquery(self, query):
        try:
            query = ' '.join(query)
            count = 0
            for row in self.cur.execute(query):
                self.PutModule(str(row))
                count += 1
            self.conn.commit()
            if self.cur.rowcount >= 0:
                self.PutModule('Query successful: %s rows affected' % self.cur.rowcount)
            else:
                self.PutModule('%s records retrieved' % count)
        except sqlite3.Error as e:
            self.PutModule('Error: %s' % e)

    def cmd_getconfig(self):
        for key, value in self.nv.items():
            self.PutModule("%s = %s" % (key, value))

    def cmd_config(self, var_name, value):
        valid = True
        bools = ["WHO_ON_JOIN", "RECORD_WHOIS", "RECORD_WHOWAS"]
        if var_name.upper() in bools:
            if not str(value).upper() == "TRUE" and not str(value).upper() == "FALSE":
                valid = False
                self.PutModule("%s must be either True or False" % var_name)
        else:
            valid = False
            self.PutModule("%s is not a valid setting." % var_name)

        if valid:
            self.SetNV(str(var_name).upper(), str(value).upper(), True)
            self.PutModule("%s => %s" % (var_name.upper(), value.upper()))

    def configure(self):

        if not os.path.exists(self.GetSavePath() + "/.registry"):
            for setting in DEFAULT_CONFIG:
                self.SetNV(setting.upper(), str(DEFAULT_CONFIG[setting]).upper(), True)

        if os.path.exists(self.GetSavePath() + "/.registry"):
            for setting in DEFAULT_CONFIG:
                if setting not in self.nv:
                    self.SetNV(setting.upper(), str(DEFAULT_CONFIG[setting]).upper(), True)
            for setting in self.nv:
                if self.nv[setting] != self.nv[setting].upper():
                    self.SetNV(setting.upper(), self.nv[setting].upper(), True)

    def db_setup(self):
        self.conn = sqlite3.connect(self.GetSavePath() + "/aka.db")
        self.cur = self.conn.cursor()
        self.cur.execute("PRAGMA auto_vacuum=2;")
        self.cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, network TEXT, nick TEXT, ident TEXT, host TEXT, channel TEXT, event TEXT, message TEXT, firstseen INTEGER, lastseen INTEGER, texts INTEGER, joins INTEGER, parts INTEGER, quits INTEGER, account TEXT, gecos TEXT, UNIQUE (network, nick, ident, host, channel));")

        self.cur.execute("CREATE INDEX IF NOT EXISTS networks ON users (network ASC);")
        self.cur.execute("CREATE INDEX IF NOT EXISTS nicks ON users (nick ASC);")

        # Update any existing query events that are not set at '0'.
        # self.cur.execute("UPDATE users SET joins = '0' WHERE channel = 'query' and joins = '1';")
        self.conn.commit()

        # Maybe support this in a setting?
        #self.cur.execute("VACUUM;")

    def OnModCommand(self, command):
        line = command.lower()
        commands = line.split()
        cmds = ["all", "history", "config", "getconfig", "users", "channels", "sharedchans", "sharedusers", "seen", "geo", "process", "who", "rawquery", "import", "stats", "about", "help"]

        if commands[0] in cmds:
            if "--type=" in line:
                type = (line.split('=')[1]).lower()
                if type != 'nick' and type != 'host' and type != 'ident':
                    self.PutModule("Valid types are \x02nick\x02, \x02ident\x02, and \x02host\x02.")
                    return znc.HALT
                else:
                    del commands[-1]
            else:
                type = None
            if commands[0] == "all":
                try:
                    self.PutModule("Getting \x02all\x02 for \x02{}\x02.".format(commands[1]))
                    self.cmd_history(type, commands[1], False)
                    self.cmd_channels(type, commands[1:])
                    self.cmd_seen(type, commands[1], None)
                    self.cmd_geo(type, commands[1])
                    self.PutModule("All \x02complete\x02.")
                except:
                    self.PutModule("You must specify a user.")
            elif commands[0] == "history":
                try:
                    if "--deep" in line:
                        self.cmd_history(type, commands[1], True)
                    else:
                        self.cmd_history(type, commands[1], False)
                except:
                    self.PutModule("You must specify a user.")
            elif commands[0] == "users" or commands[0] == "channels" or commands[0] == "sharedchans" or commands[0] == "sharedusers":
                if commands[0] == 'channels' or commands[0] == 'sharedchans':
                    try:
                        self.cmd_channels(type, commands[1:])
                    except:
                        self.PutModule("You must specify at least one user.")
                elif commands[0] == 'users' or commands[0] == 'sharedusers':
                    try:
                        self.cmd_users(commands[1:])
                    except:
                        self.PutModule("You must specify at least one channel.")
            elif commands[0] == "seen":
                try:
                    try:
                        self.cmd_seen(type, commands[1], commands[2])
                    except:
                        self.cmd_seen(type, commands[1], None)
                except:
                    self.PutModule("You must specify a user and optional channel.")
            elif commands[0] == "geo":
                try:
                    self.cmd_geo(type, commands[1])
                except:
                    self.PutModule("You must specify a user, host, or IP address.")
            elif commands[0] == "process" or commands[0] == "who":
                try:
                    if commands[0] == "process":
                        self.cmd_process(commands[1])
                    elif commands[0] == "who":
                        self.cmd_who(commands[1])
                except:
                    self.PutModule("Valid options: #channel, network, all")
            elif commands[0] == "rawquery":
                try:
                    self.cmd_rawquery(commands[1:])
                except:
                    self.PutModule("You must specify a query.")
            elif commands[0] == "stats":
                self.cmd_stats()
            elif command.split()[0] == "config":
                self.cmd_config(command.split()[1], command.split()[2])
            elif command.split()[0] == "getconfig":
                self.cmd_getconfig()

            elif commands[0] == "about":
                self.cmd_about()
            elif commands[0] == "help":
                self.cmd_help()
        else:
            self.PutModule("Invalid command. See \x02help\x02 for a list of available commands.")

    def cmd_help(self):
        help = znc.CTable()
        help.AddColumn("Command")
        help.AddColumn("Arguments")
        help.AddColumn("Description")
        for x, y, z in self.HELP_COMMANDS:
            help.AddRow()
            help.SetCell("Command", x)
            help.SetCell("Arguments", y)
            help.SetCell("Description", z)
        self.PutModule(help)