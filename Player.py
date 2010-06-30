'''
Created on Dec 3, 2009

@author: ghoti
'''
class player(object):
    """
    Our player class will hold each client on the game server,
    tracking kills, deaths, tks, pbpower, and maybe more in 
    the future
    """
    PUBLIC = 0
    RECRUIT = 1
    MOD = 2
    ADMIN = 3
    SUPER = 4

    def __init__(self, name, tag, team):
        ADMINS = {'-gH0Ti-':self.SUPER, 'H0FFA':self.SUPER, 'JimmyT13':self.SUPER, 'Madindian':self.SUPER,
                'HaveSocks':self.SUPER, '|-Smoke-|':self.SUPER, 'Astromarmot':self.SUPER, 'l3ONE':self.SUPER,
                'OBMer':self.SUPER,'Gwawk':self.SUPER, 'phyZilla':self.SUPER, 'Fralix':self.SUPER, 'Luxxord':self.ADMIN,
                'ch3w3mup':self.RECRUIT, 'jhfveritas':self.SUPER}
        if name.count("'"):
            self.name = name.replace("'", '')
        elif name.count('"'):
            self.name = name.replace('"', '')
        else:
            self.name = name
        self.rank = ''
        #self.guid = guid
        self.pbid = 0
        self.pbslot = None
        self.eaguid = 0
        if tag.count("'"):
            self.tag = tag.replace("'", '')
        elif tag.count('"'):
            self.tag = tag.replace('"', '')
        else:
            self.tag = tag
        self.ip = '0.0.0.0'
        self.seen = 0
        self.chat = 0
        self.suicides = 0
        self.kills = 0
        self.deaths = 0
        self.ratio = 0.00
        self.streak = 0
        self.team = team
        self.kit = '' 
        self.teamkills = 0
        self.teamkiller = None
        if ADMINS.has_key(name):
            self.power = ADMINS[name]
        else:
            self.power = self.PUBLIC
        self.warning = 0
        self.votekicks = 0
    def kill(self):
        self.kills += 1
        self.streak += 1
        if self.deaths == 0:
            self.ratio = self.kills
        else:
            self.ratio = round(float(self.kills)/float(self.deaths), 2)
            
    def death(self):
        self.deaths += 1
        self.streak = 0
        
        if self.kills == 0:
            self.ratio = 0.00
        else:
            self.ratio = round(float(self.kills)/float(self.deaths),2)
            
    def suicide(self):
        self.death()
        self.suicides += 1
    def teamkill(self):
        self.teamkills += 1
    def teamkilled(self, cid):
        self.teamkiller = cid
    def forgive(self, player):
        player.forgiven()
        self.teamkiller = None
    def forgiven(self):
        self.teamkills -= 1
    def setAtt(self, tag, team):
        self.tag = tag
        self.team = team
