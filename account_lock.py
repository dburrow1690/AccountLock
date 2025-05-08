class AccountLockStatus:
    """
    This script checks for new emails in a specific Gmail label/folder using IMAP.
    It sends notifications via email and text message if any new emails are found.
    """

    def __init__(self):
        import  sys
        import  json
        import  jsonschema
        import  imaplib
        import  os
        import  logging
        from    logging.handlers import RotatingFileHandler

        import  email
        from    email.header import decode_header

        if len(sys.argv) > 1:
            self.CONF_FILE = sys.argv[1]                                        # Path to the configuration file provided as a command-line argument
        else:
            self.CONF_FILE = "account_lock.json"                                # Default configuration file

        log_file = os.path.join(os.path.dirname(__file__), "account_lock.log")  # Log file in the same directory as the script

        logging.basicConfig(
            level=logging.INFO,                                                 # Set logging level to INFO
            format="%(asctime)s - %(levelname)s - %(message)s",                 # Log format with timestamp
            handlers=[
                RotatingFileHandler(
                    log_file,                                                   # Log file path
                    maxBytes=10 * 1024 * 1024,                                  # Max size: 10 MB
                    backupCount=2                                               # Keep up to 5 backup log files
                )
            ]
        )

        self.exception = None                                                   # Initialize exception variable
        self.schema = \
        {
            "type": "object",
            "properties": {
                "gmail_label": {"type": "string"},
                "gmail_server": {"type": "string"},
                "gmail_account": {"type": "string"},
                "gmail_password": {"type": "string"},
                "ifttt_webhook_key": {"type": "string"},
                "recipients": {"type": "object"},
                "properties": {
                    "user_email": {
                        "type": "object",
                        "patternProperties": {
                            "^[\\w.%+-]+@[\\w.-]+\\.[a-zA-Z]{2,}$": {"type": "string"}
                        },
                        "additionalProperties": False
                    }
                },
            },
            "required": [
                "gmail_label",
                "gmail_server",
                "gmail_account",
                "gmail_password",
                "ifttt_webhook_key",
                "ifttt_event",
                "recipients"
            ]
        }                                                                       # JSON schema for validation

        with open(self.CONF_FILE) as f:
            self.config = json.load(f)                                          # Load configuration file
            try:
                jsonschema.validate(self.config, self.schema)                   # Validate configuration file
            except jsonschema.ValidationError as e:
                self.wail_n_fail(f"Config File Validation error: {str(e)}")     # Raise exception to stop the program

        try:
            self.imap = imaplib.IMAP4_SSL(self.config['gmail_server'])          # Setup connection to the server
            self.imap.login(                                                    # Login to the account
                self.config['gmail_account'],
                self.config['gmail_password']
            )
        except imaplib.IMAP4.error as e:
            self.wail_n_fail(None,f"IMAP4 error: {str(e)}")                     # Raise exception to stop the program

        self.SUBJECT = ""                                                       # Subject of the email/texts
        self.MESSAGE = ""                                                       # Message body of the email/texts
        self.account_status = {}                                                # Dictionary to store account status

    def send_text(self, phone_number):
        import requests
        import logging

        # Replace with your IFTTT webhook details
        event = self.config['ifttt_event']                                      # IFTTT event name
        webhook = self.config['ifttt_webhook_key']

        trigger = f"{event}/json/with/key/{webhook}"
        url = f"https://maker.ifttt.com/trigger/{trigger}"                      # IFTTT webhook URL
        payload = {
            "number": phone_number,                                             # Phone number (if configured in IFTTT)
            "subject": self.SUBJECT,                                            # Subject of the SMS
            "message": self.MESSAGE                                             # Message body of the SMS
        }

        try:
            response = requests.post(url, json=payload)                         # Send the request to IFTTT
            logging.info(str(response.content.decode()))
        except Exception as e:
            err = f"Failed to send SMS via IFTTT: {str(e)}"
            logging.err(err)                                                    # Log the error
            raise Exception(err)

    def send_email(self,email_address):
        import smtplib
        import logging
        from email.mime.text import MIMEText

        msg = MIMEText(self.MESSAGE)                                            # Create the email message
        msg['Subject'] = self.SUBJECT
        msg['From'] = self.config['gmail_account']
        msg['To'] = email_address

        try:
            with smtplib.SMTP_SSL(self.config['gmail_server'], 465) as server:   # Connect to the SMTP server
                server.login(                                                   # Login to the email account
                    self.config['gmail_account'],
                    self.config['gmail_password']
                )
                server.sendmail(                                                # Send the email
                    self.config['gmail_account'],
                    email_address,
                    msg.as_string()
                )
            logging.info(f"Email sent to {email_address}")                      # Log the email sending
        except Exception as e:
            err = f"Failed to send email: {str(e)}"
            logging.error(err)                                                  # Log the error
            wail_n_fail(err)                                                    # Raise exception to stop the program

    def wail_n_fail(self, message):
        self.SUBJECT = "Account Locking Exception"                              # Set the subject for the error notification
        err =  "An error/exception has occured"
        self.notify(f"{err}\n\n{message}")                                      # Notify the user
        raise Exception(f"{self.SUBJECT} {self.MESSAGE}")                       # Raise exception to stop the program

    def notify(self, message, subject=None):
        import time
        import logging

        if self.SUBJECT is None:                                                # Check if subject is None
            subject = "Account Locking Notification"                            # Set the subject for the notification
        else:
            subject = self.SUBJECT                                              # Use class attribute for subject

        self.MESSAGE = message

        date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        logging.info(f"{date} Subject: {subject} Error: {message}")             # Log the subject/message to the console

        for smtpaddr,cellnum in self.config['recipients'].items():
            self.send_email(smtpaddr)                                           # Send email
            self.send_text(cellnum)                                             # Send text message

        return

    def main(self):
        import  logging
        import  email
        import  json
        from    email.header    import decode_header
        from    email.utils     import parsedate_to_datetime

        status, folders = self.imap.list()
        if status != 'OK':
            err = f"Error in listing folders, status: {str(status)}"
            self.wail_n_fail(err)                                               # Raise exception to stop the program with default subject

        FOUND = False
        label_name = self.config['gmail_label']                                 # Simple string represents the label/folder name (no escaping needed)

        for label in folders:
            label_parts = label.decode().split('"')
            if label_name in label_parts:
                FOUND = True
                break

        if not FOUND:
            err = f"Error finding folder {label_name}"
            self.wail_n_fail(err)                                               # Raise exception to stop the program with default subject

        logging.info(f"Found folder '{label_name}'")
        status, _ = self.imap.select(f'"{label_name}"', readonly=True)          # Don't change the single/double quotes
        if status != 'OK':
            err = f"Error opening folder {label_name}, status: {str(status)}"
            self.wail_n_fail(err)                                               # Raise exception to stop the program with default subject

        status, message_nums = self.imap.search(None, 'ALL')                    # Search for UNSEEN messages in that folder
        if status != 'OK':
            err = f"Error searching {label_name}, status: {str(status)}"
            self.wail_n_fail(None,err)                                          # Raise exception to stop the program with default subject

        email_ids = message_nums[0].split()
        logging.info(f"Found {len(email_ids)} emails in '{label_name}':")


        for num in email_ids:
            status, data = self.imap.fetch(num, '(RFC822)')
            if status != 'OK':
                logging.error(f"Failed to fetch message {num}")
                continue

            msg = email.message_from_bytes(data[0][1])

            # Extract and parse the 'Date' header
            date_header = msg.get('Date')
            if date_header:
                try:
                    email_date = parsedate_to_datetime(date_header)             # Convert to datetime object
                    logging.info(f"Email received on: {email_date}")
                except Exception as e:
                    logging.error(f"Failed to parse email date: {str(e)}")
                    email_date = None
            else:
                logging.warning("No 'Date' header found in email.")
                email_date = None

            subject, encoding = decode_header(msg['Subject'])[0]                # Extract and decode the subject
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')

            logging.info(f"Found Subject: {subject}")
            subject_starts = {
                'We unlocked your credit card ending in ': 'UNLOCKED',
                'We locked your credit card ending in ': 'LOCKED'
            }                                                                   # Dictionary to check for specific subject lines

            for test_subject, status in subject_starts.items():
                if subject.startswith(test_subject):
                    account_number = subject.split(" ")[-1]                     # Extract the account number from the subject
                    if account_number not in self.account_status \
                    or self.account_status[account_number]['since'] < str(email_date):
                        self.account_status[account_number] = {
                            "status": status,
                            "since": str(email_date)                            # Store the email's timestamp
                        }

        with open('account_status.json','w') as f:
            try:
                json.dump(self.account_status, f, indent=4)                     # Save the account status to a JSON file
            except Exception as e:
                err = f"Failed to write account status to file: {str(e)}"
                logging.error(err)                                              # Log the error
                self.wail_n_fail(err)                                           # Raise exception to stop the program

        for account_number, details in self.account_status.items():             # Log the account statuses with timestamps
            acct_txt = f"Account ending in {account_number}"
            stat_txt = f" is {details['status']} as of {details['since']}"
            curr_state = (f"{acct_txt}{stat_txt}")
            if details['status'] == 'UNLOCKED':
                self.SUBJECT = "FOUND AN UNLOCKED ACCOUNT"                      # Set the subject for unlocked accounts
                self.notify(curr_state)                                         # Now that were sure we have the

        self.imap.logout()

if __name__ == "__main__":
    AccountLockStatus().main()