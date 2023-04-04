# vk_api
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

# mysql
from sql import DataBase

# user
from user import User


class VkBot:
    vk_session: vk_api.vk_api.VkApiGroup
    long_poll: VkBotLongPoll
    db: DataBase | None

    def __init__(self, token: str, club_id: str):
        self.db = None
        self.vk_session = vk_api.vk_api.VkApiGroup(token=token)
        self.long_poll = VkBotLongPoll(self.vk_session, club_id)

    def create_user(self, personal_id: str) -> None | User:
        response = self.vk_session.method(method="users.get", values={"user_ids": personal_id})
        if not response:
            return None
        vk_id = response[0]["id"]
        first_name = response[0]["first_name"]
        last_name = response[0]["last_name"]
        return User(personal_id, vk_id, first_name, last_name)

    def process(self) -> None:
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.user_message_handler(event)
            else:
                print(event.type)

    def user_message_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        # getting user_id
        user_id = event.obj["message"]["from_id"]
        user = self.create_user(user_id)

        self.mark_as_read(event.obj["message"]["peer_id"])

        # working with database
        self.user_database_handler(event, user)

        # printing data to terminal
        print(f'Who: {user.first_name} {user.last_name} |id: {user.vk_id}|')
        print(f'Text:', event.obj["message"]["text"])

    def mark_as_read(self, peer_id: int) -> None:
        self.vk_session.method("messages.markAsRead", {"peer_id": peer_id})

    def user_database_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        # creating database connection
        self.db = DataBase("localhost", "admin", "vk_bot")

        # adding new client to database
        if not self.db.user_role_check(user.vk_id, "user"):
            self.db.sql_execute_query(f'INSERT INTO user VALUES ({user.vk_id})')

        if event.obj["message"]["text"]:
            if self.user_command_handler(event, user):
                self.db.close()
                return

        # TODO: add support of forwarding another data from message (such as gifs, docs, music, etc.)
        # forwarding message to other member of dialog if it exists
        if self.db.is_connected(user.vk_id):
            self.forward_message(message=event.obj["message"]["text"],
                                 user_id=self.db.get_companion(user.vk_id),
                                 attachments=event.obj["message"]["attachments"])

        # closing database connection
        self.db.close()

    def user_command_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> bool:
        # TODO: Add errors handler
        # TODO: DELETE DEBUG INFO
        command = (event.obj["message"]["text"].split())[0]
        setters = {
            '/add_author': self.add_author,
            '/del_author': self.delete_author,
            '/add_admin': self.add_admin,
            '/del_admin': self.delete_admin,
            '/req_connection': self.request_connection,
            '/accept': self.accept_connection,
            '/decline': self.decline_connection,
            '/add_connection': self.create_connection,
            '/del_connection': self.delete_connection,
        }
        if command in setters:
            setters[command](event, user)
            return True

        getters = {
            '/authors': self.get_authors,
            '/admins': self.get_admins,
            '/connections': self.get_connections,
            '/disconnect': self.disconnect,
        }

        if command in getters:
            getters[command](user)
            return True

        return False

    def invalid_command(self, text: str, user: User) -> None:
        self.forward_message(message=f'⛔️ Ошибка: ' + text + ' ⛔️',
                             user_id=user.vk_id)

    # commands
    def add_author(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/add_author id_автора', user)
            return

        _, author_personal_id = event.obj["message"]["text"].split()
        new_author = self.create_user(author_personal_id)
        if not new_author:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        if self.db.user_role_check(user.vk_id, "admin") and not self.db.user_role_check(new_author.vk_id, "author"):
            self.db.sql_execute_query(f'INSERT INTO author VALUES ({new_author.vk_id})')
            self.forward_message(
                message=f'✅ Автор @id{new_author.vk_id} ({new_author.first_name} {new_author.last_name}) был добавлен! ✅',
                user_id=user.vk_id
            )
            self.forward_message(
                message=f'✅ Вы были добавлены в список авторов! ✅',
                user_id=new_author.vk_id
            )
        else:
            if self.db.user_role_check(user.vk_id, "admin"):
                self.forward_message(
                    message=f'⚠️ Автор @id{new_author.vk_id} ({new_author.first_name} {new_author.last_name}) уже существовал! ⚠️',
                    user_id=user.vk_id
                )
            else:
                self.forward_message(
                    message=f'⛔️ У вас недостаточно прав для этой команды! ⛔️',
                    user_id=user.vk_id
                )

    def get_authors(self, user: User) -> None:
        if self.db.user_role_check(user.vk_id, "admin"):
            authors_id = self.get_pretty_id(self.db.sql_read_query('SELECT * FROM author'))
            if len(authors_id):
                self.forward_message(
                    message='Список авторов:\n' + ", ".join(authors_id),
                    user_id=user.vk_id
                )
            else:
                self.forward_message(
                    message='⚠️ Список авторов пуст! ⚠️',
                    user_id=user.vk_id
                )
        else:
            self.forward_message(
                message='⛔️ У вас недостаточно прав! ⛔️',
                user_id=user.vk_id
            )

    def delete_author(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/del_author id_автора', user)
            return

        _, author_personal_id = (event.obj["message"]["text"].split())
        new_author = self.create_user(author_personal_id)
        if not new_author:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        if self.db.user_role_check(user.vk_id, "admin") and self.db.user_role_check(new_author.vk_id, "author"):
            self.db.sql_execute_query(f'DELETE FROM author WHERE author_id = {new_author.vk_id}')
            self.forward_message(
                message=f'✅ Автор @id{new_author.vk_id} ({new_author.first_name} {new_author.last_name}) был удален! ✅',
                user_id=user.vk_id
            )
            self.forward_message(
                message=f'⚠️ Вас исключили из списка авторов! ⚠️',
                user_id=new_author.vk_id
            )
        else:
            if self.db.user_role_check(user.vk_id, "admin"):
                self.forward_message(message=f'⚠️ Автора {new_author.personal_id} не существует! ⚠️',
                                     user_id=user.vk_id)
            else:
                self.forward_message(message=f'⛔️ У вас недостаточно прав! ⛔️',
                                     user_id=user.vk_id)

    def add_admin(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/add_admin id_администратора', user)
            return

        _, admin_personal_id = (event.obj["message"]["text"].split())
        new_admin = self.create_user(admin_personal_id)
        if not new_admin:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        if self.db.user_role_check(user.vk_id, "admin") and not self.db.user_role_check(new_admin.vk_id, "admin"):
            self.db.sql_execute_query(f'INSERT INTO admin VALUES ({new_admin.vk_id})')
            self.forward_message(
                message=f'✅ Администратор @id{new_admin.vk_id} ({new_admin.first_name} {new_admin.last_name}) был добавлен! ✅',
                user_id=user.vk_id
            )
            self.forward_message(
                message=f'✅ Вы были добавлены в список администраторов! ✅',
                user_id=new_admin.vk_id
            )
        else:
            if self.db.user_role_check(user.vk_id, "admin"):
                self.forward_message(
                    message=f'⚠️ Администратор @id{new_admin.vk_id} ({new_admin.first_name} {new_admin.last_name}) уже существует! ⚠️',
                    user_id=user.vk_id
                )
            else:
                self.forward_message(
                    message=f'⛔️ У вас недостаточно прав! ⛔️',
                    user_id=user.vk_id
                )

    def get_pretty_id(self, response):
        result = []
        for val in response:
            user = self.create_user(val[0])
            result.append(f"@id{user.vk_id} ({user.first_name} {user.last_name})")
        return result

    def get_pretty_connections(self, response):
        result = []
        for val in response:
            client = self.create_user(val[1])
            author = self.create_user(val[2])
            result.append(
                f"Соединение #{val[0]}\n"
                f"👔 Клиент: @id{client.vk_id} ({client.first_name} {client.last_name})\n"
                f"✏️ Автор: @id{author.vk_id} ({author.first_name} {author.last_name})\n"
            )
        return result

    def get_admins(self, user: User) -> None:
        if self.db.user_role_check(user.vk_id, "admin"):
            admins_id = self.get_pretty_id(self.db.sql_read_query('SELECT * FROM admin'))
            if len(admins_id):
                self.forward_message(
                    message='Список администраторов:\n' + ', '.join(admins_id),
                    user_id=user.vk_id,
                )
            else:
                self.forward_message(
                    message='🤯 Проект был сделан компанией MOVTUT inc. 🤯',
                    user_id=user.vk_id,
                )
        else:
            self.forward_message(
                message=f'⛔️ У вас недостаточно прав! ⛔️',
                user_id=user.vk_id
            )

    def delete_admin(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/del_admin id_администратора', user)
            return

        _, admin_personal_id = (event.obj["message"]["text"].split())
        new_admin = self.create_user(admin_personal_id)
        if not new_admin:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        if self.db.user_role_check(user.vk_id, "admin") and self.db.user_role_check(new_admin.vk_id, "admin"):
            self.db.sql_execute_query(f'DELETE FROM admin WHERE admin_id = {new_admin.vk_id}')
            self.forward_message(
                message=f'✅ Администратор @id{new_admin.vk_id} ({new_admin.first_name} {new_admin.last_name}) был удален! ✅',
                user_id=user.vk_id
            )
            self.forward_message(
                message=f'⚠️ Вас исключили из списков администраторов! ⚠️',
                user_id=new_admin.vk_id
            )
        else:
            if self.db.user_role_check(user.vk_id, "admin"):
                self.forward_message(
                    message=f'⚠️ Администратора {new_admin.personal_id} не существует! ⚠️',
                    user_id=user.vk_id
                )
            else:
                self.forward_message(
                    message=f'⛔️ У вас недостаточно прав! ⛔️',
                    user_id=user.vk_id
                )

    def request_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/req_connection id_клиента', user)
            return

        if self.db.user_role_check(user.vk_id, 'author'):
            _, client_id = event.obj["message"]["text"].split()
            new_client = self.create_user(client_id)
            if not new_client:
                self.invalid_command(
                    text='Неверный id!',
                    user=user
                )
                return

            if self.db.is_connection_exist(new_client.vk_id):
                self.forward_message(
                    message='⚠️ У клиента уже есть активное/запрошенное соединение! ⚠️',
                    user_id=user.vk_id,
                )
                return

            if self.db.is_connection_exist(user.vk_id):
                self.forward_message(
                    message='⚠️ У вас уже есть активное/запрошенное соединение! ⚠️',
                    user_id=user.vk_id,
                )
                return

            if not self.db.user_role_check(new_client.vk_id, 'user'):
                self.invalid_command(
                    text='Неверный id клиента!',
                    user=user
                )
                return

            self.db.sql_execute_query(
                f'INSERT INTO connection(client_id, author_id, answered) VALUES({new_client.vk_id}, {user.vk_id}, 0)')

            connection_id = self.db.sql_read_query(
                f'SELECT connection_id FROM connection WHERE client_id={new_client.vk_id} AND author_id={user.vk_id}')[
                0][0]

            self.forward_message(
                message='✉️ Запрос на соединение с клиентом отправлен! ✉️',
                user_id=user.vk_id,
            )

            admins_id = self.db.sql_read_query('SELECT admin_id FROM admin')
            inline_keyboard = VkKeyboard(
                one_time=False,
                inline=True
            )
            inline_keyboard.add_button(
                label=f'/accept {connection_id}',
                color=VkKeyboardColor.POSITIVE,
            )
            inline_keyboard.add_button(
                label=f'/decline {connection_id}',
                color=VkKeyboardColor.NEGATIVE,
            )
            for admin_id in admins_id:
                self.forward_message(
                    message=f'❓ Запрос на соединение #{connection_id}:\n@id{user.vk_id} ({user.first_name} {user.last_name}) запрашивает соединение с'
                            f' @id{new_client.vk_id} ({new_client.first_name} {new_client.last_name})!',
                    user_id=admin_id,
                    keyboard=inline_keyboard.get_keyboard(),
                )
        else:
            self.forward_message(
                message='⚠️ Только автор может запросить соединение! ⚠️',
                user_id=user.vk_id,
            )

    def accept_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if not self.db.user_role_check(user.vk_id, "admin"):
            self.forward_message(message=f'⛔️ У вас недостаточно прав! ⛔️',
                                 user_id=user.vk_id)
            return

        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/accept id_соединения', user)
            return

        _, connection_id = event.obj["message"]["text"].split()
        raw_data = self.db.sql_read_query(
            f"SELECT client_id, author_id, answered FROM connection WHERE connection_id = {connection_id}")
        if raw_data:
            client_id, author_id, is_answered = raw_data[0]
            if is_answered:
                self.forward_message(
                    message=f"⚠️ Соединение #{connection_id} уже было одобрено! ⚠️",
                    user_id=user.vk_id
                )
            else:
                self.db.sql_execute_query(f"UPDATE connection SET answered=1 WHERE connection_id = {connection_id}")
                self.forward_message(
                    message=f"💬 Соединение с клиентом было установленно! 💬",
                    user_id=author_id,
                )
                self.forward_message(
                    message=f"💬 Соединение с автором было установленно! 💬",
                    user_id=client_id,
                )
                self.forward_message(
                    message=f"✅ Соединение было одобрено! ✅",
                    user_id=user.vk_id,
                )
        else:
            self.forward_message(
                message=f"⚠️ Соединение #{connection_id} неактуально! ⚠️",
                user_id=user.vk_id
            )

    def decline_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if not self.db.user_role_check(user.vk_id, "admin"):
            self.forward_message(message=f'⛔️ У вас недостаточно прав! ⛔️',
                                 user_id=user.vk_id)
            return

        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command('/decline id_соединения', user)
            return

        _, connection_id = event.obj["message"]["text"].split()
        raw_data = self.db.sql_read_query(
            f"SELECT client_id, author_id, answered FROM connection WHERE connection_id = {connection_id}")
        if raw_data:
            client_id, author_id, is_answered = raw_data[0]
            if is_answered:
                self.forward_message(
                    message=f"⚠️ Соединение #{connection_id} уже было одобрено! ⚠️",
                    user_id=user.vk_id
                )
            else:
                self.db.sql_execute_query(
                    f"DELETE FROM connection WHERE connection_id={connection_id} AND answered = 0")
                self.forward_message(
                    message=f"❌ Соединение было отклонено! ❌",
                    user_id=user.vk_id,
                )
                self.forward_message(
                    message=f"❌ Соединение с клиентом было отклонено! ❌",
                    user_id=author_id,
                )
        else:
            self.forward_message(
                message=f"⚠️ Соединение #{connection_id} неактуально! ⚠️",
                user_id=user.vk_id
            )

    def create_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 3:
            self.invalid_command('/add_connection id_клиента id_автора', user)
            return

        _, client_personal_id, author_personal_id = (event.obj["message"]["text"].split())
        new_client = self.create_user(client_personal_id)
        if not new_client:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        new_author = self.create_user(author_personal_id)
        if not new_author:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        if self.db.user_role_check(user.vk_id, "admin"):
            if not self.db.is_result_exists(
                    f'SELECT client_id, author_id FROM connection WHERE client_id = {new_client.vk_id} OR author_id = {new_author.vk_id}'):
                if not self.db.user_role_check(new_client.vk_id, 'user'):
                    self.invalid_command(
                        text='Неверный id клиента!',
                        user=user
                    )
                    return

                if not self.db.user_role_check(new_author.vk_id, 'author'):
                    self.invalid_command(
                        text='Неверный id автора!',
                        user=user
                    )
                    return
                self.db.sql_execute_query(
                    f'INSERT INTO connection(client_id, author_id, answered) VALUES({new_client.vk_id}, {new_author.vk_id}, 1)')

                self.forward_message(message=f'✅ Связь между клиентом: {new_client.personal_id} и '
                                             f'автором: {new_author.personal_id} установлена! ✅',
                                     user_id=user.vk_id)

                self.forward_message(message='✅ Связь с автором установлена! ✅',
                                     user_id=new_client.vk_id,
                                     attachments=event.obj["message"]["attachments"])

                self.forward_message(message='✅ Связь с клиентом установлена! ✅',
                                     user_id=new_author.vk_id,
                                     attachments=event.obj["message"]["attachments"])
            else:
                if self.db.is_connection_exist(new_client.vk_id):
                    self.forward_message(
                        message='⚠️ У клиента уже есть активное/запрошенное соединение! ⚠️',
                        user_id=user.vk_id,
                    )
                    return

                if self.db.is_connection_exist(user.vk_id):
                    self.forward_message(
                        message='⚠️ У автора уже есть активное/запрошенное соединение! ⚠️',
                        user_id=user.vk_id,
                    )
                    return
        else:
            self.forward_message(message=f'⛔️ У вас недостаточно прав! ⛔️',
                                 user_id=user.vk_id)

    def get_connections(self, user: User) -> None:
        if self.db.user_role_check(user.vk_id, "admin"):
            connections_id = self.get_pretty_connections(self.db.sql_read_query('SELECT * FROM connection'))
            if len(connections_id):
                self.forward_message(message='Список установленных соединений:\n' +
                                             ''.join(connections_id),
                                     user_id=user.vk_id)
            else:
                self.forward_message(message='⚠️ Нет активных/запрошенных соединений! ⚠️',
                                     user_id=user.vk_id)
        else:
            self.forward_message(message=f'⛔️ У вас недостаточно прав! ⛔️',
                                 user_id=user.vk_id)

    def delete_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, user: User) -> None:
        if len(event.obj["message"]["text"].split()) != 3:
            self.invalid_command('/del_connection id_клиента id_автора', user)
            return

        _, client_personal_id, author_personal_id = (event.obj["message"]["text"].split())

        new_client = self.create_user(client_personal_id)
        if not new_client:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        new_author = self.create_user(author_personal_id)
        if not new_author:
            self.invalid_command(
                text='Неверный id!',
                user=user
            )
            return

        if self.db.user_role_check(user.vk_id, "admin"):
            if self.db.is_result_exists(
                    f'SELECT client_id, author_id FROM connection WHERE client_id = {new_client.vk_id} AND author_id = {new_author.vk_id}'):
                self.db.sql_execute_query(
                    f'DELETE FROM connection WHERE client_id = {new_client.vk_id} AND author_id = {new_author.vk_id}')
                self.forward_message(message=f'🚫 Связь между клиентом: {new_client.personal_id} и '
                                             f'автором: {new_author.personal_id} прервана! 🚫',
                                     user_id=user.vk_id)
                self.forward_message(message=f'⚠️ Связь с автором прервана! ⚠️',
                                     user_id=new_client.vk_id)
                self.forward_message(message=f'⚠️ Связь с клиентом прервана! ⚠️',
                                     user_id=new_author.vk_id)
            else:
                self.forward_message(message=f'⚠️ Связи между клиентом: {new_client.personal_id} и '
                                             f'автором: {new_author.personal_id} не существует! ⚠️',
                                     user_id=user.vk_id)
        else:
            self.forward_message(message=f'⛔️ У вас недостаточно прав! ⛔️',
                                 user_id=user.vk_id)

    def disconnect(self, user: User) -> None:
        if self.db.is_connection_exist(user.vk_id):
            companion_id = self.db.get_companion(user.vk_id)
            is_answered = self.db.sql_read_query(
                f'SELECT answered FROM connection WHERE client_id = {user.vk_id} OR author_id = {user.vk_id}'
            )[0][0]
            self.db.sql_execute_query(f'DELETE FROM connection WHERE client_id = {user.vk_id} OR '
                                      f'author_id = {user.vk_id}')
            self.forward_message('🚫 Вы отключились от чата! 🚫',
                                 user_id=user.vk_id)
            if is_answered:
                self.forward_message('🚫 Собеседник отключился от чата! 🚫',
                                     user_id=companion_id)
        else:
            self.forward_message('❌ Вы не подключены к чату! ❌',
                                 user_id=user.vk_id)

    def forward_message(self, message: str, user_id: int, keyboard=VkKeyboard().get_empty_keyboard(),
                        attachments=None) -> None:
        if attachments is None:
            attachments = []

        print('message', message)

        attachment = []

        for attach in attachments:
            if attach["type"] != "photo":
                continue
            attachment.append(
                f'{attach["type"]}{attach[attach["type"]]["owner_id"]}_{attach[attach["type"]]["id"]}' +
                f'_{attach[attach["type"]]["access_key"]}'
            )

        if not attachment and not message:
            return

        if self.db.is_connection_exist(user_id):
            kb = VkKeyboard(one_time=False)
            kb.add_button(label="/disconnect", color=VkKeyboardColor.NEGATIVE)
            keyboard = kb.get_keyboard()

        self.vk_session.get_api().messages.send(
            user_id=user_id,
            random_id=get_random_id(),
            keyboard=keyboard,
            message=message,
            attachment=attachment
        )
