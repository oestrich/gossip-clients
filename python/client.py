#! usr/bin/env python3
# Project: Akrios
# Filename: gossip.py
#
# File Description: A module to allow connection to Gossip chat network.
#                   Visit https://www.gossip.haus/
#
# Implemented features:
#       Auhentication to the Gossip network.
#       Registration to the Gossip Channel.
#       Restart messages from the Gossip network.
#       Sending and receiving messages to the Gossip channel.
#       Sending and receiving Player sign-in/sign-out messages.
#
# Need to Implement:
#       Player sending and receiving Tells
#       Sending and receiving player status requests.
#       Sending single game requests.
#       Game connect and disconnect messages.
#       Sending and receiving game status requests.
#       Game Status (all connected games, and single game)
#
#
# Example usage would be to import this module into your main game server.  When this module
# is imported, gsocket is assigned to an instance of GossipSocket.  During instance initialization
# is when the connection to Gossip.haus happens.  PLEASE PUT YOUR CLIENT ID AND CLIENT SECRET
# into the appropriate instance attributes of GossipSocket below.
#
# You will need to periodically call the gsocket.handle_read() and gsocket.handle_write() as
# required by your configuration.   Please see the examples below of how this might look for you.
#
# The below two functions are being passed in the gossip.gsocket.
#
#def event_gossip_send_message(event_):
#    if len(event_.owner.outbound_frame_buffer) > 0:
#        event_.owner.handle_write()#
#
#def event_gossip_receive_message(event_):
#    gossip_ = event_.owner
#    gossip_.handle_read()
#    if len(gossip_.inbound_frame_buffer) > 0:
#        rcvd_msg = gossip.GossipReceivedMessage(gossip_.read_in(), gossip_)
#
#        returned_from_parse = rcvd_msg.parse_frame()
#
#        message = ""
#        if rcvd_msg.event == "channels/broadcast":
#            if rcvd_msg.is_received_channel_message():
#                name, game, message = rcvd_msg.received_message_string()
#                message = (f"\n\r{{GMultiMUD Chat{{x:{{Y{name.capitalize()}"
#                           f"@{game.capitalize()}{{x:{message}{{x")
#        if rcvd_msg.is_other_game_player_update():
#                name, inout, game = rcvd_msg.received_other_game_player_update()
#                message = (f"{{GMultiMUD Chat{{x: {{Y{name.capitalize()} "
#                           f"has {inout} {game.capitalize()}{{x.")
#        if message != "":
#            for eachplayer in player.playerlist:
#                if eachplayer.oocflags_stored['mmchat'] == 'true':
#                   eachplayer.write(message)
#            return
#
#        if rcvd_msg.event == "restart":
#            fuzz_time = 5
#            restart_time = retvalue + fuzz_time * PULSE_PER_SECOND
#            things_with_events["gossip"] = []
#            gossip.gsocket.gsocket_disconnect()
#
#            nextevent = Event()
#            nextevent.owner = gossip.gsocket
#            nextevent.ownertype = "gossip"
#            nextevent.eventtype = "gossip restart"
#            nextevent.func = init_events_gossip(gossip.gsocket, restart=True)
#            nextevent.passes = restart_time
#            nextevent.totalpasses = nextevent.passes
#            gossip.gsocket.events.add(nextevent)
#
#
# An example player command to send a message might look something like the below.
#
#def mmchat(caller, args):
#    if len(args.split()) == 0:
#        caller.write("Did you have something to say or not?")
#        return
#
#    to_send = gossip.gsocket.msg_gen_message_channel_send(caller, args)
#    gossip.gsocket.outbound_frame_buffer.append(to_send)
#    caller.write(f"{{GYou MultiMUD Chat{{x: {{G{args}{{x")
#
#
#
# By: Jubelo, Creator of AkriosMUD
#     akriosmud@gmail.com
#

import json
import socket
import uuid
from websocket import WebSocket


import event
import player


class GossipReceivedMessage():
    def __init__(self, message, gsock):
        for eachkey, eachvalue in json.loads(message).items():
            setattr(self, eachkey, eachvalue)

        self.gsock = gsock

        self.rcvr_func = {"heartbeat": (self.gsock.msg_gen_heartbeat, None),
                          "authenticate": (self.is_received_auth, None),
                          "restart": (self.is_received_restart, None),
                          "channels/broadcast": (self.received_message_string, None),
                          "channels/subscribe": (self.received_chan_sub_valid, gsock.sent_refs),
                          "players/sign-out": (self.received_player_logout, gsock.sent_refs),
                          "players/sign-in": (self.received_player_login, gsock.sent_refs),
                          "channels/send": (self.received_message_confirm, gsock.sent_refs)}


    def parse_frame(self):
        if hasattr(self, "event") and self.event in self.rcvr_func:
            exec_func, args = self.rcvr_func[self.event]
            if args == None:
                retvalue = exec_func()
            else:
                retvalue = exec_func(args
                        )
            if retvalue != None:
                return retvalue

    def is_event_status(self, status):
        if hasattr(self, "event") and hasattr(self, "status"):
            if self.status == status:
                return True
            else:
                return False

    def is_received_auth(self):
        if self.is_event_status("success"):
            self.gsock.state["authenticated"] == True
            self.gsock.msg_gen_chan_subscribe()
        elif self.gsock.state["authenticated"] == False:
            self.gsock.msg_gen_authenticate()

        return None

    def is_received_restart(self):
        if hasattr(self, "payload"):
            return int(self.payload["downtime"])

        return None

    def received_chan_sub_valid(self, sent_refs):
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref)

        return None

    def received_player_logout(self, sent_refs):
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref)

        return None

    def received_player_login(self, sent_refs):
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref)

        return None

    def received_message_confirm(self, sent_refs):
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref)

        return None

    def is_other_game_player_update(self):
        if hasattr(self, "event"):
            if self.event == "players/sign-in" or self.event == "players/sign-out":
                if hasattr(self, "payload") and 'game' in self.payload:
                    return True
            else:
                return False

    def received_other_game_player_update(self):
        in_or_out = ""
        if self.event == "players/sign-in":
            in_or_out = "signed out of"
        else:
            in_or_out = "signed into"

        return (self.payload['name'], in_or_out, self.payload['game'])

    def received_message_string(self):
        return (self.payload['name'], self.payload['game'], self.payload['message'])


