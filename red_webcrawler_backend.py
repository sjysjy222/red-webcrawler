import requests
import pandas as pd
from pprint import pprint
import time
import random
import re
from urllib.parse import unquote
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba
import numpy as np
import json
import os
from flask import Flask, render_template



# 导入包
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')  # 让它加载你原来的 HTML 文件

comments_cache = []
@app.route('/get_latest_comments')
def get_latest_comments():
    return jsonify({'comments': comments_cache})

notice_cache = []
@app.route('/get_latest_notice')
def get_latest_notice():
    return jsonify({'notice': notice_cache})


@app.route('/process', methods=['POST'])
def process():
    data = request.json
    print("收到前端发来的数据：", data)
    global comments_cache, notice_cache, word_cloud_image,comment_df # 声明用的是外面的全局变量
    comments_cache.clear()               # 清空列表
    notice_cache.clear()
    word_cloud_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBg2ogq8gAAAAASUVORK5CYII="

    #采集并搜索评论
    user_cookie=data.get('cookie')
    user_url=data.get('url')
    user_keyword=data.get('keyword')

    #annoymous header
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Cookie': 'abRequestId=64747ee4-d70b-58a5-bed4-452a6daaefd5; webBuild=4.70.2; xsecappid=xhs-pc-web; a1=197d39186015ez2t2k4z644y6k1n6q5u0hq3u980p50000240529; webId=ac8717725100c00a4884db187f5156b9; unread={%22ub%22:%2264c530cb000000000c0357a4%22%2C%22ue%22:%226464b089000000001402534d%22%2C%22uc%22:11}; acw_tc=0a0bb19e17516012209735757e3f82f141b48f175a42c3a31025cbe0fb3bd7; web_session=030037af540430132bbd09161f2f4aba353f09; websectiga=9730ffafd96f2d09dc024760e253af6ab1feb0002827740b95a255ddf6847fc8; sec_poison_id=e3b1161a-b1d7-49db-8bc8-05bd40dad671; gid=yjWfqjy0yS84yjWfqjyYKxjY8y2duJ9JT4uKA8U44vKTyq28IKA277888J482Jj8KqfjWd80; loadts=1751601232123',
    'Referer': f'https://www.xiaohongshu.com/'
    }

    #截取url
    pass_url= re.search(r'(https?://xhslink\.com/\S+)', user_url).group(1)
    print(pass_url)
    response=requests.get(url=pass_url,headers=headers,allow_redirects=True)
    pass_url=response.url
    print(pass_url)

    redirect_match = re.search(r'redirectPath=([^&]+)', pass_url)
    if redirect_match:
        redirect_url = unquote(redirect_match.group(1))
        print(f"解码后的 redirect URL:\n{redirect_url}\n")
        notice_cache.append(f"解码后的 redirect URL:\n{redirect_url}\n")

    # 在解码后的 URL 里找 xsec_token
        token_match = re.search(r'xsec_token=([^&]+)', redirect_url)
        if token_match:
            xsec_token = unquote(token_match.group(1))
            print(f"xsec_token: {xsec_token}")
        else:
            print("❌ 没有找到 xsec_token")
    else:
        print("❌ 没有找到 redirectPath")



    noteid = re.search(r'/item/([a-zA-Z0-9]+)', redirect_url).group(1)
    print(f'笔记ID：{noteid}')
    notice_cache.append(f'笔记ID：{noteid}')

    #login header
    cursor = None
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Cookie': user_cookie,
    'Referer': f'https://www.xiaohongshu.com/discovery/item/{noteid}'
    }
    url='https://edith.xiaohongshu.com/api/sns/web/v2/comment/page'

    comment_df=pd.DataFrame(columns=['user_name','comment'])
    comment_list=[]
    user_name_list=[]
    cursor = None
    keyword=user_keyword

    print(f'正在200个页面中搜索“{keyword}”......')
    notice_cache.append(f'正在200个页面中搜索“{keyword}”......')
    i=True
    page=0
    while i == True:

        #链接参数
        params={
        'note_id': noteid,
        'cursor' : cursor,
        'image_formats': 'jpg,webp,avif',
        'xsec_token': xsec_token,
        }
    
        response=requests.get(url=url,headers=headers,params=params)
        #print(response.json())
        if not response.json()['data']:
            i=False
            notice_cache.append(f'评论数据为空！请检查cookie或url是否过期')
            break
        else:
            response_json=response.json()['data']['comments']
        #print(response_cursor)
        has_more=response.json()['data']['has_more']
        for reply in response_json:
            comment=reply['content']
            match=bool(re.search(keyword, str(comment)))
            user_name=reply['user_info']['nickname']
            if match == True:
                print(f'{user_name}:{comment}')
                comments_cache.append(comment)
            comment_list.append(comment)
            user_name_list.append(user_name)
        if has_more == True:
            cursor=response.json()['data']['cursor']
        else:
            print('已完成搜索！')
            notice_cache.append('已完成搜索！')
            i=False
            break
        print(f'第{page}页已完成！')
        notice_cache.append(f'第{page}页已完成！')
        if page % 10 == 0: #模拟真人休息
            time.sleep(random.uniform(10, 20))
        if page == 199:
            i=False
            print('已完成搜索！')
            notice_cache.append('已完成搜索！')
            break
        page=page+1
        time.sleep(random.uniform(3,10))#模拟真人翻页速度

    comment_df['user_name']=user_name_list
    comment_df['comment']=comment_list
    print(comment_df)

    comment_df['matched_comment']=comment_df['comment'].apply(
    lambda x: bool(re.search(keyword, str(x)))
    )
    print('搜索结果：')
    print()
    print(comment_df[comment_df['matched_comment'] == True])
    matched_case_number=sum(comment_df['matched_comment'] == True)
    print(f'共搜索到{matched_case_number}个结果。')


    #tfidf
    def remove_xhs_emojis(text):
    # 匹配 [xxxx] 格式的表情
        return re.sub(r'\[.*?]', '', text)
    comment_df['comment'] = comment_df['comment'].apply(lambda x: remove_xhs_emojis(x))
    corpus=comment_df['comment']

    chinese_stopwords = ["、","。","〈","〉","《","》","一","一些","一何","一切","一则","一方面","一旦","一来","一样","一般","一转眼","七","万一","三","上","上下","下","不","不仅","不但","不光","不单","不只","不外乎","不如","不妨","不尽","不尽然","不得","不怕","不惟","不成","不拘","不料","不是","不比","不然","不特","不独","不管","不至于","不若","不论","不过","不问","与","与其","与其说","与否","与此同时","且","且不说","且说","两者","个","个别","中","临","为","为了","为什么","为何","为止","为此","为着","乃","乃至","乃至于","么","之","之一","之所以","之类","乌乎","乎","乘","九","也","也好","也罢","了","二","二来","于","于是","于是乎","云云","云尔","五","些","亦","人","人们","人家","什","什么","什么样","今","介于","仍","仍旧","从","从此","从而","他","他人","他们","他们们","以","以上","以为","以便","以免","以及","以故","以期","以来","以至","以至于","以致","们","任","任何","任凭","会","似的","但","但凡","但是","何","何以","何况","何处","何时","余外","作为","你","你们","使","使得","例如","依","依据","依照","便于","俺","俺们","倘","倘使","倘或","倘然","倘若","借","借傥然","假使","假如","假若","做","像","儿","先不先","光是","全体","全部","八","六","兮","共","关于","关于具体地说","其","其一","其中","其二","其他","其余","其它","其次","具体地说","具体说来","兼之","内","再","再其次","再则","再有","再者","再者说","再说","冒","冲","况且","几","几时","凡","凡是","凭","凭借","出于","出来","分","分别","则","则甚","别","别人","别处","别是","别的","别管","别说","到","前后","前此","前者","加之","加以","即","即令","即使","即便","即如","即或","即若","却","去","又","又及","及","及其","及至","反之","反而","反过来","反过来说","受到","另","另一方面","另外","另悉","只","只当","只怕","只是","只有","只消","只要","只限","叫","叮咚","可","可以","可是","可见","各","各个","各位","各种","各自","同","同时","后","后者","向","向使","向着","吓","吗","否则","吧","吧哒","含","吱","呀","呃","呕","呗","呜","呜呼","呢","呵","呵呵","呸","呼哧","咋","和","咚","咦","咧","咱","咱们","咳","哇","哈","哈哈","哉","哎","哎呀","哎哟","哗","哟","哦","哩","哪","哪个","哪些","哪儿","哪天","哪年","哪怕","哪样","哪边","哪里","哼","哼唷","唉","唯有","啊","啐","啥","啦","啪达","啷当","喂","喏","喔唷","喽","嗡","嗡嗡","嗬","嗯","嗳","嘎","嘎登","嘘","嘛","嘻","嘿","嘿嘿","四","因","因为","因了","因此","因着","因而","固然","在","在下","在于","地","基于","处在","多","多么","多少","大","大家","她","她们","好","如","如上","如上所述","如下","如何","如其","如同","如是","如果","如此","如若","始而","孰料","孰知","宁","宁可","宁愿","宁肯","它","它们","对","对于","对待","对方","对比","将","小","尔","尔后","尔尔","尚且","就","就是","就是了","就是说","就算","就要","尽","尽管","尽管如此","岂但","己","已","已矣","巴","巴巴","年","并","并且","庶乎","庶几","开外","开始","归","归齐","当","当地","当然","当着","彼","彼时","彼此","往","待","很","得","得了","怎","怎么","怎么办","怎么样","怎奈","怎样","总之","总的来看","总的来说","总的说来","总而言之","恰恰相反","您","惟其","慢说","我","我们","或","或则","或是","或曰","或者","截至","所","所以","所在","所幸","所有","才","才能","打","打从","把","抑或","拿","按","按照","换句话说","换言之","据","据此","接着","故","故此","故而","旁人","无","无宁","无论","既","既往","既是","既然","日","时","时候","是","是以","是的","更","曾","替","替代","最","月","有","有些","有关","有及","有时","有的","望","朝","朝着","本","本人","本地","本着","本身","来","来着","来自","来说","极了","果然","果真","某","某个","某些","某某","根据","欤","正值","正如","正巧","正是","此","此地","此处","此外","此时","此次","此间","毋宁","每","每当","比","比及","比如","比方","没奈何","沿","沿着","漫说","焉","然则","然后","然而","照","照着","犹且","犹自","甚且","甚么","甚或","甚而","甚至","甚至于","用","用来","由","由于","由是","由此","由此可见","的","的确","的话","直到","相对而言","省得","看","眨眼","着","着呢","矣","矣乎","矣哉","离","秒","竟而","第","等","等到","等等","简言之","管","类如","紧接着","纵","纵令","纵使","纵然","经","经过","结果","给","继之","继后","继而","综上所述","罢了","者","而","而且","而况","而后","而外","而已","而是","而言","能","能否","腾","自","自个儿","自从","自各儿","自后","自家","自己","自打","自身","至","至于","至今","至若","致","般的","若","若夫","若是","若果","若非","莫不然","莫如","莫若","虽","虽则","虽然","虽说","被","要","要不","要不是","要不然","要么","要是","譬喻","譬如","让","许多","论","设使","设或","设若","诚如","诚然","该","说","说来","请","诸","诸位","诸如","谁","谁人","谁料","谁知","贼死","赖以","赶","起","起见","趁","趁着","越是","距","跟","较","较之","边","过","还","还是","还有","还要","这","这一来","这个","这么","这么些","这么样","这么点儿","这些","这会儿","这儿","这就是说","这时","这样","这次","这般","这边","这里","进而","连","连同","逐步","通过","遵循","遵照","那","那个","那么","那么些","那么样","那些","那会儿","那儿","那时","那样","那般","那边","那里","都","鄙人","鉴于","针对","阿","除","除了","除外","除开","除此之外","除非","随","随后","随时","随着","难道说","零","非","非但","非徒","非特","非独","靠","顺","顺着","首先","︿","！","＃","＄","％","＆","（","）","＊","＋","，","０","１","２","３","４","５","６","７","８","９","：","；","＜","＞","？","＠","［","］","｛","｜","｝","～","￥"]
    additional_stopwords=['真的','感觉','一个','知道','现在','觉得','原来','没有','已经','不会','这种','看过','一下']
    chinese_stopwords.extend(additional_stopwords)

    if len(comment_df) < 10:
        notice_cache.append("评论数量过少，跳过TF-IDF计算。")
        tfidf_importance = [{'word': 'null', 'importance': 0}]
        word_cloud_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAoMBg2ogq8gAAAAASUVORK5CYII="# 或者一张空白图的base64，避免前端崩溃
        
        result={
        'comment_length': len(comment_df),#总评论数
        'matched_case_number': matched_case_number,#搜索结果数量
        'tfidf_importance':'null',#tfidf分析结果
        'word_cloud_image':word_cloud_image
        }
    else:
        def chinese_tokenizer(text):
            words = jieba.cut(text)
            return [word for word in words if word not in chinese_stopwords and len(word) > 1]

        vectorizer=TfidfVectorizer(tokenizer=chinese_tokenizer,
                            max_df=0.9,
                            min_df=3,
                            )

        X=vectorizer.fit_transform(corpus)
        tfidf_matrix=pd.DataFrame(X.toarray(),columns=vectorizer.get_feature_names_out())
        importance=(tfidf_matrix.sum(axis=0)).sort_values(ascending=False)
        importance_df = importance.reset_index()
        importance_df.rename(columns={'index': 'word','0':'importance'}, inplace=True)

        tfidf_importance = json.dumps(
        importance_df.to_dict(orient='records'),
        ensure_ascii=False,  # 保留中文
        indent=2             # 美化格式
        )
        print(tfidf_importance)

        def generate_wordcloud_base64_from_df(df, text_col='comment', font_path = os.path.join(os.path.dirname(__file__), 'simhei.ttf')):
     
            all_text = " ".join(df[text_col].astype(str).tolist())
    
    
            words = [word for word in jieba.cut(all_text)
             if word not in chinese_stopwords and len(word) > 1] 
            cut_text = " ".join(words)
            
            wc = WordCloud(
            font_path=font_path,
            background_color='white',
            width=800,
            height=600,
            max_words=200
            ).generate(cut_text)
    
            buffer = BytesIO()
            wc.to_image().save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
    
        word_cloud_image=generate_wordcloud_base64_from_df(comment_df)


        result={
        'comment_length': len(comment_df),#总评论数
        'matched_case_number': matched_case_number,#搜索结果数量
        'tfidf_importance':tfidf_importance,#tfidf分析结果
        'word_cloud_image':word_cloud_image
        }
    return jsonify(result)


@app.route('/anysearch', methods=['POST'])
def anysearch():
    data = request.json
    anykeyword=data.get('anykeyword')
    keyword=anykeyword
    comment_df['matched_comment']=comment_df['comment'].apply(
                                                        lambda x: bool(re.search(keyword, str(x))
                                                        ))
    print('搜索结果：')
    print()
    print(comment_df[comment_df['matched_comment'] == True])
    matched_comment_list=comment_df[comment_df['matched_comment'] == True]['comment'].tolist()
    matched_case_number_any=sum(comment_df['matched_comment'] == True)
    print(f'共搜索到{matched_case_number_any}个结果。')
    result_anysearch={
        'match_case_number_any':matched_case_number_any,
        'matched_comment_list':matched_comment_list #list
    }
    return jsonify(result_anysearch)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # 默认5000，本地运行用
    app.run(host='0.0.0.0', port=port)