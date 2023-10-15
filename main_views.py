from flask import Blueprint, render_template, url_for, request, session, g
from bs4 import BeautifulSoup
import urllib.request as REQ
from urllib import parse
import pandas as pd
from flask import jsonify
import re
import json
import sqlite3
import hashlib
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
import gluonnlp as nlp
import numpy as np
from kobert.utils import get_tokenizer
from kobert.pytorch_kobert import get_pytorch_kobert_model

from gensim.models import FastText
from sklearn.metrics.pairwise import cosine_similarity
from konlpy.tag import Kkma

import time
bp = Blueprint('main', __name__, url_prefix='/')


def set_n_dic(name_list, last_num, page, word, total):
    n_dic = {}
    n_dic['name_list'] = name_list
    n_dic['last_num'] = last_num #마지막 페이지 넘버
    n_dic['page'] = page #현재 페이지
    n_dic['prev_num'] = page -1
    n_dic['word'] = word
    n_dic['total'] = total #전체 개수
    if page == last_num:
        n_dic['next_num'] = 0  ##마지막 페이지이면 next_num에 0 저장
    else:
        n_dic['next_num'] = page + 1  ##다음 페이지 번호

    start = (page-1) // 5
    end = (start+1)*5
    if end > last_num:
        end = last_num
    n_dic['iter_pages'] = list(range(start*5+1, end+1))  ##페이지 번호 리스트 다섯개만
    return n_dic

def pan_api(word, opt):
    u1 = ('http://www.law.go.kr/DRF/lawSearch.do?OC=jw01012&search=2&target=prec&type=XML&display=100&page=')
    u2 = ('http://www.law.go.kr/DRF/lawService.do?OC=jw01012&type=XML&target=prec&ID=')
    prece_list = []
    w = parse.quote(word)
    pan_list = ['판시사항', '판결요지', '판례내용'] ##검색 결과로 보여줄 내용 후보
    t = 1
    res = '사건명'
    while True:
        url = u1 + str(t) + '&query=' + w
        print(url)
        try:
            xml = REQ.urlopen(url).read()
            soup = BeautifulSoup(xml, "lxml-xml")
            nums = soup.select('판례일련번호')
            kinds = soup.select('사건종류명')
            print(nums)
            if len(nums) == 0:
                break
            for k in range(len(nums)):
                if kinds[k].text == '민사':
                    try:
                        w = parse.quote(nums[k].text)
                        print(w)
                        url = u2 + w
                        html = REQ.urlopen(url).read()
                        soup = BeautifulSoup(html, "xml")
                        print(url)
                        try:
                                r = soup.find(res)
                                r = r.text.split(word)
                                new_r = []
                                if len(r) == 1:
                                    new_r = r
                                else:
                                    for i in range(len(r)):
                                        if r[i] == '' or r[i] == ' ':
                                            new_r.append(word)
                                            c += len(word)
                                        else:
                                            new_r.append(r[i])
                                            c += len(r[i])
                                            if i != len(r) - 1:
                                                if r[i + 1] != '' and r[i + 1] != ' ':
                                                    new_r.append(word)
                                                    c += len(word)
                                #point = soup.select('판시사항')
                        except:
                                pass
                        if opt == 1:
                            pan = ''
                            new_list = []
                            c = 0
                            new_s = []
                            for p in pan_list:
                                if c > 60:
                                    break
                                try:
                                    pan = soup.find(p)
                                    if pan.find(word) != -1: # 검색한 단어가 있으면 검색 단어를 기준으로 분리하여 리스트에 저장
                                        pan = pan.text.split('.')
                                        while c < 60: #총 60 글자가 넘어 가지 않도록(구체적 숫자는 추후 확정)
                                            l = pan.pop()
                                            if len(l) < len(word):
                                                continue
                                            l = l.split("<")
                                            if l[0].find(word) != -1:
                                                s_list = l[0].split(word)
                                                print(s_list)
                                                for i in range(len(s_list)):
                                                    if c > 60:
                                                        break
                                                    if s_list[i] == '':
                                                        new_s.append(word)
                                                        c += len(word)
                                                    elif s_list[i] == ' ':
                                                        new_s.append(word + ' ')
                                                        c += len(word) + 1
                                                    else:
                                                        new_s.append(s_list[i])
                                                        c += len(s_list[i])
                                                        if i != len(s_list) - 1:
                                                            if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                                                new_s.append(word)
                                                                c += len(word)
                                            if len(pan) == 0:
                                                break
                                except:
                                    pass
                            if c != 0:  ##후보들(pan_list) 중 검색 단어가 포함된 게 있으면 prece_list에 추가(없으면 삭제)
                                prece_list.append([new_r, new_s, nums[k].text])
                        else: ##내용 추가 안 하는 옵션(0)
                            prece_list.append([0, nums[k].text, r])
                    except Exception as e:
                        print(e)
        except Exception as e:
            print(e)
        t += 1
    return prece_list

