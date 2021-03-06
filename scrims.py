import os
import sqlite3
import discord
import json
import requests
import sys
import traceback
import random
import time
import re
import math

sys.path.append('util/')

from discord.ext import commands
from util import maps_dict, modes_dict
from datetime import datetime, timedelta
from statistics import mean
from string_to_datetime import string_to_datetime
from string_to_date import string_to_date

from map import map_name as map_name_from_key
conn     = sqlite3.connect("scrims.db")
c        = conn.cursor()
base_url = 'https://www.bungie.net/Platform'
k_value  = 15

description = 'A bot for the creation of D2 scrims'
bot         = commands.Bot(command_prefix='?', description=description)

from secrets import token, bungie_key

try: from secrets import bot_name
except: bot_name = 'Destiny2 Scrims Groups#8958'

# token = os.environ['TOKEN']
# bungie_key = os.environ['BUNGIE_KEY']
headers = {'X-API-Key' : bungie_key}

@bot.event
async def on_ready():
    c.execute('''CREATE TABLE IF NOT EXISTS Scrims
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time DATETIME,
                team_size INTEGER,
                creator INTEGER,
                alpha INTEGER DEFAULT 0,
                bravo INTEGER DEFAULT 0,
                started INTEGER DEFAULT 0,
                FOREIGN KEY(creator) REFERENCES Players(id)
            );''')
    c.execute('''CREATE TABLE IF NOT EXISTS ScrimPlayers
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                scrim_id INTEGER,
                team INTEGER,
                FOREIGN KEY(scrim_id) REFERENCES Scrims(id),
                FOREIGN KEY(player_id) REFERENCES Players(id)
            );''')
    c.execute('''CREATE TABLE IF NOT EXISTS Players
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                psn_name TEXT UNIQUE,
                discord_name TEXT,
                membership_id TEXT,
                elo INTEGER DEFAULT 1500
            );''')
    c.execute('''CREATE TABLE IF NOT EXISTS PlayerCharacters
            (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                character_id TEXT
            );''')
    conn.commit()

    print('Bot is ready and live')


@bot.command(description='Creates a scrim', help="Takes your name as the host argument, put your time in double quotes. There is no validation.")
async def create(ctx, time, team_size):
    print('Scrim created')
    time = string_to_datetime(time)
    creator = ctx.author
    c.execute('''SELECT id, psn_name
                   FROM Players
                  WHERE discord_name = ?''', (str(creator),))
    try:
        row         = c.fetchall()[0]
        creator_id   = row[0]
        creator_name = row[1]
    except IndexError:
        await ctx.send('You need to register first using the `?register` command.')
        return


    c.execute('''INSERT INTO Scrims (time, team_size, creator)
                      VALUES (?, ?, ?);''', (time, int(team_size), creator_id))
    nextscrim = c.lastrowid
    c.execute('''INSERT INTO ScrimPlayers (player_id, scrim_id)
                      VALUES (?, ?);''', (creator_id, nextscrim))
    conn.commit()

    # Embed creation
    title = 'New Scrim: ' + str(nextscrim)
    color = 0xFFFFFF
    desc = 'Type `?join <id>` to join this scrim.'
    embed = discord.Embed(title=title, description=desc, color=color)

    # Player Iteration
    c.execute('''SELECT p.psn_name
                   FROM Players p
                   JOIN ScrimPlayers sp ON sp.player_id = p.id
                  WHERE sp.scrim_id = ?;''', (int(nextscrim),))
    rows = c.fetchall()
    counter = 1
    players = ""
    for row in rows:
        player = "%d. %s\n" % (counter, row[0])
        players = players + player
        counter = counter + 1

    embed.add_field(name='Time: ', value=time.strftime('%e-%b-%Y %H:%M'), inline=True)
    embed.add_field(name='Creator: ', value=creator_name, inline=True)
    embed.add_field(name='Team Size: ', value=team_size, inline=True)
    embed.add_field(name='Players: ', value=players, inline=False)

    await ctx.send(content=None, embed=embed)


