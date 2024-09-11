import configparser

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError, ChatAdminRequiredError
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch, InputPeerChannel, User

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Load environment variables
config = configparser.ConfigParser()
config.read("config.ini")
class TelegramScraper:
    def __init__(self):

# Setting configuration values
        self.api_id = config['Telegram']['api_id']
        self.api_hash = config['Telegram']['api_hash']

        self.api_hash = str(self.api_hash)

        self.phone = config['Telegram']['phone']
        self.username = config['Telegram']['username']
        self.client: Optional[TelegramClient] = None

    async def initialize(self):
        if not all([self.api_id, self.api_hash, self.phone, self.username]):
            raise ValueError("Missing environment variables. Please set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE, and TELEGRAM_USERNAME.")
        
        self.client = TelegramClient(self.username, self.api_id, self.api_hash)
        await self.client.start()
        logger.info("Client Created")

        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone)
            try:
                await self.client.sign_in(self.phone, input('Enter the code: '))
            except SessionPasswordNeededError:
                await self.client.sign_in(password=input('Password: '))

        me = await self.client.get_me()
        logger.info(f"Successfully signed in as {me.username}")

    async def get_all_participants(self, channel: InputPeerChannel) -> List[User]:
        all_participants = []
        offset = 0
        limit = 200
        max_retries = 5
        retry_delay = 30  # seconds

        while True:
            try:
                participants = await self.client(GetParticipantsRequest(
                    channel, ChannelParticipantsSearch(''), offset, limit,
                    hash=0
                ))
                if not participants.users:
                    break
                all_participants.extend(participants.users)
                offset += len(participants.users)
                logger.info(f"Retrieved {len(all_participants)} participants so far.")
                
                if len(participants.users) < limit:
                    # We've reached the end of the list
                    break
                
                await asyncio.sleep(1)  # Respect rate limits
            except FloodWaitError as e:
                logger.warning(f"Hit rate limit. Waiting for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
            except ChatAdminRequiredError:
                logger.error("Admin rights are required to fetch all participants.")
                break
            except Exception as e:
                logger.error(f"Error retrieving participants: {e}")
                if max_retries > 0:
                    logger.info(f"Retrying in {retry_delay} seconds... ({max_retries} retries left)")
                    await asyncio.sleep(retry_delay)
                    max_retries -= 1
                else:
                    logger.error("Max retries reached. Stopping participant retrieval.")
                    break

        return all_participants

    @staticmethod
    def participant_to_dict(participant: User) -> Dict[str, Any]:
        return {
            "id": participant.id,
            "first_name": getattr(participant, 'first_name', None),
            "last_name": getattr(participant, 'last_name', None),
            "username": getattr(participant, 'username', None),
            "phone": getattr(participant, 'phone', None),
            "is_bot": getattr(participant, 'bot', False)
        }

    async def scrape_channel(self, channel_input: str):
        try:
            if channel_input.isdigit():
                entity = InputPeerChannel(int(channel_input), 0)
            else:
                entity = channel_input

            channel = await self.client.get_entity(entity)
        except ValueError as e:
            logger.error(f"Invalid input: {e}")
            return

        all_participants = await self.get_all_participants(channel)
        all_user_details = [self.participant_to_dict(participant) for participant in all_participants]

        with open('user_data.json', 'w') as outfile:
            json.dump(all_user_details, outfile, indent=2)

        logger.info(f"Scraped {len(all_user_details)} participants. Data saved to user_data.json")

        # Print additional information about the channel
        logger.info(f"Channel ID: {channel.id}")
        logger.info(f"Channel Title: {channel.title}")
        logger.info(f"Channel Username: {channel.username}")
        logger.info(f"Channel Participants Count (from channel info): {channel.participants_count}")

async def main():
    scraper = TelegramScraper()
    await scraper.initialize()

    channel_input = input("Enter entity (Telegram URL or entity ID): ")
    await scraper.scrape_channel(channel_input)

if __name__ == "__main__":
    asyncio.run(main())