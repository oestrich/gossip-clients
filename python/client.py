#! usr/bin/env python3
# Project: Akrios
# Filename: gossip.py
# 
# File Description: A module to allow connection to Gossip chat network.
#                   Visit https://www.gossip.haus/
#
# Dependencies: You will need to 'pip3 install websocket-client' to use this module.
#
#
# Implemented features:
#       Auhentication to the Gossip network.
#       Registration to the Gossip Channel(default) or other channels.
#       Restart messages from the Gossip network.
#       Sending and receiving messages to the Gossip(default) or other channel.
#       Sending and receiving Player sign-in/sign-out messages.
#       Player sending and receiving Tells.
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
# into the appropriate instance attributes of GossipSocket below.  Please note the instance
# attribute in GossipSocket of debug, set to True if you would like to print to stdout various
# things that happen to help with debugging.
#
# You will need to periodically call the gsocket.handle_read() and gsocket.handle_write() as
# required by your configuration.   Please see the examples in the repo of how this might look
# for you.
#
# 
#
# Please see additional code examples of commands, events, etc in the repo.
# https://github.com/oestrich/gossip-clients
#
# By: Jubelo, Creator of AkriosMUD
# On: 1/6/19
# At: akriosmud.funcity.org:4000
#     jubelo@akriosmud.funcity.org
# 

import json
import socket
import datetime
import uuid
from websocket import WebSocket

# The below imports are for Akrios.  PLEASE LOOK BELOW FOR COMMENTS WITH XXX
# in them to see how I tied in my side.  You can safetly ignore some of them
# being commented, but others you will need to implement (like heartbeat player list).
#import comm
#import event
#import player
#import world