@bot.command(description="Lists all scrims scheduled, or scrims scheduled for a day if a date is passed.", help="Works "
        "with or without an argument. Without an argument, lists all scrims schedule from present time; scrims scheduled for that day are listed")

async def scrims(ctx, time_string=None):
    print('Scrims listed')
    creator = ctx.author

    # check if time_string given. If so, parse time.
    if time_string is not None:
        time = string_to_date(time_string)
        higher_time = time + timedelta(1)

        c.execute('''SELECT s.id, s.time, p.psn_name
                      FROM Scrims s
                      JOIN Players p ON p.id = s.creator
                      WHERE s.time
                      BETWEEN ? AND ?;''', (time, higher_time,))
        data = c.fetchall()

    else:
        c.execute('''SELECT s.id, s.time, p.psn_name
                       FROM Scrims s
                       JOIN Players p ON p.id = s.creator
                      WHERE s.time > date('now');''',())
        data = c.fetchall()

    # Send no scrims card if data is empty.
    if len(data) == 0:
        # Embed creation
        title = 'No scrims scheduled in the future. Schedule one now with `?create`'
        color = 0xFFFFFF
        embed = discord.Embed(title=title, color=color)
        await ctx.send(content=None, embed=embed)

    for _data in data:
        id = _data[0]
        game_time = datetime.strptime(_data[1], '%Y-%m-%d %H:%M:%S.%f')
        creator   = _data[2]
        # Embed creation
        title = 'New Scrim: ' + str(id)
        color = 0xFFFFFF
        desc  = 'Type `?join <id>` to join this scrim.'
        embed = discord.Embed(title=title, description=desc, color=color)

        # Player Iteration
        c.execute('''SELECT p.psn_name
                       FROM ScrimPlayers sp
                       JOIN Players p ON p.id = sp.player_id
                      WHERE scrim_id  = ?;''', (int(id),))
        rows = c.fetchall()
        counter = 1
        players = ""
        for row in rows:
            player = "%d. %s\n" % (counter, row[0])
            players = players + player
            counter = counter + 1

        embed.add_field(name='Time: ', value=game_time.strftime('%e-%b-%Y %H:%M')+('GMT'), inline=True)
        embed.add_field(name='Creator: ', value=creator, inline=True)
        embed.add_field(name='Players: ', value=players, inline=False)
        await ctx.send(content=None, embed=embed)


@bot.command(description="Join a scrim with a specific ID", help="Takes a scrim ID. You must be registered using `?register` first.")
async def join(ctx, scrim_id):
    print('Match joined')
    creator = ctx.author

    # Get the player ID
    c.execute('''SELECT id
                   FROM Players
                  WHERE discord_name = ?;''', (str(creator),))

    try:
        player_id = c.fetchall()[0][0]
    except IndexError:
        await ctx.send('You are not registered. Please register with `?register`.')
        return

    # Get the scrim ID
    c.execute('''SELECT id, team_size, creator
                   FROM Scrims
                  WHERE id = ?;''', (scrim_id,))
    try:
        scrim_row = c.fetchall()[0]
    except IndexError:
        await ctx.send('This is not an active scrim id. Create one with `?create`.')
        return


    # How many people are already registered for this scrim?
    c.execute('''SELECT Count(*)
                   FROM ScrimPlayers
                  WHERE scrim_id = ?;''', (scrim_id,))

    player_count = c.fetchall()[0][0]

    if player_count >= (scrim_row[1] * 2):
        await ctx.send('This scrim is full. Either see if someone leaves, or create one with `?create`.')
        return

    # How many people are already registered for this scrim?
    c.execute('''SELECT Count(*)
                   FROM ScrimPlayers
                  WHERE scrim_id = ?
                    AND player_id = ?;''', (scrim_id,player_id))

    is_here = (c.fetchall()[0][0] != 0)

    if is_here:
        await ctx.send('You already joined this scrim. Leave with `?leave`.')
        return

    # Join the scrim, doesn't matter if they already did.
    c.execute('''INSERT INTO ScrimPlayers (player_id, scrim_id)
                       VALUES (?, ?);''', (player_id, scrim_id))
    conn.commit()

    # Embed creation
    title = 'Joined Scrim: ' + str(scrim_id)
    color = 0xFFFFFF
    desc = 'Type `?join <id>` to join this scrim.'
    embed = discord.Embed(title=title, description=desc, color=color)

    c.execute('''SELECT p.psn_name, s.time
                   FROM Players p
                   JOIN Scrims s ON s.creator = p.id
                  WHERE s.id = ?;''', (scrim_id,))

    creator_and_time = c.fetchall()[0]
    creatorname      = creator_and_time[0]
    time             = creator_and_time[1]

    # Player Iteration
    c.execute('''SELECT p.psn_name
                   FROM Players p
                   JOIN ScrimPlayers sp ON sp.player_id = p.id
                  WHERE sp.scrim_id = ?;''', (int(scrim_id),))
    rows = c.fetchall()
    counter = 1
    players = ""
    for row in rows:
        player = "%d. %s\n" % (counter, row[0])
        players = players + player
        counter = counter + 1

    embed.add_field(name='Time: ', value=time, inline=True)
    embed.add_field(name='Creator: ', value=creatorname, inline=True)
    embed.add_field(name='Players: ', value=players, inline=False)

    await ctx.send(content=None, embed=embed)