class GossipSocket(WebSocket):
    def __init__(self):
        super().__init__(sockopt=((socket.IPPROTO_TCP, socket.TCP_NODELAY,1),))

        self.inbound_frame_buffer = []
        self.outbound_frame_buffer = []
        # This event attribute is specific to AkriosMUD.  Replace with your event
        # requirements, or comment/delete the below line.
        self.events = event.Queue(self, "gossip")

        self.client_id = "PUT YOUR CLIENT ID HERE"
        self.client_secret = "PUT YOUR CLIENT SECRET HERE"
        self.supports = ["channels", "games", "players"]
        self.channels = ["gossip"]
        self.version = "0.0.6"
        self.user_agent = "AkriosMUD Gossip Client"

        self.state = {"connected": False,
                      "authenticated": False}

        self.subscribed = {}
        for each_channel in self.channels:
            self.subscribed[each_channel] = False

        self.gsocket_connect()

        # This event initialization is specific to AkriosMUD. This would be a good
        # spot to initialize in your event system if required.  Otherwise comment/delete this line.
        event.init_events_gossip(self)

        self.sent_refs = {}


    def gsocket_connect(self):
        result = self.connect("wss://gossip.haus/socket")
        # We need to set the below on the socket as websockts.WebSocket is
        # blocking by default.  :(
        self.sock.setblocking(0)
        self.state["connected"] = True
        self.outbound_frame_buffer.append(self.msg_gen_authenticate())

    def gsocket_disconnect(self):
        self.state["connected"] = False
        self.close()

    def send_out(self, frame):
        self.outbound_frame_buffer.append(frame)

    def read_in(self):
        return self.inbound_frame_buffer.pop(0)

    def msg_gen_authenticate(self):
        payload = {"client_id": self.client_id,
                   "client_secret": self.client_secret,
                   "supports": self.supports,
                   "channels": self.channels,
                   "version": self.version,
                   "user_agent": self.user_agent}

        authenticate_msg = {"event": "authenticate",
                            "payload": payload}

        self.send_out(json.dumps(authenticate_msg, sort_keys=True, indent=4))
        self.state["authenticated"] = True

    def msg_gen_heartbeat(self):
        player_list = [player.name.capitalize() for player in player.playerlist]
        payload = {"players": player_list}
        heartbeat_msg = {"event": "heartbeat",
                         "payload": payload}

        self.send_out(json.dumps(heartbeat_msg, sort_keys=True, indent=4))

    def msg_gen_chan_subscribe(self):
        ref = str(uuid.uuid4())
        payload = {"channel": "gossip"}
        chan_subscribe_msg = {"event": "channels/subscribe",
                              "ref": ref,
                               "payload": payload}

        for each_channel in payload.values():
            self.subscribed[each_channel] = True

        self.send_out(json.dumps(chan_subscribe_msg, sort_keys=True, indent=4))

        self.sent_refs[ref] = chan_subscribe_msg

    def msg_gen_chan_unsubscribe(self):
        payload = {"channel": "gossip"}
        chan_unsubscribe_msg = {"event": "channels/unsubscribe",
                                "payload": payload}

        for each_channel in payload.values():
            self.subscribed[each_channel] = False

        self.send_out(json.dumps(chan_unsubscribe_msg, sort_keys=True, indent=4))

    def msg_gen_player_login(self, player_name):
        ref = str(uuid.uuid4())
        payload = {"name": player_name.capitalize()}
        player_login_msg = {"event": "players/sign-in",
                            "ref": ref,
                            "payload": payload}

        self.send_out(json.dumps(player_login_msg, sort_keys=True, indent=4))

        self.sent_refs[ref] = player_login_msg

    def msg_gen_player_logout(self, player_name):
        ref = str(uuid.uuid4())
        payload = {"name": player_name.capitalize()}
        player_logout_msg = {"event": "players/sign-out",
                             "ref": ref,
                             "payload": payload}

        self.send_out(json.dumps(player_logout_msg, sort_keys=True, indent=4))

        self.sent_refs[ref] = player_logout_msg

    def msg_gen_message_channel_send(self, caller, message):
        ref = str(uuid.uuid4())
        payload = {"channel": "gossip",
                   "name": caller.name.capitalize(),
                   "message": message[:120]}
        message_to_send = {"event": "channels/send",
                           "ref": ref,
                           "payload": payload}

        self.send_out(json.dumps(message_to_send, sort_keys=True, indent=4))

        self.sent_refs[ref] = message_to_send

    def handle_read(self):
        try:
            self.inbound_frame_buffer.append(self.recv())
            print(f"Received : {self.inbound_frame_buffer[-1]}")
        except:
            pass
    def handle_write(self):
        try:
            outdata = self.outbound_frame_buffer.pop(0)
            if outdata != None:
                self.send(outdata)
        except:
            print(f"Error sending data frame: {outdata}")


gsocket = GossipSocket()
