import jwt
import datetime
import hashlib
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
        return render_template('my-words.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/my-words/<username>', methods=['GET'])
def get_mywords():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        posts = list(db.posts.find({}).sort("date", -1))
        for post in posts:
            post["_id"] = str(post["_id"])
            post["chosen_by_me"] = bool(db
                                        .find_one({"post_id": post["_id"], "type": "heart", "username": payload['id']}))
        return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다."})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

    return jsonify({'msg': '내 단어장 목록입니다.'})


@app.route('/my-words/<username>/delete', methods=['POST'])
def delete_mywords():
    return jsonify({'msg': '내 단어장에서 삭제되었습니다.'})


# //규진 (검증필요)


@app.route('/list', methods=['GET'])
def listing():
    words = list(db.두유노우.find({}, {'_id': False}))
    return jsonify({'all_words': words})


@app.route('/api/post-mine', methods=['POST'])
def saving():
    url_receive = request.form['url_give']
    english_receive = request.form['english_give']
    korean_receive = request.form['korean_give']

    doc = {
        'url': url_receive,
        'english': english_receive,
        'korean': korean_receive
    }
    db.두유노우.insert_one(doc)
    # // 저장위치를 두유노우로 잡으면 안되는것인가? 개인의 저장공간이 필요한가?
    return jsonify({'msg': '내 단어장에 저장되었습니다.'})


@app.route('/api/change', methods=['POST'])
def changing():
    url_receive = request.form['url_give']
    english_receive = request.form['english_give']
    korean_receive = request.form['korean_give']

    doc = {
        'url': url_receive,
        'english': english_receive,
        'korean': korean_receive
    }
    target_word = db.두유노우.find_one(doc)
    current_word= target_word['url', 'english', 'korean']

    db.두유노우.update_one({'name': 'bobby'}, {'$set': {'url': url_receive, 'english': english_receive, 'korean': korean_receive}})
    return jsonify({'msg': '해당 글이 수정되었습니다.'})


@app.route('/api/delete', methods=['POST'])
def delete():
    url_receive = request.form['url_give']
    english_receive = request.form['english_give']
    korean_receive = request.form['korean_give']

    doc = {
        'url': url_receive,
        'english': english_receive,
        'korean': korean_receive
    }
    target_word_receive = db.두유노우.find_one(doc)
    db.두유노우.delete_one({'target_word': target_word_receive})
    return jsonify({'msg': '해당 글이 삭제 되었습니다.'})


# 예은
@app.route('/api/list', methods=['GET'])
def ewords():
    mWords =list(db.서버.find({}, {'_id':False}))

    return jsonify({'all_words': mWords})

# 확실치않아요ㅠㅠ
# @app.route('/api/like', methods=['POST'])
# def saving():
#     url_receive = request.form['url_give']
#
#     headers = {
#         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
#     data = requests.get(url_receive, headers=headers)
#
#     soup = BeautifulSoup(data.text, 'html.parser')
#
#     image = soup.select_one('meta[property="og:image"]')['content']
#
#     doc = {
#         'url' : url_receive,
#         'image': image
#     }
#
#     db.서버.insert_one(doc)
#     return jsonify({'msg': '저장이 연결되었습니다!'})


# 혁준
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('index.html')
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
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 1)
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