@bot.command(description='Pulls the most recent private match you played. This is probably a scrim', help="This uses the API, and requires you to have used `?register`. Without it, you will get back an error message.")
async def match(ctx):
    print('Match requested')
    creator = ctx.author

    # Player Iteration
    c.execute('SELECT psn_name from Players WHERE discord_name  = ?;', (str(creator),))
    player = c.fetchall()[0][0]

    if player == None:
        await ctx.send('You are not registered. Please register with `?register`.')


    c.execute('''SELECT p.membership_id, pc.character_id
                   FROM Players p
                   JOIN PlayerCharacters pc ON p.id = pc.player_id
                  WHERE discord_name  = ?;''', (str(creator),))

    id_rows = c.fetchall()
    d2_membership_id = id_rows[0][0]
    characters = [n[1] for n in id_rows]

    date_instances = {}

    # Get recent activity data for all characters
    for character in characters:
        matches = '/Destiny2/2/Account/' + d2_membership_id + '/Character/' + character + '/Stats/Activities/?mode=32&count=1'
        r       = json.loads(requests.get(base_url + matches, headers = headers).content)

        if 'activities' in r['Response']:
            for match in r['Response']['activities']:
                date     = match['period']
                mode     = modes_dict[match['activityDetails']['mode']]
                map_name = map_name_from_key(match['activityDetails']['referenceId'])
                instance = match['activityDetails']['instanceId']

                dateobject = datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
                date_instances[dateobject] = instance

    sorted_dates = sorted(date_instances.keys())
    instance = date_instances[sorted_dates.pop()]

    if instance == None:
        await ctx.send("Why the hell are you using this if you don't play private matches")
        return

    activity_url = '/Destiny2/Stats/PostGameCarnageReport/' + instance
    r            = json.loads(requests.get(base_url + activity_url, headers = headers).content)

    # Creates the match embed
    title = 'Scrim Post Game Report for : ' + str(creator)
    color = 0xFFFFFF
    desc  = mode + ' on ' + map_name
    embed = discord.Embed(title=title, description=desc, color=color)

    dateobject = datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
    date       = dateobject.strftime('%m-%d-%Y')
    embed.add_field(name='Time: ', value=date, inline=True)

    players_table = ""
    # Get the players and their individual stats
    players = r['Response']['entries']
    for player in players:
        standing = player['standing'] + 1
        name    = player['player']['destinyUserInfo']['displayName']
        score   = player['values']['score']['basic']['displayValue']
        kills   = player['values']['kills']['basic']['displayValue']
        deaths  = player['values']['deaths']['basic']['displayValue']
        assists = player['values']['assists']['basic']['displayValue']
        kdr     = player['values']['killsDeathsRatio']['basic']['displayValue']
        new_row = '**' + str(standing) + '.** ' + name + ' - ' + score +  ' (' + kills + '/' + deaths + '/' + assists + ')\n'
        players_table = players_table + new_row

    embed.add_field(name='Players: ', value=players_table, inline=False)

    await ctx.send(content=None, embed=embed)


