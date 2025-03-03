import requests, json,os
from dotenv import load_dotenv
load_dotenv()
Channel_access_token=os.environ['Channel_access_token']
Channel_secret=os.environ['Channel_secret']
group_id='C4710e536d71bd32489cfe9e3a6716550'
# headers = {'Authorization':'Bearer access token','Content-Type':'application/json'}
# body = {
#     'replyToken':replyToken,
#     'messages':[{
#             'type': 'text',
#             'text': 'hello'
#         }]
# }
# req = requests.request('POST', 'https://api.line.me/v2/bot/message/reply', headers=headers,data=json.dumps(body).encode('utf-8'))
# print(req.text)

push_url='https://api.line.me/v2/bot/message/push'
home = os.path.expanduser('~')
image_path = os.path.join(home, 'aaa.png')
image = open(image_path, 'rb')
opened_files=[]
opened_files.append(image)
defaultImg="data:image/png;base64,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"

headers = {'Authorization':f'Bearer {Channel_access_token}','Content-Type':'application/json'}
body = {
    'to':group_id,
    'messages':[{
            'type': 'text',
            'text': 'hello'
        },{
          "type": "sticker",
          "packageId": "446",
          "stickerId": "1988"
        },
        {
            "type": "image",
            "originalContentUrl": "https://www.decade.tw/wp-content/uploads/2021/09/DECADE_new.png",
            "previewImageUrl": "https://www.decade.tw/wp-content/uploads/2021/09/DECADE_new.png"
        }
    ]
    }

if len(opened_files) > 0:
    for img in opened_files:
        img.seek(0)
        imagefile = {'imageFile': img}
        # result = requests.post(push_url, headers=headers, data=json.dumps(body).encode('utf-8'), files=imagefile)
        # result = requests.request('POST', push_url, headers=headers, data=json.dumps(body).encode('utf-8'), files=imagefile)
        result = requests.request('POST', push_url, headers=headers, data=json.dumps(body).encode('utf-8'))
        print(result.text)

# req = requests.request('POST', push_url,headers=headers,data=json.dumps(body).encode('utf-8'))
# print(req.text)

# type='message'
# source=UserSource(type='user', user_id='U257d96c8f1349d285c473527d958d669')
# timestamp=1740978401141
# mode=<EventMode.ACTIVE: 'active'>
# webhook_event_id='01JND6CCBH614TSC7XG5PSV4JG'
# delivery_context=DeliveryContext(is_redelivery=False)
# reply_token='9ade8b81a70e457a8ba63090ba59c7eb'
# message=TextMessageContent(
#     type='text',
#     id='550539472832299233',
#     text='f',
#     emojis=None,
#     mention=None,
#     quote_token='xvnXciyeSjAtLYz8-WI-IJLZvUqFq7Ui5GfVN6bdYrruVpJpPOM8wEgyejnYxJd3yYhPK-J8l0RgI4ewN2rgopJABVcg1keXfQWhxCHXLSb9kpVpPwqhQ7SiQcaVLYHU91vvo2EqWw_Zpbi3KP1t1g',
#     quoted_message_id=None)


# OFF-LIGHT
# type='message'
# source=GroupSource(type='group',
#                    group_id='C4710e536d71bd32489cfe9e3a6716550',
#                    user_id='U257d96c8f1349d285c473527d958d669')
# timestamp=1740979810907 mode=<EventMode.ACTIVE: 'active'>
# webhook_event_id='01JND7QD2M6VEHPJ4CZFSHN51W'
# delivery_context=DeliveryContext(is_redelivery=False)
# reply_token='97c4693b0a72407ca99efb61e19930b0'
# message=TextMessageContent(type='text',
#                            id='550541838017888737',
#                            text='OFF-LIGHT',
#                            emojis=None, mention=None,
#                            quote_token='tf87CYSKmolXURih2kCHR24p1VrWplkd6NJDxz2Q3LHu1hObBpa8CX4V9HHIkaQcex8DXku9AbLsavUEZ4Tfs5FXLZ1vbk-zqrVuConyouJZRT8CQFPzwxg8-5y4RiZL6FgqLucJdZ7T6Vxe9IZUOA', quoted_message_id=None)