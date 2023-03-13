from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage
import requests
import json
import time
import pygsheets
import time
import os

access_token=os.getenv("access_token")
channel_secret=os.getenv("channel_secret")
sheet_url=os.getenv("sheet_url")
sheet_json_path = 'sheet_key_json.json'


def chatbot(request):
    body = request.get_data(as_text=True)
    json_data = json.loads(body)
    try:
        line_bot_api = LineBotApi(access_token)
        handler = WebhookHandler(channel_secret)
        signature = request.headers['X-Line-Signature']
        handler.handle(body, signature)
        col_conf = {
            "id": "A",
            "name": "B",
            "update_time": "C",
            "openai_key": "D",
            "content": "E",
        }

        localtime = time.localtime()
        now_time = time.strftime("%Y-%m-%d %I:%M:%S %p", localtime)

        tk = json_data['events'][0]['replyToken']
        line_msg = json_data['events'][0]['message']['text']
        user_id = json_data['events'][0]['source']['userId']
        user_profile = line_bot_api.get_profile(user_id)
        user_name = user_profile.display_name

        gc = pygsheets.authorize(service_file=sheet_json_path)
        sht = gc.open_by_url(sheet_url)
        wks_list = sht.worksheets()
        wks = wks_list[0]

        line_no = get_user_line_no(wks, user_id)

        if (line_no == 0):
            max_line = get_sheet_max_line(wks)
            line_no = str(max_line+1)
            wks.update_value(col_conf['id']+line_no, user_id)
            wks.update_value(col_conf['name']+line_no, user_name)
            wks.update_value(col_conf['update_time']+line_no, now_time)
            wks.update_value(col_conf['content']+line_no, 'set')
            wks.update_value(col_conf['update_time']+line_no, now_time)
            text_message = TextSendMessage(text='請輸入open ai提供的API key')
            line_bot_api.reply_message(tk, text_message)
        else:
            line_no = str(line_no)
            if(line_msg.lower() == 'set'):
                wks.update_value(col_conf['content']+line_no, 'set')
                wks.update_value(col_conf['update_time']+str(line_no), now_time)
                text_message = TextSendMessage(text='請輸入open ai提供的API key')
                line_bot_api.reply_message(tk, text_message)
            elif (line_msg.lower() == 'reset'):
                wks.update_value(col_conf['content']+line_no, '')
                wks.update_value(col_conf['update_time']+str(line_no), now_time)
                text_message = TextSendMessage(text='我是誰...？我在哪..?請問有什麼事嗎?')
                line_bot_api.reply_message(tk, text_message)
            else:
                openai_key = wks.cell(col_conf['openai_key']+line_no)
                openai_key = openai_key.value
                history_cell = wks.cell(col_conf['content']+line_no)
                chat_history_json = history_cell.value
                if(history_cell.value=='set'):
                    chat_history_list = [{"role": "user", "content": '你是誰？用最簡短的方式說明'}]
                    response = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {line_msg}'
                        },
                        json={
                            'model': 'gpt-3.5-turbo',
                            'messages': chat_history_list
                        })
                    response_json = response.json()
                    result = True
                    try:
                        response_msg = response_json['choices'][0]['message']['content']
                    except:
                        result = False
                    if(result==True):
                        wks.update_value(col_conf['content']+line_no, '')
                        wks.update_value(col_conf['openai_key']+line_no, line_msg)
                        wks.update_value(col_conf['update_time']+str(line_no), now_time)
                        text_message = TextSendMessage(text='設定成功')
                        line_bot_api.reply_message(tk, text_message)
                    else:
                        wks.update_value(col_conf['update_time']+str(line_no), now_time)
                        text_message = TextSendMessage(text='不正確的API key')
                        line_bot_api.reply_message(tk, text_message)
                else:
                    try:
                        chat_history_list = json.loads(chat_history_json)
                    except:
                        chat_history_list = []
                        pass
                    chat_history_list.append({"role": "user", "content": line_msg})

                    response = requests.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {openai_key}'
                        },
                        json={
                            'model': 'gpt-3.5-turbo',  # 一定要用chat可以用的模型
                            'messages': chat_history_list
                        })
                    response_json = response.json()
                    chat_history_list.append(response_json['choices'][0]['message'])
                    response_msg = response_json['choices'][0]['message']['content']
                    chat_history_json = json.dumps(chat_history_list)
                    wks.update_value(col_conf['content']+line_no, chat_history_json)
                    wks.update_value(col_conf['update_time']+str(line_no), now_time)
                    reply_msg = response_msg.strip("\n")
                    text_message = TextSendMessage(text=reply_msg)    # 設定回傳同樣的訊息
                    line_bot_api.reply_message(tk, text_message)       # 回傳訊息

    except:
        print('error')


def get_sheet_max_line(wks):
    row_list = wks.get_all_values()
    n = 0
    for row_val in row_list:
        if (row_val[0] == ''):
            break
        n = n+1
    return n


def get_user_line_no(wks, id):
    cell_list = wks.find(id)
    line = 0
    for cell in cell_list:
        if (cell.col == 1):
            line = cell.row
    return line
