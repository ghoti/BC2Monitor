import Player
import weakref

class clients(dict):
    def connect(self, tag, name, team):
        if not self.has_key(name):
            self[name] = Player.player(name, tag, team)
    def disconnect(self, name):
        if self.has_key(name):
            del self[name]
    def getAll(self):
        plist = []
        for player in self.values():
            plist.append(weakref.ref(player)())
        return plist
    def getTeam(self, team):
        tlist = []
        for p in self.values():
            if p.team == team:
                tlist.append(p)
        return tlist
    def getPlayer(self, name):
        return self[name]
    def hasPlayer(self, name):
        return self.has_key(name)
       