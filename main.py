import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

def main():
    vk_session = vk_api.VkApi(token='')
    longpoll = VkBotLongPoll(vk_session, '')

    for event in longpoll.listen():
        print(event.obj)
        if event.type == VkBotEventType.MESSAGE_NEW:
            print('Новое сообщение:')
            #
            user_id = event.obj["message"]["from_id"]
            response = vk_session.method(method="users.get", values={"user_ids": user_id})
            user_vk = (response[0]['first_name'], response[0]['last_name'])
            #
            print(f'Для меня от: {user_vk[0]} {user_vk[1]}')

            print(f'Текст:', event.obj["message"]["text"])
            print()
        else:
            print(event.type)
            print()



if __name__ == '__main__':
    main()