class GossipReceivedMessage():
    def __init__(self, message, gsock):
        # Short hand to convert JSON data to instance attributes.
        # Not secure at all.  If you're worreid about it feel free to modify
        # to your needs.
        for eachkey, eachvalue in json.loads(message).items():
            setattr(self, eachkey, eachvalue)

        # Point an instance attribute to the module level gossip socket.
        # Used for adding to and removing refs in some of the below methods.
        self.gsock = gsock
        
        # When we receive a websocket it will always have an event type.
        # We utilize the event type as the key and associate a receiver method and gsock
        # dependent on what we want to do with the received data.
        self.rcvr_func = {"heartbeat": (self.gsock.msg_gen_heartbeat, None),
                          "authenticate": (self.is_received_auth, None),
                          "restart": (self.is_received_restart, None),
                          "channels/broadcast": (self.received_broadcast_message, None),
                          "channels/subscribe": (self.received_chan_sub, gsock.sent_refs),
                          "channels/unsubscribe": (self.received_chan_unsub, gsock.sent_refs),
                          "players/sign-out": (self.received_player_logout, gsock.sent_refs),
                          "players/sign-in": (self.received_player_login, gsock.sent_refs),
                          "games/connect": (self.received_games_connected, None),
                          "games/disconnect": (self.received_games_disconnected, None),
                          "games/status": (self.received_games_status, gsock.sent_refs),
                          "players/status": (self.received_player_status, gsock.sent_refs),
                          "tells/send": (self.received_tells_status, gsock.sent_refs),
                          "tells/receive": (self.received_tells_message, None),
                          "channels/send": (self.received_message_confirm, gsock.sent_refs)}

        # If we receive a restart, this will be updated.
        self.restart_downtime = 0

    # Verify we have an attribute from the JSON that is 'event'.  If we have a key
    # in the rcvr_func that matches, go ahead and execute.
    def parse_frame(self):
        if hasattr(self, "event") and self.event in self.rcvr_func:
            exec_func, args = self.rcvr_func[self.event]
            if args == None:
                retvalue = exec_func()
            else:
                retvalue = exec_func(args)
                
            if retvalue:
                return retvalue

    def is_event_status(self, status):
        # A helper method to determine if the event we received is type of status
        if hasattr(self, "event") and hasattr(self, "status"):
            if self.status == status:
                return True
            else:
                return False

    def is_received_auth(self):
        # We received an event Auth event type.
        # Determine if we are already authenticated, if so subscribe to the channels
        # as determined in msg_gen_chan_subscribed in the Gossip Socket Object.
        # Otherwise, if we are not authenticated yet we send another authentication attempt
        # via msg_gen_authenticate().  This is in place for path hiccups or restart events.
        if self.is_event_status("success"):
            self.gsock.state["authenticated"] = True
            self.gsock.msg_gen_chan_subscribe()
            self.gsock.msg_gen_player_status_query()
        elif self.gsock.state["authenticated"] == False:
            self.gsock.msg_gen_authenticate()
        
    def is_received_restart(self):
        # We received a restart event. We'll asign the value to the restart_downtime
        # attribute for access by the calling code.
        if hasattr(self, "payload"):
            self.restart_downtime = int(self.payload["downtime"])


    # The below status successful methods are quite generic.  They are currently individualized
    # placeholders so that code specific to those received successes can be written if required.
    # For example, received_chan_sub versus received_player_login which we don't care too much
    # about.

    def received_chan_sub(self, sent_refs):
        # We have attempted to subscribe to a channel.  This is a response message
        # from Gossip.
        # If failure, we make sure we show unsubbed in our local list.
        # if success, we make sure we show subscribed in our local list.
        if hasattr(self, "ref") and self.ref in sent_refs:
            orig_req = sent_refs.pop(self.ref)
            if self.is_event_status("failure"):
                channel = orig_req["payload"]["channel"]
                self.gsock.subscribed[channel] = False
                if self.gsock.debug:
                    print(f"Failed to subscribe to channel {channel}")
            elif self.is_event_status("success"):
                channel = orig_req["payload"]["channel"]
                self.gsock.subscribed[channel] = True

    def received_chan_unsub(self, sent_refs):
        # We at some point sent a channel unsubscribe. This is verifying Gossip
        # received that.  We unsub in our local list.
        if hasattr(self, "ref") and self.ref in sent_refs:
            orig_req = sent_refs.pop(self.ref)
            channel = orig_req["payload"]["channel"]
            self.gsock.subscribed[channel] = False

    def received_player_logout(self, sent_refs):
        # NOTE: This is a success message from Gossip indicating a player
        # logout message WE sent was received successfully.  Don't get confused
        # with a foreign player message sign-out which we deal with below.
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref)

    def received_player_login(self, sent_refs):
        # NOTE: This is a success message from Gossip indicating a player
        # login message WE sent was received successfully. Don't get confused
        # with a foreign player message sign-in which we deal with below.
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref)

    def received_player_status(self, sent_refs):
        # We have requested a multi-game or single game status update.
        # This is the response. We pop the valid Ref from our local list
        # and add them to the local cache.
        if hasattr(self, "ref") and hasattr(self, "payload"):
            # On first receive we pop the ref just so it's gone from the queue
            if self.ref in sent_refs:
                orig_req = sent_refs.pop(self.ref)
            game = self.payload["game"].capitalize()

            if len(self.payload["players"]) == 1 and self.payload["players"] == "":
                self.gsock.other_games_players[game] = []
                return
            if len(self.payload["players"]) == 1:
                player = self.payload["players"][0].capitalize()
                self.gsock.other_games_players[game] = []
                self.gsock.other_games_players[game].append(player)
                return
            if len(self.payload["players"]) > 1:
                player = [player.capitalize() for player in self.payload["players"]]
                self.gsock.other_games_players[game] = []
                self.gsock.other_games_players[game] = player
                return

    def received_tells_status(self, sent_refs):
        # One of the local players has sent a tell.  This is specific response of an error
        # Provide the error and other pertinent info to the local game for handling
        # as required.
        if hasattr(self, "ref"):
            if self.ref in sent_refs and hasattr(self, "error"):
                orig_req = sent_refs.pop(self.ref)
                if self.is_event_status("failure"):
                    caller = orig_req["payload"]['from_name'].capitalize()
                    target = orig_req["payload"]['to_name'].capitalize()
                    game = orig_req["payload"]['to_game'].capitalize()
                    return (caller, target, game, self.error)

    def received_tells_message(self):
        # We have received a tell message destined for a player in our game.
        # Grab the details and return to the local game to handle as required.
        if hasattr(self, "ref") and hasattr(self, "payload"):
            sender = self.payload['from_name']
            target = self.payload['to_name']
            game = self.payload['from_game']
            sent = self.payload['sent_at']
            message = self.payload['message']
                
            return (sender, target, game, sent, message)

    def received_games_status(self, sent_refs):
        # Received a game status response.  Return the received info to the local
        # game to handle as required.  Not using this in Akrios at the moment.
        if hasattr(self, "ref") and hasattr(self, "payload") and self.is_event_status("success"):
            orig_req = sent_refs.pop(self.ref)
            if self.ref in sent_refs:
                game = self.payload['game']
                display_name = self.payload['display_name']
                description = self.payload['description']
                homepage = self.payload['homepage_url']
                user_agent = self.payload['user_agent']
                user_agent_repo = self.payload['user_agent_repo_url']
                connections = self.payload['connections']

                supports = self.payload['supports']
                num_players = self.payload['players_online_count']

                return(game, display_name, description, homepage, user_agent,
                       user_agent_repo, connections, supports, num_players)

        if hasattr(self, "ref") and hasattr(self, "error") and self.is_event_status("failure"):
            orig_req = sent_refs.pop(self.ref)
            if self.ref in sent_refs:
                game = orig_req["payload"]["game"]
                error_code = self.error
                return (game, error_code)


    def received_message_confirm(self, sent_refs):
        # We received a confirmation that Gossip received an outbound broadcase message
        # from us.  Nothing to see here other than removing from our sent references list.
        if hasattr(self, "ref"):
            if self.ref in sent_refs and self.is_event_status("success"):
                orig_req = sent_refs.pop(self.ref) 

    def is_other_game_player_update(self):
        # A helper method to determine if this is a player update from another game.
        if hasattr(self, "event"):
            if self.event == "players/sign-in" or self.event == "players/sign-out":
                if hasattr(self, "payload") and 'game' in self.payload:
                    return True
            else:
                return False

    def received_other_game_player_update(self):
        # We verified externally that this is an update for a player from another game.
        # Set the correct verbiage and return the information to be utilized for messaging.
        # Also update our local cache of games/players.
        in_or_out = ""
        game = self.payload['game'].capitalize()
        player = self.payload['name'][0].capitalize()
        if self.gsock.debug:
            print(f"Received other game player update: {player} @ {game}")
        if self.event == "players/sign-in":
            in_or_out = "signed into"
            self.gsock.other_games_players[game].append(player)
            if self.gsock.debug:
                print(f"In: {self.gsock.other_games_players}")
        elif self.event == "players/sign-out":
            in_or_out = "signed out of"
            self.gsock.other_games_players[game].remove(player)
            if self.gsock.debug:
                print(f"Out: {self.gsock.other_games_players}")

        return (player, in_or_out, game)
                
    def received_games_connected(self):
        # A foreign game has connected to the network, add the game to our local
        # cache of games/players and send a request for player list.
        if hasattr(self, "payload"):
            # Clear what we knew about this game and request an update.
            # Requesting updates from all games at this point, might as well refresh
            # as I'm sure some games don't implement all features like player sign-in
            # and sign-outs.
            self.gsock.other_games_players[self.payload["game"]] = []
            self.gsock.msg_gen_player_status_query()
            return self.payload["game"]

    def received_games_disconnected(self):
        # A foreign game has disconnected, remove it from our local cache and return
        # details to local game to handle as required.
        if hasattr(self, "payload"):
            if self.payload["game"] in self.gsock.other_games_players:
                self.gsock.other_games_players.pop(self.payload["game"])
            return self.payload["game"]

    def received_broadcast_message(self):
        # We received a broadcast message from another game.  Return the pertinent
        # info so the local game can handle as required.  See examples above.
        if hasattr(self, "payload"):
            return (self.payload['name'], self.payload['game'], self.payload['message'])


