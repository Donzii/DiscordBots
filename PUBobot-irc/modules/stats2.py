#!/usr/bin/python2
import sqlite3, operator
from datetime import timedelta
from time import time
import re

#INIT
def init(filename="stats.sql"):
	global conn, c
	conn = sqlite3.connect(filename)
	c = conn.cursor()

	#check if we have tables, create if needed
	check_tables()

def register_pickup(gametype, players, caps,):
  playersstr = " " + " ".join(players) + " "
  #update overall_stats
  c.execute("UPDATE overall_stats SET pickups = pickups+1")

  #insert pickup
  c.execute("INSERT INTO pickups (time, gametype, cap1, cap2, players) VALUES (?, ?, ?, ?, ?)", (int(time()), gametype, caps[0], caps[1], playersstr))
  c.execute("SELECT last_insert_rowid()")
  pickupid = c.fetchone()[0]

  #update gametype
  c.execute("INSERT OR IGNORE INTO gametypes VALUES (?, 0, 0)", (gametype, ))
  c.execute("UPDATE gametypes SET played = played+1, lastgame = ? WHERE gametype = ?", (pickupid, gametype))

  #update player_games and players
  for player in players:
    c.execute("INSERT OR IGNORE INTO players VALUES (?, 0, 0, 0, 0, 'False', 'False')", (player, ))
    c.execute("UPDATE players SET played=played+1, lastgame = ? WHERE nick = ?", (pickupid, player))
    c.execute("INSERT INTO player_games (pickup_id, nick, time, gametype) VALUES (?, ?, ?, ?)", (pickupid, player, int(time()), gametype))
  for player in caps:
    c.execute("UPDATE players SET caps=caps+1 WHERE nick = ?", (player, ))
  conn.commit()

