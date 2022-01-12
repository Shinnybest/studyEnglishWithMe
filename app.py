import jwt
import datetime
import hashlib
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'SPARTA'

client = MongoClient('localhost', 27017)
db = client.doyouknow


@app.route('/upload')
def upload_page():
    return render_template('uploads.html')


@app.route('/upload', methods=['POST'])
def upload_words():
    url = request.form['url']
    english = request.form['english']
    korean = request.form['korean']
    
    english = english.replace('\"', '')
    korean = korean.replace('\"', '')
    english = english.replace('[', '')
    korean = korean.replace('[', '')
    english = english.replace(']', '')
    korean = korean.replace(']', '')

    doc = {
        'url' : url,
        'english' : english,
        'korean' : korean
    }

    db.words.insert_one(doc)
    return jsonify({'msg': '새 글이 업로드 되었습니다.'})


@app.route('/my-words/<username>')
def mywords_page(username):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False
        user_info = db.users.find_one({"username": username}, {"_id": False})
        return render_template('my-words.html', user_info=user_info, status=status, username=username)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/my-words', methods=['GET'])
def get_mywords():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        likes = list(db.likes.find({"username": user_info["username"]}).sort("date", -1))
        posts = list(db.posts.find({"_id": likes["post_id"]}))
        return jsonify({"result": "success", "msg": "내 단어장 목록입니다.", "all_likes" : likes, "all_posts": posts})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/my-words/delete', methods=['POST'])
def delete_mywords():
    token_receive = request.cookies.get('mytoken')
    try:
        # 그 삭제하고 싶은 것의 고유 id 값을 브라우저에서 받아온다.
        post_id_receive = request.args.get("post_id_give")
        db.likes.delete_one({"post_id": post_id_receive})
        return jsonify({"result": "success", "msg": "내 단어장에서 삭제되었습니다."})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))




# //규진(미완성)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/list', methods=['GET'])
def listing():
    words = db.words.find_one({유저가 클릭한 값의 posts....post_id는 아닌거 같은데 무슨 값을 넣어야 할까요}, {'_id': False})
    return jsonify({'all_words': words})


@app.route('/api/post-mine', methods=['POST'])
def saving():
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    post_id_receive = request.form['post_id_give']

    doc = {
        "post_id": post_id_receive,
        "username": payload["id"]
    }
        db.likes.insert_one(doc)
        return jsonify({'msg': '내 단어장에 저장되었습니다.'})



@app.route('/api/change', methods=['POST'])
# 수정버튼은 전체적으로 조금 더 손 봐야합니다.
def changing():
    url_receive = request.form['url_give']
    english_receive = request.form['english_give']
    korean_receive = request.form['korean_give']
    doc = {
        'url': url_receive,
        'english': english_receive,
        'korean': korean_receive
    }
    target_word = db.words.find_one(doc)
    current_word = target_word['url', 'english', 'korean']
    db.words.update_one({'name': 'bobby'},{'$set': {'url': url_receive, 'english': english_receive, 'korean': korean_receive}})
    return jsonify({'msg': '해당 글이 수정되었습니다.'})


@app.route('/api/delete', methods=['POST'])
def delete():
    url_receive = request.form['url_give']
    # english_receive = request.form['english_give']
    # korean_receive = request.form['korean_give']

    db.posts.delete_one({'url': url_receive})
    # , 'english': english_receive, 'korean': korean_receive})
    return jsonify({'msg': '해당 글이 삭제 되었습니다.'})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)


# 예은
@app.route('/upload')
def upload_page():
    return render_template('uploads.html')


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

    doc = {
        'url': url,
        'english': english,
        'korean': korean,
        'image' : image
    }

    db.posts.insert_one(doc)
    return jsonify({'msg': '새 글이 업로드 되었습니다.'})


# 메인페이지 보이기
@app.route('/')
def mhome():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({'id': payload['id']})
        posts = list(db.posts.find({}))
        for post in posts:
            post["_id"] = str(post["_id"])
        return render_template('main.html', username = user_info['id'], posts = posts)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


# 혁준
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('main.html')
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/sign_in', methods=['POST'])
def sign_in():
    username_receive = request.form['id']
    password_receive = request.form['pw']
    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.user.find_one({'id': username_receive, 'pw': pw_hash})
    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 1 * 1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({'result': 'success', 'token': token})
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


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


@app.route('/register/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['id_give']
    exists = bool(db.user.find_one({"id": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
