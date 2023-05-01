# AWS Lambda SES Emailer

This Lambda function sends emails using AWS Simple Email Service (SES) with attachments from S3. It reads an HTML file stored in an S3 bucket, extracts the meta information for the email, and sends it to the specified recipients.

## Prerequisites

1. AWS account with access to Lambda, S3, and SES.
2. Python 3.8+.
3. Boto3 and BeautifulSoup4 installed (`pip install boto3 beautifulsoup4`).
4. Proper IAM role for Lambda function to access S3 and SES.

## Setup

1. Create an S3 bucket and configure environment variables in the Lambda function as follows:
   - `REGION_NAME`: AWS region where your resources are located.
   - `BUCKET_NAME`: Name of the S3 bucket where your HTML files and attachments are stored.
   - `MAIL_PASS_PATH`: S3 folder path to move files after successful processing.
   - `MAIL_FAIL_PATH`: S3 folder path to move files after failed processing.
   - `MAIL_QUEUE_PATH`: S3 folder path where HTML files and attachments are queued for processing.
   - `HTML_FILE_EXT`: File extension of HTML files (e.g., ".html").
2. Create a Lambda function with a Python 3.8+ runtime and upload the provided script.
3. Attach an IAM role to the Lambda function that allows access to S3 and SES.

## Usage

Upload HTML files and attachments (if any) to the specified `MAIL_QUEUE_PATH` in your S3 bucket. The Lambda function will automatically process the files in the queue and send emails based on the metadata provided in the HTML files.

### HTML File Metadata

The HTML files should include the following meta tags:

- `og:fromAddress`: Sender's email address.
- `og:toAddress`: Recipient's email address.
- `og:subject`: Email subject.
- `og:attachmentName`: Attachment file name (optional).
- `og:attachmentFile`: Attachment file path (relative to `MAIL_QUEUE_PATH`) in the S3 bucket (required if `og:attachmentName` is set).

## Function Flow

1. The Lambda function lists objects in the specified S3 bucket.
2. It filters HTML files from the list and processes them one by one.
3. For each HTML file, the function extracts the email metadata (sender, recipient, subject, attachment name, and attachment file) using BeautifulSoup4.
4. It composes a MIME email using the extracted metadata and sends it using AWS SES.
5. If the email is sent successfully, the function moves the processed HTML file and its attachment (if any) to the `MAIL_PASS_PATH` in the S3 bucket.
6. If the email fails to send, the function moves the processed HTML file and its attachment (if any) to the `MAIL_FAIL_PATH` in the S3 bucket.

## Want to connect?

Feel free to contact me on [Twitter](https://twitter.com/OnlineAnto), [DEV Community](https://dev.to/antoonline/) or [LinkedIn](https://www.linkedin.com/in/anto-online) if you have any questions or suggestions.

Or just visit my [website](https://anto.online) to see what I do.
