import re
import base64
import quopri
import email
from email.header import decode_header
from typing import Optional, List, Union
from dataclasses import dataclass
import aioimaplib


@dataclass
class MessageAttachment:
    uid: Optional[str]
    filename: Optional[str]
    attachment: Optional[str]


@dataclass
class Message:
    uid: Optional[str]
    subject: Optional[str]
    date_sent: Optional[str]
    date_received: Optional[str]
    body: Optional[str] = None
    attachments: Optional[MessageAttachment] = None
    is_big_text: Optional[bool] = False


class AsyncEmailClient:

    def __init__(self,
                 host: str,
                 port: int = 993,
                 ssl: bool = True,
                 timeout: float = None
                 ) -> None:
        """
        Initializes the IMAP client.

        :param host: Хост почтового сервера (например, "imap.gmail.com")
        :param port: Порт для подключения к почтовому серверу (по умолчанию 993)
        :param ssl: Использовать SSL/TLS для подключения (по умолчанию True)
        """
        self.host = host
        self.port = port
        self.ssl = ssl
        self.timeout = timeout
        self.conn = None

    @staticmethod
    def _clean_date_received(date_str: str) -> Optional[str]:
        cleaned_str = re.sub(r'\s*$.*?$', '', date_str).strip()
        date_pattern = re.compile(r'^([A-Za-z]{3}, )?\d{1,2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{4}')
        day_remove = re.sub(r'^[A-Za-z]{3},', '', cleaned_str).strip()
        if date_pattern.match(day_remove):
            date = re.sub(r'\([^)]*\)', '', day_remove)
            return date.strip()
        return None

    @staticmethod
    def _contains_html(text):
        if text:
            html_pattern = re.compile(r'<[^>]*>')
            return bool(html_pattern.search(text))
        return False

    @staticmethod
    def _get_uid(uid_str: str) -> Optional[str]:
        match = re.search(r'UID (\d+) RFC822', uid_str)
        if match:
            return match.group(1)
        return None

    async def _connect(self) -> Union[aioimaplib.IMAP4, aioimaplib.IMAP4_SSL]:
        """
        Подключается к почтовому серверу.

        :return: Возвращает экземпляр aioimaplib.IMAP4 или aioimaplib.IMAP4_SSL в зависимости от настроек SSL
        """
        if self.ssl:
            self.conn = aioimaplib.IMAP4_SSL(host=self.host, port=self.port, timeout=self.timeout)
        else:
            self.conn = aioimaplib.IMAP4(host=self.host, port=self.port, timeout=self.timeout)

    async def login(self, username: str, password: str) -> bool:
        """
        Вход на почтовый сервер.

        :param username: Имя пользователя
        :param password: Пароль пользователя
        :return: Возвращает True в случае успешного входа
        """
        try:
            await self.conn.wait_hello_from_server()
            _, data = await self.conn.login(username, password)
            return _ == 'OK'
        except Exception as e:
            print(e)
            return False

    async def disconnect(self):
        """Отключение от IMAP сервера."""
        try:
            if self.conn:
                await self.conn.logout()
                await self.conn.close()
        except Exception as e:
            print(e)

    async def messages_list(self, folder: str, query: str = None) -> List[str]:
        """
        Запрос для получения всех писем в папке
        :param query:
        :param folder: Папка
        :return: Возвращает список найденных сообщений
        """
        try:
            await self.conn.select(folder)
            if query:
                _, data = await self.conn.search(query)
            else:
                _, data = await self.conn.search('ALL')
            return [item.decode() for item in data[0].split()]
        except Exception as e:
            print(f"Ошибка поиска сообщений: {e}")
            return []

    async def fetch_message(self, message_id: str) -> Optional[Message]:
        """
        Загружает указанное сообщение на почтовом сервере.

        :param message_id: Идентификатор загружаемого сообщения
        :return: Возвращает объект с загруженным сообщением или None в случае ошибки
        """
        try:
            message_dict = dict()
            _, msg_data = await self.conn.fetch(message_id, '(UID RFC822)')
            msg = email.message_from_bytes(msg_data[1])
            subject_ = msg.get('Subject')
            if subject_:
                subject, encoding = decode_header(subject_)[0]
                if isinstance(subject, bytes):
                    subject_ = subject.decode(encoding if encoding else 'utf-8')
                else:
                    subject_ = None
            uid_decode = msg_data[0].decode('utf-8')
            message_dict['uid'] = self._get_uid(uid_decode)
            message_dict['date_sent'] = self._clean_date_received(msg.get('Date'))
            message_dict['subject'] = subject_
            received_headers = msg.get_all('Received')
            if received_headers:
                received_date_str = received_headers[-1]
                try:
                    date_part = received_date_str.split(';')[-1]
                    message_dict['date_received'] = self._clean_date_received(date_part)
                except Exception as e:
                    message_dict['date_received'] = None

            attachments = list()
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        try:
                            message_dict['body'] = part.get_payload(decode=True).decode('utf-8')
                            message_dict['is_big_text'] = True
                        except Exception as e:
                            print(e, subject_)

                    if part.get_content_disposition() == 'attachment':
                        filename = part.get_filename()
                        if filename:
                            try:
                                decode_headers = decode_header(filename)[0]
                                if decode_headers[1]:
                                    decoded_filename = decode_headers[0].decode()
                                else:
                                    decoded_filename = decode_headers[0]
                                uid = message_dict['uid']
                                attachments.append(
                                    MessageAttachment(
                                        uid=uid,
                                        filename=decoded_filename,
                                        attachment=part.get_payload(decode=True)
                                    )
                                )
                            except Exception as e:
                                print('attachment error', subject_, e)
            else:
                body = msg.get_payload(decode=True).decode('utf-8')
                message_dict['body'] = body
                message_dict['is_big_text'] = self._contains_html(body)
            message_dict['attachments'] = attachments
            return Message(**message_dict)
        except Exception as e:
            print(f"Ошибка загрузки сообщения: {e} {message_id}")
            return None

    async def __aenter__(self):
        """Вход в контекстный менеджер."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера."""
        await self.disconnect()
