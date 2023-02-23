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
    vk_bot.process()


if __name__ == '__main__':
    main()
