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
