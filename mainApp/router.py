from fastapi import UploadFile,APIRouter,HTTPException,Request,Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from azure.storage.blob import BlobClient,generate_blob_sas
import os
 
from .utils.jwtHandler import JWT 


accountName = os.getenv("accountName")
accountKey = os.getenv("accountKey")
containerName = os.getenv("containerName")
connectionString = f"DefaultEndpointsProtocol=https;AccountName={accountName};AccountKey={accountKey};EndpointSuffix=core.windows.net"   
router = APIRouter()
myclient = MongoClient("mongodb://admin:admin123@20.219.77.42:27017")
mydb = myclient["qapp"]
userTable = mydb["User"]
siteTable = mydb["Site"]
questionAnswersTable = mydb["OuestionAnswers"]
tokenAuthScheme = HTTPBearer()


class Login(BaseModel):
    username:str
    password:str

class User(BaseModel):
    name: str
    gender: str 
    dept: str
    designation: str
    email:str
    mobile:str
    password:str

class Site(BaseModel):
    name: str
    code: str 
    address: str
    latitude: str
    longitude:str
    province:str
    municipality:str

class SiteMapping(BaseModel):
    id: str
    userIds: list  

def authCheck(token:str):
    if not token:
        raise HTTPException(status_code=401, detail="Authorization is missing")

@router.post("/login",tags=["User"])
def login(user:Login):
    password = user.password
    username = user.username 
    userData = userTable.find_one({"isActive":True,"mobile":username,"password":password})
    if not userData:
        raise HTTPException(status_code=403,details="Incorrect username or password")
    token = JWT().encrypt({"id":userData.get("_id")})

    return {"success":True,"data":{"token":token,"user":userData}}

@router.post("/user",tags=["User"])
def addUser(user:User, token: str = Depends(tokenAuthScheme)):
    userData = verifyToken(token.credentials)
    checkExist = dict(userTable.find_one({"$or":[{"mobile":user.mobile},{"email":user.email}]}))
    if checkExist:
        raise HTTPException(status_code=422,detail="Email or Mobile already exist")
    dataToInsert = {
        "name":user.name,
        "gender":user.gender,
        "dept":user.dept,
        "designation":user.designation,
        "mobile":user.mobile,
        "email":user.email,
        "isActive":True,
        "createdAt":datetime.now(),
        "isAdmin":False,
        "password":user.password,
        "sites":[],
        "createdBy":userData.get("_id")
    }
    #user["isActive"] = True 
    userTable.insert_one(dataToInsert)
    return {"success":True,"data":"User Creation Success"}


@router.get("/user",tags=["User"])
def getUser(page:int = 1, limit:int = 10, token: str = Depends(tokenAuthScheme)): 
    verifyToken(token.credentials)
    skip = (page - 1)*limit
    print(skip)
    data = list(userTable.find({"isActive":True,"isAdmin":False}).limit(limit).skip(skip)) 
    for el in data:
        el["_id"] = str(el["_id"])
        if el.get("sites") and len(el.get("sites")) > 0:
            el["sites"] = siteTable.find({"_id":{"$in":el["sites"]}})
    return {"success":True,"data":data}

@router.put("/user/{id}",tags=["User"])
def editUser(id:str,user:User, token: str = Depends(tokenAuthScheme)):
    userData = verifyToken(token.credentials)
    checkExist = dict(userTable.find_one({"_id":{"$ne":ObjectId(id)},"$or":[{"mobile":user.mobile},{"email":user.email}]}))
    if checkExist:
        raise HTTPException(status_code=422,detail="Email or Mobile already exist")
    dataToInsert = {
        "name":user.name,
        "gender":user.gender,
        "dept":user.dept,
        "designation":user.designation,
        "mobile":user.mobile,
        "email":user.email,
        "isActive":True,
        "updatedAt":datetime.now(),
        "updatedBy":userData.get("_id"),
        "isAdmin":False,
        "password":user.password
    }
    #user["isActive"] = True 
    userTable.update_one({"_id":ObjectId(id)},dataToInsert)
    return {"success":True,"data":"User Update Success"}

@router.post("/site",tags=["Site"])
def addSite(site:Site, token: str = Depends(tokenAuthScheme)):
    userData = verifyToken(token.credentials)
    dataToInsert = {
        "name":site.name,
        "code":site.code,
        "address":site.address,
        "latitude":site.latitude,
        "longitude":site.longitude,
        "province":site.province,
        "municipality":site.municipality,
        "isActive":True,
        "createdAt":datetime.now(),
        "createdBy":userData.get("_id")
    }
    #user["isActive"] = True 
    siteTable.insert_one(dataToInsert)
    return {"success":True,"data":"Site Creation Success"}

