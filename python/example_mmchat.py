#! /usr/bin/env python3
# Project: Akrios
# Filename: commands/mmchat.py
#
# Capability: player
#
# Command Description: This is the Out of Character (OOC) chat command. It goes
# to the Grapevine MUD Chat Network.
#
# By: Jubelo

from commands import *

name = "mmchat"
version = 1

requirements = {'capability': 'player',
                'generic_fail': "See {WHelp mmchat{x for help with this command.",
                'truth_checks':  ['args_required'],
                'false_checks': []}

@Command(**requirements)
def mmchat(caller, args, **kwargs):
    if caller.oocflags_stored['mmchat'] == 'false':
        caller.write("You have that command self disabled with the 'toggle' command.")
        return

    try:
        grapevine.gsocket.msg_gen_message_channel_send(caller, "grapevine",  args) 
    except:
        caller.write(f"{{WError chatting to grapevine.haus Network, try again later{{x")
        comm.wiznet(f"Error writing to grapevine.haus network. {caller.name_cap} : {args}")
        return
    
    caller.write(f"{{GYou MultiMUD Chat{{x: '{{G{args}{{x'")

    for eachplayer in player.playerlist:
        if eachplayer.oocflags_stored['mmchat'] == 'true' and eachplayer.aid != caller.aid:
            eachplayer.write(f"\n\r{{G{caller.name_cap} MultiMUD Chats{{x: '{{G{args}{{x'")



