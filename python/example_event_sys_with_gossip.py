#! usr/bin/env python
# Project: Akrios
# Filename: event.py
# 
# File Description: Module to handle event queues.
# 
# By: Jubelo

import random
import time
import uuid

import comm
import grapevine
import player
import server
import world

PULSE_PER_SECOND = 8
PULSE_PER_MINUTE = 60 * PULSE_PER_SECOND


class Queue:
    def __init__(self, owner, owner_type):
        self.aid = str(uuid.uuid4())
        self.eventlist = []
        self.owner = owner
        self.owner_type = owner_type

    def add(self, event):
        if self.is_empty():
            things_with_events[self.owner_type].append(self.owner)
        self.eventlist.append(event)

    def remove(self, event):
        # Some events may be destroyed within an event.  Player autoquit
        # and a player being forced to drop within an event and having their
        # queue cleared is one example.
        if event in self.eventlist:
            self.eventlist.remove(event)
        if self.is_empty():
            if self.owner in things_with_events[self.owner_type]:
                things_with_events[self.owner_type].remove(self.owner)

    def remove_event_type(self, eventtype=None):
        if eventtype == None:
            return
        for eachevent in self.eventlist:
            if eachevent.eventtype == eventtype:
                self.eventlist.remove(eachevent)

    def update(self):
        for event in self.eventlist:
            if event == None or event.func == None:
                self.eventlist.remove(event)
                return
            event.passes -= 1
            if event.passes <= 0:
                event.fire()
       
    def clear(self):
        for eachthing in things_with_events[self.owner_type]:
            if eachthing == self.owner:
                things_with_events[self.owner_type].remove(eachthing)
        self.eventlist = []

    def num_events(self):
        return len(self.eventlist)

    def is_empty(self):
        if len(self.eventlist) == 0:
            return True
        else:
            return False



class Event:
    def __init__(self):
        self.aid = str(uuid.uuid4())
        self.eventtype = None
        self.ownertype = None
        self.owner = None
        self.func = None
        self.arguments = None
        self.passes = 0
        self.totalpasses = 0

    def fire(self):
        self.func(self)
        owner_exists = self.owner != None
        owner_has_events_attrib = hasattr(self.owner, "events")
        if owner_exists and owner_has_events_attrib:
            self.owner.events.remove(self)
        


things_with_events = {"player": [],
                      "area": [],
                      "room": [],
                      "exit": [],
                      "mobile": [],
                      "object": [],
                      "server": [],
                      "socket": [],
                      "grapevine": []}


def heartbeat():
    for each_event_type in things_with_events:
        for each_queue in things_with_events[each_event_type]:
            each_queue.events.update()


# Below follows the init functions.  If a particular thing needs to have
# an event set when it's created, it should go inside the appropriate
# init below.

def init_events_socket(socket):
    pass
    
def init_events_server(server):
    pass

def init_events_grapevine(grapevine_):
    event = Event()
    event.owner = grapevine_
    event.ownertype = "grapevine"
    event.eventtype = "grapevine receive"
    event.func = event_grapevine_receive_message
    event.passes = 1 * PULSE_PER_SECOND
    event.totalpasses =event.passes
    grapevine_.events.add(event)

    event = Event()
    event.owner = grapevine_
    event.ownertype = "grapevine"
    event.eventtype = "grapevine send"
    event.func = event_grapevine_send_message
    event.passes = 1 * PULSE_PER_SECOND
    event.totalpasses = event.passes
    grapevine_.events.add(event)

    event = Event()
    event.owner = grapevine_
    event.ownertype = "grapevine"
    event.eventtype = "grapevine player query status"
    event.func = event_grapevine_player_query_status
    event.passes = 5 * PULSE_PER_MINUTE
    event.totalpasses = event.passes
    grapevine_.events.add(event)

    event = Event()
    event.owner = grapevine_
    event.ownertype = "grapevine"
    event.eventtype = "graevine state check"
    event.func = event_grapevine_state_check
    event.passes = 5 * PULSE_PER_MINUTE
    event.totalpasses = event.passes
    grapevine_.events.add(event)

def init_events_area(area):
    pass

def init_events_room(room):
    pass

def init_events_exit(exit_):
    pass

def init_events_mobile(mobile):
    pass