@router.put("/site/{id}",tags=["Site"])
def editSite(id:str,site:Site, token: str = Depends(tokenAuthScheme)):
    userData = verifyToken(token.credentials)
    dataToInsert = {
        "name":site.name,
        "code":site.code,
        "address":site.address,
        "latitude":site.latitude,
        "longitude":site.longitude,
        "province":site.province,
        "municipality":site.municipality, 
        "updatedAt":datetime.now(),
        "updatedBy":userData.get("_id")
    }
    #user["isActive"] = True 
    siteTable.update_one({"_id":ObjectId(id)},dataToInsert)
    return {"success":True,"data":"Site Update Success"}

@router.get("/site",tags=["Site"])
def getSite(page:int = 1, limit:int = 10, token: str = Depends(tokenAuthScheme)):
    verifyToken(token.credentials)
    skip = (page - 1)*limit
    print(skip)
    data = list(siteTable.find({"isActive":True}).limit(limit).skip(skip)) 
    for el in data:
        el["_id"] = str(el["_id"])
    return {"success":True,"data":data}

@router.get("/site/user-mapped/{id}",tags=["Site"])
def getSite(id:str, token: str = Depends(tokenAuthScheme)):
    verifyToken(token.credentials)  
    data = userTable.find({"isAdmin":False},{"_id":1,"name":1})
    followData = userTable.find({"isAdmin":False,"sites":id},{"_id":1})
    followIds = [el["_id"] for el in followData]
    for el in data:
        data["isMapped"] = el["_id"] in followIds
    return {"success":True,"data":data}

@router.post("/site/user-mapping",tags=["Site"])
def userSiteMapping(site:SiteMapping, token: str = Depends(tokenAuthScheme)):
    userData = verifyToken(token.credentials)
    dataToUpdate = {
        "$addToSet":{"sites":site.id},
        "updatedAt": datetime.now(),
        "updatedBy": userData.get("_id")
    } 
    userTable.update_many({"_id":{"$in":site.userIds}},dataToUpdate)
    return {"success":True,"data":"Site Mapping Success"}

@router.post("/qn-ans",tags=["QA"])
def addQans(body:dict, token: str = Depends(tokenAuthScheme)): 
    userData = verifyToken(token.credentials)
    body["createdBy"] = userData.get("_id")
    body["isActive"]= True
    body["createdAt"]= datetime.now()
    siteTable.insert_one(body)
    return {"success":True,"data":"Answer Creation Success"}

@router.get("/qn-ans",tags=["QA"])
def getQuestionAnswer(page:int = 1, limit:int = 10, token: str = Depends(tokenAuthScheme)):
    verifyToken(token.credentials)
    skip = (page - 1)*limit
    print(skip)
    data = list(questionAnswersTable.find({"isActive":True}).limit(limit).skip(skip)) 
    for el in data:
        el["_id"] = str(el["_id"])
    return {"success":True,"data":data}

@router.get("/qn-ans/{id}",tags=["QA"])
def getgetQuestionAnswerById(id, token: str = Depends(tokenAuthScheme)):  
    verifyToken(token.credentials)
    data = dict(questionAnswersTable.find_one({"_id":ObjectId(id),"isActive":True}))  
    return {"success":True,"data":data}

@router.post("/blob/upload",tags=["QA"])
def uploadOnBlob(file:UploadFile, token: str = Depends(tokenAuthScheme)):  
    verifyToken(token.credentials)
    blobName = f"{datetime.now().timestamp()}-{file.filename}"
    blob = BlobClient.from_connection_string(conn_str=connectionString, container_name=containerName, blob_name=blobName) 
    blob.upload_blob(file.file) 
    sas_token = generate_blob_sas(blob_name=blobName,account_name=accountName, container_name=containerName,account_key=accountKey)
    sas_url = f"{blob.url}?{sas_token}" 
    return {"success":True,"data":{"fileUrl":sas_url}}

def verifyToken(token:str):
    unAuthError = HTTPException(status_code="401",detail="Invalid token or expired!!!")
    userId = JWT().decrypt(token.credentials)
    if not userId or not userId.get("id"):
        raise unAuthError
    userData = dict(userTable.find_one({"_id":ObjectId(userId.get("id"))}))
    if not userData:
        raise unAuthError
    return userData