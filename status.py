import flask
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

def status(webip, webport):         
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
     
    http_server = HTTPServer(WSGIContainer(monitor))
    http_server.listen(webport)
    IOLoop.instance().start()

def stop_status():
    IOLoop.instance().stop()
    