def init_events_player(player):
    # Begin with events _all_ players will have.

    # First is the autosave for players every 5 minutes
    event = Event()
    event.owner = player
    event.ownertype = "player"
    event.eventtype = "autosave"
    event.func = event_player_autosave
    event.passes = 5 * PULSE_PER_MINUTE
    event.totalpasses = event.passes
    player.events.add(event)

    # Check for player idle time here once per minute.
    event = Event()
    event.owner = player
    event.ownertype = "player"
    event.eventtype = "idle check"
    event.func = event_player_idle_check
    event.passes = 1 * PULSE_PER_MINUTE
    event.totalpasses = event.passes
    player.events.add(event)


    # Player dependant events go below here.

    # If player is a newbie, or has the flag enabled send them newbie tips.
    if player.oocflags_stored['newbie'] == 'true':
        event = Event()
        event.owner = player
        event.ownertype = "player"
        event.eventtype = "newbie tips"
        event.func = event_player_newbie_notify
        event.passes = 45 * PULSE_PER_SECOND
        event.totalpasses = event.passes
        player.events.add(event)
        if player.sock == None:
            return
        player.sock.dispatch("\n\r{P[NEWBIE TIP]{x: You will receive Newbie Tips periodically "
                             "until disabled.\n\r              Use the 'toggle newbie' command "
                             "to enable/disable")

    # Admin characters will receive a system status update.
    if player.is_admin:
        event = Event()
        event.owner = player
        event.ownertype = "admin"
        event.eventtype = "system status"
        event.func = event_admin_system_status
        event.passes = 5 * PULSE_PER_MINUTE
        event.totalpasses = event.passes
        player.events.add(event)

def init_events_object(object_):
    pass



# Below are the actual events.
# Some events will be reoccuring.  Those events can be decorated with the
# reoccuring_event decorator to automate the creation of the next event.

def reoccuring_event(func_to_decorate):
    def new_func(*args, **kwargs):
        event, = args
        nextevent = Event()
        nextevent.owner = event.owner
        nextevent.ownertype = event.ownertype
        nextevent.eventtype = event.eventtype
        nextevent.func = event.func
        nextevent.passes = event.totalpasses
        nextevent.totalpasses = event.totalpasses
        event.owner.events.add(nextevent)

        return func_to_decorate(*args, **kwargs)

    return new_func


def event_grapevine_restart(event_):
    event_.owner.gsocket = grapevine.GrapevineSocket()

@reoccuring_event
def event_grapevine_send_message(event_):
    if len(event_.owner.outbound_frame_buffer) > 0:
        event_.owner.handle_write()

@reoccuring_event
def event_grapevine_player_query_status(event_):
    event_.owner.msg_gen_player_status_query()

@reoccuring_event
def event_grapevine_receive_message(event_):
    grapevine_ = event_.owner
    grapevine_.handle_read()
    if len(grapevine_.inbound_frame_buffer) > 0:
        # Assign rcvd_msg to a GrapevineReceivedMessage instance.
        # The initialization of the object takes care of parsing the data
        # we received and setting appropritae values.
        #rcvd_msg = grapevine.GrapevineReceivedMessage(grapevine_.read_in(), grapevine_)

        rcvd_msg = grapevine_.receive_message()
        ret_value = rcvd_msg.parse_frame()

        if ret_value:
            # We will receive a "tells/send" if there was an error telling a
            # foreign game player.
            if rcvd_msg.event == "tells/send":
                caller, target, game, error_msg = ret_value
                message = (f"\n\r{{GMultiMUD Tell to {{y{target}@{game}{{G "
                           f"returned an Error{{x: {{R{error_msg}{{x")
                for eachplayer in player.playerlist:
                    if eachplayer.name.capitalize() == caller:
                        if eachplayer.oocflags_stored['mmchat'] == 'true':
                            eachplayer.write(message)
                            return

            if rcvd_msg.event == "tells/receive":
                sender, target, game, sent, message = ret_value
                message = (f"\n\r{{GMultiMUD Tell from {{y{sender}@{game}{{x: "
                           f"{{G{message}{{x.\n\rReceived at : {sent}.")
                for eachplayer in player.playerlist:
                    if eachplayer.name.capitalize() == target.capitalize():
                        if eachplayer.oocflags_stored['mmchat'] == 'true':
                            eachplayer.write(message)
                            return

            if rcvd_msg.event == "games/status":
                if ret_value:
                    # We've received a game status request response from
                    # grapevine.  Do what you will here with the information,
                    # Not going to do anything with it in Akrios at the moment.
                    return


            # Received Grapevine Info that goes to all players goes here.
            message = ""
            if rcvd_msg.event == "games/connect":
                game = ret_value.capitalize()
                message = f"\n\r{{GMultiMUD Status Update: {game} connected to network{{x"
            if rcvd_msg.event == "games/disconnect":
                game = ret_value.capitalize()
                message = f"\n\r{{GMultiMUD Status Update: {game} disconnected from network{{x"
            if rcvd_msg.event == "channels/broadcast":
                name, game, message = ret_value
                message = (f"\n\r{{GMultiMUD Chat{{x:{{y{name.capitalize()}"
                           f"@{game.capitalize()}{{x:{{G{message}{{x")
            if rcvd_msg.is_other_game_player_update():
                name, inout, game = ret_value
                message = (f"\n\r{{GMultiMUD Chat{{x: {{y{name.capitalize()}{{G "
                           f"has {inout} {{Y{game.capitalize()}{{x.")

            if message != "":
                for eachplayer in player.playerlist:
                    if eachplayer.oocflags_stored['mmchat'] == 'true':
                        eachplayer.write(message)
                return

        if hasattr(rcvd_msg, "event") and rcvd_msg.event == "restart":
            comm.log(world.serverlog, "Received restart event from Grapevine.")
            restart_time = rcvd_msg.restart_downtime
            restart_fuzz = 20
 
            grapevine_.gsocket_disconnect()

            nextevent = Event()
            nextevent.owner = grapevine_
            nextevent.ownertype = "grapevine"
            nextevent.eventtype = "grapevine restart"
            nextevent.func = event_grapevine_restart
            nextevent.passes = restart_time + restart_fuzz
            nextevent.totalpasses = nextevent.passes
            grapevine_.events.add(nextevent)

