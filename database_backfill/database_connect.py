from pymongo import MongoClient

CONNECTION_STRING = "mongodb+srv://recipe-gen-auth:nuvklQyHU5qPNi1D@recipe-gen.kbrot3f.mongodb.net/?retryWrites=true&w=majority"

def get_database():
    client = MongoClient(CONNECTION_STRING)
    return client.recipe_gen