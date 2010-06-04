<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>
	<title>BC2 Server Status</title>
	<meta http-equiv="refresh" content="15" />
	<link rel="stylesheet" href="css/bc2status.css" type="text/css" media="screen" />
</head>

<body>

<div id="container">

<!-- HEADER & Nav -->

	<div id="header">
	<div id="banner">
		<img src="images/banner.jpg" width="876" height="111" alt="banner" />
	</div>
	<div id="nav">
		<ul>
			<li><a href="http://www.jhfgames.com/">=JHF= Home</a></li>
			<li><a href="">Bad Company Player Stats</a></li>
			<li><a href="http://www.jhfgames.com/forum/">=JHF= Forum</a></li>
		</ul>
	</div>
</div>

<div id="status">
	<div id="info_chat">
		<div id="game_info">

			<div id="text">
				<h4><span class="white">=</span>J<span class="white">H</span><span class="blue">F</span><span class="white">=</span> Just Having Fun - Recruiting</h4>
				<ul>
					<li>IP: {{host}}:19567</li>
					<li>Map: {{map}}</li>
					<li>Gametype:  {{gametype}}</li>
					<li>Players:  <span class="red">{{pcount}}/32</span></li>
				</ul>
			</div>
			<div id="map">
				<img src="images/{{mapfile}}.jpg" width="160" height="120" alt="mapimage" />
			</div>

		</div>
		<div id="kill_death">
			<h4>Last 10 Kills</h4>
			<p>
                %for k in kills:
                    {{k}}<br />
                %end
			</p>
		</div>
		<div id="gamechat">
			<h4>In Game Chat</h4>
			<p>
                %for c in chat:
                    {{c}}<br />
                %end
            </p>
		</div>
		</div>
	<div id="team_info1">
		<p class="team_title">Team 1</p>

		<table width="100%">
		<tr>
		<td>Slot</td><td>Rank</td><td>Player</td><td>Kills</td><td>Deaths</td><td>Ratio</td><td>Streak</td></tr>
		<tr><td colspan="6"></td></tr>
		<!-- <tr><td>1</td><td></td><td></td><td></td><td></td><td></td></tr> -->
        %for i, p in zip(xrange(1, 17), team1):
            <tr><td>{{i}}</td><td>{{p.rank}}</td><td><a href="http://bfbcs.com/stats_pc/{{p.name}}" target="new">{{p.tag + ' ' + p.name}}</a></td><td>{{p.kills}}</td><td>{{p.deaths}}</td><td>{{'%.2f' % p.ratio}}</td><td>{{p.streak}}</td></tr>
        %end
		</table>
	</div>
	<div id="team_info2">
		<p class="team_title">Team 2</p>

		<table width="100%">
		<tr>
		<td>Slot</td><td>Rank</td><td>Player</td><td>Kills</td><td>Deaths</td><td>Ratio</td><td>Streak</td></tr>
		<tr><td colspan="6"></td></tr>
		<!--<tr><td>1</td><td></td><td></td><td></td><td></td><td></td></tr>-->
        %for i, p in zip(xrange(1, 17), team2):
            <tr><td>{{i}}</td><td>{{p.rank}}</td><td><a href="http://bfbcs.com/stats_pc/{{p.name}}" target="new">{{p.tag + ' ' + p.name}}</a></td><td>{{p.kills}}</td><td>{{p.deaths}}</td><td>{{'%.2f' % p.ratio}}</td><td>{{p.streak}}</td></tr>
        %end
		</table>
	</div>
</div>

<!--footer-->

</div></body></html>
