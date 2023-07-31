class authorize():

    def __init__(self,token:str) -> None:
        self.token = token

    def decrypt(self):
        print("token",self.token)
        pass