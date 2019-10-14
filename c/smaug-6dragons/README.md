For 6dragons & smaug

You will need the libwsclient library located below, along with curl and jansson

```bash
sudo apt-get update
sudo apt-get install curl libcurl4-openssl-dev libtool libjansson-dev build-essential pkg-config libssl-dev
```

In your home directory, clone the wsclient

sudo git clone https://github.com/payden/libwsclient.git

cd libwsclient

Now install the library
```bash
sudo ./autogen.sh
sudo ./configure && make && make install
```

drop in gossip.c into your src directory
Change at the top your CLIENT_ID and CLIENT_SECRET to what is shown on your mud on grapevine.haus


in comm.c in between copyover/hotboot recovery and the game loop, paste in

  // connect to Gossip
  gossip_connect();

It should look like this

   if( fCopyOver )
   {
      log_string( "Initiating hotboot recovery." );
      hotboot_recover(  );
   }

  // connect to Gossip
  gossip_connect();

   game_loop(  );

   close( control );

In mud.h (merc.h for other codebases) add the following:

/* gossip.c */
void gossip_connect();
void gossip_heartbeat();
void gossip_broadcast(const char * channel, const char * name, const char * game, const char * message);
void gossip_send(char * player, char * message);

in the channel section of mud.h of Smaug
#define CHANNEL_GOSSIP		   BV28

For 6dragons add the channel in
CHANNEL_SWEAR, CHANNEL_TELEPATHY, CHANNEL_6D, CHANNEL_GOSSIP


Now add in the command in the DECLARE_DO_FUN section
DECLARE_DO_FUN( do_gossip );


Add in the gossip command in and make a channel named gossip
You may need to change send_tochannel to whatver works on your mud.

For 6dragons in channels.c
void do_gossip( CHAR_DATA *ch, char *argument ) 
{
  MUD_CHANNEL            *channel;

  channel = find_channel("gossip");

  gossip_send(ch->name, argument);
  send_tochannel( ch, channel, argument );
  return;
}

For Smaug at the bottom of act_comm.c
void do_gossip( CHAR_DATA *ch, char *argument ) 
{
  gossip_send(ch->name, argument);
  talk_channel( ch, argument, CHANNEL_GOSSIP, "gossip"  );
  return;
}
In your makefile, add to the a PKG_CFG option and add it to the end of the compiler.

at the top add this
PKG_CFG        = `pkg-config --cflags --libs jansson libcurl` -lwsclient

add in gossip.c in the appropriate place

For Smaug at the bottom
	$(CC) -export-dynamic -o smaug $(O_FILES) $(PKG_CFG) $(L_FLAGS)

For 6dragons, make it look like this
all:
	@$(MAKE) -s $(PROG_NAME)

$(PROG_NAME): $(O_FILES)
	@rm -f $(PROG_NAME)
	@$(CC) $(L_FLAGS) -o $(PROG_NAME) $(O_FILES) $(L_FLAGS) $(PKG_CFG)

Recompile and boot 6dragons or Smaug, then add in the gossip command
cedit gossip create do_gossip
