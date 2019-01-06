#! /usr/bin/env python3
# Project: Akrios
# Filename: commands/mmchat.py
#
# Capability: player
#
# Command Description: This is the Out of Character (OOC) chat command. It goes
# to the Gossip MUD Chat Network.
#
# By: Jubelo

from commands import *

name = "mmchat"
version = 1

@Command(capability="player")
def mmchat(caller, args):
    if caller.oocflags_stored['mmchat'] == 'false':
        caller.write("You have that command self disabled with the 'toggle' command.")
        return

    if len(args.split()) == 0:
        caller.write("Did you have something to say or not?")
        return

    try:
        # XXX Gossip specific here
        gossip.gsocket.msg_gen_message_channel_send(caller, "gossip",  args) 
    except:
        caller.write(f"{{WError chatting to Gossip.haus Network, try again later{{x")
        comm.wiznet(f"Error writing to Gossip.haus network. {caller.name} : {args}")
        return

    
    caller.write(f"{{GYou MultiMUD Chat{{x: '{{G{args}{{x'")

    for eachplayer in player.playerlist:
        if eachplayer.oocflags_stored['mmchat'] == 'true' and eachplayer.aid != caller.aid:
            eachplayer.write(f"\n\r{{G{caller.name.capitalize()} MultiMUD Chats{{x: '{{G{args}{{x'")