def lastgame(text=False): #[id, gametype, ago, [players], [caps]]
  if not text: #return lastest game
    c.execute("SELECT * FROM pickups ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
  else:
    #try to find last game by gametype
    c.execute("SELECT lastgame FROM gametypes WHERE gametype = ?", (text,))
    tmp = c.fetchone()
    if tmp != None:
      pickupid = tmp[0]
      c.execute("SELECT * FROM pickups WHERE id = ?", (pickupid,))
      result = c.fetchone()
    else: #no results, try to find last game by player
      c.execute("SELECT * FROM pickups WHERE players LIKE ? ORDER BY id DESC LIMIT 1", ('% {0} %'.format(text),))
      result = c.fetchone()

  #return result
  if result != None:
    #players = result[5].strip().replace(" ",", ")
    #caps = "{0}, {1}".format(result[3],result[4])
    #ago = timedelta(seconds=int(time() - int(result[1])))
    
    #return id, time, gametype, caps, players
    return result[0], result[1], result[2], [result[3],result[4]], result[5].strip().split()
  else:
    return False

def stats(text=False):
  if not text: #return overall stats
    c.execute("SELECT * FROM overall_stats")
    l = c.fetchone()
    if l != None:
	  pickups, bans = l[0], l[1]
	  c.execute("SELECT * FROM gametypes ORDER BY played DESC")
	  l=[]
	  for i in c:
	    l.append("{0}: {1}".format(i[0],i[1]))
	  return "Total pickups: {0}, noadds: {1}. | {2}".format(pickups, bans, ", ".join(l))
    else:
	  return "No pickups played yet."
  else:
    d=dict()
    c.execute("SELECT * FROM players WHERE nick = ?", (text, ))
    result = c.fetchone()
    print result
    if result != None:
      played, wascap, bans = result[1], result[2], result[3]
      c.execute("SELECT pickups FROM overall_stats")
      if played != 0:
        percent = int((float(played) / c.fetchone()[0]) * 100)
      else:
        percent = 0
      c.execute("SELECT * FROM player_stats WHERE nick = ?", (text, ))
      dstr = ""
      for i in c.fetchall():
        if i[1] in d:
          d[i[1]]+=1
        else:
          d[i[1]]=1
        dstr = ', '.join("{0}: {1}".format(key,val) for (key,val) in d.iteritems())
      return "Stats for {0}. Played: {1} ({2}%), was cap: {3}, noadded: {4} | {5}.".format(text, played, percent, wascap, bans, dstr)
    c.execute("SELECT * FROM gametypes WHERE gametype = ?", (text, ))
    result = c.fetchone()
    if result != None:
      played = result[1]
      c.execute("SELECT pickups FROM overall_stats")
      percent = int((float(played) / c.fetchone()[0]) * 100)
      return "Stats for {0} gt. Played {1}, {2}% of all games.".format(text, played, percent)
    return "No pickups found for " + text

def top(timegap=False):
  if not timegap:
    c.execute("SELECT nick, played FROM players ORDER BY played DESC LIMIT 10")
    l = c.fetchall()
    s = ', '.join("{0}: {1}".format(i[0],i[1]) for i in [x for x in l])
    return s
  if timegap:
    d=dict()
    c.execute("SELECT nick FROM player_games WHERE time > ?", (timegap, ))
    l = c.fetchall()
    if l == []:
      return ""
    for player in l:
      if player[0] in d:
        d[player[0]] += 1
      else:
        d[player[0]] = 1
    top = sorted(d.items(), key=operator.itemgetter(1), reverse=True)
    s = ', '.join("{0}: {1}".format(i[0],i[1]) for i in [x for x in top[0:10]])
    return s
  #print [x for x in c]



def noadd(ip, nick, duratation, admin, reason=''):
  c.execute("SELECT * FROM bans WHERE active = 1 AND nick = ?", (nick, ))
  ban = c.fetchone()
  if ip == False:
    if ban != None:
      c.execute("""UPDATE bans SET time=?, duratation=?, reason=?, admin=? WHERE active = 1 AND NICK = ?""", (int(time()), duratation*60*60, reason, admin, nick))
      conn.commit()
      return("Updated {0}'s noadd to {1} hours from now.".format(nick, duratation))
    else:
      return("Couldnt find the nick on the IRC server nor in active noadds list.")

  else:
    if ban != None:
      c.execute("""UPDATE bans SET ip=?, time=?, duratation=?, reason=?, admin=? WHERE active = 1 AND NICK = ?""", (ip, int(time()), duratation*60*60, reason, admin, nick))
      conn.commit()
      return("Updated {0}'s noadd to {1} hours from now.".format(nick, duratation))
    #add new ban
    c.execute("UPDATE overall_stats SET bans = bans+1")
    c.execute("INSERT OR IGNORE INTO players VALUES (?, 0, 0, 0, 0, 'False', 'False')", (nick, ))
    c.execute("UPDATE players SET bans = bans+1 WHERE nick = ?", (nick, ))
    c.execute("INSERT INTO bans (ip, nick, active, time, duratation, reason, admin) VALUES (?, ?, 1, ?, ?, ?, ?)", (ip, nick, int(time()), duratation*60*60, reason, admin))
    conn.commit()
    #return("Banned {0} for {1} hours".format(nick, duratation))
    #Get a quote!
    c.execute("SELECT * FROM nukem_quotes ORDER BY RANDOM() LIMIT 1")
    quote = c.fetchone()
    return(quote[0])

def forgive(nick, admin):
  c.execute("SELECT * FROM bans WHERE active = 1 and nick = ?", (nick, ))
  ban = c.fetchone()
  if ban != None:
    c.execute("UPDATE bans SET active = 0, unban_admin = ? WHERE active = 1 and nick = ?", (admin, nick))
    conn.commit()
    return("{0} forgiven.".format(nick))
  return("Ban not found!")

def noadds(nick=False):
  if not nick:
    l,s,s1 = [],"", "Noadds: "
    c.execute("SELECT * FROM bans WHERE active = 1")
    bans = c.fetchall()
    for i in bans:
      print i
      if i[4]+i[5] > time(): # if time didnt ran out
        number = i[0]
        name = i[2]+"@"+i[1]
        timeleft=timedelta( seconds=int(i[5]-(time()-i[4])) )
        s='#{0} {1}, {2} time left | '.format(number,name,timeleft)
        print len(s1+s)
        if len(s1+s) > 230:
          l.append(s1)
          s1 = s
        else:
          s1 = s1+s
    if s1 != "Noadds: ":
      l.append(s1)
      return l
  else:
    if nick[0] == "#": #search by number
      c.execute("SELECT * FROM bans WHERE id = ?", (nick.lstrip("#"), ))
    else: #search active ban by nick
      c.execute("SELECT * FROM bans WHERE active = 1 AND nick = ?", (nick, ))
    ban = c.fetchone()
    if ban != None:
      number = ban[0]
      name = ban[2]+"@"+ban[1]
      if ban[6] == "False":
        reason = "\"\""
      else:
        reason = "\"{0}\"".format(ban[6])
      admin = ban[7]
      if ban[8] != None:
	unbanned_or_timeleft="unbanned by "+ban[8]
      else:
        print "time", ban[5] - (time()-ban[4])
        unbanned_or_timeleft=str(timedelta( seconds=int(ban[5]-(time()-ban[4])) ))+" time left"
      s='#{0} {1}, {2}, by {3}, {4}.'.format(number,name,reason, admin, unbanned_or_timeleft)
      return([s,])
  return(["Nothing found.", ])

def check_ip(ip, nick): #check on bans and phrases
  #check if nick is locked
  c.execute("SELECT locked FROM players WHERE nick = ? AND locked != 'False'", (nick, ))
  lock = c.fetchone()
  if lock != None:
    if lock[0] != ip:
      return((True, "This nick is locked on a Quakenet account."))

  #check if he is banned
  unbanned=False
  c.execute("SELECT * FROM bans WHERE active = 1")
  bans = c.fetchall()
  for ban in bans:
    if ban[2] == nick or re.match("^{0}$".format(re.escape(ban[1]).replace("\*",".*")), ip):
      if ban[4]+ban[5] > time():
        timeleft=timedelta( seconds=int(ban[5]-(time()-ban[4])) )
        if ban[2] == nick:
          return((True, "04You have been banned. {0} time left.".format(timeleft)))
        else:
          return((True, "04You have been banned, mr. {0}. {1} time left.".format(ban[2],timeleft)))
      else: #ban time ran out, disable ban
        c.execute("UPDATE bans SET active = 0, unban_admin = ? WHERE id = ? ", ("time", ban[0]))
        unbanned=True
    if unbanned:
      conn.commit()
      return((False, "03Be nice next time, please."))

  #no bans, find phrases!
  c.execute("SELECT phrase FROM players WHERE nick = ? AND phrase != 'False'", (nick, ))
  phrase = c.fetchone()
  if phrase != None:
    return((False, phrase[0]))
  return((False, False))

def set_phrase(nick, phrase):
  c.execute("SELECT phrase FROM players WHERE nick = ?", (nick, ))
  sel = c.fetchone()
  if sel != None:
    c.execute("""UPDATE players SET phrase = ? WHERE nick = ?""", (phrase, nick))
    conn.commit()
  else:
    c.execute("INSERT INTO players VALUES (?, 0, 0, 0, 0, 'False', ?)", (nick, phrase))
    conn.commit()

def lock_nick(nick, ip, is_admin):
  #check if there is a lock already
  c.execute("SELECT * FROM players WHERE nick = ? AND locked != 'False'", (nick, ))
  lock = c.fetchone()
  if lock != None:
    if is_admin == False:
      return("You must unlock it first! Use !unlock")
    else: #obey an admin
      c.execute("UPDATE players SET locked = ? WHERE nick = ?", (ip, nick,))
      conn.commit()
      return("Successfully locked {0} to {1}.".format(nick, ip))
  elif ip.find(".users.quakenet.org") > 0 or is_admin:
    c.execute("INSERT OR IGNORE INTO players VALUES (?, 0, 0, 0, 0, 'False', 'False')", (nick, ))
    c.execute("UPDATE players SET locked = ? WHERE nick = ?", (ip, nick))
    conn.commit()
    return("Successfully locked {0} to {1}.".format(nick, ip))
  else:
    return("You can only lock nick on Quakenet account ip.")
  
def unlock_nick(nick, ip, is_admin):
  c.execute("SELECT locked FROM players WHERE nick = ? AND locked != 'False'", (nick, ))
  lock = c.fetchone()
  if lock != None:
    if is_admin or ip == lock[0]:
      c.execute("UPDATE players SET locked = 'False' WHERE nick = ?", (nick, ))
      conn.commit()
      return("Successfully unlocked.")
    else:
      return("Access denied.")
  else:
    return("This nick was not locked")

def vote_topic(nick, topic): #add topic
  c.execute("SELECT * FROM votes_topics ORDER BY id DESC LIMIT 1")
  topic = c.fetchone()
  if topic != None:
    if topic[3] == 1:
      return("You must close current vote topic first. !vote_close.")

  c.execute("INSERT INTO votes_topics (topic, author, active) VALUES (?, ?, 1)", (nick, topic))
  conn.commit()
  return("New vote started! Now add vote options. '!vote_option text'")

def vote_option(option): #add option to current topic
  c.execute("SELECT * FROM votes_topics ORDER BY id DESC LIMIT 1")
  topic = c.fetchone()
  if topic != None:
    if topic[3] == 1:
      c.execute("SELECT * FROM votes_options WHERE topic_id = ? AND option = ?", (topic[0], option))
      found = c.fetchone()
      if found == None:
        c.execute("INSERT INTO vote_options (topic_id, option, votes) VALUES (?, ?, 0)", (topic[0], option))
        conn.commit()
        return("Successfully added new vote option.")
      else:
        return("This option already exist for this vote topic.")
    else:
      return("Current vote topic is closed. Use !vote_open.")
  else:
    return("No vote topics was created yet.")

def vote_open(): #open current vote
  c.execute("SELECT * FROM votes_topics ORDER BY id DESC LIMIT 1")
  topic = c.fetchone()
  if topic != None:
    if topic[3] == 0:
      c.execute("UPDATE votes_topics SET active = 1 WHERE id = ?", (topic[0], ))
      conn.commit()
      return("Successfully opened current vote topic.")
    else:
      return("Current vote topic is already opened.")
  else:
    return("No vote topics was created yet.")

def vote_close(): #close current vote topic
  c.execute("SELECT * FROM votes_topics ORDER BY id DESC LIMIT 1")
  topic = c.fetchone()
  if topic != None:
    if topic[3] == 1:
      c.execute("UPDATE votes_topics SET active = 1 WHERE id = ?", (topic[0], ))
      conn.commit()
      return("Successfully closed current vote topic.")
    else:
      return("Current vote topic is already closed.")
  else:
    return("No vote topics was created yet.")

def vote_vote(nick, ip, option): #vote
  #check if its not faker first
  c.execute("SELECT locked FROM players WHERE nick = ? AND locked != 'False'", (nick, ))
  lock = c.fetchone()
  if lock != None:
    if lock[0] != ip:
      return("This nick is locked on a Quakenet account.")

  c.execute("SELECT * FROM votes_topics ORDER BY id DESC LIMIT 1")
  topic = c.fetchone()
  if topic != None:
    if topic[3] == 1:
      c.execute("SELECT * FROM votes_options WHERE topic_id = ? AND option = ?", (topic[0], option))
      vote_option = c.fetchone()
      if vote_option != None:
        c.execute("SELECT * FROM votes_votes WHERE option_id = ? AND ( nick = ? OR ip = ?)", (vote_option[0], nick, ip))
        vote_vote = c.fetchone()
        if vote_vote == None:
          c.execute("INSERT INTO votes_votes (option_id, nick, ip) VALUES (?, ?, ?)", (vote_option[0], nick, ip))
          c.execute("UPDATE votes_options SET votes = votes+1 WHERE id = ?", (vote_option[0], ))
          return("Vote added.")
        else:
          return("You have already voted for this option.")
      else:
        return("Incorrect vote option.")
    else:
      return("Current vote topic is closed.")
  else:
    return("No vote topics was created yet.")

def votes_show(args):
  if len(args) < 2: 
    c.execute("SELECT * FROM votes_topics ORDER BY id DESC LIMIT 1")
    vote_topic = c.fetchone()
    if topic != None:
      if args == []: #show overall votes
        c.execute("SELECT (option, votes) FROM votes_options WHERE topic_id = ?", (vote_topic[0], ))
        vote_options = c.fetchall()
        result = " | ".join((": ".join([i[0],str(i[1])]) for i in vote_options)) #sum complicated formatting
        return(("#{0}: {1}".format(vote_topic[0], vote_topic[1]), result))
      else: #show votes by vote option
        c.execute("SELECT * FROM votes_options WHERE topic_id = ? AND option = ?", (vote_topic[0], args[0]))
        vote_option = c.fetchone()
        if vote_option != None:
          c.execute("SELECT nick FROM votes_votes WHERE option_id = ?", (vote_option[0], ))
          vote_votes = c.fetchall()
          result = ", ".join((i[0][0] for i in vote_votes))
          return(("Players voted for {0}:".format(vote_option[1]), result))
        else:
          return(("Incorrect vote option specified."), )
    else:
      return(("No vote topics was created yet."), )
  else:
    return(("Usage: !votes [option]."), )
    
def highlight_blacklist(nick = False):
	if nick:
		c.execute("SELECT * FROM highlight_blacklist WHERE nick = ?", (nick, ))
		result = c.fetchone()
		if result != None:
			c.execute("DELETE FROM highlight_blacklist WHERE nick = ?", (nick, ))
			s = "You were removed from highlight blacklist."
		else:
			c.execute("INSERT INTO highlight_blacklist values ( ? )", (nick, ))
			s = "You were added to highlight blacklist."
		conn.commit()
		return s
	else:
		c.execute("SELECT nick FROM highlight_blacklist")
		result = c.fetchall()
		return [ i[0] for i in result ]
	
def show_help(command):
	c.execute("SELECT text FROM help WHERE command = ?", (command, ))
	result = c.fetchone()
	if result != None:
		return result[0]
	else:
		return "Command not found! See '!commands'."
def show_commands():
	c.execute("SELECT command FROM help")
	result = c.fetchall()
	commands = [x[0] for x in result]
	return " ".join(commands)

def check_tables():
	c.execute("""SELECT name FROM sqlite_master WHERE type='table' OR type='view';""")
	t = c.fetchall()
	tables = [ x[0] for x in t ]
	if not 'bans' in tables:
		c.execute("""CREATE TABLE bans (id INTEGER, ip TEXT NOT NULL, nick TEXT NOT NULL, active INTEGER DEFAULT 0, time INTEGER, duratation INTEGER, reason TEXT, admin TEXT, unban_admin TEXT, PRIMARY KEY(id) );""")
		c.execute("""CREATE INDEX bans_active ON bans (active DESC)""")
	if not 'gametypes' in tables:
		c.execute("""CREATE TABLE gametypes ( gametype TEXT, played INTEGER DEFAULT 0, lastgame INTEGER, PRIMARY KEY(gametype));""")
	if not 'overall_stats' in tables:
		c.execute("""CREATE TABLE overall_stats (pickups INTEGER, bans INTEGER, quotes INTEGER, votes INTEGER);""")
		c.execute("""INSERT INTO overall_stats VALUES (0, 0, 0, 0);""")
	if not 'pickups' in tables:
		c.execute("""CREATE TABLE pickups (id INTEGER PRIMARY KEY AUTOINCREMENT, time INTEGER, gametype TEXT, cap1 TEXT, cap2 TEXT, players TEXT);""")
	if not 'player_games' in tables:
		c.execute("""CREATE TABLE player_games (id INTEGER PRIMARY KEY AUTOINCREMENT, pickup_id INTEGER, nick TEXT, time INTEGER, gametype TEXT);""")
	if not 'players' in tables:
		c.execute("""CREATE TABLE players (nick TEXT, played INTEGER, caps INTEGER, bans INTEGER, lastgame INTEGER, locked TEXT, phrase TEXT, PRIMARY KEY(nick));""")
	if not 'quotes' in tables:
		c.execute("""CREATE TABLE quotes (id INTEGER PRIMARY KEY AUTOINCREMENT, author TEXT, text TEXT);""")
	if not 'votes_topics' in tables:
		c.execute("""CREATE TABLE votes_topics (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT, author TEXT, active INTEGER, votes INTEGER);""")
	if not 'votes_votes' in tables:
		c.execute("""CREATE TABLE votes_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id INTEGER, nick TEXT, ip TEXT);""")
	if not 'highlight_blacklist' in tables:
		c.execute("""CREATE TABLE highlight_blacklist (nick TEXT PRIMARY KEY);""")
	if not 'player_stats' in tables:
		c.execute("""CREATE VIEW player_stats AS SELECT pgs.nick, pus.gametype FROM player_games pgs, pickups pus WHERE pgs.pickup_id = pus.id""")
	if not 'player_votes' in tables:
		c.execute("""CREATE VIEW player_votes AS SELECT p.nick, v.topic FROM votes_votes p, votes_topics v WHERE p.topic_id = v.id""")
	if not 'help' in tables:
		c.execute("""CREATE TABLE help (command TEXT, text TEXT);""")
		c.executescript("""
			INSERT INTO help VALUES ("add", "'!add' or '++' - adds you to default pickups. '!add game[ game ..]]' or '+game[ game ..]]' - adds you to specified pickups.");
			INSERT INTO help VALUES ("remove", "'!remove' or '--' - removes you from all pickups. '!remove game[ game ...]' or '-[game[ game ..]]' - removes you from specified pickups.");
			INSERT INTO help VALUES ("expire", "'!expire time' - Sets new time delay after you will be removed from all pickups, example: '!expire 1h 2m 3s'.");
			INSERT INTO help VALUES ("sub", "'!sub' - request sub for last game.");
			INSERT INTO help VALUES ("promote", "'!promote [game]' - promotes pickup on channels. Can be used only once in a minut.");
			INSERT INTO help VALUES ("highlight", "'!highlight' - highlights not added and not blacklisted users on pickup channel. Can be used once in a hour after each pickup.");
			INSERT INTO help VALUES ("nohighlight", "'!stfu' or '!nohighlight' - puts your nick in highlight blacklist or removes your nick from it.");
			INSERT INTO help VALUES ("stfu", "'!stfu' or '!nohighlight' - puts your nick in highlight blacklist or removes your nick from it. Use '!highlight_blacklist' to view blacklist.");
			INSERT INTO help VALUES ("lock", "'!lock' - locks your current nick to a Q account. You must be logged in and have +x mode on connect to be able to lock your nick. '!lock nick[ ip] - admins can forcefully lock nick on current nick's owner or specified ip.");
			INSERT INTO help VALUES ("unlock", "'!unlock' - unlock your current nick. '!unlock nick' - admins can forcefully unlock specified nick.");
			INSERT INTO help VALUES ("who", "'!who [game[ game ...]]' - list of people who added to the pickups.");
			INSERT INTO help VALUES ("expire", "'!expire' - shows you how much time left before you will be removed from all pickups.");
			INSERT INTO help VALUES ("pickups", "'!pickups' or '!games' - complete pickups list.");
			INSERT INTO help VALUES ("games", "'!pickups' or '!games' - complete pickups list.");
			INSERT INTO help VALUES ("noadds", "'!noadds' - show list of users who are disallowed to play pickups.");
			INSERT INTO help VALUES ("lastgame", "'!lastgame [nick or pickup]' - show last pickup, or last pickup by specified argument.");
			INSERT INTO help VALUES ("top", "'!top [weekly or monthly or yearly]' - shows you most active players.");
			INSERT INTO help VALUES ("stats", "'!stats [nick or pickup]' - shows you overall stats or stats for specified argument.");
			INSERT INTO help VALUES ("ip", "'!ip [pickup or 'default']' - shows you ip of last pickup or specified pickup. Shows pickups with default ip if argument is 'default'. '!ip pickup[ pickup...] or 'default' : ip' - sets ip for specified pickups. Changes default ip and pickups ip with old default ip if argument if 'default'");
			INSERT INTO help VALUES ("spamchans", "'!spamchans' - list of channels to promote pickups on.");
			INSERT INTO help VALUES ("highlight_blacklist", "'!highlight_blacklist' - shows nicks in highlight blacklist. Users in this list wont be highlighted on !highlight command. Use '!stfu' or '!nohighlight' to join or leave the list.");
			INSERT INTO help VALUES ("motd", "'!motd text' - sets the channel topic message.");
			INSERT INTO help VALUES ("noadd", "'!noadd nick [hours] [-t hours] [-r reason] [-m ip_address_mask] - disallow user to play pickups. Ip address will be detected automaticly if '-m' argument is not specified.");
			INSERT INTO help VALUES ("forgive", "'!forgive nick' - allow user from noadds list to play pickups.");
			INSERT INTO help VALUES ("chanban", "'!chanban nick[ hours]' - kick and ban specified user from channel. Command is made to allow +v users to ban for short amount of time (12 hours max).");
			INSERT INTO help VALUES ("phrase", "'!phrase nick text' - set specified reply for specified nick after !add command.");
			INSERT INTO help VALUES ("remove_players", "'!remove_players nick[ nick ...]' - remove specified players from all pickups.");
			INSERT INTO help VALUES ("reset", "'!reset' - removes all players from all pickups.");
			INSERT INTO help VALUES ("add_pickups", "'!add_pickups name:players[ name:players ...]' - creates new pickups.");
			INSERT INTO help VALUES ("remove_pickups", "'!remove_pickups name[ name ...]' - removes specified pickups.");
			INSERT INTO help VALUES ("default_pickups", "'!default_pickups name[ name ...]' - sets default pickups.");
			INSERT INTO help VALUES ("topiclimit", "'!topiclimit number' - sets maximum amount of pickups to be displayed in topic.");
			INSERT INTO help VALUES ("autoremove_time", "'!autoremove_time minutes' - set default !expire time.");
			INSERT INTO help VALUES ("spam", "'!spam channel' - add channel to list of channels to promote pickups on.");
			INSERT INTO help VALUES ("nospam", "'!nospam channel' - remove channel from list of channels to promote pickups on.");
			INSERT INTO help VALUES ("silent", "'!silent [botnick]' - enable silent mode, bot will listen to all commands but will remain silent.");
			INSERT INTO help VALUES ("backup_save", "'!backup_save' - save backup.");
			INSERT INTO help VALUES ("backup_load", "'!backup_load [name] - load last or specified backup.");
			INSERT INTO help VALUES ("puquit", "'!puquit [botnick]' - terminate the bot.")
		""")
	if not 'nukem_quotes' in tables:
		c.execute("""CREATE TABLE nukem_quotes (quote TEXT);""")
		c.executescript("""
			INSERT INTO nukem_quotes VALUES ("AAhhh... much better!");
			INSERT INTO nukem_quotes VALUES ("Bitchin'!");
			INSERT INTO nukem_quotes VALUES ("Come get some!");
			INSERT INTO nukem_quotes VALUES ("Do, or do not, there is no try.");
			INSERT INTO nukem_quotes VALUES ("Eat shit and die.");
			INSERT INTO nukem_quotes VALUES ("Get that crap outta here!");
			INSERT INTO nukem_quotes VALUES ("Go ahead, make my day.");
			INSERT INTO nukem_quotes VALUES ("Hail to the king, baby!");
			INSERT INTO nukem_quotes VALUES ("Heh, heh, heh... what a mess!");
			INSERT INTO nukem_quotes VALUES ("Holy cow!");
			INSERT INTO nukem_quotes VALUES ("Holy shit!");
			INSERT INTO nukem_quotes VALUES ("I'm gonna get medieval on your asses!");
			INSERT INTO nukem_quotes VALUES ("I'm gonna kick your ass, bitch!");
			INSERT INTO nukem_quotes VALUES ("Let God sort 'em out!");
			INSERT INTO nukem_quotes VALUES ("Ooh, that's gotta hurt.");
			INSERT INTO nukem_quotes VALUES ("See you in Hell!");
			INSERT INTO nukem_quotes VALUES ("Piece of Cake.");
			INSERT INTO nukem_quotes VALUES ("Suck it down!");
			INSERT INTO nukem_quotes VALUES ("Terminated!");
			INSERT INTO nukem_quotes VALUES ("Your face, your ass - what's the difference?");
			INSERT INTO nukem_quotes VALUES ("Nobody fucks up our pickups... and lives!");
			INSERT INTO nukem_quotes VALUES ("My boot, your face; the perfect couple.")
		""")
	conn.commit()

def close():
  conn.commit()
  conn.close()
