# SMS Bomber Telegram Bot

This project implements a Telegram bot that provides SMS bombing functionality. It's designed to send multiple SMS messages to a specified phone number for testing purposes. Please use responsibly and only on numbers you own or have explicit permission to test.

## Features

- SMS and call bombing functionality
- User management system
- Admin panel with various controls
- Database integration for user data storage
- Rate limiting and user blocking capabilities

## Prerequisites

- Python 3.7+
- MySQL database
- Telegram Bot Token

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/sms-bomber-bot.git
   cd sms-bomber-bot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your MySQL database and note down the credentials.

4. Create a `.env` file in the project root and add the following environment variables:
   ```
   BOT_TOKEN=your_telegram_bot_token
   MAIN_CHANNEL_ID=your_main_channel_id
   DB_NAME=your_database_name
   DB_HOST=your_database_host
   DB_USER=your_database_user
   DB_PASS=your_database_password
   ADMIN_ID=your_admin_user_id
   ```

## Usage

Run the bot using the following command:

```
python main.py
```

The bot will start and listen for commands on Telegram.

## Commands

- `/start` - Start the bot and check user membership
- `/admin` - Access the admin panel (for admin users only)

## Admin Panel Features

- View admin information
- Broadcast messages to all users
- Add new admin users
- Ban/unban users
- Set custom usage limits for users
- Set global usage limit

## Security Notes

- Ensure that your `.env` file is not committed to the repository
- Regularly update your bot token and database credentials
- Monitor bot usage to prevent abuse

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Do not use it for illegal activities. The authors are not responsible for any misuse or damage caused by this program.
