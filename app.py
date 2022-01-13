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

client = MongoClient('localhost', 27017)
db = client.doyouknow


# 로그인페이지
@app.route('/login')
def login():
    msg = request.args.get("msg")
    # msg를 login.html로 전달
    return render_template('login.html', msg=msg)

# 로그인 JWT
@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 유저의 id,pw의 값을 요구
    username_receive = request.form['id']
    password_receive = request.form['pw']
    # 해시함수를 통해서 어떤 암호값으로 저장되는지 알수 없게 만듬.
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    # user DB에서 아이디와 비번을 찾아서 result으로 설정
    result = db.user.find_one({'id': username_receive, 'pw': pw_hash})
    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({'result': 'success', 'token': token})
    # 그밖에 상황에는 아이디/비밀번호가 일치하지 않습니다 메세지
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# 회원가입
@app.route('/register/save', methods=['POST'])
def sign_up():
    # 아이디와 해시함수된 비번, 네임을 요구하고 그것을 doc으로 설정.
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



# 메인페이지 보이기
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        # 로그인된 jwt 토큰 디코드하여 payload 설정
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # 로그인 정보를 토대로 user_info 설정
        user_info = db.user.find_one({'id': payload['id']})
        # posts DB 리스트를 posts로 설정
        posts = list(db.posts.find({}))
        for post in posts:
            post["_id"] = str(post["_id"])
        # username과 함께 posts를 main.html로 전달
        return render_template('main.html', username = user_info['id'], posts=posts)
    # jwt토큰 유효시간이 만료되면 로그인 시간이 만료되었습니다 메세지
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    # jwt토큰을 가지고 오는것에 문제가 생기면 로그인 정보가 존재하지 않습니다 메세지
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))





# 업로드 페이지
@app.route('/upload')
def upload_page():
    return render_template('uploads.html')

# 업로드 DB에 넣기
@app.route('/upload', methods=['POST'])
def upload_words():
    # url, english, korean을 요구
    url = request.form['url']
    english = request.form['english']
    korean = request.form['korean']
    # bs4를 이용해서 크롤링 하기.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')
    #크롤링을 통해 선택한 og이미지를 이미지로 선택.
    image = soup.select_one('meta[property="og:image"]')['content']
    # db에 저장할때 필요 없는 값을 바꾸기
    english = english.replace('\"', '')
    korean = korean.replace('\"', '')
    english = english.replace('[', '')
    korean = korean.replace('[', '')
    english = english.replace(']', '')
    korean = korean.replace(']', '')
    # url, english, koran, image를 doc으로 묶기
    doc = {
        'url': url,
        'english': english,
        'korean': korean,
        'image' : image
    }
    # 변환된 doc값을 posts db에 저장
    db.posts.insert_one(doc)
    # 메인페이지인 home으로 정보를 전달
    return redirect(url_for('home'))

# 메인페이지 - 상세단어(모달)에서 나도 학습하기 버튼
@app.route('/api/gotomywords', methods=['POST'])
def go_tomywords():
    # mytoken을 요구.
    token_receive = request.cookies.get('mytoken')
    # 로그인된 jwt 토큰 디스코하여 payload 설정
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    # post_id_give를 토대로 post_id_receive 설정
    post_id_receive = request.form['post_id_give']
    # post_id, username을 doc으로 묶기
    doc = {
        "post_id": post_id_receive,
        "username": payload["id"]
    }
    # 변환된 doc값을 likes db에 저장
    db.likes.insert_one(doc)
    # 작동하면 내 단어장에 등록되었습니다라는 메세지 띄우기
    return jsonify({"msg": "내 단어장에 등록되었습니다."})


# 내 단어장 페이지 띄우기
@app.route('/my-words/<username>')
def mywords_page(username):
    # mytoken을 요구
    token_receive = request.cookies.get('mytoken')
    posts = list()
    try:
        # 로그인된 jwt 토큰 디스코하여 payload 설정
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        # user DB에서 "id"정보중 _id 제외하고 user_info으로 설정
        user_info = db.user.find_one({"id": payload["id"]}, {'_id': False})
        # likes DB에서 user_info정보중 _id를 제외하고 업데이트 순으로 정렬해서 likes으로 설정
        likes = list(db.likes.find({"username": user_info["id"]}, {'_id': False}).sort("date", -1))
        for i in range(len(likes)):
            posts.append(db.posts.find_one({'_id': ObjectId(likes[i]['post_id'])}))
        for post in posts:
            post["_id"] = str(post["_id"])
        # username을 my-words.html로 전달
        return render_template('my-words.html', username=username, likes=likes, posts=posts)
    # 메인페이지인 home으로 정보를 전달
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# 내 단어장 보여주기
@app.route('/my-words', methods=['GET'])
def get_mywords():
    # mytoken을 요구
    token_receive = request.cookies.get('mytoken')
    posts = list()
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload["id"]}, {'_id': False})
        likes = list(db.likes.find({"username": user_info["id"]}, {'_id': False}).sort("date", -1))
        for i in range(len(likes)):
            posts.append(db.posts.find_one({'_id': ObjectId(likes[i]['post_id'])}, {'_id': False}))
        #작동하면 결과를 성공으로, 라이크를 올라이크로, 포스트를 올 포스츠로 전달
        return jsonify({"result": "success", "all_likes": likes, "all_posts": posts})
    # jwt토큰 유효시간이 만료되거나 가지고 오는것이 안되면 home으로
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

# 내 단어장 - 단어 삭제하기
@app.route('/my-words/delete', methods=['POST'])
def delete_mywords():
    # post_id_receive를 요구.
    post_id_receive = request.form["post_id_give"]
    # likes db에서 post_id값을 삭제
    db.likes.delete_one({"post_id": post_id_receive})
    # 작동하면 내 단어장에서 삭제되었습니다 메세지
    return jsonify({"msg": "내 단어장에서 삭제되었습니다."})

# 메인페이지 - 상세단어(모달)에서 수정하기 버튼
@app.route('/api/change', methods=['POST'])
def changing():
    # url, english, korean을 요구
    url_receive = request.form['url_give']
    english_receive = request.form['english_give']
    korean_receive = request.form['korean_give']
    post_id_receive = request.form['post_id']
    # # db에 저장할때 필요 없는 값을 바꾸기
    english = english_receive.replace('\"', '')
    korean = korean_receive.replace('\"', '')
    english = english.replace('[', '')
    korean = korean.replace('[', '')
    english = english.replace(']', '')
    korean = korean.replace(']', '')
    # url, english, korean을 doc으로 묶어서 포스츠 디비에서 아이디값중 ObjectId(post_id_receive를 doc으로 업데이트.
    doc = {
        'url': url_receive,
        'english': english,
        'korean': korean
    }
    db.posts.update_one({"_id": ObjectId(post_id_receive)},
                        {'$set': doc})
    return jsonify({'msg': '해당 글이 수정되었습니다.'})

# 메인페이지 - 상세단어(모달)에서 삭제하기 버튼
@app.route('/api/delete', methods=['POST'])
def delete():
    post_id_receive = request.form['post_id_give']
    # 포스츠 디비에서 ObjectId(post_id_receive를 삭제
    db.posts.delete_one({"_id": ObjectId(post_id_receive)})
    if (db.likes.find_one({"post_id": post_id_receive})) is not None:
        db.likes.delete_one({"post_id": post_id_receive})
    # 작동하면 해당 글이 영구 삭제 되었습니다 메셋지
    return jsonify({'msg': '해당 글이 영구 삭제 되었습니다.'})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
