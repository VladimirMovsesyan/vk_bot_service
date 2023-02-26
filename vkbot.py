# vk_api
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

# mysql
from sql import DataBase


class VkBot:
    vk_session: vk_api.vk_api.VkApiGroup
    long_poll: VkBotLongPoll

    def __init__(self, token: str, club_id: str):
        self.vk_session = vk_api.vk_api.VkApiGroup(token=token)
        self.long_poll = VkBotLongPoll(self.vk_session, club_id)

    def process(self) -> None:
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.user_message_handler(event)
            else:
                print(event.type)

    def get_name_from_id(self, user_id):
        response = self.vk_session.method(method="users.get", values={"user_ids": user_id})
        return response[0]['first_name'], response[0]['last_name']

    def user_message_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        # getting user_id
        user_id = event.obj["message"]["from_id"]

        # getting users name TODO: Delete response
        response = self.vk_session.method(method="users.get", values={"user_ids": user_id})
        user_vk = (response[0]['first_name'], response[0]['last_name'])

        # working with database
        self.user_database_handler(event)

        # printing data to terminal
        print(f'Who: {user_vk[0]} {user_vk[1]} |id: {user_id}|')
        print(f'Text:', event.obj["message"]["text"])

    def user_database_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        # creating database connection
        db = DataBase("localhost", "admin", "vk_bot")

        # adding new client to database
        if not db.user_role_check(event.obj["message"]["from_id"], "user"):
            db.sql_execute_query(f'INSERT INTO user VALUES ({event.obj["message"]["from_id"]})')

        if event.obj["message"]["text"]:
            self.user_command_handler(event, db)

        # TODO: add support of forwarding another data from message (such as gifs, docs, music, etc.)
        # forwarding message to other member of dialog if it exists
        if db.is_connected(event.obj["message"]["from_id"]):
            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button('/disconnect', VkKeyboardColor.NEGATIVE)
            self.forward_message(message=event.obj["message"]["text"],
                                 user_id=db.get_companion(event.obj["message"]["from_id"]),
                                 keyboard=keyboard.get_keyboard(),
                                 attachments=event.obj["message"]["attachments"])

        # closing database connection
        db.close()

    def user_command_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        # TODO: Add errors handler
        # TODO: DELETE DEBUG INFO
        # TODO: Warning: unexpected arguments appears when count of functions more than 10 ????
        command = (event.obj["message"]["text"].split())[0]
        commands_dict = {
            '/add_author': self.add_author,
            '/authors': self.get_authors,
            '/del_author': self.delete_author,
            '/add_admin': self.add_admin,
            '/admins': self.get_admins,
            '/del_admin': self.delete_admin,
            '/req_connection': self.request_connection,
            '/accept': self.accept_connection,
            '/decline': self.decline_connection,
            '/add_connection': self.create_connection,
            '/connections': self.get_connections,
            '/del_connection': self.delete_connection,
            '/disconnect': self.disconnect,
        }
        if command in commands_dict:
            commands_dict[command](event, db)

    def invalid_command(self, event: vk_api.bot_longpoll.VkBotMessageEvent, valid_command: str):
        self.send_message(message=f'Неверно использована команда, верное использование:\n' + valid_command,
                          user_id=event.obj["message"]["from_id"])

    # commands
    def add_author(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/add_author id_автора')
            return

        _, author_personal_id = (event.obj["message"]["text"].split())
        author_id = self.vk_session.method(method="users.get", values={"user_ids": author_personal_id})[0]["id"]

        if db.user_role_check(event.obj["message"]["from_id"], "admin") and \
                not db.user_role_check(author_id, "author"):
            db.sql_execute_query(f'INSERT INTO author VALUES ({author_id})')
            self.send_message(message=f'Автор с {author_personal_id} был добавлен!',
                              user_id=event.obj["message"]["from_id"])
        else:
            if db.user_role_check(event.obj["message"]["from_id"], "admin"):
                self.send_message(message=f'Автор с {author_personal_id} уже существовал!',
                                  user_id=event.obj["message"]["from_id"])
            else:
                self.send_message(message=f'У вас недостаточно прав для этой команды!',
                                  user_id=event.obj["message"]["from_id"])

    def get_authors(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if db.user_role_check(event.obj["message"]["from_id"], "admin"):
            self.send_message(message='Список авторов:\n' + str(db.sql_read_query('SELECT * FROM author')),
                              user_id=event.obj["message"]["from_id"])
        else:
            self.send_message(message='У вас недостаточно прав для этой команды!',
                              user_id=event.obj["message"]["from_id"])

    def delete_author(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/del_author id_автора')
            return

        _, author_personal_id = (event.obj["message"]["text"].split())
        author_id = self.vk_session.method(method="users.get", values={"user_ids": author_personal_id})[0]["id"]

        if db.user_role_check(event.obj["message"]["from_id"], "admin") and db.user_role_check(author_id, "author"):
            db.sql_execute_query(f'DELETE FROM author WHERE author_id = {author_id}')
            self.send_message(message=f'Автор {author_personal_id} был удален!',
                              user_id=event.obj["message"]["from_id"])
        else:
            if db.user_role_check(event.obj["message"]["from_id"], "admin"):
                self.send_message(message=f'Автора {author_personal_id} не существует!',
                                  user_id=event.obj["message"]["from_id"])
            else:
                self.send_message(message=f'У вас недостаточно прав!',
                                  user_id=event.obj["message"]["from_id"])

    def add_admin(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/add_admin id_администратора')
            return

        _, admin_personal_id = (event.obj["message"]["text"].split())
        admin_id = self.vk_session.method(method="users.get", values={"user_ids": admin_personal_id})[0]["id"]

        if db.user_role_check(event.obj["message"]["from_id"], "admin") and \
                not db.user_role_check(admin_id, "admin"):
            db.sql_execute_query(f'INSERT INTO admin VALUES ({admin_id})')
            self.send_message(message=f'Администратор {admin_personal_id} был добавлен!',
                              user_id=event.obj["message"]["from_id"])
        else:
            if db.user_role_check(event.obj["message"]["from_id"], "admin"):
                self.send_message(message=f'Администратор {admin_personal_id} уже существует!',
                                  user_id=event.obj["message"]["from_id"])
            else:
                self.send_message(message=f'У вас недостаточно прав!',
                                  user_id=event.obj["message"]["from_id"])

    def get_admins(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if db.user_role_check(event.obj["message"]["from_id"], "admin"):
            self.send_message(message='Список администраторов:\n' + str(db.sql_read_query('SELECT * FROM admin')),
                              user_id=event.obj["message"]["from_id"])
        else:
            self.send_message(message=f'У вас недостаточно прав!', user_id=event.obj["message"]["from_id"])

    def delete_admin(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/del_admin id_администратора')
            return

        _, admin_personal_id = (event.obj["message"]["text"].split())
        admin_id = self.vk_session.method(method="users.get", values={"user_ids": admin_personal_id})[0]["id"]

        if db.user_role_check(event.obj["message"]["from_id"], "admin") and db.user_role_check(admin_id, "admin"):
            db.sql_execute_query(f'DELETE FROM admin WHERE admin_id = {admin_id}')
            self.send_message(message=f'Администратор {admin_personal_id} был удален!',
                              user_id=event.obj["message"]["from_id"])
        else:
            if db.user_role_check(event.obj["message"]["from_id"], "admin"):
                self.send_message(message=f'Администратора {admin_personal_id} не существует!',
                                  user_id=event.obj["message"]["from_id"])
            else:
                self.send_message(message=f'У вас недостаточно прав!',
                                  user_id=event.obj["message"]["from_id"])

    def request_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/req_connection id_клиента')
            return

        if db.user_role_check(event.obj["message"]["from_id"], 'author'):
            _, client_id = event.obj["message"]["text"].split()
            client_first_name, client_last_name = self.get_name_from_id(client_id)
            author_id = event.obj["message"]["from_id"]
            author_first_name, author_last_name = self.get_name_from_id(author_id)

            keyboard = VkKeyboard(one_time=True)
            keyboard.add_button(
                label='/disconnect',
                color=VkKeyboardColor.NEGATIVE
            )
            if db.is_connection_exist(client_id):
                self.forward_message(
                    message='У клиента уже есть активное/запрошенное соединение!',
                    user_id=author_id,
                    keyboard=keyboard.get_empty_keyboard(),
                    attachments=[]
                )
                return

            if db.is_connection_exist(author_id):
                self.forward_message(
                    message='У вас уже есть активное/запрошенное соединение!',
                    user_id=author_id,
                    keyboard=keyboard.get_keyboard(),
                    attachments=[]
                )
                return

            db.sql_execute_query(
                f'INSERT INTO connection(client_id, author_id, answered) VALUES({client_id}, {author_id}, 0)')
            connection_id = db.sql_read_query(
                f'SELECT connection_id FROM connection WHERE client_id={client_id} AND author_id={author_id}')[0][0]

            self.forward_message(
                message='Запрос на соединение с клиентом отправлен!',
                user_id=author_id,
                keyboard=keyboard.get_keyboard(),
                attachments=[]
            )

            admins_id = db.sql_read_query('SELECT admin_id FROM admin')
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
                    message=f'{author_last_name} {author_first_name} (id{author_id}) запрашивает соединение с \
                    {client_last_name} {client_first_name} (id{client_id}) #{connection_id}',
                    user_id=admin_id,
                    keyboard=inline_keyboard.get_keyboard(),
                    attachments=[]
                )
        else:
            self.send_message(
                message='Только автор может запросить соединение!',
                user_id=event.obj["message"]["from_id"],
            )

    def accept_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/accept id_соединения')
            return

        _, connection_id = event.obj["message"]["text"].split()
        raw_data = db.sql_read_query(
            f"SELECT client_id, author_id, answered FROM connection WHERE connection_id = {connection_id}")
        admin_id = event.obj["message"]["from_id"]
        if raw_data:
            client_id, author_id, is_answered = raw_data[0]
            if is_answered:
                self.send_message(
                    message=f"Соединение #{connection_id} уже было одобрено!",
                    user_id=admin_id
                )
            else:
                db.sql_execute_query(f"UPDATE connection SET answered=1 WHERE connection_id = {connection_id}")
                keyboard = VkKeyboard(one_time=True)
                keyboard.add_button(
                    label='/disconnect',
                    color=VkKeyboardColor.NEGATIVE
                )
                self.forward_message(
                    message=f"Соединение с клиентом было установленно!",
                    user_id=author_id,
                    keyboard=keyboard.get_keyboard(),
                    attachments=[]
                )
                self.forward_message(
                    message=f"Соединение с автором было установленно!",
                    user_id=client_id,
                    keyboard=keyboard.get_keyboard(),
                    attachments=[]
                )
        else:
            self.send_message(
                message=f"Соединение #{connection_id} неактуально!",
                user_id=admin_id
            )

    def decline_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 2:
            self.invalid_command(event, '/decline id_соединения')
            return

        _, connection_id = event.obj["message"]["text"].split()
        raw_data = db.sql_read_query(
            f"SELECT client_id, author_id, answered FROM connection WHERE connection_id = {connection_id}")
        admin_id = event.obj["message"]["from_id"]
        if raw_data:
            client_id, author_id, is_answered = raw_data[0]
            if is_answered:
                self.send_message(
                    message=f"Соединение #{connection_id} уже было одобрено!",
                    user_id=admin_id
                )
            else:
                db.sql_execute_query(f"DELETE FROM connection WHERE connection_id={connection_id} AND answered = 0")
                self.send_message(
                    message=f"Соединение с клиентом было отклонено!",
                    user_id=author_id,
                )
        else:
            self.send_message(
                message=f"Соединение #{connection_id} неактуально!",
                user_id=admin_id
            )

    def create_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 3:
            self.invalid_command(event, '/add_connection id_клиента id_автора')
            return

        _, client_personal_id, author_personal_id = (event.obj["message"]["text"].split())
        client_id = self.vk_session.method(method="users.get", values={"user_ids": client_personal_id})[0]["id"]
        author_id = self.vk_session.method(method="users.get", values={"user_ids": author_personal_id})[0]["id"]

        if db.user_role_check(event.obj["message"]["from_id"], "admin"):
            if not db.is_result_exists(f'SELECT client_id, author_id FROM connection WHERE client_id = {client_id} AND author_id = {author_id}'):
                keyboard = VkKeyboard(one_time=True)
                keyboard.add_button('/disconnect', VkKeyboardColor.NEGATIVE)

                db.sql_execute_query(
                    f'INSERT INTO connection(client_id, author_id, answered) VALUES({client_id}, {author_id}, 1)')

                self.send_message(message=f'Связь между клиентом: {client_personal_id} и '
                                          f'автором: {author_personal_id} установлена!',
                                  user_id=event.obj["message"]["from_id"])

                self.forward_message(message='Связь с автором установлена!',
                                     user_id=client_id,
                                     keyboard=keyboard.get_keyboard(),
                                     attachments=event.obj["message"]["attachments"])

                self.forward_message(message='Связь с клиентом установлена!',
                                     user_id=author_id,
                                     keyboard=keyboard.get_keyboard(),
                                     attachments=event.obj["message"]["attachments"])
            else:
                self.send_message(message=f'Связь между клиентом: {client_personal_id} и '
                                          f'автором: {author_personal_id} уже существует!',
                                  user_id=event.obj["message"]["from_id"])
        else:
            self.send_message(message=f'У вас недостаточно прав!',
                              user_id=event.obj["message"]["from_id"])

    def get_connections(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if db.user_role_check(event.obj["message"]["from_id"], "admin"):
            self.send_message(message='Список установленных соединений:\n' +
                                      str(db.sql_read_query('SELECT * FROM connection')),
                              user_id=event.obj["message"]["from_id"])
        else:
            self.send_message(message=f'У вас недостаточно прав!',
                              user_id=event.obj["message"]["from_id"])

    def delete_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if len(event.obj["message"]["text"].split()) != 3:
            self.invalid_command(event, '/add_connection id_клиента id_автора')
            return

        _, client_personal_id, author_personal_id = (event.obj["message"]["text"].split())
        client_id = self.vk_session.method(method="users.get", values={"user_ids": client_personal_id})[0]["id"]
        author_id = self.vk_session.method(method="users.get", values={"user_ids": author_personal_id})[0]["id"]

        if db.user_role_check(event.obj["message"]["from_id"], "admin"):
            if db.is_result_exists(f'SELECT client_id, author_id FROM connection WHERE client_id = {client_id} AND author_id = {author_id}'):
                db.sql_execute_query(f'DELETE FROM connection WHERE client_id = {client_id} AND author_id = {author_id}')
                self.send_message(message=f'Связь между клиентом: {client_personal_id} и '
                                          f'автором: {author_personal_id} прервана!',
                                  user_id=event.obj["message"]["from_id"])
            else:
                self.send_message(message=f'Связи между клиентом: {client_personal_id} и '
                                          f'автором: {author_personal_id} не существует!',
                                  user_id=event.obj["message"]["from_id"])
        else:
            self.send_message(message=f'У вас недостаточно прав!',
                              user_id=event.obj["message"]["from_id"])

    def disconnect(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        if db.is_connection_exist(event.obj["message"]["from_id"]):
            db.sql_execute_query(f'DELETE FROM connection WHERE client_id = {event.obj["message"]["from_id"]} OR '
                                 f'author_id = {event.obj["message"]["from_id"]}')
            self.send_message('Вы отключились от чата!',
                              user_id=event.obj["message"]["from_id"])
        else:
            self.send_message('Вы не подключены к чату!',
                              user_id=event.obj["message"]["from_id"])

    def send_message(self, message: str, user_id: int) -> None:
        self.vk_session.get_api().messages.send(
            user_id=user_id,
            random_id=get_random_id(),
            message=message
        )

    def forward_message(self, message: str, user_id: int, keyboard: str, attachments: list) -> None:
        attachment = [
            f'{attach["type"]}{attach[attach["type"]]["owner_id"]}_{attach[attach["type"]]["id"]}' +
            f'_{attach[attach["type"]]["access_key"]}'
            for attach in attachments
        ]
        self.vk_session.get_api().messages.send(
            user_id=user_id,
            random_id=get_random_id(),
            keyboard=keyboard,
            message=message,
            attachment=attachment
        )