@bot.command(description='Starts a scrim. Auto creates teams.', help="If you are the creator of a scrim, randomly generates the teams and starts it.")
async def start(ctx, scrim_id):
    print('Scrim started')
    creator = ctx.author

    # Get the scrim ID
    c.execute('''SELECT id, team_size, creator, alpha, bravo, started
                   FROM Scrims
                  WHERE id = ?;''', (scrim_id,))
    try:
        scrim_row = c.fetchall()[0]
    except IndexError:
        await ctx.send('This is not an active scrim id. Create one with `?create`.')
        return

    creator = ctx.author
    c.execute('''SELECT id
                   FROM Players
                  WHERE discord_name = ?''', (str(creator),))

    player_id = c.fetchall()[0][0]

    if(player_id != scrim_row[2]):
        await ctx.send('You are not the creator of this scrim. Let them start it.')
        return

    team_size = scrim_row[1]
    started   = scrim_row[5]

    if(started > 0):
        await ctx.send('This scrim has already started. Create a new one with `?create`.')
        return

    # How many people are already registered for this scrim?
    c.execute('''SELECT Count(*)
                   FROM ScrimPlayers
                  WHERE scrim_id = ?;''', (scrim_id,))

    player_count = c.fetchall()[0][0]

    if player_count != (team_size * 2):
        await ctx.send('This scrim is not full. More people need to join with `?join`.')
        return

    # Start the scrim officially
    # Disable this if you are testing
    c.execute('''UPDATE Scrims
                    SET started = 1
                  WHERE id = ?''', (scrim_id,))
    conn.commit()

    # Embed creation
    title = 'Scrim ' + str(scrim_id) + ' beginning now'
    color = 0xFFFFFF
    desc  = "Join the creator's party unless otherwise specified."
    embed = discord.Embed(title=title, description=desc, color=color)

    c.execute('''SELECT p.psn_name
                   FROM Players p
                   JOIN Scrims s ON s.creator = p.id
                  WHERE s.id = ?;''', (scrim_id,))

    creator_and_time = c.fetchall()[0]
    creatorname      = creator_and_time[0]

    embed.add_field(name='Creator: ', value=creatorname, inline=False)

    # Player Iteration
    c.execute('''SELECT sp.player_id, p.psn_name, p.elo
                   FROM ScrimPlayers sp
                   JOIN Players p ON p.id = sp.player_id
                  WHERE sp.scrim_id = ?
               ORDER BY p.elo DESC;''', (scrim_id,))

    player_row = c.fetchall()

    # Grabs every other person in order of elo. Updates the ScrimPlayers afterwards to allow for proper scorekeeping afterwards.
    alpha = player_row[::2]
    bravo = player_row[1::2]

    alpha_ids = [x[0] for x in alpha]
    bravo_ids = [x[0] for x in bravo]

    for player in alpha_ids:
        c.execute('''UPDATE ScrimPlayers
                        SET team = 1
                      WHERE player_id = ?;''', (player,))
    for player in bravo_ids:
        c.execute('''UPDATE ScrimPlayers
                        SET team = 2
                      WHERE player_id = ?;''', (player,))

    counter = 1
    alpha_team = ""
    for player in alpha:
        a_player = "%d. %s\n" % (counter, player[1])
        alpha_team = alpha_team + a_player
        counter = counter + 1

    counter = 1
    bravo_team = ""
    for player in bravo:
        b_player = "%d. %s\n" % (counter, player[1])
        bravo_team = bravo_team + b_player
        counter = counter + 1

    embed.add_field(name='Alpha Team: ', value=alpha_team, inline=True)
    embed.add_field(name='Bravo Team: ', value=bravo_team, inline=True)
    embed.add_field(name='Score: ', value='Alpha {} - {} Bravo'.format(scrim_row[3], scrim_row[4]), inline=False)

    message = await ctx.send(content=None, embed=embed)

    emojis = ["{}\N{COMBINING ENCLOSING KEYCAP}".format(num) for num in range(1, 3)]

    # Adds the scorekeeping reactions
    for emoji in emojis:
        await message.add_reaction(emoji)


