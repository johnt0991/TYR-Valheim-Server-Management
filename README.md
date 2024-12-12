TYR - Valheim Server Management 

Tyr runs off prexisting files from the Valheim Server install.  It provides options for Discord Webhooking, Automated server restarts, and logging to make troubleshooting easier.

Session Info Tab - 
  Here you will find information on your server.  Once the server fully starts, the session name, IP address and Join code will be visible.

Restart Settings tab - 
  Here you are able to schedule automated restarts for your server.  To enable this feature, please check the "Enable Reset Scheduling" box, enter how often you would like the server to restart, the select the time you would like the restart schedule to start at.  
  This will occure daily, in your selected intervals at the designated time.  You can change the settings here at any time or disable them to manually restart your server.

Webhook Settings Tab - 
  Please set up a discord webhook for where you would like your notifications to post.
  Then take your webhook URL and paste it in the text box under the webhok tab in TYR.  Tyr will notify for server start up, join codes, server shutdowns, and 15 minute warnings for server restarts (if enabled).  TYR DOES NOT post server IP addresses to avoid giving IP information to any publc chats.  You will need to post that on your own.

Join Codes Tab - 
  This tab will show all join codes from oldest to most recent for as long as the program is running.

All Messages, Warnings, Errors, Console Printout, Proccesses tabs - 
  These tabs are all console based read outs.  

  All messages, warnings and errors are from the command console running valheim_server.exe
  Console Printouts are from messages being posted by Tyr into the console
  Proccesess are individual running threads and subproccesses that Tyr has started. 

Start and Stop Server Buttons - 
  They do exactly as they say they do, start and stop the server.

Clear All Button - 
  This clears all text fields inside the All Messages, Warnings, Errors, Console Printout, Proccesses tabs.  Server info, Webhook info, and restart settings are uneffected.
