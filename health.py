import requests
import hashlib
import yagmail
import yaml
import json
import time
from urllib.parse import urlencode
import random


def Login(headers, username, password):
    login_url = 'https://gw.wozaixiaoyuan.com/basicinfo/mobile/login/username'
    params = {
        'username': username,
        'password': password
    }
    login_req = requests.post(login_url, params=params, headers=headers)
    text = json.loads(login_req.text)
    if text['code'] == 0:
        print(f"{username}账号登陆成功！")
        jws = login_req.headers['JWSESSION']
        return jws
    else:
        print(f"{username}登陆失败，请检查账号密码！")
        return False


def ReadConfigData():
    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load_all(f.read())
            return config
    except Exception as e:
        print("读取错误", e)
        exit(0)


def GetMailConfig(config):
    mail = yagmail.SMTP(config['mail'], config['password'], config['host'])
    return mail


def GetJWData():
    try:
        with open('jws.txt', 'r') as f:
            jws_data = json.loads(f.read().replace("'", '"'))
            print("读取现存jws文件成功！")
            return jws_data
    except FileNotFoundError:
        print("jws文件不存在，正在创建！")
        return {}
    except Exception as e:
        print("未知错误", e)
        exit(0)


def GetEach(config, data, headers):
    try:
        return data[config['username']]
    except:
        print(config['username'], "尝试登陆！")
        login = Login(headers, config['username'], config['password'])
        if login is False:
            mail.send(config['receive'], '登陆失败', '登陆失败，请检查账号密码')
            return False
        data[str(config['username'])] = login
        return login


def testLoginStatus(headers, jws):
    # 用任意需要鉴权的接口即可，这里随便选了一个
    url = "https://student.wozaixiaoyuan.com/heat/getTodayHeatList.json"
    headers['Host'] = "student.wozaixiaoyuan.com"
    headers['JWSESSION'] = jws
    res = requests.post(url, headers=headers)
    text = json.loads(res.text)
    if text['code'] == 0:
        return True
    elif text['code'] == -10:
        return False
    else:
        return 0


def GetSeq():
    hour = int(time.localtime(time.time()).tm_hour)
    if hour < 12 and hour > 7:
        return 1
    elif hour >= 12 and hour < 22:
        return 2
    else:
        return 3


def GetRandonTemp():
    A = 36.5
    B = 37
    a = random.uniform(A, B)
    C = 1
    return round(a, C)


def Punch(headers, jws, address, health, *heat):
    cur_time = int(round(time.time()*1000))
    heat_url = 'https://student.wozaixiaoyuan.com/heat/save.json'
    health_url = 'https://student.wozaixiaoyuan.com/health/save.json'
    headers['JWSESSION'] = jws
    headers["Host"] = "student.wozaixiaoyuan.com"
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    sign_data = {
        'answers': '["0"]',
        'seq': GetSeq(),
        'temperature': GetRandonTemp(),
        'latitude': '24.856392957899306',
        'longitude': '102.85788872612848',
        'country': '中国',
        'city': '昆明市',
        'district': '呈贡区',
        'province': '云南省',
        'township': '吴家营街道',
        'street': '樱花大道',
        'myArea': '呈贡校区怡园',
        'areacode': '530114',  # 似乎是该地区身份证前六位
        'towncode': '530114005',
        'citycode': '156530100',
        'timestampHeader': cur_time,
        'signatureHeader': hashlib.sha256(
            '云南省_{cur_time}_昆明市'.encode('utf-8')
        ).hexdigest()
    }
    if address == '憬园':
        sign_data['myArea'] = '呈贡校区憬园'
        sign_data['latitude'] = '24.849622'
        sign_data['longitude'] = '102.860621'
    elif address == '恒园':
        sign_data['myArea'] = '呈贡校区憬园'
        sign_data['latitude'] = '24.846489'
        sign_data['longitude'] = '102.855935'
    elif address == '恬园':
        sign_data['myArea'] = '呈贡校区恬园'
        sign_data['latitude'] = '24.844536'
        sign_data['longitude'] = '102.863238'
    data = urlencode(sign_data)
    if heat[0][GetSeq() - 1] == 1:
        heat_req = requests.post(heat_url, data=data,
                                 headers=headers)
        heat_text = json.loads(heat_req.text)
    if health == 1 and GetSeq() == 1:
        sign_data.pop('seq')
        data = urlencode(sign_data)
        health_req = requests.post(
            health_url, data=data, headers=headers)
        health_text = json.loads(health_req.text)
    if heat_text:
        return heat_text
    if health_text:
        return health_text


def main(config, data):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 7.1.2; TEL-AN10 Build/N6F26Q; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/81.0.4044.117 Mobile Safari/537.36 MicroMessenger/8.0.25.2200(0x28001937) WeChat/arm64 Weixin NetType/WIFI Language/zh_CN ABI/arm64 MiniProgramEnv/android'
    }
    jws = GetEach(config, data, headers)
    if jws:
        login_code = testLoginStatus(headers, jws)
    else:
        return
    if login_code is False:
        print(config['username'], "jws失效！")
        jws = Login(headers, config['username'], config['password'])
        if jws is False:
            return False
        print("jws文件更新成功")
        data[config['username']] = jws
    try:
        punch_code = Punch(
            headers, jws, config['address'], config['health'], config['daily'])
        if punch_code['code'] == 0:
            mail.send(config['receive'], '打卡成功', '打卡成功')
            print("打卡成功！")
            return True
        else:
            mail.send(config['receive'], '打卡失败', punch_code['message'])
            print("打卡失败！", punch_code['message'])
            return False
    except Exception as e:
        print("无需打卡！", e)


if __name__ == '__main__':
    configs = ReadConfigData()
    mail = GetMailConfig(next(configs))
    jws_data = GetJWData()
    for config in configs:
        main(config, jws_data)
    with open('jws.txt', 'w') as f:
        f.write(str(jws_data))
