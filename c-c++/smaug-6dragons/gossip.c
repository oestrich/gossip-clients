/* ************************************************************************
*  File: gossip.c                                                         *
*  Usage: grapevine chat from grapevine.haus                              *
*                                                                         *
*  Adapted for SMAUG/6dragons by Ixliam of Whispers of Times Lost         *
*  Based on original code by Zach of Maelstrom & test.c from wsclient     *
*                                                                         *
*  Copyright (C) 2019 Ixliam                                              *
*  This program is free software: you can redistribute it and/or modify   *
*  it under the terms of the GNU General Public License as published by   *
*  the Free Software Foundation, either version 3 of the License, or      *
*  (at your option) any later version.                                    *
*                                                                         *
*  This program is distributed in the hope that it will be useful,        *
*  but WITHOUT ANY WARRANTY; without even the implied warranty of         *
*  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          *
*  GNU General Public License for more details.                           *
*                                                                         *
*  You should have received a copy of the GNU General Public License      *
*  along with this program.  If not, see <https://www.gnu.org/licenses/>. * 
************************************************************************ */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include "mud.h"

#define CLIENT_ID "YOUR CLIENT ID HERE" // Change this to yours on grapevine.haus
#define CLIENT_SECRET "YOUR SECRET ID HERE"

extern "C"
{
 #include <wsclient/wsclient.h>
}

 int gossip_onclose( wsclient *c );
 int gossip_onerror( wsclient *c, wsclient_error *err );
 int gossip_onmessage( wsclient *c, wsclient_message *msg );
 int gossip_onopen( wsclient *c );


extern "C"
{
 void libwsclient_onclose(wsclient *client, int (*cb)(wsclient *c));
 void libwsclient_onopen(wsclient *client, int (*cb)(wsclient *c));
 void libwsclient_onmessage(wsclient *client, int (*cb)(wsclient *c, wsclient_message *msg));
 void libwsclient_onerror(wsclient *client, int (*cb)(wsclient *c, wsclient_error *err));
 int libwsclient_send(wsclient *client, char *strdata);
}

/*
 * Globals
 */
extern wsclient *gossip_ws;

/*
 * Globals
 */
wsclient *gossip_ws;

void gossip_connect() {
  // initialize new wsclient * using specified URI
  gossip_ws = libwsclient_new("wss://grapevine.haus/socket");

  if(!gossip_ws) {
    log_string( "Unable to connect to Gossip" );
    bug("Unable to connect to Gossip");
    return;
  }

  // set callback functions for this client
  libwsclient_onopen(gossip_ws, &gossip_onopen);
  libwsclient_onmessage(gossip_ws, &gossip_onmessage);
  libwsclient_onerror(gossip_ws, &gossip_onerror);
  libwsclient_onclose(gossip_ws, &gossip_onclose);

  // starts run thread.
  libwsclient_run(gossip_ws);
}

void gossip_send(char * player, char * message) {
  char * payload;
  json_t * obj;

  obj = json_pack("{s:s, s:{s:s, s:s, s:s}}",
                  "event", "channels/send",
                  "payload",
                  "channel", "gossip",
                  "name", player,
                  "message", message
                  );

  payload = json_dumps( obj, 0 );

  libwsclient_send(gossip_ws, payload);

  free( payload );
}

void gossip_broadcast(const char * channel, const char * name, const char * game, const char * message) {
  char              buf[ MAX_STRING_LENGTH ];
  DESCRIPTOR_DATA * d;

  if(!gossip_ws) {
    return;
  }

  if ( !strcmp("gossip", channel) ) {
    sprintf( buf, " &G[Gossip] &C%s@%s: &G%s", capitalize(name), game, message );
  } else {
    return;
  }

  for ( d = first_descriptor; d; d = d->next ) {
    CHAR_DATA * ch = ( d->original ? d->original : d->character );

    if ( d->connected == CON_PLAYING  ) {    // && !xIS_SET( ch->deaf, CHANNEL_GOSSIP )
      send_to_char( buf, d->character );
      send_to_char( "\n\r", d->character );
    }
  }
}

void gossip_heartbeat() {
  DESCRIPTOR_DATA * d;
  char * payload;
  json_t * obj;
  json_t * players = json_array();

  for ( d = first_descriptor; d; d = d->next ) {
    CHAR_DATA  * wch;
    wch = ( d->original ) ? d->original : d->character;

    if ( d->connected != CON_PLAYING ) {
      continue;
    }

    json_array_append_new( players, json_string( wch->name ) );
  }

  obj = json_pack("{s:s, s:{s:o}}", "event", "heartbeat", "payload", "players", players);

  payload = json_dumps( obj, 0 );

  libwsclient_send(gossip_ws, payload);

  free( payload );
}

int gossip_onclose(wsclient *c) {
   log_string("Disconnected from Gossip");
   bug("Disconnected from Gossip");

  return 0;
}

int gossip_onerror(wsclient *c, wsclient_error *err) {
  char buf[ MAX_STRING_LENGTH ];

  sprintf(buf, "Gossip: %s", err->str);
  log_string(buf);

  if(err->extra_code) {
    errno = err->extra_code;
    perror("recv");
  }

  return 0;
}

int gossip_onmessage(wsclient *c, wsclient_message *msg) {
  char buf[ MAX_STRING_LENGTH ];
  const char * event;
  json_t     * message, * raw, * payload;
  json_error_t error;

  message = json_loads( msg->payload, 0, &error );

  if ( !message ) {
    sprintf( buf, "Gossip: JSON error on line %d: %s", error.line, error.text );
    log_string(buf);
    return 1;
  }

  raw = json_object_get( message, "event" );

  if ( !json_is_string( raw ) ) {
    log_string("Gossip: Unable to parse message JSON");
    return 1;
  }

  event = json_string_value( raw );
  payload = json_object_get( message, "payload" );

  if ( !strcmp(event, "heartbeat") ) {
    gossip_heartbeat();
  } else if ( !strcmp(event, "channels/broadcast") ) {
    const char * channel, * name, * game, * message1;

    json_unpack(payload,
                "{s:s, s:s, s:s, s:s}",
                "channel", &channel,
                "name", &name,
                "game", &game,
                "message", &message1
                );

    gossip_broadcast(channel, name, game, message);
  }

  return 0;
}

int gossip_onopen(wsclient *c) {
  char * payload;
  json_t * obj;

  log_string("Connected to Gossip");

  obj = json_pack("{s:s, s:{s:s, s:s, s:[s], s:[s], s:s, s:s}}",
                    "event", "authenticate",
                    "payload",
                    "client_id", CLIENT_ID,
                    "client_secret", CLIENT_SECRET,
                    "supports", "channels",
                    "channels", "gossip",
                    "version", "2.2.0",
                    "user_agent", "Smaug"
                    );

  payload = json_dumps( obj, 0 );

  libwsclient_send(c, payload);

  free( payload );

  return 0;
}
