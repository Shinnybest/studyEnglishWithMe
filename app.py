import jwt
import datetime
import hashlib
from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from bson.objectid import ObjectId
import json

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

client = MongoClient('mongodb://test:test@localhost', 27017)
db = client.doyouknow

# 메인페이지 보이기
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({'id': payload['id']})
        posts = list(db.posts.find({}))
        for post in posts:
            post["_id"] = str(post["_id"])
        return render_template('main.html', username = user_info['id'], posts=posts)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# 전체 영단어 보여주기
# @app.route('/', methods=['GET'])
# def ewords():
#     mWords =list(db.posts.find({}, {'_id':False}))
#
#     return jsonify({'all_words': mWords})

# 로그인페이지
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

# 로그인 JWT
@app.route('/sign_in', methods=['POST'])
def sign_in():
    username_receive = request.form['id']
    password_receive = request.form['pw']
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.user.find_one({'id': username_receive, 'pw': pw_hash})
    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# 회원가입
@app.route('/register/save', methods=['POST'])
def sign_up():
    username_receive = request.form['id']
    password_receive = request.form['pw']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    name_receive = request.form['name']
    doc = {
        "id": username_receive,
        "pw": password_hash,
        "name": name_receive
    }
    db.user.insert_one(doc)
    return jsonify({'result': 'success'})

# 회원가입 중복확인
@app.route('/register/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['id_give']
    exists = bool(db.user.find_one({"id": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})

# 업로드 페이지
@app.route('/upload')
def upload_page():
    return render_template('uploads.html')

# 업로드 DB에 넣기
@app.route('/upload', methods=['POST'])
def upload_words():
    url = request.form['url']
    english = request.form['english']
    korean = request.form['korean']

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')

    image = soup.select_one('meta[property="og:image"]')['content']

    english = english.replace('\"', '')
    korean = korean.replace('\"', '')
    english = english.replace('[', '')
    korean = korean.replace('[', '')
    english = english.replace(']', '')
    korean = korean.replace(']', '')

    doc = {
        'url': url,
        'english': english,
        'korean': korean,
        'image' : image
    }

    db.posts.insert_one(doc)
    return redirect(url_for('home'))
    # return jsonify({'msg': '새 글이 업로드 되었습니다.'})

# like db collection에 넣기
@app.route('/api/gotomywords', methods=['POST'])
def go_tomywords():
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    post_id_receive = request.form['post_id_give']
    doc = {
        "post_id": post_id_receive,
        "username": payload["id"]
    }
    db.likes.insert_one(doc)
    return jsonify({"msg": "내 단어장에 등록되었습니다."})

# 내 단어장 페이지 띄우기
@app.route('/my-words/<username>')
def mywords_page(username):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('my-words.html', username=username)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# 내단어장 단어 보여주기
# @app.route('/my-words', methods=['GET'])
# def get_mywords():
#     token_receive = request.cookies.get('mytoken')
#     try:
#         payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#         eachlikes = list(db.likes.find({"username": payload["id"]}, {"_id": False}))
#         array = []
#         for element in eachlikes:
#             array.append(element['post_id'])
#         posts = list(db.posts.find({}))
#         for post in posts:
#             post['_id'] = str(post['_id'])
#         likepostsID = []
#         for post in posts:
#             for element in array:
#                 if str(post['_id']) == element:
#                     likepostsID.append(post)
#         print(likepostsID)
#         return jsonify({"msg": "내 단어장 목록입니다.", "likeposts": likepostsID})
#     except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
#         return redirect(url_for("home"))

# 내 단어장 보여주기 version 2
@app.route('/my-words', methods=['GET'])
def get_mywords():
    token_receive = request.cookies.get('mytoken')
    posts = list()
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload["id"]}, {'_id': False})
        likes = list(db.likes.find({"username": user_info["id"]}, {'_id': False}).sort("date", -1))
        for i in range(len(likes)):
            posts.append(db.posts.find_one({'_id': ObjectId(likes[i]['post_id'])}, {'_id': False}))

        return jsonify({"result": "success", "all_likes": likes, "all_posts": posts})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# 내 단어장 단어 삭제하기
@app.route('/my-words/delete', methods=['POST'])
def delete_mywords():
    post_id_receive = request.form["post_id_give"]
    db.likes.delete_one({"post_id": post_id_receive})
    return jsonify({"msg": "내 단어장에서 삭제되었습니다."})

# @app.route('/api/post-mine', methods=['POST'])
# def saving():
#     token_receive = request.cookies.get('mytoken')
#     payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
#     post_id_receive = request.form['post_id_give']
#
#     doc = {
#         "post_id": post_id_receive,
#         "username": payload["id"]
#     }
#     db.likes.insert_one(doc)
#     return jsonify({'msg': '내 단어장에 저장되었습니다.'})

@app.route('/api/change', methods=['POST'])
def changing():
    url_receive = request.form['url_give']
    english_receive = request.form['english_give']
    korean_receive = request.form['korean_give']
    post_id_receive = request.form['post_id']

    english = english_receive.replace('\"', '')
    korean = korean_receive.replace('\"', '')
    english = english.replace('[', '')
    korean = korean.replace('[', '')
    english = english.replace(']', '')
    korean = korean.replace(']', '')

    doc = {
        'url': url_receive,
        'english': english,
        'korean': korean
    }
    db.posts.update_one({"_id": ObjectId(post_id_receive)},
                        {'$set': doc})
    return jsonify({'msg': '해당 글이 수정되었습니다.'})


@app.route('/api/delete', methods=['POST'])
def delete():
    post_id_receive = request.form['post_id_give']
    db.posts.delete_one({"_id": ObjectId(post_id_receive)})
    if (db.likes.find_one({"post_id": post_id_receive})) is not None:
        db.likes.delete_one({"post_id": post_id_receive})
    return jsonify({'msg': '해당 글이 영구 삭제 되었습니다.'})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
