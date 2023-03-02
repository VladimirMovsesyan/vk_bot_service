class User:
    personal_id: str
    vk_id: int
    first_name: str
    last_name: str

    def __init__(self, personal_id: str, vk_id: int, first_name: str, last_name: str):
        self.personal_id = personal_id
        self.vk_id = vk_id
        self.first_name = first_name
        self.last_name = last_name
