#!/usr/bin/env python

from __future__ import with_statement
import ConfigParser
import datetime
import json
import linecache
import logging
import os
import Queue
import random                                                                                           
import re
import sqlalchemy
import string
import sys
import time
import threading
import urllib
import smtplib

from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText

import flask
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import clients
import rcon
import subprocess

#import bottle

class monitor3(object):
    def __init__(self):
        if os.path.isfile(os.path.join('', '.monitor.lock')):
            print 'Instance of monitor already running...'
            sys.exit(0)
        else:
            f = open(os.path.join('', '.monitor.lock'), 'w')
            f.write('running!')
            f.close()
            
        #are we running? hah!
        self.running = True
        #set up the loggers
        self.logger = logging.getLogger('chatlog')
        self.logger.setLevel(logging.INFO)
        ch = logging.FileHandler('chatlog.txt')
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.log = logging.getLogger('gamelog')
        self.log.setLevel(logging.INFO)
        ch = logging.FileHandler('logfile.txt')
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter(None)
        ch.setFormatter(formatter)
        self.log.addHandler(ch)

        #read config options
        config = ConfigParser.ConfigParser()
        config.readfp(open(os.path.abspath('.') + '//config.cfg'))
        self.host = config.get('server', 'ip')
        self.port = int(config.get('server', 'port'))
        self.pw = config.get('server', 'pass')
        self.dbhost = config.get('mysql', 'host')
        self.dbuser = config.get('mysql', 'user')
        self.dbpasswd = config.get('mysql', 'passwd')
        self.dbname = config.get('mysql', 'db')
        self.webip = config.get('web', 'ip')
        self.webport = config.get('web', 'port')
        self.gmail_user = config.get('email', 'user')
        self.gmail_pwd = config.get('email', 'pass')
        self.mail_to = config.get('email', 'send_to')
        
        #try:
        #    self.ip = urllib.urlopen('http://whatismyip.org/').read()
        #except:
        #    pass
        
        self.sqlerror = False

        self.PBMessages = (
            (re.compile(r'^PunkBuster Server: Running PB Scheduled Task \(slot #(?P<slot>\d+)\)\s+(?P<task>.*)$'), 'PBScheduledTask'),
            (re.compile(r'^PunkBuster Server: Lost Connection \(slot #(?P<slot>\d+)\) (?P<ip>[^:]+):(?P<port>\d+) (?P<pbuid>[^\s]+)\(-\)\s(?P<name>.+)$'), 'PBLostConnection'),
            (re.compile(r'^PunkBuster Server: Master Query Sent to \((?P<pbmaster>[^\s]+)\) (?P<ip>[^:]+)$'), 'PBMasterQuerySent'),
            (re.compile(r'^PunkBuster Server: Player GUID Computed (?P<pbid>[0-9a-fA-F]+)\(-\) \(slot #(?P<slot>\d+)\) (?P<ip>[^:]+):(?P<port>\d+)\s(?P<name>.+)$'), 'PBPlayerGuid'),
            (re.compile(r'^PunkBuster Server: New Connection \(slot #(?P<slot>\d+)\) (?P<ip>[^:]+):(?P<port>\d+) \[(?P<something>[^\s]+)\]\s"(?P<name>.+)".*$'), 'PBNewConnection')
            )

        self.mapnames = ['Panama Canal', 'Valparaiso', 'Laguna Alta', 'Isla Inocentes', 'Atacama Desert', 'Africa Harbor',
                    'White Pass', 'Nelson Bay', 'Laguna Presa', 'Port Valdez']
        
        self.ALLmaps = {'Panama Canal':'MP_001', 'Valparioso':'MP_002', 'Laguna Alta':'MP_003', 'Isla Inocentes':'MP_004',
               'Atacama Desert':'MP_005', 'Africa Harbor':'MP_006', 'White Pass':'MP_007', 'Nelson Bay':'MP_008',
               'Laguna Presa':'MP_009', 'Port Valdez':'MP_012'}
        self.CONQUEST = {'Panama Canal':'MP_003', 'Atacama Desert':'MP_005', 'Africa Harbor':'MP_006CQ',
                        'White Pass':'MP_007', 'Laguna Presa':'MP_009CQ'}
        self.RUSH = {'Valparaiso':'MP_002', 'Isla Inocentes':'MP_004', 'Neslon Bay':'MP_008', 'Port Valdez':'MP_012GR',
                   'Laguna Presa':'MP_009GR'}
        self.SQDM = {'Isla Inocentes':'MP_004SDM', 'Africa Harbor':'MP_006SDM', 'White Pass':'MP_007SDM', 'Laguna Presa':'MP_009SDM'}
        self.SQRUSH = {'Panama Canal':'MP_001SR', 'Valparaiso':'MP_002SR', 'Atacama Desert':'MP_005SR', 'Port Valdez':'MP_012SR'}
        
        self.commands = {'!rules':'Show the server rules to player', '!help': 'Show player general help.  Takes optional argument command for specific help', '!stats':'Show all players kills, deaths, and ratio for player', 
                        '!chuck':'Show all players a random Chuck Norris message', '!punish':'Required argument [player].  Kills [player] and displays attention getting message', 
                        '!map':'Required argument [map].  Changes map to [map] with immediate effect.', '!restart':'Restarts current map', '!kick':'Required arguments [player],[time],and [reason] Kicks [player] for [time] for [reason]',
                        '!ban':'Required arguments [player] and [reason].  Bans [player] for [reason]', '!gametype':'Required argument [gametype].  Changes server to [gametype] with immediate effect.'}
        
        self.command = re.compile(r'^(?P<cid>\'[^\']{2,}\'|[0-9]+|[^\s]{2,}|@[0-9]+)\s?(?P<parms>.*)$')

        self.players = clients.clients()
        self.queue = Queue.Queue()
        self.chat = []
        self.kills = []
        self.map = ''
        self.round = ['0', '0']
        self.scores = [0,0,0]
        self.pcount = 0
        self.serverrank = ''
        self.serverperc = ''
        self.gametype = 'None'
        self.rc = rcon.RCon()
        self.eventmon = rcon.RCon()

        self.badwords = []
        with open('badwords.txt', 'r') as f:
            for line in f:
                if line:
                    self.badwords.append(line.strip('\n'))
        
        self.banwords = []
        with open('banlist.txt', 'r') as f:
            for line in f:
                if line:
                    self.banwords.append(line.strip('\n'))
        
        eq = threading.Thread(target=self.event_queue)
        eq.name = 'events'
        eq.start()
        #hw = threading.Thread(target=self.host_watch)
        #hw.name = 'host_watch'
        #hw.start()
        self.do_first_run()
        threading.Thread(target=self.status).start()
        self.main_loop()

    def main_loop(self):
        while self.running:
            if self.eventmon.serverSocket is None:
                try:
                    self.eventmon.connect(self.host, self.port, self.pw)
                    self.eventmon.serverSocket.send(self.eventmon.EncodeClientRequest(["eventsEnabled", "true"]))
                    self.eventmon.serverSocket.settimeout(90)
                except rcon.socket.error:
                    time.sleep(10)
                    continue
            if self.rc.serverSocket is None:
                try:
                    self.rc.connect(self.host, self.port, self.pw)
                    self.rc.serverSocket.settimeout(90)
                except rcon.socket.error:
                    time.sleep(10)
                    continue

            words = None
            while self.running and self.eventmon.serverSocket is not None and self.rc.serverSocket is not None:
                try:
                    event, self.eventmon.receiveBuffer = self.eventmon.receivePacket(self.eventmon.serverSocket,
                                                                                        self.eventmon.receiveBuffer)
                    [isFromServer, isResponse, sequence, words] = self.eventmon.DecodePacket(event)

                    if words[0] == "OK":
                        continue
                    self.queue.put(words)

                except rcon.socket.timeout:
                    time.sleep(10)
                    self.rc.close()
                    self.eventmon.serverSocket.close()
                    break
                except rcon.socket.error:
                    time.sleep(10)
                    self.rc.close()
                    self.eventmon.close()
                    break
                except Exception, detail:
                    print 'CRASH:', detail
                    time.sleep(15)
                    self.rc.close()
                    self.eventmon.close()
                    break
                except KeyboardInterrupt:
                    print 'Keyboard interrupt caught, exiting...'
                    print 'There may be a delay while we close the network connections...'
                    self.stop_status()
                    self.running = False
                    os.remove(os.path.join('', '.monitor.lock'))

    def event_queue(self):
        while self.running:
            if not self.queue.empty():
                func = None
                task = self.queue.get()
                match = re.search(r"^(?P<actor>[^.]+)\.on(?P<event>.+)$", task[0])
                if match:
                    func = '%s%s' % (string.capitalize(match.group('actor')), \
                               string.capitalize(match.group('event')))
                if match and hasattr(self, func):
                    try:
                        getattr(self, func)(task[1:])
                    except:
                        pass
                else:
                    print "TODO:", func, task[1:]
                self.queue.task_done()
            time.sleep(.01)
            
    def host_watch(self):
        while self.running:
            try:
                newip = urllib.urlopen('http://whatismyip.org/').read()
                if newip != self.ip:
                    print 'SENT EMAIL ABOUT NEW IP'
                    self.mail('WAFFLES! WARNING!  IP CHANGE OCCURED!', 'Monitor\'s host has a new ip!\n %s' % newip)
                    self.ip = newip
                    time.sleep(1000)
                else:
                    time.sleep(1000)
            except Exception, error:
                print 'error in host_watch'
                print error
                continue   
    '''
    player.onSpawn <soldier name: string> <kit: string> <weapons: 3 x string> <gadgets: 3 x string>
    '''        
    def PlayerSpawn(self, data):
        try:
            player = self.players.getPlayer(data[0])
        except KeyError:
            self.PlayerJoin(data[0])
            time.sleep(.5)
            player = self.players.getPlayer(data[0])
        player.kit = data[1]
        #perhaps adding a "spawn time" to a player object to track time alive, spawnkilling, etc?
        
    #server.onRoundOver <winning team: Team ID>
    def ServerRoundover(self, data):
        print 'roundOver', data
        self.chat_queue('Round finished - Winners: %s' % data[0])
        self.log.info('%s;onRoundOver;%s' % (str(time.time()), data[0]))
    
    #server.onRoundOverPlayers <end-of-round soldier info : player info block>
    def ServerRoundoverteamscores(self, data):
        print 'teamscores', data
        pass
    
    def ServerLoadinglevel(self, data):
        self.map = data[0].strip('Levels/')
        self.round[0] = data[1]
        self.round[1] = data[2]
        self.chat_queue('Map changed to: %s - Round %s of %s' % (self.map_name(self.map), data[1], data[2]))
        self.log.info('%s;onMap;%s' % (str(time.time()), self.map))

    def ServerLevelstarted(self, data):
        pass
    
    def PlayerKicked(self, data):
        self.chat_queue(data[1])
        self.logger.info(data[1])
        self.rc.sndcmd(self.rc.SAY, '\'%s was kicked from the server\' all' % data[0])
        
    def PlayerLeave(self, data):
        try:
            self.players.disconnect(data[0])
            self.pcount -= 1
        except KeyError:
            pass
        self.log.info('%s;onLeave;%s' % (str(time.time()), data[0]))

    def PlayerAuthenticated(self, data):
        try:
            player = self.players.getPlayer(data[0])
        except KeyError:
            self.PlayerJoin(data[0])
            time.sleep(.5)
            player = self.players.getPlayer(data[0])
        player.eaguid = data[1]

    def PlayerSquadchange(self, data):
        self.PlayerTeamchange(data)

    def PlayerTeamchange(self, data):
        try:
            player = self.players.getPlayer(data[0])
        except KeyError:
            return
        player.team = data[1]
        player.squad = data[2]

    def PunkbusterMessage(self, data):
        for regex, name in self.PBMessages:
            match = re.match(regex, str(data[0]).strip())
            if match:
                if match and hasattr(self, name):
                    getattr(self, name)(match)
                    return
                else:
                    print 'todo:', data

    def PBLostConnection(self, match):
        try:
            player = self.players.getPlayer(match.group('name'))
            #self.write_to_DB(player)
            self.players.disconnect(player.name)
            self.pcount -= 1
        except KeyError:
            pass

    def PBPlayerGuid(self, match):
        player = self.players.getPlayer(match.group('name'))
        player.pbid = match.group('pbid')

    def PBNewConnection(self, match):
        try:
            player = self.players.getPlayer(match.group('name'))
            player.seen = self.has_been_seen(player)
        #no onJoin event?
        except KeyError:
            self.players.connect('', match.group('name'), 0)
            threading.Timer(60.0, self.new_player, args=[self.players.getPlayer(match.group('name'))]).start()
            player = self.players.getPlayer(match.group('name'))
            player.seen = self.has_been_seen(player)
        finally:
            player.ip = match.group('ip')
            player.pbslot = match.group('slot')
            self.pcount += 1

    #every 60 seconds an automated server message appears, so we will use an already existing timer to regulate our
    #hammering the server for player count verification.  hacky?  yes.  Awesome?  you betcha
    def PBScheduledTask(self, match):
        try:
            data, response = self.rc.sndcmd(self.rc.PINFO, 'all')
            if response:
                #self.pcount = int(data[11])
                if self.pcount != int(data[11]):
                    self.pcount = int(data[11])
                    for p in self.players.getAll():
                        if not data.count(p.name):
                            for i in threading._enumerate():
                                if i.name == p.name:
                                    return
                            self.write_to_DB(p)
                            self.players.disconnect(p.name)
            data, response = self.rc.sndcmd(self.rc.SINFO)
            if response:
                self.scores = [int(round(float(data[9]),0)), int(round(float(data[10]),0)), int(round(float(data[11]),0))]
        except Exception, error:
            print 'error in count watch'
            print error
            #print 'players dict:', len(self.players)

    #same as above, but for the gametype
    def PBMasterQuerySent(self, match):
        try:
            data, response = self.rc.sndcmd(self.rc.SINFO)
            if response:
                self.gametype = data[4]
        except Exception, error:
            print 'error in gametype watch'
            print error
        matchrank = re.compile('(?P<rank>\d+)(?P<ranksuf>\D{2})\s\(<span>(?P<percentile>\d+)(?P<percentsuf>\D{2})')
        try:
            content = urllib.urlopen("http://www.gametracker.com/server_info/68.232.162.167:19567/").read()
    
            m = re.search(matchrank, content)
            if m:
                self.serverrank = m.group('rank') + m.group('ranksuf')
                self.serverperc = m.group('percentile') + m.group('percentsuf')
        except Exception, error:
            print 'error in get_server_rank'
            print error
            
    def PlayerJoin(self, data):
        if data:
            self.players.connect('', data[0], 0)
            newp = threading.Timer(60.0, self.new_player, args=[self.players.getPlayer(data[0])])
            newp.name = self.players.getPlayer(data[0]).name
            newp.start()
            self.pcount += 1
            self.log.info('%s;onJoin;%s' % (str(time.time()), data[0]))

    #player.onKill <killing soldier name: string> <killed soldier name: string> <weapon: string>
    #<headshot: boolean> <killer location: 3 x integer> <killed location: 3 x integes> 
    def PlayerKill(self, data):
        try:
            attacker = self.players.getPlayer(data[0])
        except KeyError:
            self.PlayerJoin(data[0])
            time.sleep(.5)
            attacker = self.players.getPlayer(data[0])
        try:
            victim = self.players.getPlayer(data[1])
        except KeyError:
            self.PlayerJoin(data[1])
            time.sleep(.5)
            victim = self.players.getPlayer(data[1])
            
        weapon = data[2]
        headshot = data[3]
        #location of players on map with a +-10meter random error.  maybe used in future
        attacker_loc = data[5:8]
        victime_loc = data[7:]

        self.kill_queue(attacker, victim, weapon, headshot)

        if attacker.name != victim.name:
            if attacker.team == victim.team:
                attacker.teamkill()
            else:
                attacker.kill()
                if not attacker.streak % 10:
                    streak = string.Template(linecache.getline('streak.txt', random.randint(1,5)))
                    streak = streak.substitute(tag=attacker.tag, name=attacker.name, streak=str(attacker.streak)).strip('\n') +  ' all'
                    self.rc.sndcmd(self.rc.SAY, streak)
                    #self.rc.sndcmd(self.rc.SAY, '\'%s %s is on FIRE with %i kills since their last death!\' all'
                    #    (attacker.tags, attacker.name, attacker.kills))
        if victim.streak >= 10:
            streak = string.Template(linecache.getline('streakend.txt', random.randint(1,4)))
            streak = streak.substitute(victag=victim.tag, vicname=victim.name, streak=str(victim.streak), killertag=attacker.tag, killername=attacker.name).strip('\n') + ' all'
            self.rc.sndcmd(self.rc.SAY, streak)
        victim.death()
        self.log.info('%s;onKill;%s;%s;%s;%s;%s;%s' % (str(time.time()), attacker.name, attacker.team, victim.name, victim.team, weapon, headshot))

    def search_player(self, player, search):
        plist = []
        for p in self.players.getAll():
            if re.search(search, p.name, re.I):
                plist.append(p)
        if len(plist) != 1:
            self.rc.sndcmd(self.rc.SAY, '\'Ambiguous player defined or player not found, try being more specific...\' player \'%s\'' %
                player.name)
            return None
        else:
            return plist[0]

    def PlayerChat(self, data):
        if data and not data[0] == 'Server':
            #fix the random empty line of doom?  hacky, for sure!
            if not data[0] or not data[1] or not data[2]:
                return
            try:
                player = self.players.getPlayer(data[0])
            except KeyError:
                self.PlayerJoin(data[0])
                player = self.players.getPlayer(data[0])
                
            chat = data[1]
            who = data[2]

            if chat.startswith('/'):
                chat = chat[1:]
            if not chat:
                return
            self.chat_queue(player.name + ': ' + who + ': ' + chat)
            self.logger.info(player.name + ': ' + who + ': ' + chat)

            for word in self.badwords:
                if re.search('\\b' + word + '\\b', chat, re.I):
                    if player.warning:
                        self.rc.sndcmd(self.rc.KICK, '\"%s\" \"10\" \"That language is not acceptable here.\"\'' % player.name)
                        break
                    else:
                        self.rc.sndcmd(self.rc.SAY, '\'%s: THAT LANGUAGE WILL NOT BE TOLERATED HERE.  THIS IS YOUR ONLY WARNING!!!\' \
                                        player \"%s\"' % (player.name, player.name))
                        player.warning = 1
                        self.chat_queue('Player %s was warned for bad language' % player.name)
                        self.logger.info('Player %s was warned for bad language' % player.name)
                        break
            for word in self.banwords:
                if re.search('\\b' + word + '\\b', chat, re.I):
                    if player.pbid:
                        if player.ip:
                            self.rc.sndcmd(self.rc.BAN, '\"%s\" \"%s\" \"%s\" \"We do not tolerate that language here\""' % (player.pbid, player.name, player.ip))
                            break
                        else:
                            self.rc.sndcmd(self.rc.BAN, '\"%s\" \"%s\" \"???\" \"We do not tolerate that language here\""' % (player.pbid, player.name))
                            break
            
            #display command help to player, general help, or specific help available!
            if chat.lower().startswith('!help') and player.power >= player.PUBLIC:
                commands = ['!rules, ', '!help, ', '!stats, ', '!chuck, ']
                if player.power >= player.RECRUIT:
                    commands.append('!punish, ')
                    commands.append('!map, ')
                if player.power >= player.MOD:
                    commands.append('!gametype, ')
                    commands.append('!restart, ')
                if player.power >= player.ADMIN:
                    commands.append('!kick, ')
                if player.power >= player.SUPER:
                    commands.append('!ban')
                p = re.match(self.command, chat)
                if p.group('parms'):
                    if self.commands.has_key(p.group('parms')):
                        if commands.count(p.group('parms') + ', ') or commands.count('!ban'):
                                self.rc.sndcmd(self.rc.SAY, '\'%s - %s\' player \'%s\'' % (p.group('parms'), self.commands[p.group('parms')], player.name))
                    else:
                        self.rc.sndcmd(self.rc.SAY, '\'Command not found or command not available to you.  Please try again.\' player \'%s\'' % player.name)                           
                else:   
                    self.rc.sndcmd(self.rc.SAY, '\'Available commands to %s.  Try !help [command] for more help\' player \'%s\'' % (player.name, player.name))
                    time.sleep(.001)
                    self.rc.sndcmd(self.rc.SAY, '\'%s\' player \'%s\'' % (''.join(commands), player.name))
                return
            
            if re.search('!stats', chat, re.I):
                if player.deaths == 0:
                    statline = '\'%s %s: %i kills and 0 deaths for a ratio of %.2f\'' % \
                        (player.tag, player.name, player.kills, float(player.kills))
                    #self.rc.sndcmd(self.rc.SAY, '\'%s %s: %i kills and 0 deaths for a ratio of %.2f\' all' %
                    #    (player.tag, player.name, player.kills, float(player.kills)))
                else:
                    statline = '\'%s %s: %i kills and %i deaths for a ratio of %.2f\'' % \
                        (player.tag, player.name, player.kills, player.deaths, float(player.kills)/float(player.deaths))
                    #self.rc.sndcmd(self.rc.SAY, '\'%s %s: %i kills and %i deaths for a ratio of %.2f\' all' %
                    #    (player.tag, player.name, player.kills, player.deaths, float(player.kills)/float(player.deaths)))
                self.rc.sndcmd(self.rc.SAY, statline + ' all')
                self.chat_queue(statline)

            elif re.search('!chuck', chat, re.I):
                fact = ''
                while True:
                    #strip out any apostrophe's cuz the rcon doesn't like em :(
                    fact = linecache.getline('chuck.txt', random.randint(1, 76)).replace('\"', '').replace("\'", '')
                    if len(fact) <= 100:
                        break
                self.rc.sndcmd(self.rc.SAY, '\'' + fact + '\' all')
                self.chat_queue('Server: ' + fact)

            elif chat.lower().startswith('!punish') and player.power >= player.RECRUIT:
                m = re.match(self.command, chat)
                punish = self.search_player(player, m.group('parms').split()[0])
                if punish:
                    self.rc.sndcmd(self.rc.YELL, '\'You are being punished by a JHF admin for misbehaving.There will be no more warnings!!!\' 6000 player \'%s\'' % punish.name)
                    time.sleep(2)
                    self.rc.sndcmd(self.rc.PUNISH, punish.name)
                    
            elif chat.lower().startswith('!kick') and player.power >= player.ADMIN:
                print chat
                kickcommand = re.compile(r'^(?P<command>![^\s]{2,})\s(?P<name>.*)\s(?P<time>[0-9]{1,2})\s(?P<reason>.*)', re.I)
                m = re.match(kickcommand, chat)
                if m:
                    print m.group()
                    kick = self.search_player(player, m.group('name'))
                    print kick.name
                    if kick:
                        
                        self.rc.sndcmd(self.rc.KICK, '\"%s\" \"%s\" \"%s\"\'' % (kick.name, m.group('time'), m.group('reason')))

            elif chat.lower().startswith('!ban') and player.power >= player.SUPER:
                m = re.match(self.command, chat, re.I)
                parms = m.group('parms').split()
                print parms
                if len(parms) > 1:
                    r = parms[1:]
                    reason = ''
                    for part in r:
                        reason = reason + part + ' '
                    reason = reason.strip()
                    ban = self.search_player(player, parms[0])
                    if ban:
                        if ban.pbid:
                            if ban.ip:
                                #self.rc.sndcmd(self.rc.KICK, '\"%s\" \"10\" \"That language is not acceptable here.\"\'' % player.name)
                                data, response = self.rc.sndcmd(self.rc.BAN, '\"%s\" \"%s\" \"%s\" \"%s\"\'' % (ban.pbid, ban.name, ban.ip, reason))
                                if response:
                                    print 'full ban', response
                            else:
                                data, response = self.rc.sndcmd(self.rc.BAN, '\"%s\" \"%s\" \"???\" \"%s\"\'' % (ban.pbid, ban.name, reason))
                                if response:
                                    print 'no ip ban', reponse
                else:
                    self.rc.sndcmd(self.rc.SAY, '\'A reason is required to BAN a player\' player \'%s\'' %
                        player.name)
                    
            elif re.search('!restart', chat, re.I) and player.power >= player.MOD:
                self.rc.sndcmd(self.rc.RESTART)

            elif chat.lower().startswith('!map') and player.power >= player.RECRUIT:
                m = re.match(self.command, chat)
                self.map_name_easy(player, m.group('parms'))
            
            elif chat.lower().startswith('!rotate') and player.power >= player.MOD:
                self.rc.sndcmd(self.rc.ROTATE)
            
            elif chat.lower().startswith('!gametype') and player.power >= player.MOD:
                m = re.match(self.command, chat)
                if m and m.group('parms').lower().count('rush'):
                    self.rc.sndcmd(self.rc.SETGAMETYPE, 'RUSH')
                    time.sleep(.01)
                    for map in self.RUSH.values():
                        self.rc.sndcmd(self.rc.ADDMAP, 'Levels/%s' % map)
                        time.sleep(.01)
                    self.rc.sndcmd(self.rc.ROTATE)
                elif m and m.group('parms').lower().count('conquest'):
                    self.rc.sndcmd(self.rc.SETGAMETYPE, 'CONQUEST')
                    time.sleep(.01)
                    for map in self.CONQUEST.values():
                        self.rc.sndcmd(self.rc.ADDMAP, 'Levels/%s' % map)
                        time.sleep(.01)
                    self.rc.sndcmd(self.rc.ROTATE)
                    
            #display rules of server to player - seems to be used in other admin programs
            elif re.search('!rules', chat, re.I) and player.power >= player.PUBLIC:
                with open('rules.txt', 'r') as f:
                    for line in f:
                        self.rc.sndcmd(self.rc.SAY, '\'%s\' player \'%s\'' % (line.strip('\n'), player.name))
                        time.sleep(2)                    
            #even if we never use it, it's got to be included ;)
            elif chat.lower().startswith('!forgive'):
                pass
            
            self.log.info('%s;onChat;%s;%s' % (str(time.time()), player.name, chat))

