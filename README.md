# Script 'account_lock_imap.py'
- is expected to run from a cron job every 5 minutes
- connects to a Gmail account using IMAP
- searches for emails in gmail account folder/label "Account Locking"
- tracks the last seen email for state "LOCKED" or "UNLOCKED" within the account number hint
- accounts (credit cards) are expected to be unlocked for less than 5 minutes, or a notification will be sent
- if the last seen email is "UNLOCKED" for more than 5 minutes, then it will send a notification
- notification will be sent to both of us, as an email and a text message, on failures or unlock expiration

This is for Chase bank account locking, where the original email is sent to Kim by the bank.
Kim's email is forwarded to David, so she can delete whatever she wants. The copy of the same
email for David is all we have to work with, so David needs to keep the right number and stat of each account
by ensuring the last seen email for an account reflects the current state of the account.

# The subject line of the email from Chase is expected to be one of:
- We unlocked your credit card ending in xxxx
- We locked your credit card ending in xxxx

Where xxxx is the last 4 digits of the credit card number.

# Configuration values are stored in 'account_lock.json'
- Things like account name, app password, IFTTT Webhook, etc

# Flow
All emails in the "Account Locking" folder are read
- There may be emails from multiple accounts in this folder
- Within each account that is tracked here:
  - The email's timestamp is compared to the the most recent encountered
  - If the email is the the most recent found, the subject line is parsed for LOCK/UNLOCK
- If the last known state for an account is "UNLOCKED", then a notification is sent.
- If any failures are detected, then a notification is sent.

# Notification
Currently, "notification" is:
- a text message to David's phone
- an email to both of us
- a log entry in the log file

# Crontab and code location
- script is run every 5 minutes from the crontab of the "david" account on the media server
- all related files are in "/home/david/projects/HOME/account_locking/"