def pan_api_two(word, n_list, opt):
    u2 = ('http://www.law.go.kr/DRF/lawService.do?OC=jw01012&type=XML&target=prec&ID=')
    prece_list = []
    pan_list = ['판시사항', '판결요지', '판례내용'] ##검색 결과로 보여줄 내용 후보
    t = 1
    res = '사건명'
    for k in range(len(n_list)):
            try:
                w = parse.quote(str(n_list[k]))
                url = u2 + w
                print(url)
                html = REQ.urlopen(url).read()
                soup = BeautifulSoup(html, "xml")
                try:
                    r = soup.find(res)
                    print(r)
                    # point = soup.select('판시사항')
                except:
                    pass
                if opt == 1: ## 내용 추가하는 옵션
                    pan = ''
                    cont = ''
                    for p in pan_list:
                        try:
                            pan = soup.find(p)
                            if pan.find(word) != -1:
                                pan = pan.text.split('.')
                                while(len(cont) < 60): #총 60 글자가 넘어 가지 않도록(구체적 숫자는 추후 확정)
                                    l = pan.pop()
                                    l = l.split("<")
                                    cont += l[0]
                        except:
                            pass
                    if cont != '':  ##후보들(pan_list) 중 검색 단어가 포함된 게 있으면 prece_list에 추가(없으면 삭제)
                        prece_list.append([n_list[k], r.text, cont])
                else: ##내용 추가 안 하는 옵션(0)
                    prece_list.append([n_list[k], r.text, 0])
                    print(prece_list)
            except Exception as e:
                print(e)
            t += 1
    print(prece_list)
    return prece_list

def pan_api_three(word):
    u1 = ('http://www.law.go.kr/DRF/lawSearch.do?OC=jw01012&search=2&target=prec&type=XML&display=10&page=')
    u2 = ('http://www.law.go.kr/DRF/lawService.do?OC=jw01012&type=XML&target=prec&ID=')
    prece_list = []
    w = parse.quote(word)
    t = 1
    res = '사건명'
    while len(prece_list) < 5:
        url = u1 + str(t) + '&query=' + w
        t += 1
        try:
            xml = REQ.urlopen(url).read()
            soup = BeautifulSoup(xml, "lxml-xml")
            nums = soup.select('판례일련번호')
            kinds = soup.select('사건종류명')
            if len(nums) == 0:
                break
            for k in range(len(nums)):
                if kinds[k].text == '민사':
                    try:
                        w = parse.quote(nums[k].text)
                        print(w)
                        url = u2 + w
                        html = REQ.urlopen(url).read()
                        soup = BeautifulSoup(html, "xml")
                        print(url)
                        try:
                            r = soup.find(res)
                        except:
                            continue
                    except:
                        continue
                    prece_list.append([nums[k].text, r.text])
        except:
            continue
    return prece_list
            
@bp.route('/',  methods=('GET', 'POST'))
def index():
    return render_template('index.html')

@bp.route('/api/signup', methods=('GET', 'POST'))
def signup():
    if request.method == 'POST':
        con = sqlite3.connect('./database.db', check_same_thread=False)
        id = request.form['id']
        pw = request.form['password']
        if not (id and pw):
            return "입력되지 않은 정보가 있습니다"
        cur = con.cursor()
        cur.execute('SELECT id FROM Test')
        for row in cur:
            print(row)
            if row[0] == id:
                return '이미 존재하는 사용자입니다.'
        m = hashlib.sha256()
        m.update(pw.encode('utf-8'))
        cur.execute("INSERT INTO Test Values(?, ?);", (id, m.hexdigest()))
        con.commit()
        con.close()
        return '회원가입이 완료되었습니다.'
    else :
        return '잘못된 접근입니다.'


@bp.route('/api/checkLaw')
def checkLaw():
    con = sqlite3.connect('./database.db', check_same_thread=False)
    cur = con.cursor()
    jo = request.args.get('jo', type=str)
    #opt = request.args.get('opt', type=int)
    lawBookmark = session['lawBookmark']
    userId = session['userId']
    print(userId)
    print('lawBookmark: ', lawBookmark)
    for l in lawBookmark:
        if l == jo:
            lawBookmark.remove(l)
            session['lawBookmark'] = lawBookmark
            cur.execute("UPDATE Test SET article=? Where id=?", (' '.join(s for s in lawBookmark), userId))
            print('삭제 후 lawBookmark: ', lawBookmark)
            return {'isExist': True}
    lawBookmark.append(jo)
    print('추가 후 lawBookmark: ', lawBookmark)
    session['lawBookmark'] = lawBookmark
    #if opt == 0:
    #    lawBookmark.append(jo)
    #else:
    #    lawBookmark.remove(jo)
    session['lawBookmark'] = lawBookmark
    cur.execute("UPDATE Test SET article=? Where id=?", (' '.join(s for s in lawBookmark), userId))
    con.commit()
    con.close()
    return {'isExist': False}