#        elif m and m.group('cid').lower() == '!ff' and player.power:
#            data, response = self.rc.sndcmd(self.rc.FF)
#            if response:
#                if data[1] == 'true':
#                    self.rc.sndcmd(self.rc.FF, 'false')
#                    self.rc.sndcmd(self.rc.SAY, '\'!!!Friendly Fire will be OFF after the current round!!!\' all')
#                else:
#                    self.rc.sndcmd(self.rc.FF, 'true')
#                    for i in xrange(0,3):
#                        self.rc.sndcmd(self.rc.SAY, '\'!!!Friendly Fire will be ON after the current round!!!  Watch your fire!!!\' all')
#                        time.sleep(3)
                    
    def mail(self, subject, text):
        try:
            msg = MIMEMultipart()
            
            msg['From'] = self.gmail_user
            msg['To'] = self.mail_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(text))
            
            part = MIMEBase('application', 'octet-stream')
            
            mailServer = smtplib.SMTP("smtp.gmail.com", 587)
            mailServer.ehlo()
            mailServer.starttls()
            mailServer.ehlo()
            mailServer.login(self.gmail_user, self.gmail_pwd)
            mailServer.sendmail(self.gmail_user, self.mail_to, msg.as_string())
            # Should be mailServer.quit(), but that crashes...
            mailServer.close()
        except Exception, error:
            print 'error sending email~'
            print error

    def write_to_DB(self, play):
        try:
            sql = sqlalchemy.create_engine("mysql://%s:%s@%s/%s" % (self.dbuser, self.dbpasswd, self.dbhost, self.dbname),
                                pool_size = 5, pool_recycle=45).connect()
            dbplayers = sqlalchemy.Table('player_info', sqlalchemy.MetaData(sql), autoload=True)
            today = time.strftime('%m/%d/%Y', time.localtime())
            if self.has_been_seen(play):
                current = dbplayers.select(dbplayers.c.player_name == play.name).execute()
                current = current.fetchone()
                timesSeen = int(current['times_seen']) + 1
                if current['last_seen'] == today:
                    dbplayers.update(dbplayers.c.player_name == play.name).execute(clan_tag = play.tag, ip=play.ip,
                                                                                   guid=play.pbid, times_seen=timesSeen)
                else:
                    dbplayers.update(dbplayers.c.player_name == play.name).execute(clan_tag=play.tag, ip=play.ip,
                                                                    guid=play.pbid, times_seen=timesSeen, last_seen=today)
            else:
                dbplayers.insert().execute(player_name=play.name, clan_tag=play.tag, ip=play.ip, guid=play.pbid,
                                           times_seen=1, first_seen=today, last_seen=today)
        except Exception, error:
            print 'error in writing_db'
            print error
            self.mail('ZOMG SQL ERROR', 'WARNING.  WAFFLES.\n There was a problem with the database.\n\n %s' % error)            
        finally:
            try:
                sql.close()
            except:
                pass
    def has_been_seen(self, player):
        try:
            sql = sqlalchemy.create_engine("mysql://%s:%s@%s/%s" % (self.dbuser, self.dbpasswd, self.dbhost, self.dbname),
                pool_size = 5, pool_recycle=45).connect()
            dbplayers = sqlalchemy.Table('player_info', sqlalchemy.MetaData(sql), autoload=True)
            p = dbplayers.select(dbplayers.c.player_name == player.name).execute()
            if p.fetchone():
                return True
            else:
                return False
        except Exception, error:
            print 'error in has_been_seen'
            print error
            self.mail('ZOMG SQL ERROR', 'WARNING.  WAFFLES.\n There was a problem with the database.\n\n %s' % error)
        finally:
            try:
                sql.close()
            except:
                pass
            
    def get_rank(self,player):
        while self.running:
            if not self.players.has_key(player.name):
                return
            try:
                url = 'http://api.bfbcs.com/api/pc?players=%s&fields=general' % player.name
                webFile = urllib.urlopen(url)
                rank = webFile.read()
                data = json.loads(rank)
                player.rank = str(data['players'][0]['rank'])
                return
            except Exception:
                #got to sleep, sometimes the player doesn't exist with this api yet, and we need time to let it update
                time.sleep(60)

            
    def new_player(self, player):
        try:
            np = rcon.RCon()
            np.connect(self.host, self.port, self.pw)
            data, response = np.sndcmd(np.PINFO, 'player \'%s\'' % player.name)
            if response and data[11]:
                player.tag = data[12]
                player.eaguid = data[14]
                player.team = data[15]
                player.squad = data[16]
                player.kills += int(data[17])
                player.deaths += int(data[18])
            if player.seen:
                np.sndcmd(np.YELL, "'Welcome back to JHF, %s %s! Be sure to visit jhfgames.com and get to know us!' \
                    6000 player '%s'" % (player.tag, player.name, player.name))
            else:
                np.sndcmd(np.YELL, "'Welcome to JHF, %s %s! Play fair, Have fun and visit us at jhfgames.com sometime!' \
                    6000 player '%s'" % (player.tag, player.name, player.name))
            time.sleep(10)
            if player.power:
                np.sndcmd(np.SAY, "'%s %s, you have FULL admin rights on the server' player '%s'" % (player.tag, player.name, player.name))
            self.get_rank(player)
            self.write_to_DB(player)
        except KeyError:
            pass
        except IndexError:
            pass
        except rcon.socket.error:
            pass
        except Exception, error:
            print 'some other error in new_player'
            print error

    def chat_queue(self, chat):
        if chat:
            if len(self.chat) >= 20:
                self.chat.pop(0)
            self.chat.append('%s - %s' % (time.strftime("%m/%d %H:%M:%S", time.localtime()), chat))

    def kill_queue(self, attacker, victim, weapon, headshot):
        if len(self.kills) >= 10:
            self.kills.pop(0)
        if attacker.name == victim.name:
            self.kills.append('%s commited suicide with a %s' % (attacker.name, weapon))
        elif attacker.team == victim.team:
            self.kills.append('%s teamkilled %s with a %s' % (attacker.name, victim.name, weapon))
        else:
            if headshot == 'false':
                self.kills.append('%s killed %s with a %s' % (attacker.name, victim.name, weapon))
            else:
                self.kills.append('%s blew %s\'s head off with a %s' % (attacker.name, victim.name, weapon))
    
    def do_first_run(self):
        '''
        Some initial recording of what's going on in the server
        '''
        rc = rcon.RCon()
        rc.connect(self.host, self.port, self.pw)
        data, response = rc.sndcmd(rc.PINFO, 'all')
        if response and len(data) > 1:
            data = data[12:]
            while data:
                tag = data.pop(0)
                name = data.pop(0)
                guid = data.pop(0)
                team = data.pop(0)
                squad = data.pop(0)
                kills = data.pop(0)
                deaths = data.pop(0)
                data.pop(0)
                #score = data.pop(0)
                data.pop(0)
                #ping = data.pop(0)
                self.players.connect(tag, name, team)
                self.players.getPlayer(name).kills = int(kills)
                self.players.getPlayer(name).deaths = int(deaths)
                self.players.getPlayer(name).eaguid = guid
                self.players.getPlayer(name).squad = squad
                threading.Thread(target=self.get_rank, args=[self.players.getPlayer(name)]).start()
        #OK <serverName: string> <current playercount: integer> <max playercount: integer> 
        #<current gamemode: string> <current map: string> 
        #<roundsPlayed: integer> <roundsTotal: string> <scores: team scores> 
        data, response = rc.sndcmd(rc.SINFO)
        if response and len(data) == 12:
            self.pcount = int(data[2])
            self.map = data[5].strip('Levels/')
            self.round[0] = data[6]
            self.round[1] = data[7]
            self.gametype = data[4].lower()
            self.scores = [int(round(float(data[9]),0)), int(round(float(data[10]),0)), int(round(float(data[11]),0))]
        rc.serverSocket.close()
        matchrank = re.compile('(?P<rank>\d+)(?P<ranksuf>\D{2})\s\(<span>(?P<percentile>\d+)(?P<percentsuf>\D{2})')
        content = urllib.urlopen("http://www.gametracker.com/server_info/68.232.162.167:19567/").read()

        m = re.search(matchrank, content)
        if m:
            self.serverrank = m.group('rank') + m.group('ranksuf')
            self.serverperc = m.group('percentile') + m.group('percentsuf')
        self.chat_queue('Monitor is alive!')

    def map_name(self, map):
        for i, j in self.ALLmaps.items():
            if map.count(j):
                return i
        return map
    
    def map_server(self, map):
        counter = 0
        for i, j in self.ALLmaps.items():
            if re.search(map, i, re.I):
                counter += 1
                mapname = j
        return counter, mapname
    
    #This code blatantly stolen and adapted from b3 bot
    def getNextMapIndex(self):
        try:
            data, response = self.rc.sndcmd(self.rc.MAP)
            if response:
                nextIndex = int(data)
                if nextIndex == -1:
                    return -1
                data, response = self.rc.sndcmd(self.rc.MAPLIST)
                if response:
                    if data[nextIndex] == self.map: 
                        nextIndex = (nextIndex + 1) % len(data)
                return nextIndex
        except:
            return -2            

    def map_name_easy(self, player, map):
        try:
            data, response = self.rc.sndcmd(self.rc.GAMETYPE)
            if response:
                self.gametype = data[1]
            
            if response:
                available_maps = data[1:]

            i, mapname = self.map_server(map)
            if i > 1:
                self.rc.sndcmd(self.rc.SAY, '\'Ambiguous map named!  Try being more specific!\' player \'%s\'' % player.name)
            elif i == 0:
                self.rc.sndcmd(self.rc.SAY, '\'No map found with that name, TRY AGAIN! :-p\' player \'%s\'' % player.name)
            elif i == 1:
                data, response = self.rc.sndcmd(self.rc.AVAILMAPS)
                if response:
                    if data.count(mapname):
                        data, response = self.rc.sndcmd(self.rc.MAPLIST)
                        if response:
                            if mapname not in data:
                                nextIndex = self.getNextMapIndex()
                                if nextIndex == -2:
                                    return
                                elif nextIndex == -1:
                                    self.rc.sndcmd(self.rc.ADDMAP, mapname)
                                    nexIndex = 0
                                else:
                                    if nextIndex == 0:
                                        nextIndex = 1
                                    self.rc.sndcmd(self.rc.MAPINSERT, str(nextIndex) + ' ' + mapname)
                            else:
                                nextIndex = 0
                                while nextIndex < len(data) and data[nextIndex] != mapname:
                                    nextIndex += 1
                        print 'current map', self.map
                        print 'changing map', mapname, nextIndex
                        self.rc.sndcmd(self.rc.MAP, nextIndex)
                        self.rc.sndcmd(self.rc.ROTATE)   
        except Exception, detail:
            print detail           
            
