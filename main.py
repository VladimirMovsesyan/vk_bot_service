# store secret keys
from dotenv import load_dotenv
import os

# vk_api
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id

# mysql
import mysql.connector
from mysql.connector import Error


class DataBase:
    db: mysql.connector.pooling.PooledMySQLConnection | \
        mysql.connector.connection.MySQLConnection | \
        mysql.connector.connection_cext.CMySQLConnection | \
        None

    def __init__(self, host_name: str, user_password: str, db_name: str):
        self.db = None
        try:
            self.db = mysql.connector.connect(
                host=host_name,
                passwd=user_password,
                database=db_name
            )
            print(type(self.db))
            print("MySQL Database connection successful")
        except Error as err:
            print(f"Error: '{err}'")

    def sql_execute_query(self, query: str):
        cursor = self.db.cursor()
        try:
            cursor.execute(query)
            self.db.commit()
            print("Query successful")
        except Error as err:
            print(f"Error: '{err}'")

    def sql_read_query(self, query: str):
        cursor = self.db.cursor()
        result = None
        try:
            cursor.execute(query)
            result = cursor.fetchall()
        except Error as err:
            print(f"Error: '{err}'")

        return result

    def user_role_check(self, user_id: int, role: str) -> bool:
        return True if self.sql_read_query(f'SELECT {role}_id FROM {role} WHERE {role}_id = {user_id}') else False

    def add_author(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        _, author_id = (event.obj["message"]["text"].split())

        # check if user is admin
        if self.user_role_check(event.obj["message"]["from_id"], "admin") and \
                not self.user_role_check(author_id, "author"):
            self.sql_execute_query(f"INSERT INTO author VALUES ({author_id})")

    def get_authors(self, vk_session: vk_api.vk_api.VkApi, user_id: int) -> None:
        # check if user is admin
        if self.user_role_check(user_id, "admin"):
            vk_session.get_api().messages.send(
                user_id=user_id,
                random_id=get_random_id(),
                message=str(self.sql_read_query("SELECT * FROM author"))
            )

    def delete_author(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        _, author_id = (event.obj["message"]["text"].split())

        # check if user is admin
        if self.user_role_check(event.obj["message"]["from_id"], "admin") and self.user_role_check(author_id, "author"):
            self.sql_execute_query(f"DELETE FROM author WHERE author_id = {author_id}")

    def add_admin(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        _, admin_id = (event.obj["message"]["text"].split())

        # check if user is admin
        if self.user_role_check(event.obj["message"]["from_id"], "admin") and \
                not self.user_role_check(admin_id, "admin"):
            self.sql_execute_query(f"INSERT INTO admin VALUES ({admin_id})")

    def get_admins(self, vk_session: vk_api.vk_api.VkApi, user_id: int) -> None:
        # check if user is admin
        if self.user_role_check(user_id, "admin"):
            vk_session.get_api().messages.send(
                user_id=user_id,
                random_id=get_random_id(),
                message=str(self.sql_read_query("SELECT * FROM admin"))
            )

    def delete_admin(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        _, admin_id = (event.obj["message"]["text"].split())

        # check if user is admin
        if self.user_role_check(event.obj["message"]["from_id"], "admin") and self.user_role_check(admin_id, "admin"):
            self.sql_execute_query(f"DELETE FROM admin WHERE admin_id = {admin_id}")

    def create_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        _, client_id, author_id = (event.obj["message"]["text"].split())

        # TODO: Add handler of unique connection
        # check if user is admin
        if self.user_role_check(event.obj["message"]["from_id"], "admin"):
            self.sql_execute_query(f"INSERT INTO connection(client_id, author_id) VALUES({client_id}, {author_id})")

    def get_connections(self, vk_session: vk_api.vk_api.VkApi, user_id: int) -> None:
        # check if user is admin
        if self.user_role_check(user_id, "admin"):
            vk_session.get_api().messages.send(
                user_id=user_id,
                random_id=get_random_id(),
                message=str(self.sql_read_query("SELECT * FROM connection"))
            )

    def delete_connection(self, event: vk_api.bot_longpoll.VkBotMessageEvent) -> None:
        _, client_id, author_id = (event.obj["message"]["text"].split())

        # check if user is admin
        if self.user_role_check(event.obj["message"]["from_id"], "admin"):
            self.sql_execute_query(f"DELETE FROM connection WHERE client_id = {client_id} AND author_id = {author_id}")

    def disconnect(self, user_id: int) -> None:
        self.sql_execute_query(f"DELETE FROM connection WHERE client_id = {user_id} OR author_id = {user_id}")

    def is_connected(self, user_id: int) -> bool:
        return True if self.sql_read_query(f"SELECT client_id, author_id FROM connection WHERE client_id = {user_id} "
                                           f"OR author_id = {user_id}") else False

    def get_companion(self, user_id: int) -> None | int:
        connection = list(
            self.sql_read_query(f"SELECT client_id, author_id FROM connection WHERE client_id = {user_id} "
                                f"OR author_id = {user_id}")[0])
        connection.remove(user_id)

        return None if not connection else connection[0]

    def close(self):
        self.db.close()


class VkBot:
    vk_session: vk_api.vk_api.VkApi
    long_poll: VkBotLongPoll

    def __init__(self, token: str, club_id: str):
        self.vk_session = vk_api.VkApi(token=token)
        self.long_poll = VkBotLongPoll(self.vk_session, club_id)

    def process(self) -> None:
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.user_message_handler(event)
            else:
                print(event.type)

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

        self.user_command_handler(event, db)

        if db.is_connected(event.obj["message"]["from_id"]):
            self.echo(event.obj["message"]["text"], db.get_companion(event.obj["message"]["from_id"]))

        # closing database connection
        db.close()

    def user_command_handler(self, event: vk_api.bot_longpoll.VkBotMessageEvent, db: DataBase) -> None:
        # TODO: Add errors handler
        # TODO: DELETE DEBUG INFO
        command = (event.obj["message"]["text"].split())[0]
        if command == '/add_author':
            db.add_author(event)
        elif command == '/authors':
            db.get_authors(self.vk_session, event.obj["message"]["from_id"])
        elif command == '/del_author':
            db.delete_author(event)
        elif command == '/add_admin':
            db.add_admin(event)
        elif command == '/admins':
            db.get_admins(self.vk_session, event.obj["message"]["from_id"])
        elif command == '/del_admin':
            db.delete_admin(event)
        elif command == '/add_connection':
            db.create_connection(event)
        elif command == '/connections':
            db.get_connections(self.vk_session, event.obj["message"]["from_id"])
        elif command == '/del_connection':
            db.delete_connection(event)
        elif command == '/disconnect':
            db.disconnect(event.obj["message"]["from_id"])

    # TODO: Rename
    def echo(self, message: str, user_id: int) -> None:
        self.vk_session.get_api().messages.send(
            user_id=user_id,
            random_id=get_random_id(),
            message=message
        )


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
