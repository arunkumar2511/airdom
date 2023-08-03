import jwt

class JWT():

    def __init__(self) -> None:
        self.secret = "airdom235_)()s123a^78%(pptesttoken"

    def decrypt(self,token:str):
        details = jwt.decode(token, self.secret, algorithms=["HS256"])
        return details

    def encrypt(self,payload:dict):
        token = jwt.encode(payload,self.secret, algorithm="HS256")
        return token