@reoccuring_event
def event_grapevine_state_check(event_):
    grapevine_ = event_.owner
    if grapevine_.state["connected"] == True:
        return
    else:
        grapevine_.gsocket_disconnect()

        nextevent = Event()
        nextevent.owner = grapevine_
        nextevent.ownertype = "grapevine"
        nextevent.eventtype = "grapevine restart"
        nextevent.func = event_grapevine_restart
        nextevent.passes = 3 * 60
        nextevent.totalpasses = nextevent.passes
        grapevine_.events.add(nextevent)



@reoccuring_event
def event_admin_system_status(event_):

    event_count = {'player': 0,
                   'mobile': 0,
                   'object': 0,
                   'area': 0,
                   'room': 0,
                   'exit': 0,
                   'server': 0,
                   'socket': 0,
                   'grapevine': 0}

    for each_type in things_with_events:
        for each_thing in things_with_events[each_type]:
            event_count[each_type] += each_thing.events.num_events()

    msg = (f"\n\r{{RAkrios System Status (5 minute update){{x\n\r"
           f"{{GPlayer Connections{{x: {{R{len(server.connlist)}{{x\n\r"
           f"{{G  Game Events List{{x\n\r"
           f"{{G        Player Events{{x: {{R{event_count['player']}{{x\n\r"
           f"{{G        Mobile Events{{x: {{R{event_count['mobile']}{{x\n\r"
           f"{{G        Object Events{{x: {{R{event_count['object']}{{x\n\r"
           f"{{G          Area Events{{x: {{R{event_count['area']}{{x\n\r"
           f"{{G          Room Events{{x: {{R{event_count['room']}{{x\n\r"
           f"{{G          Exit Events{{x: {{R{event_count['exit']}{{x\n\r"
           f"{{G        Server Events{{x: {{R{event_count['server']}{{x\n\r"
           f"{{G        Socket Events{{x: {{R{event_count['socket']}{{x\n\r"
           f"{{G     Grapevine Events{{x: {{R{event_count['grapevine']}{{x\n\r")

    event_.owner.write(msg)

@reoccuring_event
def event_player_autosave(event_):
    event_.owner.save()
    event_.owner.write("\n\rA cool breeze blows across your neck.")

@reoccuring_event
def event_player_idle_check(event_):
    idle_time = time.time() - event_.owner.last_input
 
    if event_.owner.is_building or event_.owner.is_editing or event_.owner.is_admin:
        return

    if idle_time >= 10 * 60:
        event_.owner.write("\n\r{WYou have been idle for over 10 minutes.  Logging you out.{x")
        event_.owner.interp('quit force')
        return

    if idle_time > 8 * 60:
        event_.owner.write("\n\r{WYou have been idle for over 8 mimutes. Auto logout in 2 minutes.{x")
        event_.owner.sock.send(b'\x07')
        return

    if idle_time >= 5 * 60:
        event_.owner.save()
        if event_.owner.oocflags['afk'] == True:
            return
        event_.owner.write("\n\r{WYou have been idle for over 5 minutes.  Placing you in AFK.{x")
        event_.owner.sock.send(b'\x07')
        event_.owner.oocflags['afk'] = True

@reoccuring_event
def event_player_newbie_notify(event_):
    if event_.owner.oocflags_stored['newbie'] == 'false':
        return

    tips = ["You will receive Newbie Tips periodically until disabled.\n\r"
            "              Use the 'toggle newbie' command to enable/disable.",
            "Type 'help' to see help topics.",
            "You can configure alias' for commands.  See 'help alias' for usage details",
            "Type 'who' to see who else is playing in Akrios.",
            "Type 'commands' to see the commands available to you.",
            "Type 'ooc <message>' to post an Out of Character message to all players in Akrios.",
            "Type 'beep Jubelo' to send a beep to Jubelo if you need help!",
            "Type 'say <message>' to say something to other players in the same room.",
            "Type 'look' to look at the room you are in",
            "Akrios is connected to grapevine.haus for MultiMUD Chat!\n\rType"
            " 'toggle mmchat' to disable or 'mmchat <message>' to speak to other players!"]
        
    event_.owner.write(f"\n\r{{P[NEWBIE TIP]{{x: {random.choice(tips)}")