@bot.command(description='Lists out the rankings of all active players.', help='Fairly self explanatory.')
async def ranking(ctx):
    # We don't care about players that have registered but not played.
    # We also only want the top 25.
    c.execute('''SELECT p.elo, p.psn_name
                   FROM Players p
                  WHERE p.elo != 1500
               ORDER BY p.elo DESC
                  LIMIT 25;''')
    player_rows = c.fetchall()

    title = 'Scrim Player ELO Rankings'
    color = 0xFFFFFF
    desc  = "Top 25 players in order of ranking. Players who have not played yet are hidden."
    embed = discord.Embed(title=title, description=desc, color=color)

    counter = 1
    rankings = ""
    for player in player_rows:
        player_rank = "%d. (%s) %s\n" % (counter, player[0], player[1])
        rankings = rankings + player_rank
        counter = counter + 1

    embed.add_field(name='Rankings: ', value=rankings, inline=True)

    await ctx.send(content=None, embed=embed)


@bot.command(description='Registers your PSN with your Discord', help="Takes your psn name as the psn argument.")
async def register(ctx, psn):
    creator = ctx.author

    # Get user id by PSN
    search_user = '/Destiny2/SearchDestinyPlayer/2/' + psn + '/'
    r           = json.loads(requests.get(base_url + search_user, headers = headers).content)

    d2_membership_id = r['Response'][0]['membershipId']

    # Saves the ID's in the database to speed up the query
    c.execute('''REPLACE INTO Players (psn_name, discord_name, membership_id)
                       VALUES (?, ?, ?);''', (psn, str(creator), d2_membership_id))
    player_id = c.lastrowid

    await ctx.send('`Registered %s with the PSN as %s. If this was done in error use ?register again.`' % (creator, psn))

    profile   = '/Destiny2/2/Profile/' + d2_membership_id + '/?components=100'
    r         = json.loads(requests.get(base_url + profile, headers = headers).content)
    characters = r['Response']['profile']['data']['characterIds']

    for character in characters:
        c.execute('''REPLACE INTO PlayerCharacters (player_id, character_id)
                           VALUES (?, ?);''', (player_id, character))
    conn.commit()