#        for i, j in self.ALLmaps.items():
#            if re.search(map.lower(), i.lower()):
#                data, response = self.rc.sndcmd(self.rc.GAMETYPE)
#                if response:
#                    if i in eval('self.' + data[1]):
#                        list, res = self.rc.sndcmd(self.rc.MAPLIST)
#                        list.pop(0)
#                        print list,
#                        index = 0
#                        if res:
#                            while index < len(list):
#                                if list[index].count(j):
#                                    break
#                                else:
#                                    index += 1
#                            print index, map, j
#                            
#                        self.rc.sndcmd(self.rc.MAP, str(index))
#                        time.sleep(.001)
#                        self.rc.sndcmd(self.rc.ROTATE)
#                        return
        #self.rc.sndcmd(self.rc.SAY, '\'Map not found or map not supported by gametype, try again!\' player \'%s\'' % player.name)
        #self.rc.sndcmd(self.rc.SAY, '\'Sorry SOX, that map doesnt exist or wont work here... TRY AGAIN!!! :-p\' player \'%s\'' % player.name)

    def status(self):         
        monitor = flask.Flask(__name__)
         
        @monitor.route('/')
        def index():
            return flask.render_template('status.html', host=self.host, map=self.map_name(self.map) + ' ' + self.round[0] + '/' + self.round[1], gametype=(self.gametype[0].upper() + self.gametype[1:]),\
                pcount=self.pcount, mapfile=self.map, kills=reversed(self.kills), chat=reversed(self.chat), team1=self.players.getTeam('1'), team2=self.players.getTeam('2'), rank=self.serverrank, percent=self.serverperc, \
                scores=self.scores)
         
        @monitor.route('/pcount.html')
        def pcount():
            return '<html>\n<head>\n<title></title>\n</head>\n<body style="color: #ffffff; background-color: #000000;  font-size: 12px; font-family: Verdana, Arial, Helvetica, sans-serif;">\n \
                %s / 32\n</body>\n</html>' % self.pcount
                
        @monitor.route('/chatlog/')
        @monitor.route('/chatlog/<search>')
        def chatlog(search=None):
            f = open('chatlog.txt', 'r')
            chat = ''
            if not search:
                for line in f:
                    chat += line + '<br>'
            else:
                search = search.replace('+', ' ')
                for line in f:
                    if line.count(search):
                        chat += line + '<br>'
            f.close()
            return chat
        
        @monitor.route('/log/')
        def log():
            f = open('logfile.txt', 'r')
            log = '' 
            for line in f:
                log += line + '<br>'
            f.close()
            return log
        
        @monitor.route('/chattail/')
        def tailchat():
            tail = ''
            for line in subprocess.Popen(['tail', '-n 10', '/home/ghoti/BC2Monitor/chatlog.txt'], shell=False, stdout=subprocess.PIPE).communicate()[0].split('\n'):
                tail += line + '<br>'
            return tail
         
        http_server = HTTPServer(WSGIContainer(monitor))
        http_server.listen(8088)
        while self.running:
            IOLoop.instance().start()
                
    def stop_status(self):
        self.server.stop()
        self.running = False
        

if __name__ == '__main__':
    monitor3()
