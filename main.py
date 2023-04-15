import datetime

# store secret keys
from dotenv import load_dotenv
import os

# vkbot
from vkbot import VkBot


def main():
    # getting tokens from dotenv
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    CLUB_ID = os.getenv("CLUB_ID")

    # creating vk_bot
    vk_bot = VkBot(TOKEN, CLUB_ID)
    try:
        vk_bot.process()
    except KeyboardInterrupt:
        print("Process interrupted!")
    except Exception as e:
        with open("bot.log", "a") as file:
            print(f"Bot crashed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=file)
            print(f"Error: {e}", file=file)
        exit(1)


if __name__ == '__main__':
    main()
