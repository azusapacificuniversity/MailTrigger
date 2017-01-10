# MailTrigger

IMAP Email reader script that triggers a pin on the Raspberry Pi for 1/4 second when an Email is received in a specific label.  This can be used to control a soda machine to support remote payments, for example.

## Dependencies

* Python 2.6+

## Configuration

Add a ".mailtrigger" (no quotes) file in the running user's home directory with the following:

```
[Configuration]
server = 
port = 
user = 
password = 
imaplabel = 
audiofile = 
```
* *server* - Mail server (ie, imap.google.com)
* *port* - IMAP port
* *user* - Email account to access
* *password* - Password for email account
* *imaplabel* - Folder or Label of email account to monitor
* *audiofile* - Play a sound when triggered