class GossipSocket(WebSocket):
    def __init__(self):
        super().__init__(sockopt=((socket.IPPROTO_TCP, socket.TCP_NODELAY,1),))
        
        self.debug = False

        self.inbound_frame_buffer = []
        self.outbound_frame_buffer = []
        # This event attribute is specific to AkriosMUD.  Replace with your event
        # requirements, or comment/delete the below line.
        self.events = event.Queue(self, "gossip")
        
        # Replace the below with your specific information
        # XXX
        self.client_id = "YOUR-CLIENT-ID-HERE"
        self.client_secret = "YOUR-CLIENT-SECRET-HERE"
        self.supports = ["channels", "games", "players", "tells"]

        # Populate the channels attribute if you want to subscribe to a specific
        # channel or channels during authentication.
        self.channels = []
        # Set your version and user_agent here. XXX
        self.version = "0.0.14"
        self.user_agent = "AkriosMUD v0.4.4"

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

        # The below is a cache of players we know about from other games.
        # Right now I just use this to populate additional fields in our in-game 'who' command
        # to also show players logged into other Gossip connected games.
        self.other_games_players = {}


    def gsocket_connect(self):
        result = self.connect("wss://gossip.haus/socket")
        # We need to set the below on the socket as websockets.WebSocket is 
        # blocking by default.  :(
        self.sock.setblocking(0)
        self.state["connected"] = True
        self.outbound_frame_buffer.append(self.msg_gen_authenticate())

        # The below is a log specific to Akrios.  Leave commented or replace.
        # XXX
        #comm.log(world.serverlog, "Sending Auth to Gossip Network.")

    def gsocket_disconnect(self):
        self.state["connected"] = False
        self.events.clear()
        self.subscribed.clear()
        self.other_games_players.clear()
        self.close()

    def send_out(self, frame):
        # A generic to make writing out cleaner, nothing more.
        self.outbound_frame_buffer.append(frame)

    def read_in(self):
        # A generic to make reading in cleaner, nothing more.
        return self.inbound_frame_buffer.pop(0)

    def msg_gen_authenticate(self):
        # Need to authenticate to the Gossip.haus network to participate.
        # This creates and sends that authentication as well as defaults us to
        # an authenticated state unless we get an error back indicating otherwise.

        payload = {"client_id": self.client_id,
                   "client_secret": self.client_secret,
                   "supports": self.supports,
                   "channels": self.channels,
                   "version": self.version,
                   "user_agent": self.user_agent}

        # If we haven't assigned any channels, lets pull that out of our auth
        # so we aren't trying to auth to an empty string.  This also causes us
        # to receive an error back from Gossip.
        if len(self.channels) == 0 :
            payload.pop("channels")
 

        msg = {"event": "authenticate",
               "payload": payload}

        self.state["authenticated"] = True

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_heartbeat(self):
        # Once registered to Gossip we will receive regular heartbeats.  The
        # docs indicate to respond with the below heartbeat response which 
        # also provides an update player logged in list to the network.

        # The below line builds a list of player names logged into Akrios for sending
        # in response to a gossip heartbeat.  Uncomment/replace with your functionality.
        # XXX
        #player_list = [player.name.capitalize() for player in player.playerlist]
        #payload = {"players": player_list}
        payload = {"players": "AkriosExample!"}
        msg = {"event": "heartbeat",
               "payload": payload}

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_chan_subscribe(self, chan=None):
        # Subscribe to a specific channel, or Gossip by default.

        ref = str(uuid.uuid4())
        if not chan:
            payload = {"channel": "gossip"}
        else:
            payload = {"channel": chan}

        # Don't subscribe again if we already are.  Just bail out.
        if payload["channel"] in self.subscribed:
            return

        msg = {"event": "channels/subscribe",
               "ref": ref,
               "payload": payload}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_chan_unsubscribe(self, chan=None):
        # Unsubscribe from a specific channel, defaul to Gossip channel if
        # none given.
        ref = str(uuid.uuid4())
        if not chan:
            payload = {"channel": "gossip"}
        else:
            payload = {"channel": chan}

        msg = {"event": "channels/unsubscribe",
               "ref": ref,
               "payload": payload}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_player_login(self, player_name):
        # Notify the Gossip network of a player login.
        ref = str(uuid.uuid4())
        payload = {"name": player_name.capitalize()}
        msg = {"event": "players/sign-in",
               "ref": ref,
               "payload": payload}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_player_logout(self, player_name):
        # Notify the Gossip network of a player logout.
        ref = str(uuid.uuid4())
        payload = {"name": player_name.capitalize()}
        msg = {"event": "players/sign-out",
               "ref": ref,
               "payload": payload}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_message_channel_send(self, caller, channel, message):
        # Sends a channel message to the Gossip network.  If we're not showing
        # as subscribed on our end, we bail out.
        if channel not in self.subscribed:
            return

        ref = str(uuid.uuid4())        
        payload = {"channel": channel,
                   "name": caller.name.capitalize(),
                   "message": message[:290]}
        msg = {"event": "channels/send",
               "ref": ref,
               "payload": payload}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_game_all_status_query(self):
        # Request for each game to send full status update.  You will receive in
        # return from each game quite a bit of detailed information.  See the
        # Gossip.haus Documentation or review the receiver code above.
        ref = str(uuid.uuid4())

        msg = {"events": "games/status",
               "ref": ref}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_game_single_status_query(self, game):
        # Request for a single game to send full status update.  You will receive in
        # return from each game quite a bit of detailed information.  See the
        # Gossip.haus Documentation or review the receiver code above.
        ref = str(uuid.uuid4())

        msg = {"events": "games/status",
               "ref": ref,
               "payload": {"game": game}}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_player_status_query(self):
        # This requests a player list status update from all connected games.
        ref = str(uuid.uuid4())

        msg = {"event": "players/status",
               "ref": ref}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_player_single_status_query(self, game):
        # Request a player list status update from a single connected game.
        ref = str(uuid.uuid4())

        msg = {"events": "players/status",
               "ref": ref,
               "payload": {"game": game}}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))

    def msg_gen_player_tells(self, caller_name, game, target, msg):
        game = game.capitalize()
        target = target.capitalize()

        ref = str(uuid.uuid4())
        time_now = f"{datetime.datetime.utcnow().replace(microsecond=0).isoformat()}Z"
        payload = {"from_name": caller_name,
                   "to_game": game,
                   "to_name": target,
                   "sent_at": time_now,
                   "message": msg[:290]}

        msg = {"event": "tells/send",
               "ref": ref,
               "payload": payload}

        self.sent_refs[ref] = msg

        self.send_out(json.dumps(msg, sort_keys=True, indent=4))


    # Read and Write methods below with some error printing.  Change to logging or
    # wiznet, or whatever depending on your style.

    def handle_read(self):
        try:
            self.inbound_frame_buffer.append(self.recv())
            if self.debug:
                print(f"Gossip In: {self.inbound_frame_buffer[-1]}")
                print("")
        except:
            pass

    def handle_write(self):
        try:
            outdata = self.outbound_frame_buffer.pop(0)
            if outdata != None:
                self.send(outdata)
                if self.debug:
                    print(f"Gossip Out: {outdata}")
                    print("")
        except:
            if self.debug:
                print(f"Error sending data frame: {outdata}")


gsocket = GossipSocket()
