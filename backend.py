import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles 
from pymongo import MongoClient
from bson.objectid import ObjectId  
from fastapi import Query
from typing import List, Dict, Optional
# TODO: Import your database driver/modules here 
# (e.g. from pymongo import MongoClient, from bson.objectid import ObjectId)
MONGO_URI = "mongodb://localhost:27017/"
# --- Configuration ---
# TODO: Define your Database Connection String and Variables here (URI, DB Name)
DB_name='my_blog_db'
app = FastAPI()

# Enable CORS so the frontend can communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Setup ---
# TODO: Initialize your Client, connect to the Database, and select your Collection here
client = MongoClient(MONGO_URI)
db=client[DB_name]
posts_col=db['posts']


# --- Pydantic Models (Data Validation) ---
class Comment(BaseModel):
    author: str
    content: str

class Post(BaseModel):
    title: str
    content: str
    author: str

class PostResponse(Post):
    id: str
    date: str
    # NEW: The post now carries the author's count inside it
    author_post_count: Optional[int] = 0 
    comments: List[Comment] = []

class FeedResponse(BaseModel):
    posts: List[PostResponse]
    stats: Dict[str, int]

# --- Dummy Data Generator ---
def seed_dummy_data():
    """Checks if DB is empty and populates it with dummy data."""
    # TODO: 
    # 1. Check if the database collection is empty (count documents).
    # 2. If it is 0, define a list of dictionary dummy posts.
    # 3. Insert the list into the database.
    if posts_col.count_documents({})==0:
        dummy_posts = [
            {
                "title": "Getting Started with Python",
                "content": "Python is a versatile language used for web dev, AI, and more.",
                "author": "DevUser",
                "date": datetime.datetime.now().isoformat()
            },
            {
                "title": "Why NoSQL?",
                "content": "NoSQL databases like MongoDB provide flexibility for unstructured data.",
                "author": "DataGuru",
                "date": datetime.datetime.now().isoformat()
            },
            {
                "title": "FastAPI Speed",
                "content": "FastAPI is one of the fastest Python frameworks available.",
                "author": "Speedster",
                "date": datetime.datetime.now().isoformat()
            }
        ]
        posts_col.insert_many(dummy_posts)
        print("--- Dummy Database Created & Populated ---")
    else:
        print("--- Database already exists. Skipping seed. ---")
    print("Checking for dummy data...") 
    pass
def sync_counts():
    """Calculates real counts and saves them into every post document."""
    print("--- Syncing Post Counts... ---")
    authors = posts_col.distinct("author")
    for author in authors:
        count = posts_col.count_documents({"author": author})
        posts_col.update_many(
            {"author": author}, 
            {"$set": {"author_post_count": count}}
        )
# --- Event Handlers ---
@app.on_event("startup")
def startup_event():
    seed_dummy_data()
    sync_counts()

# --- API Endpoints ---
@app.get("/")
def read_root():
    return FileResponse("index.html")

@app.get("/feed", response_model=FeedResponse)
def get_feed(sort_option: str = Query("date_desc", enum=["date_desc", "date_asc", "title_asc", "title_desc"])):
    """
    OPTIMIZED READ: Fetches posts and reads the count directly from the document.
    No aggregation or calculation happens here.
    """
    # 1. Sort Logic
    cursor = None
    if sort_option == 'date_asc':
        cursor = posts_col.find().sort('date', 1)
    elif sort_option == 'date_desc':
        cursor = posts_col.find().sort('date', -1)
    elif sort_option == 'title_asc':
        cursor = posts_col.find().sort('title', 1)
    elif sort_option == 'title_desc':
        cursor = posts_col.find().sort('title', -1)
    
    posts_list = []
    stats_dict = {}

    for post in cursor:
        post['id'] = str(post['_id'])
        
        # 2. Denormalization Magic:
        # We just read the count that is already saved in the post.
        count = post.get('author_post_count', 0)
        
        # Add to stats dictionary for the frontend
        stats_dict[post['author']] = count
        
        posts_list.append(post)

    return {"posts": posts_list, "stats": stats_dict}

@app.post("/posts/{post_id}/comments")
def add_comment(post_id: str, comment: Comment):
    """Add a comment to a specific post using MongoDB $push"""
    
    # TODO:
    # 1. Convert the 'post_id' string to an ObjectId.
    # 2. Update the document with that ID.
    # 3. Use the $push operator to add 'comment.dict()' to the 'comments' array.
    posts_col.update_one({'_id': ObjectId(post_id)},{'$push':{'comments':comment.dict()}})
    
    return {"message": "Comment added successfully"}

@app.post("/posts")
def create_post(post: Post):
    """Create a new post."""
    new_post = post.dict()
    new_post["date"] = datetime.datetime.now().isoformat()
    
    # TODO:
    # 1. Insert 'new_post' into your collection.
    # 2. Capture the result to get the new ID.
    
    result=posts_col.insert_one(new_post)
    new_total = posts_col.count_documents({"author": post.author})
    posts_col.update_many({"author": post.author},{"$set": {"author_post_count": new_total}})
    

    
    # Replace "replace_with_real_id" with the string version of result.inserted_id
    return {"id": str(result.inserted_id), "message": "Post created successfully"}

if __name__ == "__main__":
    import uvicorn
    # Change host to 127.0.0.1 to avoid the 0.0.0.0 confusion
    uvicorn.run(app, host="127.0.0.1", port=8000)

    