@bot.event
async def on_reaction_add(reaction, user):
    # Is this even an embed?
    if(len(reaction.message.embeds) == 0):
        return

    # We only care if this embed is a scrim match record
    embed = reaction.message.embeds[0]
    r     = re.compile('Start ')

    if(r.match(embed.title)):
        return

    # Get the match ID
    r        = re.compile(' (\d) ')
    scrim_id = r.findall(embed.title)[0]

    c.execute('''SELECT p.discord_name, s.alpha, s.bravo
                   FROM Scrims s
                   JOIN Players p ON p.id = s.creator
                  WHERE s.id = ?;''', (scrim_id,))

    scrim_row = c.fetchall()[0]
    creator   = scrim_row[0]
    alpha     = scrim_row[1]
    bravo     = scrim_row[2]

    reactants = [(i.name+'#'+i.discriminator) for i in await reaction.users().flatten()]

    if(creator in reactants):
        # Get the emoji and update the score
        # Alpha won
        if reaction.emoji == '1⃣':
            alpha = alpha + 1
        # Bravo won
        else:
            bravo = bravo + 1

        c.execute('''UPDATE Scrims
                        SET alpha = ?,
                            bravo = ?
                      WHERE id = ?;''', (alpha, bravo, scrim_id))

        embed.set_field_at(3, name='Score: ', value='Alpha '+str(alpha)+' - '+str(bravo) + ' Bravo', inline=False)

        # Checks for a winner
        winner = False
        if(alpha == 3):
            winner = 'Alpha'
        elif(bravo == 3):
            winner = 'Bravo'

        await reaction.message.edit(embed=embed)
        await reaction.message.clear_reactions()

        # If a team wins the scrim, updates the team elo's
        if(winner):
            # First get all of the ELOs
            c.execute('''SELECT p.id, p.psn_name, p.elo
                        FROM ScrimPlayers sp
                        JOIN Players p ON p.id = sp.player_id
                        WHERE sp.scrim_id = ?
                          AND team = 1
                    ORDER BY p.elo DESC;''', (scrim_id,))
            alpha_row = c.fetchall()
            c.execute('''SELECT p.id, p.psn_name, p.elo
                        FROM ScrimPlayers sp
                        JOIN Players p ON p.id = sp.player_id
                        WHERE sp.scrim_id = ?
                          AND team = 2
                    ORDER BY p.elo DESC;''', (scrim_id,))
            bravo_row = c.fetchall()

            rating_alpha = mean([x[2] for x in alpha_row])
            rating_bravo = mean([x[2] for x in bravo_row])

            # This is the expected odds of winning for each team
            expected_alpha = 1 / ( 1 + 10**( ( rating_bravo - rating_alpha ) / 400 ) )
            expected_bravo = 1 / ( 1 + 10**( ( rating_alpha - rating_bravo ) / 400 ) )

            mov_multiplier = math.log(abs(int(alpha) - int(bravo)) + 1)

            if(alpha == 3):
                corr_coefficient = 2.2 / ((rating_alpha - rating_bravo) * 0.001 + 2.2)
            else:
                corr_coefficient = 2.2 / ((rating_bravo - rating_alpha) * 0.001 + 2.2)

            # Calculates the modifiers
            alpha_modifier = k_value * (alpha - expected_alpha) * mov_multiplier * corr_coefficient
            bravo_modifier = k_value * (bravo - expected_bravo) * mov_multiplier * corr_coefficient

            # Updates the ELO's for all players
            for player in alpha_row:
                new_elo = int(player[2] + alpha_modifier)
                player_id = player[0]
                c.execute('''UPDATE Players
                                SET elo = ?
                              WHERE id = ?;''', (new_elo,player_id))
            conn.commit()
            for player in bravo_row:
                new_elo = int(player[2] + bravo_modifier)
                player_id = player[0]
                c.execute('''UPDATE Players
                                SET elo = ?
                              WHERE id = ?;''', (new_elo,player_id))
            conn.commit()

        else:
            # Edit the old message
            emojis = ["{}\N{COMBINING ENCLOSING KEYCAP}".format(num) for num in range(1, 3)]

            # Adds the scorekeeping reactions
            for emoji in emojis:
                await reaction.message.add_reaction(emoji)
    else:
        if(user.name+'#'+user.discriminator != bot_name):
            await reaction.remove(user)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.DisabledCommand):
        await ctx.send(ctx.message.author, "I'm Sorry. This command is disabled and it can't be used.")
    elif isinstance(error, commands.CommandInvokeError):
        print('In {0.command.qualified_name}:'.format(ctx), file=sys.stderr)
        traceback.print_tb(error.original.__traceback__)
        print('{0.__class__.__name__}: {0}'.format(error.original), file=sys.stderr)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(ctx.message.channel, "It seems you are trying to use a command that does not exist.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("It seems you are missing required argument(s). Try again if you have all the arguments needed.")
    elif isinstance(error, KeyError):
        await ctx.send("This is a KeyError cause the developers are idiots. Shoot them a message.")


bot.run(token)
