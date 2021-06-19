import os
from flask import Flask
from flask import request
from flaskext.mysql import MySQL
from random import shuffle
import logging
import json

app = Flask(__name__)

app.logger.setLevel(logging.INFO)

mysql = MySQL()
# TODO Remove this
app.config['MYSQL_DATABASE_USER'] = 'pASQrpqoMf'
app.config['MYSQL_DATABASE_PASSWORD'] = 'wV7XAntpAS'
app.config['MYSQL_DATABASE_DB'] = 'pASQrpqoMf'
app.config['MYSQL_DATABASE_HOST'] = 'remotemysql.com'
mysql.init_app(app)


@app.route('/first/')
def first():
    conn = mysql.connect()
    cursor = conn.cursor()
    query_string = '''select id,total,rankvv,round(10*(cnt-rankvv+1)/cnt,0) as decile from   
    (SELECT  id,total,@currankvv := @currankvv + 1 AS rankvv
    FROM      (select id,sum(karma) as total from `question` group by id)
    p, (SELECT @currankvv := 0) r
    ORDER BY  total desc ) as dt,(select count(distinct id) as cnt from
    `question`) as ct where rankvv = 85 '''
    cursor.execute(query_string, )
    rv = cursor.fetchone()
    result = rv[0]
    conn.close()
    return str(result)


@app.route('/question/<question_id>')
def question(question_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    query_string = "SELECT * FROM question WHERE id = %s"
    cursor.execute(query_string, (question_id,))
    row_headers = [x[0] for x in cursor.description]
    rv = cursor.fetchone()
    json_data = [dict(zip(row_headers, rv))]
    conn.close()
    return json.dumps(json_data[0])


@app.route('/send/', methods=['POST'])
def send():
    json_from_user = request.json
    question_id = json_from_user['id']
    user_answer = json_from_user['answer']
    cursor, question_from_db = get_question(question_id)
    real_answer = question_from_db[4]
    karma = question_from_db[5]
    cursor.close()

    next_question_id = update_karma(real_answer, user_answer, question_id, karma)

    return get_question_json(next_question_id)


def get_question(id_from_front):
    conn = mysql.connect()
    cursor = conn.cursor()
    query = "SELECT * FROM question WHERE id = %s"
    cursor.execute(query, (id_from_front,))
    record = cursor.fetchone()
    conn.close()
    return cursor, record


def update_karma(real_answer, user_answer, question_id, karma):
    real_answer = handle_multiple_answers(user_answer, real_answer)
    if user_answer == real_answer:
        result_id = get_next_question_id_by_decile(get_decile(question_id), bool(0))
        update_question_karma(question_id, karma + 1)
        return str(result_id)
    else:
        result_id = get_next_question_id_by_decile(get_decile(question_id), bool(1))
        update_question_karma(question_id, karma - 1)
        return str(result_id)


def handle_multiple_answers(user_answer, real_answer):
    answers = real_answer.split("-")
    if user_answer in answers:
        return user_answer
    else:
        return real_answer


def update_question_karma(id_from_db, karma):
    conn = mysql.connect()
    cursor = conn.cursor()
    sql = "UPDATE question SET karma = %s WHERE id = %s"
    cursor.execute(sql, (karma, id_from_db,))
    conn.commit()
    conn.close()


def get_next_question_id_by_decile(_decile, is_plus):
    conn = mysql.connect()
    cursor = conn.cursor()
    query_string = '''SELECT id
                FROM 
                ( select id,total,rankvv,round(10*(cnt-rankvv+1)/cnt,0) as decile from   
               (SELECT  id,total,@currankvv := @currankvv + 1 AS rankvv
               FROM      (select id,sum(karma) as total from `question` group by id)
               p, (SELECT @currankvv := 0) r
               ORDER BY  total desc ) as dt,(select count(distinct id) as cnt from
               `question`) as ct ) sub where sub.decile = %s '''
    cursor.execute(query_string, (plus_or_minus(_decile, is_plus),))
    rv = list(cursor.fetchall())
    shuffle(rv)
    result_id = rv[0]
    conn.close()
    return str(result_id)


def plus_or_minus(_decile, is_plus):
    if is_plus:
        if _decile == 10:
            return 10
        else:
            return _decile + 1
    else:
        if _decile == 0:
            return 0
        else:
            return _decile - 1


def get_question_json(next_question_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    next_question_id = next_question_id.replace('(', '').replace(')', '').replace(',', '')
    query_string = "SELECT * FROM question WHERE id = %s "
    cursor.execute(query_string, (next_question_id,))
    row_headers = [x[0] for x in cursor.description]
    rv = cursor.fetchone()
    json_data = [dict(zip(row_headers, rv))]
    conn.close()
    return json.dumps(json_data[0])


@app.route('/decile/<question_id>')
def decile(question_id):
    return str(get_decile(question_id))


def get_decile(question_id):
    conn = mysql.connect()
    cursor = conn.cursor()
    query_string = '''select id,total,rankvv,round(10*(cnt-rankvv+1)/cnt,0) as decile from   
    (SELECT  id,total,@currankvv := @currankvv + 1 AS rankvv
    FROM      (select id,sum(karma) as total from `question` group by id)
    p, (SELECT @currankvv := 0) r
    ORDER BY  total desc ) as dt,(select count(distinct id) as cnt from
    `question`) as ct where id = %s '''
    cursor.execute(query_string, (question_id,))
    rv = cursor.fetchone()
    result = rv[3]
    conn.close()
    print(result)
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
