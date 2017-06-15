#!/bin/bash
INSTANZ="PickupBot"
SCREENNAME='pickupbot'
SERVICE='./pubobot.py'
BPDIR=/home/~user/discord/bots/PUBobot-discord/
SCREENPID=/home/~user/discord/bots/PUBobot-discord/logs/PickupBotScreen.pid


case "$1" in
'start')
		if [ -f $SCREENPID ]
			then
				PID=`cat $SCREENPID`
			if ps ax | grep -v grep | grep $PID > /dev/null
			then
				echo "Not starting $INSTANZ - instance already running with PID: $PID"
			else
				echo "Script is not running - attempting to Start"
				rm -f $SCREENPID
				cd $BPDIR
				screen -L screen.log -dmS $SCREENNAME $SERVICE
				sleep 2
				ps -ef | grep SCREEN | grep $SCREENNAME | grep -v grep | awk ' { print $2 }' > $SCREENPID
		fi
			else
				echo "Attempting to ReStart"
				cd $BPDIR
				screen -L screen.log -dmS $SCREENNAME $SERVICE
				sleep 2
				ps -ef | grep SCREEN | grep $SCREENNAME | grep -v grep | awk ' { print $2 }' > $SCREENPID
		fi
		;;

'stop')
		if [ -f $SCREENPID ]
			then
				echo "stopping $INSTANZ"
				PID="`cat $SCREENPID`"
				kill -15 $PID
				#sleep 2
				#screen -S $SCREENNAME -X quit
				rm -f $SCREENPID
				
			else
				echo "Cannot stop $INSTANZ - no Pidfile found!"
		fi
		;;

'restart')
		$0 stop
		$0 start
		;;

'status')
		if [ -f $SCREENPID ]
			then
				PID=`cat $SCREENPID`
				if ps ax | grep -v grep | grep $PID > /dev/null
			then
				echo "$INSTANZ running with PID: [$PID]"
			else
				echo "$INSTANZ not running"
		fi
			else
				echo "$SCREENPID does not exist! Cannot process $INSTANZ status!"
				exit 1
		fi
		;;
		
'debug')
		screen -r $SCREENNAME
		;;
*)
		echo "usage: $0 { start | stop | restart | status | debug }"
		;;

esac
exit 0