#!/usr/bin/python
# This script must be run as root because it uses the Raspberry Pi GPIO (sorry but it's a must)

# Needed to get values in from a configuration file
import ConfigParser
import os

# Needed for playing audio
import pygame.mixer as pymix

# Needed for IMAP Mail Checking and Marking Emails as Read in Specific Labels
import imaplib

# Needed for accessing Raspberry Pi GPIO connected devices
import RPi.GPIO as GPIO

# Needed for timing events
import time

# Needed for logging
import logging

# Load up the configuration file with default values
section = 'Configuration'
config = ConfigParser.SafeConfigParser({ 'loggingfacility' : 'sodapurchases', 'pollinginterval' : '10', \
	'pollrelogininterval' : '100', 'purchasedelay' : '10', 'relaypin' : '11', 'ledpin' : '12', \
 	'logfilename' : '/var/log/mailtrigger.log', 'heartbeatfile' : '/tmp/mailtrigger' })

# This is probably /root/.mailtrigger since the script has to be run as root to work
config.read([os.path.expanduser('~/.mailtrigger')])

# Logging settings
FORMAT = '%(asctime)-15s %(message)s'
FILENAME = config.get(section,'logfilename')
try:
	logging.basicConfig(filename=FILENAME,format=FORMAT,level=logging.DEBUG)
except:
	print "ERROR: Unable to initialize logging configuration!"
	print "We probably didn't have the root access to the log file we needed. Try starting with sudo."
	quit()
	
#-Get a logger for the specified logging facility
log = logging.getLogger(config.get(section,'loggingfacility'))

# IMAP Email Inbox SSL Connection Settings
server = config.get(section,'server')
port = int(config.get(section,'port'))
user = config.get(section,'user')
password = config.get(section,'password')
#-Needs to have no spaces in name
imaplabel = config.get(section,'imaplabel')
#-Number of seconds to wait between checking mailbox
pollingInterval = int(config.get(section,'pollinginterval'))
#-Reconnect every so often to keep a fresh connection
pollreloginInterval = int(config.get(section,'pollrelogininterval'))
#-Get heartbeat file (it gets 'touch'ed as long as mailtrigger is successful)
heartbeatFile = config.get(section,'heartbeatfile')
#-Start the poll count at 1
polledTimes = 1
#-Set the connection to "None" (NULL)
m = None
#-Set a delay after a purchase is made
purchaseDelay = int(config.get(section,'purchasedelay'))

# GPIO Settings
relaypin = int(config.get(section,'relaypin'))
ledpin = int(config.get(section,'ledpin'))
#-Just in case it hasn't been cleaned up yet
#GPIO.cleanup()
GPIO.setmode(GPIO.BOARD)

# Audio Settings
audiofile = config.get(section,'audiofile')
pymix.init()
try:
	pymix.music.load(audiofile)
except:
	log.warn("Failed to load the audio file on startup!")

try:
	#-Pin to control relay
	GPIO.setup(relaypin, GPIO.OUT)

	#-Pin to control led
	GPIO.setup(ledpin, GPIO.OUT)
except RuntimeError:
	print "ERROR: Unable to setup PI pin communication!"
	print "We probably didn't have the root access we needed. Try starting with sudo."
	quit()

#-Turn off LED to start
GPIO.output(ledpin, False)

# For some reason relyapin has to be "on" in order for the relay to be "off"
GPIO.output(relaypin, True)

# Define a function to 'touch' a file on success -- this is a sort of heartbeat to make sure script is running properly
# Borrowed from: http://stackoverflow.com/questions/1158076/implement-touch-using-python
def touch(fname, times=None):
    with open(fname, 'a'):
        os.utime(fname, times)

try:
	while True:
		if m is None or (polledTimes % pollreloginInterval) == 0:
			# Clear any previous connections
			if m is not None:
				try:
					log.info("Attempting to logout and close the connection to refresh it.")
					m.close()
					m.logout()
					m = None
				except:
					log.warn("Failed to logout and close the connection!")
					m = None

			# Reset polledTimes and open an SSL connection + Try to login
			pwSuccessCheck = False
			while m is None or pwSuccessCheck == False:
				try:
					log.info("Connecting to the IMAP4 server through SSL.")
					m = imaplib.IMAP4_SSL(server, port)
					polledTimes = 0
				except:
					log.error("Unabled to contact IMAP4 SSL server!")
					m = None
					# 3 second delay before trying to connect again
					time.sleep(3)

				# Attempt to login
				if m is not None:
					try:
						log.info("Logging in with saved credentials.")
						m.login(user, password)
						pwSuccessCheck = True
					except:
						log.error("Unable to login!")
						# 3 second delay before trying again
						time.sleep(3)

		try:
			m.select(imaplabel)
			status, response = m.search(None, "(UNSEEN)")
			unreadcount = 0

			# 'touch' the heartbeat file at this point
			touch(heartbeatFile)

			if len(response[0]) > 0:
				unreadmessages = response[0].split()
				unreadcount = len(unreadmessages)
				
				# Grab the first unread messaage
				newmesg = unreadmessages.pop()
				
				# Stole this bit of code to read the header from the email so we can verify it
				dummy, msg_data = m.fetch(newmesg, '(BODY.PEEK[HEADER])')
				for response_part in msg_data:
					if isinstance(response_part, tuple):
						log.debug(response_part[1])
            		
        # <-- Need to check the header here to make sure the email is legit

				log.info("Marking the first unread email as Seen.")
				m.store(newmesg,'+FLAGS','\Seen')

			log.info("Unread (Before marking any emails): " + `unreadcount`)
		except:
			log.error("Could not get unread messages from " + imaplabel + " label!")
			m = None
			unreadcount = 0

		if unreadcount > 0:
			try:
				try:
					pymix.music.play()

					# Wait until sound finishes
					while pymix.music.get_busy() == True:
						continue	
				except:
					log.error("Error while trying to play the sound!")

				# Turn on the relay for 1/4 second to trigger 110VAC solenoid that opens soda machine
				# Apparently for the relay -- False = "on", True = "off"
				GPIO.output(relaypin, False)
				time.sleep(0.25)
				GPIO.output(relaypin, True)

				# Turn on LED indicating the purchase
				GPIO.output(ledpin, True)
				
			except:
				log.error("Error occured while triggering relay to solenoid or purchase led!")

			# ...and wait for a period of time as an extra delay after purchase
			log.info("Delaying for purchase")
			time.sleep(purchaseDelay)


		# Wait some seconds between checking for unread messages (only if there's still an IMAP mail connection)
		if m is not None:
			time.sleep(pollingInterval)

		# Turn off LED indicator (if it's already off nothing happens)
		GPIO.output(ledpin, False)

		# Increment the pollTimes
		polledTimes = polledTimes + 1
except KeyboardInterrupt:
	log.critical("Script interrupted by keyboard!")
	#GPIO.cleanup()
