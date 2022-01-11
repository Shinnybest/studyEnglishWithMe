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
            post["chosen_by_me"] = bool(db.
                                        # 각 단어장에서 '나도 학습하기' 버튼 누른 데이터 저장된 mongodb collection 이름
                                        .find_one({"post_id": post["_id"], "type": "heart", "username": payload['id']}))
        return jsonify({"result": "success", "msg": "포스팅을 가져왔습니다."})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

    return jsonify({'msg': '내 단어장 목록입니다.'})


@app.route('/my-words/<username>/delete', methods=['POST'])
def delete_mywords():
    return jsonify({'msg': '내 단어장에서 삭제되었습니다.'})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)