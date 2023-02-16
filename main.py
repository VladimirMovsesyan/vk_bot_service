# vk_api
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

# mysql
import mysql.connector
from mysql.connector import Error


def sql_create_db_connection(host_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            passwd=user_password,
            database=db_name
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


def sql_execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query successful")
    except Error as err:
        print(f"Error: '{err}'")


def sql_read_query(connection, query):
    cursor = connection.cursor()
    result = None
    try:
        cursor.execute(query)
        result = cursor.fetchall()
    except Error as err:
        print(f"Error: '{err}'")

    return result


def user_role_check(connection, user_id, role):
    return True if sql_read_query(connection, f"SELECT {role}_id FROM {role}s WHERE {role}_id = {user_id}") else False


def user_message_handler(event, vk_session):
    # getting user_id
    user_id = event.obj["message"]["from_id"]

    # getting users name
    response = vk_session.method(method="users.get", values={"user_ids": user_id})
    user_vk = (response[0]['first_name'], response[0]['last_name'])

    # working with database
    user_database_handler(event, vk_session, user_id, user_vk)

    # printing data to terminal
    print(f'Who: {user_vk[0]} {user_vk[1]} |id: {user_id}|')
    print(f'Text:', event.obj["message"]["text"])


def user_database_handler(event, vk_session, user_id, user_vk):
    # creating database connection
    db = sql_create_db_connection("localhost", "admin", "vk_service_bot")

    # adding new client to database
    if not user_role_check(db, user_id, "client"):
        sql_execute_query(db, f"INSERT INTO clients VALUES ({user_id}, '{user_vk[0]}', '{user_vk[1]}')")

    # TODO: Add errors handler
    # adding new author to database
    if (event.obj["message"]["text"].split())[0] == '/add_author':
        command, author_id = (event.obj["message"]["text"].split())

        # check if user is admin
        if user_role_check(db, user_id, "admin") and not user_role_check(db, author_id, "author"):
            # TODO: Very expensive operation :(
            author_response = vk_session.method(method="users.get", values={"user_ids": author_id})
            sql_execute_query(db, f"INSERT INTO authors VALUES ({author_id}, "
                                  f"'{author_response[0]['first_name']}', "
                                  f"'{author_response[0]['last_name']}')")

    # closing database connection
    db.close()


def main():
    vk_session = vk_api.VkApi(
        token='')
    long_poll = VkBotLongPoll(vk_session, '')

    for event in long_poll.listen():
        # message data
        # print(event.obj)

        if event.type == VkBotEventType.MESSAGE_NEW:
            user_message_handler(event, vk_session)
        else:
            print(event.type)


if __name__ == '__main__':
    main()
