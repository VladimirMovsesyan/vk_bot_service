# vk_api
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

# mysql
import mysql.connector
from mysql.connector import Error


def create_db_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            # user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query successful")
    except Error as err:
        print(f"Error: '{err}'")


def read_query(connection, query):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        return result
    except Error as err:
        print(f"Error: '{err}'")


def main():
    vk_session = vk_api.VkApi(
        token='')
    long_poll = VkBotLongPoll(vk_session, '')

    for event in long_poll.listen():
        # message data
        # print(event.obj)

        if event.type == VkBotEventType.MESSAGE_NEW:
            # getting user_id
            user_id = event.obj["message"]["from_id"]

            # getting users name
            response = vk_session.method(method="users.get", values={"user_ids": user_id})
            user_vk = (response[0]['first_name'], response[0]['last_name'])

            # creating database connection
            db = create_db_connection("localhost", "", "admin", "vk_service_bot")

            # adding new client to database
            clients_id = [client[0] for client in read_query(db, "SELECT client_id FROM clients")]
            if user_id not in clients_id:
                execute_query(db, f"INSERT INTO clients VALUES ({user_id}, '{user_vk[0]}', '{user_vk[1]}')")

            # TODO: Add errors handler
            # adding new author to database
            if (event.obj["message"]["text"].split())[0] == '/add_author':
                command, author_id = (event.obj["message"]["text"].split())

                # getting all id's of admins
                admins_id = [admin[0] for admin in read_query(db, "SELECT admin_id FROM admins")]

                # check if user is admin
                if user_id in admins_id:
                    # TODO: Very expensive operation :(
                    author_response = vk_session.method(method="users.get", values={"user_ids": author_id})
                    execute_query(db, f"INSERT INTO authors VALUES ({author_id}, "
                                      f"'{author_response[0]['first_name']}', "
                                      f"'{author_response[0]['last_name']}')")

            # closing database connection
            db.close()

            # printing data to terminal
            print(f'Who: {user_vk[0]} {user_vk[1]} |id: {user_id}|')
            print(f'Text:', event.obj["message"]["text"])
        else:
            print(event.type)


if __name__ == '__main__':
    main()