@bp.route('/api/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        session['isLoggedIn'] = False
        con = sqlite3.connect('./database.db', check_same_thread=False)
        id = request.form['id']
        pw = request.form['password']
        if not (id and pw):
            return "입력되지 않은 정보가 있습니다"
        print(id)
        cur = con.cursor()
        cur.execute('SELECT * FROM Test')
        for row in cur:
            print(row)
            if row[0] == id :
                m = hashlib.sha256()
                m.update(pw.encode('utf-8'))
                new_pw = m.hexdigest()
                if row[1] == new_pw:
                    print('로그인 성공')
                    #return {'조아': '조아'}
                    session['isLoggedIn'] = True
                    session['userId'] = id

                    session['lawBookmark'] = row[2].split(' ')
                    return {'isLoggedIn': session['isLoggedIn']}
                else:
                    return '아이디 혹은 패스워드를 잘못 입력했습니다. 입력하신 내용을 확인해주세요.'
        con.close()
        return '존재하지 않는 아이디 입니다.'
    else :
        return '잘못된 접근입니다.'
##app 실행 전에 실행됨
@bp.before_app_request
def load_logged_in_user():
    print('app 실행')
    isLoggedIn = session.get('isLoggedIn')
    if isLoggedIn is None:
        session['isLoggedIn'] = False
    else :
        lawBookmark = session.get('lawBookmark') #민법 조항 즐겨찾기('제nn'형태)
        preceBookmark = session.get('preceBookmark') #판례 즐겨찾기('nn(일련번호)' 형태)
        rPreceBookmark = session.get('rPreceBookmark') #판례 추천 즐겨찾기(['사용자 입력', 'nn(일련번호)'] 형태)
        if lawBookmark is None:
            session['lawBookmark'] = []
        if preceBookmark is None:
            session['preceBookmark'] = []
        if rPreceBookmark is None:
            session['rPreceBookmark'] = []

    print(isLoggedIn)


@bp.route('/api/checkLogin', methods=['GET'])
def u():
    type = request.args.get('type', type=str, default='0')
    isLoggedIn = session.get('isLoggedIn')
    userId = session.get('userId')
    if type == '0':
        return jsonify({'isLoggedIn': isLoggedIn, 'userId': userId})
    elif type == 'article':
        lawBookmark = session.get('lawBookmark')  # 민법 조항 즐겨찾기('제nn'형태)
        print(lawBookmark)
        return jsonify({'isLoggedIn': isLoggedIn, 'userId': userId, 'lawBookmark': lawBookmark})
    elif type == 'precedent':
        preceBookmark = session.get('preceBookmark')  # 판례 즐겨찾기('nn(일련번호)' 형태)
        return jsonify({'isLoggedIn': isLoggedIn, 'userId': userId, 'preceBookmark': preceBookmark})
    elif type == 'rprecedent':
        rPreceBookmark = session.get('rPreceBookmark')  # 판례 추천 즐겨찾기(['사용자 입력', 'nn(일련번호)'] 형태)
        return jsonify({'isLoggedIn' : isLoggedIn, 'userId' : userId, 'rPreceBookmark':rPreceBookmark})
    return '잘못된 접근입니다.'

@bp.route('/api/logout', methods=['GET'])
def logout():
    session.clear()
    session['isLoggedIn'] = False
    #return '로그아웃 완료'
    return jsonify({'isLoggedIn' : session['isLoggedIn']})

@bp.route('/api/product/search')
def productSearch():
    word = request.args.get('word', type=str)
    return jsonify({ "id" : 2, "name" : word})

@bp.route('/api/homeContents/<string:c>')
def generate_home_contents(c):
    data = {}
    article = pd.read_pickle("/var/www/myapp/src/law/article_1_label.pkl")[:5]
    a_list = []
    for i in range(len(article)):
        a_list.append([article['title'][i], article['contents'][i]])
    prece_list = pan_api_three(c)
    data['article'] = a_list
    data['precedent'] = prece_list
    return json.dumps(data, ensure_ascii=False)
    
@bp.route('/api/precedent/<string:c1>/<string:c2>')
def generate_pan_list(c1, c2):
    c_list = ['총칙', '물권', '채권', '친족', '상속']
    c_list2 = {'총칙': ['통칙', '인', '법인', '물건', '법률행위', '기간', '소멸시효'],
                '물권': ['총칙', '점유권', '소유권', '지상권', '지역권', '전세권', '유치권', '질권', '저당권'],
                '채권' : ['총칙', '증여', '매매', '교환', '소비대차', '사용대차', '임대차', '고용', '도급', '여행계약',
                '현상광고', '위임', '임치', '조합', '종신정기금', '화해', '사무관리', '부당이득', '불법행위'],
                '친족' : ['총칙', '가족의 범위와 자의 성과 본', '혼인', '친생자', '양자', '친권', '후견', '부양'],
                '상속' : ['상속', '유언', '유류분']}
    prece_list = []
    page = request.args.get('page', type=int, default=1)  # 페이지


    prece_list = pan_api(c2, 0) ##[일련번호, 사건명, 0]으로 이루어진 2차원 배열(opt=0)

    last_num = 0
    l = len(prece_list)
    if l % 10 != 0:
        last_num = 1
    last_num += l//10

    p_dic = set_n_dic(prece_list, last_num, page, c2, l)
    num_list = []  ##일련번호 리스트
    for p in prece_list:
        num_list.append(p[1])
    session["num_list"] = num_list ##session storage에 num_list 저장
    session["page"] = page ##session storage에 page 저장
    session["word"] = c2 ##session storage에 last_num 저장
    session["total"] = p_dic['total']
    print(num_list)
    data = {}
    data["c_list1"] = c_list
    data["c_list2"] = c_list2
    data["dic"] = p_dic
    data["c1"] = c1
    data["c2"] = c2

    #return render_template('precedent/category.html', category_list = c_list, category_list2 = c_list2, p_dic=p_dic, category=c1, category2=c2)
    return json.dumps(data, ensure_ascii=False)
@bp.route('/api/search')
def search_index():
    prece_list = []
    a_dic = {} ##민법 조항 딕셔너리
    p_dic = {}
    content = request.args.get('query', type=str)
    opt = request.args.get('option', type=int, default=1) ##검색 옵션(1: 전체, 2:민법, 3:판례)
    page = request.args.get('page', type=int, default=1)  # 페이지
    isSummary = request.args.get('isSummary', type=int, default=0)
    #content = request.form['input'] #post 방식
    #opt = request.form['opt']
    #page = request.form['page']
    opt_list = ['통합검색', '민법', '판례']
    if opt != 3:
        a_list = []
        a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_1_label.pkl"))
        a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_2_label.pkl"))
        a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_3_label.pkl"))
        a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_4_label.pkl"))
        a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_5_label.pkl"))
        article = pd.concat(a_list, sort=False)
        article.index = range(len(article))
        article_list = [] #전체 리스트(n개의 new_s로 이루어짐)
        a_list = [] #각 조항을 검색 단어로 분할한 리스트
        for i in range(len(article)):
            check = 0 #단어가 있으면 1, 없으면 0
            a = list(article.loc[i])
            for k in range(len(a)-1): #맨 뒤는 레이블이므로 제외해줌.
                if k == 0:
                    #조항 제목에 해당 단어가 있을 때
                    if a[k].find(content) != -1:
                        check = 1
                        s_list = a[k].split(content)
                        new_s = []
                        for i in range(len(s_list)):
                            if s_list[i] == '':
                                new_s.append(content)
                            elif s_list[i] == ' ':
                                new_s.append(content + ' ')
                            else:
                                new_s.append(s_list[i])
                                if i != len(s_list) - 1:
                                    if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                        new_s.append(content)
                        a_list.append(new_s)
                    else:
                        a_list.append([a[k]])
                else:
                    for s in a[k]:
                        if s.find(content) != -1:
                            check = 1
                            s_list = s.split(content)
                            new_s = []
                            for i in range(len(s_list)):
                                if s_list[i] == '':
                                    new_s.append(content)
                                elif s_list[i] == ' ':
                                    new_s.append(content + ' ')
                                else:
                                    new_s.append(s_list[i])
                                    if i != len(s_list) - 1:
                                        if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                            new_s.append(content)
                            a_list.append(new_s)
                        else:
                            a_list.append([s])
            if check == 1:
                    article_list.append(a_list)
            a_list = []
        last_num = 0
        l = len(article_list)
        if l % 10 != 0:
            last_num = 1
        last_num += l // 10
        print(article_list)
        a_dic = set_n_dic(article_list, last_num, page, content, l)
    if opt != 2:
        prece_list = [] #전체 리스트(n개의 new_s로 이루어짐)
        if isSummary:
            p_list = []
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_1.pkl"))
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_2.pkl"))
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_3.pkl"))
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_4.pkl"))
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_5.pkl"))
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_6.pkl"))
            p_list.append(pd.read_pickle("/var/www/myapp/law/pan/panyo_7.pkl"))
            article = pd.concat(p_list, sort=False)
            article.index = range(len(article))
            a_list = [] #각 조항을 검색 단어로 분할한 리스트
            for i in range(len(article)):
                check = 0 #단어가 있으면 1, 없으면 0
                a = list(article.loc[i])
                for k in range(len(a)-1): #맨 뒤는 레이블이므로 제외해줌.
                    if k == 0:
                        #조항 제목에 해당 단어가 있을 때
                        if a[k].find(content) != -1:
                            check = 1
                            s_list = a[k].split(content)
                            new_s = []
                            for i in range(len(s_list)):
                                if s_list[i] == '':
                                    new_s.append(content)
                                elif s_list[i] == ' ':
                                    new_s.append(content + ' ')
                                else:
                                    new_s.append(s_list[i])
                                    if i != len(s_list) - 1:
                                        if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                            new_s.append(content)
                            a_list.append(new_s)
                        else:
                            a_list.append([a[k]])
                    else:
                        for s in a[k]:
                            if s.find(content) != -1:
                                check = 1
                                s_list = s.split(content)
                                new_s = []
                                for i in range(len(s_list)):
                                    if s_list[i] == '':
                                        new_s.append(content)
                                    elif s_list[i] == ' ':
                                        new_s.append(content + ' ')
                                    else:
                                        new_s.append(s_list[i])
                                        if i != len(s_list) - 1:
                                            if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                                new_s.append(content)
                                a_list.append(new_s)
                            else:
                                a_list.append([s])
                if check == 1:
                    prece_list.append(a_list)
                a_list = []
        else:
            prece_list = pan_api(content, 1) ##[일련번호, 사건명, 내용]으로 이루어진 2차원 리스트(opt 1)
        last_num = 0
        l = len(prece_list)
        if l % 10 != 0:
            last_num = 1
        last_num += l//10

        p_dic = set_n_dic(prece_list, last_num, page, content, l)
        print(p_dic)
        num_list = []  ##일련번호 리스트
        for p in prece_list:
            num_list.append(p[1])
        session["page"] = page ##session storage에 page 저장
        session["word"] = content ##session storage에 last_num 저장
        session["total"] = p_dic['total']
#    return render_template('search.html', p_dic=p_dic, a_dic=a_dic, opt=opt, opt_list=opt_list)
    data = {}
    data["p_dic"] = p_dic
    data["a_dic"] = a_dic
    data["opt"] = opt
    data["opt_list"] = opt_list
    #return render_template('search.html', p_dic=p_dic, a_dic=a_dic, opt_list =opt_list, opt=opt)
    return json.dumps(data, ensure_ascii=False)
@bp.route('/api/search/article/<string:c>')
def search_article(c):
    page = request.args.get('page', type=int, default=1)  # 페이지
    a_list = []
    a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_1_label.pkl"))
    a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_2_label.pkl"))
    a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_3_label.pkl"))
    a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_4_label.pkl"))
    a_list.append(pd.read_pickle("/var/www/myapp/src/law/article_5_label.pkl"))
    article = pd.concat(a_list, sort=False)
    article.index = range(len(article))
    article_list = []  # 전체 리스트(n개의 new_s로 이루어짐)
    a_list = []  # 각 조항을 검색 단어로 분할한 리스트
    for i in range(len(article)):
        check = 0  # 단어가 있으면 1, 없으면 0
        a = list(article.loc[i])
        for k in range(len(a)-1):
            if k == 0:
                # 조항 제목에 해당 단어가 있을 때
                if a[k].find(c) != -1:
                    # new_s에 해당 단어로 나눈 문자열 저장
                    s_list = a[k].split(c)
                    new_s = []
                    for i in range(len(s_list)):
                        if s_list[i] == '':
                            new_s.append(c)
                        elif s_list[i] == ' ':
                            new_s.append(c + ' ')
                        else:
                            new_s.append(s_list[i])
                            if i != len(s_list) - 1:
                                if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                    new_s.append(c)
                    check = 1
                    a_list.append(new_s)
                else:  # 해당 단어가 없으면 그냥 제목 저장
                    a_list.append([a[k]])
            else:
                for s in a[k]:
                    if s.find(c) != -1:
                        s_list = s.split(c)
                        new_s = []
                        for i in range(len(s_list)):
                            if s_list[i] == '':
                                new_s.append(c)
                            elif s_list[i] == ' ':
                                new_s.append(c + ' ')
                            else:
                                new_s.append(s_list[i])
                                if i != len(s_list) - 1:
                                    if s_list[i + 1] != '' and s_list[i + 1] != ' ':
                                        new_s.append(c)
                        check = 1
                        a_list.append(new_s)
                    else:
                        a_list.append([s])
        if check == 1:
            article_list.append(a_list)
        a_list = []

    last_num = 0
    l = len(article_list)
    if l % 10 != 0:
        last_num = 1
    last_num += l // 10

    a_dic = set_n_dic(article_list, last_num, page, c, l)
    print(l)
    data = {}
    data["dic"] = a_dic
    #return render_template('article/search.html', a_dic=a_dic)
    return json.dumps(data, ensure_ascii=False)
@bp.route('/api/search/precedent/<string:c>')
def search_precedent(c):
    p_list = []
    page = request.args.get('page', type=int, default=1)  # 페이지
    # session storage 비우기
    try:
        session.pop("page", None)
        word = session["word"]
        if word != c:  # 기존에 검색했던 단어와 다를 경우 word와 name_list, last_num 삭제
            session.pop("word", None)
            session.pop("name_list", None)
            session.pop("total", None)
        else:  # 기존에 검색했던 단어와 동일할 경우 word, name_list, last_num 그대로 쓰고, api 이용할 거 없이 바로 반환
            num_list = session["num_list"]
            total = session["total"]
            last_num = 0
            if total % 10 != 0:
                last_num = 1
            last_num += total // 10
            name_list = pan_api_two(word, num_list, 1)
            p_dic = set_n_dic(name_list, last_num, page, word, total)
            session["page"] = page  ##session storage에 page 저장
            return render_template('precedent/search.html', p_dic=p_dic)
    except:
        pass

    prece_list = pan_api(c, 1)

    last_num = 0
    l = len(prece_list)
    if l % 10 != 0:
        last_num = l
    last_num += l // 10

    p_dic = set_n_dic(prece_list, last_num, page, c, l)

    num_list = []  ##일련번호 리스트
    for p in prece_list:
        num_list.append(p[0])

    session["num_list"] = num_list  ##session storage에 name_list 저장
    session["page"] = page  ##session storage에 page 저장
    session["word"] = c  ##session storage에 last_num 저장
    session["total"] = p_dic['total']

    data = {}
    data["dic"] = p_dic
    #return render_template('precedent/search.html', p_dic=p_dic)
    return json.dumps(data, ensure_ascii=False)



@bp.route('/api/precedent/detail/<string:num>')
def show_precedent(num):
    num_list = session["num_list"]
    page = session["page"]
    word = session["word"]
    total = session["total"]
    last_num = 0
    if total % 10 != 0:
        last_num = 1
    last_num += total // 10

    p = request.args.get('page', type=int, default=page)  # 페이지
    session["page"] = p

    name_list = pan_api_two(word, num_list, 0)
    p_dic = set_n_dic(name_list, last_num, p, word, total)
    u = ('http://www.law.go.kr/DRF/lawService.do?OC=jw01012&type=XML&target=prec&ID=')
    preceList = []
    resList = ['판례정보일련번호', '사건명', '사건번호', '선고일자', '선고', '법원명', '법원종류코드',
               '사건종류명', '사건종류코드', '판시유형', '판시사항', '판결요지', '참조조문', '참조판례', '판례내용']  ##출력 결과 필드 리스트
    try:
        w = parse.quote(num)
        url = u + w
        html = REQ.urlopen(url).read()
        soup = BeautifulSoup(html, "xml")
        print(url)
        p = []
        for r in resList:
            try:
                res = soup.find(r)
                res = res.text
                res = res.split('<br/>')
                p.append([r, res])
            except:
                pass
        preceList.append(p)
    except Exception as e:
        print(e)
    for pl in preceList[0]:
        print(pl)
    data = {}
    data["preceList"] = preceList
    data["p_dic"] = p_dic
    data["num"] = num
    print(data)
    #return render_template('precedent/contents.html', precedent_list = preceList, p_dic=p_dic, num=num)
    return json.dumps(data, ensure_ascii=False)
@bp.route('/api/article/<string:c1>/<int:c2>')
def generate_article_list(c1, c2):
    c_dic = {'총칙': 1, '물권': 2, '채권': 3, '친족': 4, '상속': 5} #파일 이름을 지정하기 위한 딕셔너리.
    s = '/var/www/myapp/src/law/article_' + str(c_dic[c1]) + '_label.pkl'
    hcnList = ['총칙', '물권', '채권', '친족', '상속']
    lcnList = {'총칙': ['통칙', '인', '법인', '물건', '법률행위', '기간', '소멸시효'],
                '물권': ['총칙', '점유권', '소유권', '지상권', '지역권', '전세권', '유치권', '질권', '저당권'],
                '채권' : ['총칙', '증여', '매매', '교환', '소비대차', '사용대차', '임대차', '고용', '도급', '여행계약',
                '현상광고', '위임', '임치', '조합', '종신정기금', '화해', '사무관리', '부당이득', '불법행위'],
                '친족' : ['총칙', '가족의 범위와 자의 성과 본', '혼인', '친생자', '양자', '친권', '후견', '부양'],
                '상속' : ['상속', '유언', '유류분']}
    article = pd.read_pickle(s)
    a_list = []
    for i in range(len(article)):
        if article['label'][i] == c2:
            a_list.append([article['title'][i], article['contents'][i]])
    page = request.args.get('page', type=int, default=1)  # 페이지
    total = 0
    l = len(a_list)
    print(a_list)
    if l % 10 != 0:
        total = 1
    total += l//10
    print(total)
    a_dic = set_n_dic(a_list, total, page, c2, l)

    data = {}
    data["c_list1"] = hcnList
    data["c_list2"] = lcnList
    data["dic"] = a_dic
    data["c1"] = c1
    data["c2"] = c2

    #return render_template('article/category.html', category_list = hcnList, category_list2 = lcnList, a_dic = a_dic, category=c1, category2=c2)
    return json.dumps(data, ensure_ascii=False)



kkma = Kkma()
# 불용어 정의
stopwords = ['의','가','이','은','들','는','좀','잘','과','도','를','으로','자','에','와','한','하다',
             '적극', '소극','여부', '되다', '제', '매', '로', '때', '후', '로', '전', '민법', '방법',
             '경우', '상', '따르다', '있다', '않다', '원심', '및', '법', '에서', '또는', '그', '수', '에게',
             '인지', '해당', '에게', '위', '판결', '조', '인', '위', '사례', '사안', '대하', '되어다'
             '효력', '판단', '청구', '소송', '법원', '제기', '인정', '의미', '요건', '받다', '취지',
             '는지', '관하', '다고']


tokenized_data = []
def tokenize_sentence(sentence):
    #tokenized_sentence = kkma.morphs(sentence) # 토큰화
    tokenized_sentence = kkma.pos(sentence)
    print(tokenized_sentence)
    stopwords_removed_sentence = [word for word in tokenized_sentence if not word[0] in stopwords] # 불용어 제거
    l = []
    for s in stopwords_removed_sentence:
      #s[0] = re.sub(r"[^가-힣\s]", " ", s[0])
      #s[0] = re.sub("\s\s+", " ", s[0])
      l.append(s)
    print(l)
    return l




#GPU 사용
device = torch.device("cuda:0")
#BERT 모델, Vocabulary 불러오기
bertmodel, vocab = get_pytorch_kobert_model()

# Setting parameters
max_len = 64
batch_size = 32
warmup_ratio = 0.1
num_epochs = 10
max_grad_norm = 1
log_interval = 200
learning_rate =  5e-5

class BERTDataset(Dataset):
    def __init__(self, dataset, sent_idx, label_idx, bert_tokenizer, max_len,
                 pad, pair):
        transform = nlp.data.BERTSentenceTransform(
            bert_tokenizer, max_seq_length=max_len, pad=pad, pair=pair)

        self.sentences = [transform([i[sent_idx]]) for i in dataset]
        self.labels = [np.int32(i[label_idx]) for i in dataset]

    def __getitem__(self, i):
        return (self.sentences[i] + (self.labels[i], ))

    def __len__(self):
        return (len(self.labels))


class BERTClassifier(nn.Module):
    def __init__(self,
                 bert,
                 hidden_size=768,
                 num_classes=7,  ##클래스 수 조정##
                 dr_rate=None,
                 params=None):
        super(BERTClassifier, self).__init__()
        self.bert = bert
        self.dr_rate = dr_rate

        self.classifier = nn.Linear(hidden_size, num_classes)
        if dr_rate:
            self.dropout = nn.Dropout(p=dr_rate)

    def gen_attention_mask(self, token_ids, valid_length):
        attention_mask = torch.zeros_like(token_ids)
        for i, v in enumerate(valid_length):
            attention_mask[i][:v] = 1
        return attention_mask.float()

    def forward(self, token_ids, valid_length, segment_ids):
        attention_mask = self.gen_attention_mask(token_ids, valid_length)

        _, pooler = self.bert(input_ids=token_ids, token_type_ids=segment_ids.long(),
                              attention_mask=attention_mask.float().to(token_ids.device))
        if self.dr_rate:
            out = self.dropout(pooler)
        return self.classifier(out)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#BERT 모델 불러오기
model = BERTClassifier(bertmodel,  dr_rate=0.5).to(device)

model_state_dict = torch.load("/var/www/myapp/src/bert_q_5400_epoch10_vs1_dict.pt")
model.load_state_dict(model_state_dict)

# 토큰화
tokenizer = get_tokenizer()
tok = nlp.data.BERTSPTokenizer(tokenizer, vocab, lower=False)


def predict(predict_sentence):
    data = [predict_sentence, '0']
    dataset_another = [data]

    another_test = BERTDataset(dataset_another, 0, 1, tok, max_len, True, False)
    test_dataloader = torch.utils.data.DataLoader(another_test, batch_size=batch_size, num_workers=0)

    model.eval()

    for batch_id, (token_ids, valid_length, segment_ids, label) in enumerate(test_dataloader):
        token_ids = token_ids.long().to(device)
        segment_ids = segment_ids.long().to(device)

        valid_length = valid_length
        label = label.long().to(device)

        out = model(token_ids, valid_length, segment_ids)

        test_eval = []
        for i in out:
            logits = i
            logits = logits.detach().cpu().numpy()
            if np.argmax(logits) == 0:
                test_eval.append("손해배상")
            elif np.argmax(logits) == 1:
                test_eval.append("민사일반")
            elif np.argmax(logits) == 2:
                test_eval.append("물권")
            elif np.argmax(logits) == 3:
                test_eval.append("채권")
            elif np.argmax(logits) == 4:
                test_eval.append("계약")
            elif np.argmax(logits) == 5:
                test_eval.append("친족")
            elif np.argmax(logits) == 6:
                test_eval.append("상속")

        res = ">> 입력하신 문장은 " + test_eval[0] + " 관련 내용입니다."
        print(res)
        return res, np.argmax(logits)


def get_document_vectors(document_list):
    document_embedding_list = []
    loaded_model = FastText.load("/var/www/myapp/src/pan_20000_fst_kk_2") # 모델 로드
    #각 문서에 대해서
    for line in document_list:
        doc2vec = None
        count = 0
        for word in line.split():
            try:
                w = loaded_model.wv.get_vector(word)
                count += 1

                #해당 문서에 있는 모든 단어들의 벡터 값을 더한다.
                if doc2vec is None :
                    doc2vec = w
                else :
                    doc2vec = doc2vec + w
            except:
                pass

        if doc2vec is not None:
            # 단어 벡터를 모두 더한 벡터의 값을 문서 길이로 나눠준다.
            doc2vec = doc2vec/count
            document_embedding_list.append(doc2vec)

    # 각 문서에 대한 문서 벡터 리스트를 리턴
    return document_embedding_list


@bp.route('/api/test', methods=('GET', 'POST'))
def test():
    if request.method == 'POST':
        id = request.form['photo']
        print(id)
    return '성공'


@bp.route('/api/pan', methods=('GET', 'POST'))
def pan():
    query = 0 ##사용자 입력 문장(없으면 0)
    r = 0
    label = 0
    t1, t2 = 0, 0
    pos1 = '/var/www/myapp/src/law/pan/pansio_'
    pos2 = '/var/www/myapp/src/law/pan/pansix_'
    u = "https://www.law.go.kr/DRF/lawService.do?OC=jw01012&target=lstrmRlt&query="
    pan_list = []
    if request.method == 'POST':
        query = request.form['input']
        print(query)
        t1 =time.time()
        nums, documents, contents = [], [], []
        r, label = predict(query)
        q = tokenize_sentence(query)
        newQ = ''
        for tq in q:    
            if tq[1] != 'NNG':
                newQ += tq[0] + ' '
                print(newQ)
                continue
            tq = tq[0]
            a = '' #추가할 단어 저장
            tq = tq.replace('▁', '')
            url = u + parse.quote(tq)
            print(url)
            try:
              html = REQ.urlopen(url).read()
              soup = BeautifulSoup(html, "lxml-xml")
              try:
                wList1 = soup.select('용어관계')
                wList2 = soup.select('법령용어명')
                print(wList1, wList2)
                t = 0
                for k in range(len(wList1)):
                  if (wList1[k].text == '동의어'):
                    a = wList2[k].text
                    t = 1
                    break
                if(t == 0):
                  a = tq
              except:
                a = tq
            except:
                a = tq
            newQ += a + ' '
        
        names = ['갑', '을']

        pan = pd.read_csv(pos1 + str(label+1) + '_2000.csv', encoding='CP949')
        pan2 = pd.read_csv(pos2 + str(label+1) + '_2000.csv', encoding='CP949')
        for p in range(len(p_obj)):
          if len(pan['contents'][p]) <20:  
            pan = pan.drop(p)
            pan2 = pan2.drop(p)
        pan.index = range(len(pan))
        pan2.index = range(len(pan2))
        print(len(pan), len(pan2)
        nums = list(pan['number'])
        documents = list(pan['contents'])
        contents = list(pan2['contents'])
        for cont in contents:
            s = cont.split()
            for w in s:
                c = 0
                for n in names:
                    if w.find(n) == 0:
                        c = 1
                        break
                if c == 1:
                    continue
        #nums = [pan['number'][i] for i in range(len(pan)) if pan['label'][i] == label]
        #documents = [pan['contents'][i] for i in range(len(pan)) if pan['label'][i] == label]
        document_embedding_list = get_document_vectors(documents)
        
        print(len(document_embedding_list))
        f2v_q = get_document_vectors([newQ])
        sim_scores = [[nums[i], contents[i], cosine_similarity(f2v_q, [document_embedding_list[i]]), i] for i in
                  range(len(document_embedding_list))]
        sim_scores.sort(key=lambda x: x[2], reverse=True) #sim_scores의 각 리스트 중 세번째 요소를 정렬 기준으로.
        sim_scores = sim_scores[:5]

        for s in sim_scores:
            new_s = s[1].split('<br/>')
            pan_list.append([s[0], new_s])

    session["num_list"] = [p[0] for p in pan_list]  ##session storage에 name_list 저장
    session["page"] = 1  ##session storage에 page 저장
    session["word"] = query  ##session storage에 last_num 저장
    session["total"] = 5

    data = {}
    data['query'] = query
    data['pan_list'] = pan_list
    t2 = time.time()
    print(data)
    print('소요시간(초): ', t2-t1)
    #return render_template('pan.html', r = r, query=query, pan_list=pan_list)
    return json.dumps(data, ensure_ascii=False)

