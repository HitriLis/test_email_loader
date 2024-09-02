import asyncio
import json
from dateutil import parser
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from core.service.imap_client import AsyncEmailClient
from email_storage.models import EmailAccount, EmailMessage, EmailFile


class GeneralConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.groups = ["notifications", f'group_user_{self.user.id}_channel']
        if self.user.is_authenticated:
            for group_name in self.groups:
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
            await self.accept()

    async def receive(self, text_data):
        data_json = json.loads(text_data)
        command = data_json.get('command')

        if command == 'start_fetch':
            email_account_id = data_json.get('email_account_id')
            asyncio.create_task(self.start_fetch(email_account_id))

    async def disconnect(self, close_code):
        for group_name in self.groups:
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name
            )

    async def send_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def start_fetch(self, email_account_id):
        group_name = f'group_user_{self.user.id}_channel'
        total_messages = 0
        messages_model_list = []
        email_account = await EmailAccount.get_email_account(email_account_id, self.user.id)
        try:
            if email_account:
                messages_count = email_account.count_messages
                async with AsyncEmailClient(host=email_account.host, ssl=True) as client:
                    login = await client.login(email_account.email, email_account.password)
                    if login and not email_account.start_parse:
                        email_account.start_parse = True
                        await database_sync_to_async(email_account.save)()
                        if not messages_count:
                            email_account.message_action = 'MESSAGE_LOAD'
                            await self.send_message_status(group_name, {
                                'process_parse': email_account.start_parse,
                                'progress': total_messages,
                                'type': email_account.message_action
                            })
                            await database_sync_to_async(email_account.save)()
                            messages_list = await client.messages_list('INBOX')
                            messages_list_count = len(messages_list)
                            for item_id in messages_list:
                                message = await client.fetch_message(item_id)
                                email_message = email_generate_message_model(email_account_id, message)
                                messages_model_list.append(email_message)
                                if message.attachments:
                                    await EmailFile.email_files_create(message.attachments)
                                total_messages += 1
                                await self.send_message_update(
                                    group_name, email_message, total_messages, messages_list_count, 'get_messages')
                        else:
                            email_account.message_action = 'MESSAGE_SEARCH'
                            await database_sync_to_async(email_account.save)()
                            last_message = await EmailMessage.get_last_message(email_account_id)
                            exists_lasts_messages = await EmailMessage.exists_lasts_messages(email_account_id, last_message.date_sent)

                            query = '(SINCE "%s")' % last_message.date_sent.strftime('%d-%b-%Y')
                            messages_list = await client.messages_list(
                                'INBOX',
                                query
                            )
                            messages_list_count = len(messages_list)
                            await self.send_message_status(group_name, {
                                'process_parse': email_account.start_parse,
                                'progress': total_messages,
                                'type': email_account.message_action
                            })
                            for item_id in messages_list:
                                message = await client.fetch_message(item_id)
                                email_message = email_generate_message_model(email_account_id, message)
                                total_messages += 1
                                await self.send_message_update(
                                    group_name, email_message, total_messages, messages_list_count, 'search')
                                if message.uid not in exists_lasts_messages:
                                    messages_model_list.append(email_message)
                                    if message.attachments:
                                        await EmailFile.email_files_create(message.attachments)

                            total_messages = 0
                            messages_list_count = messages_list_count - 1
                            email_account.message_action = 'MESSAGE_LOAD'
                            await database_sync_to_async(email_account.save)()
                            if messages_model_list:
                                await self.send_message_status(group_name, {
                                    'process_parse': email_account.start_parse,
                                    'progress': total_messages,
                                    'type': email_account.message_action
                                })
                            for model in messages_model_list:
                                await asyncio.sleep(0.1)
                                total_messages += 1
                                await self.send_message_update(
                                    group_name, model, total_messages, messages_list_count, 'get_messages')
                    else:
                        await self.send_message_status(group_name, {
                            'process_parse': email_account.start_parse,
                            'type': email_account.message_action
                        })
        except Exception as e:
            print(e)
        finally:
            email_account.start_parse = False
            email_account.message_action = None
            await database_sync_to_async(email_account.save)()
            await EmailMessage.email_messages_create(messages_model_list)
            await self.send_message_status(group_name, {
                'messages_total': total_messages,
                'process_parse': email_account.start_parse,
            })

    async def send_message_status(self, group_name: str, data: dict):
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'send_message',
                'data': data
            }
        )

    async def send_message_update(self,
                                  group_name: str, email_message: EmailMessage, total_messages: int,
                                  messages_count: int, state: str = None):
        if not email_message.is_big_text:
            message_text = email_message.description
            if message_text and len(message_text) > 150:
                message_text = message_text[:150] + "..."
        else:
            message_text = 'Текст содержит HTML. Не досткпен для просмотра'
        subject = email_message.subject if email_message.subject else 'Без темы'
        date_received_str = email_message.date_received.strftime(
            "%Y-%m-%d %H:%M") if email_message.date_received else None
        date_sent_str = email_message.date_sent.strftime(
            "%Y-%m-%d %H:%M") if email_message.date_sent else None
        data = {
            'messages_count': messages_count,
            'progress': total_messages,
            'state': state,
            'message': {
                'subject': subject,
                'date_received': date_received_str,
                'date_sent': date_sent_str,
                'description': message_text
            }
        }
        await self.channel_layer.group_send(
            group_name,
            {
                'type': 'send_message',
                'data': data
            }
        )


def email_generate_message_model(email_account_id, message) -> EmailMessage:
    date_sent = parser.parse(message.date_sent) if message.date_sent else None
    date_received = parser.parse(message.date_received) if message.date_received else None
    return EmailMessage(
        uid=message.uid,
        subject=message.subject,
        description=message.body,
        date_sent=date_sent,
        date_received=date_received,
        account_id=email_account_id,
        is_big_text=message.is_big_text
    )
