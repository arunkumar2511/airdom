from fastapi import FastAPI, UploadFile
from typing import Union
from pydantic import BaseModel
from pymongo import MongoClient
from datetime import datetime,timedelta
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from azure.storage.blob import BlobClient,generate_blob_sas,BlobProperties
import os

""" accountName = "aruntestblob"
accountKey = "1sGIu7VLKqhmRc2bjRPXuLcE1Zy21iZQK2Cf51DKPBCn2yf+151vzsMm7wS0Wdp9IGwZXKKP5+q1+ASt7wCKmQ==" """
accountName = os.getenv("accountName")
accountKey = os.getenv("accountKey")
containerName = os.getenv("containerName")
connectionString = f"DefaultEndpointsProtocol=https;AccountName={accountName};AccountKey={accountKey};EndpointSuffix=core.windows.net"   
app = FastAPI()
origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
myclient = MongoClient("mongodb+srv://arunkumardev2511:ag0x27igJALeaPr4@cluster0.mirxmsy.mongodb.net/?retryWrites=true&w=majority")
mydb = myclient["qapp"]
userTable = mydb["User"]
siteTable = mydb["Site"]
questionAnswersTable = mydb["OuestionAnswers"]
class User(BaseModel):
    name: str
    gender: str 
    dept: str
    designation: str
    siteId:str
    email:str
    mobile:str

class Site(BaseModel):
    name: str
    code: str 
    address: str
    latitude: str
    longitude:str

@app.post("/api/user")
def addUser(user:User):
    dataToInsert = {
        "name":user.name,
        "gender":user.gender,
        "dept":user.dept,
        "designation":user.designation,
        "siteId":user.siteId,
        "isActive":True,
        "createdAt":datetime.now(),
        "isAdmin":False
    }
    #user["isActive"] = True 
    userTable.insert_one(dataToInsert)
    return {"success":True,"data":"User Creation Success"}


@app.get("/api/user")
def getUser(page:int = 1, limit:int = 10):
    skip = (page - 1)*limit
    print(skip)
    data = list(userTable.find({"isActive":True,"isAdmin":False}).limit(limit).skip(skip)) 
    for el in data:
        el["_id"] = str(el["_id"])
    return {"success":True,"data":data}

@app.post("/api/site")
def addSite(site:Site):
    dataToInsert = {
        "name":site.name,
        "code":site.code,
        "address":site.address,
        "latitude":site.latitude,
        "longitude":site.longitude,
        "isActive":True,
        "createdAt":datetime.now()
    }
    #user["isActive"] = True 
    siteTable.insert_one(dataToInsert)
    return {"success":True,"data":"Site Creation Success"}

@app.get("/api/site")
def getSite(page:int = 1, limit:int = 10):
    skip = (page - 1)*limit
    print(skip)
    data = list(siteTable.find({"isActive":True}).limit(limit).skip(skip)) 
    for el in data:
        el["_id"] = str(el["_id"])
    return {"success":True,"data":data}

@app.post("/api/qn-ans")
def addQans(body:dict): 
    body["isActive"]= True
    body["createdAt"]= datetime.now()
    siteTable.insert_one(body)
    return {"success":True,"data":"Answer Creation Success"}

@app.get("/api/qn-ans")
def getQuestionAnswer(page:int = 1, limit:int = 10):
    skip = (page - 1)*limit
    print(skip)
    data = list(questionAnswersTable.find({"isActive":True}).limit(limit).skip(skip)) 
    for el in data:
        el["_id"] = str(el["_id"])
    return {"success":True,"data":data}

@app.get("/api/qn-ans/{id}")
def getgetQuestionAnswerById(id):  
    data = dict(questionAnswersTable.find_one({"_id":ObjectId(id),"isActive":True}))  
    return {"success":True,"data":data}

@app.post("/api/blob/upload")
def uploadOnBlob(file:UploadFile):  
    blobName = f"{datetime.now().timestamp()}-{file.filename}"
    blob = BlobClient.from_connection_string(conn_str=connectionString, container_name=containerName, blob_name=blobName) 
    blob.upload_blob(file.file) 
    sas_token = generate_blob_sas(blob_name=blobName,account_name=accountName, container_name=containerName,account_key=accountKey)
    sas_url = f"{blob.url}?{sas_token}" 
    return {"success":True,"data":{"fileUrl":sas_url}}