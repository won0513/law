from flask import Blueprint, render_template, url_for, request, session, g
import json
import pandas as pd
from modules import str_to_vector, return_answer
bp = Blueprint('main', __name__, url_prefix='/')


df = pd.read_csv('파일위치/pan_qna_kkm_sbert.csv')
print(df.head())
df['emd'] = df.apply(lambda x: str_to_vector(x['embedding']), axis=1)


@bp.route('/recommand', methods=['POST'])
def recommand():
    query = request.form['input']
    print(query)
    result = return_answer(query, df)
    data = {'pan_list':result}
    return json.dumps(data, ensure_ascii=False)
