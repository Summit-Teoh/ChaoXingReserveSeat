from utils import AES_Encrypt, enc, generate_captcha_key
import json
import requests
import re
import time
import logging
import datetime
from urllib3.exceptions import InsecureRequestWarning

#这个函数用于获取当前日期，或者根据 day_offset 获取相对于今天的某个日期。
# 返回格式为 YYYY-MM-DD
def get_date(day_offset: int=0):
    today = datetime.datetime.now().date()
    offset_day = today + datetime.timedelta(days=day_offset)
    tomorrow = offset_day.strftime("%Y-%m-%d")
    return tomorrow


class reserve:
    def __init__(self, sleep_time=0.2, max_attempt=50, enable_slider=False, reserve_next_day=False):
        self.login_page = "https://passport2.chaoxing.com/mlogin?loginType=1&newversion=true&fid="
        self.url = "https://office.chaoxing.com/front/third/apps/seat/code?id={}&seatNum={}"
        self.submit_url = "https://office.chaoxing.com/data/apps/seat/submit"
        self.seat_url = "https://office.chaoxing.com/data/apps/seat/getusedtimes"
        self.login_url = "https://passport2.chaoxing.com/fanyalogin"
        self.token = ""
        self.success_times = 0
        self.fail_dict = []
        self.submit_msg = []
        self.requests = requests.session()
        self.token_pattern = re.compile("token = '(.*?)'")
        self.headers = {
            "Referer": "https://office.chaoxing.com/",
            "Host": "captcha.chaoxing.com",
                        "Pragma" : 'no-cache',
            "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile':'?0',
            'Sec-Ch-Ua-Platform':'"Linux"',
            'Sec-Fetch-Dest':'document',
            'Sec-Fetch-Mode':'navigate',
            'Sec-Fetch-Site':'none',
            'Sec-Fetch-User':'?1',
            'Upgrade-Insecure-Requests':'1',
            'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }
        self.login_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 10_3_1 like Mac OS X) AppleWebKit/603.1.3 (KHTML, like Gecko) Version/10.0 Mobile/14E304 Safari/602.1 wechatdevtools/1.05.2109131 MicroMessenger/8.0.5 Language/zh_CN webview/16364215743155638",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Host": "passport2.chaoxing.com"
        }

        self.sleep_time = sleep_time
        self.max_attempt = max_attempt
        self.enable_slider = enable_slider
        self.reserve_next_day = reserve_next_day
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    
    # login and page token
    def _get_page_token(self, url):
        response = self.requests.get(url=url, verify=False)
        html = response.content.decode('utf-8')
        token = re.findall(
            'token: \'(.*?)\'', html)[0] if len(re.findall('token: \'(.*?)\'', html)) > 0 else ""
        return token

    def get_login_status(self):
        self.requests.headers = self.login_headers
        self.requests.get(url=self.login_page, verify=False)

    def login(self, username, password):
        username = AES_Encrypt(username)
        password = AES_Encrypt(password)
        parm = {
            "fid": -1,
            "uname": username,
            "password": password,
            "refer": "http%3A%2F%2Foffice.chaoxing.com%2Ffront%2Fthird%2Fapps%2Fseat%2Fcode%3Fid%3D4219%26seatNum%3D380",
            "t": True
        }
        jsons = self.requests.post(
            url=self.login_url, params=parm, verify=False)
        obj = jsons.json()
        if obj['status']:#status状态可为true或false
            logging.info(f"User {username} login successfully")
            return (True, '')
        else:
            logging.info(f"User {username} login failed. Please check you password and username! ")
            return (False, obj['msg2'])

    # extra: get roomid
    def roomid(self, encode):
        url = f"https://office.chaoxing.com/data/apps/seat/room/list?cpage=1&pageSize=100&firstLevelName=&secondLevelName=&thirdLevelName=&deptIdEnc={encode}"
        json_data = self.requests.get(url=url).content.decode('utf-8')
        ori_data = json.loads(json_data)
        for i in ori_data["data"]["seatRoomList"]:
            info = f'{i["firstLevelName"]}-{i["secondLevelName"]}-{i["thirdLevelName"]} id为：{i["id"]}'
            print(info)

    # solve captcha 处理验证码部分

    def resolve_captcha(self):
        logging.info(f"Start to resolve captcha token")
        captcha_token, bg, tp = self.get_slide_captcha_data()
        logging.info(f"Successfully get prepared captcha_token {captcha_token}")
        logging.info(f"Captcha Image URL-small {tp}, URL-big {bg}")
        x = self.x_distance(bg, tp)
        logging.info(f"Successfully calculate the captcha distance {x}")

        params = {
            "callback": "jQuery33109180509737430778_1716381333117",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "slide",
            "token": captcha_token,
            "textClickArr": json.dumps([{"x": x}]),
            "coordinate": json.dumps([]),
            "runEnv": "10",
            "version": "1.1.18",
            "_": int(time.time() * 1000)
        }
        response = self.requests.get(
            f'https://captcha.chaoxing.com/captcha/check/verification/result', params=params, headers=self.headers)
        text = response.text.replace('jQuery33109180509737430778_1716381333117(', "").replace(')', "")
        data = json.loads(text)
        logging.info(f"Successfully resolve the captcha token {data}")
        try: 
           validate_val = json.loads(data["extraData"])['validate']
           return validate_val
        except KeyError as e:
            logging.info("Can't load validate value. Maybe server return mistake.")
            return ""

    def get_slide_captcha_data(self):
        url = "https://captcha.chaoxing.com/captcha/get/verification/image"
        timestamp = int(time.time() * 1000)
        capture_key, token = generate_captcha_key(timestamp)
        referer = f"https://office.chaoxing.com/front/third/apps/seat/code?id=3993&seatNum=0199"
        params = {
            "callback": f"jQuery33107685004390294206_1716461324846",
            "captchaId": "42sxgHoTPTKbt0uZxPJ7ssOvtXr3ZgZ1",
            "type": "slide",
            "version": "1.1.18",
            "captchaKey": capture_key,
            "token": token,
            "referer": referer,
            "_": timestamp,
            "d": "a",
            "b": "a"
        }
        response = self.requests.get(url=url, params=params, headers=self.headers)
        content = response.text
        
        data = content.replace("jQuery33107685004390294206_1716461324846(",
                            ")").replace(")", "")
        data = json.loads(data)
        captcha_token = data["token"]
        bg = data["imageVerificationVo"]["shadeImage"]
        tp = data["imageVerificationVo"]["cutoutImage"]
        return captcha_token, bg, tp
    
    def x_distance(self, bg, tp):
        import numpy as np
        import cv2
        def cut_slide(slide):
            slider_array = np.frombuffer(slide, np.uint8)
            slider_image = cv2.imdecode(slider_array, cv2.IMREAD_UNCHANGED)
            slider_part = slider_image[:, :, :3]
            mask = slider_image[:, :, 3]
            mask[mask != 0] = 255
            x, y, w, h = cv2.boundingRect(mask)
            cropped_image = slider_part[y:y + h, x:x + w]
            return cropped_image
        c_captcha_headers = {
            "Referer": "https://office.chaoxing.com/",
            "Host": "captcha-c.chaoxing.com",
            "Pragma" : 'no-cache',
            "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile':'?0',
            'Sec-Ch-Ua-Platform':'"Linux"',
            'Sec-Fetch-Dest':'document',
            'Sec-Fetch-Mode':'navigate',
            'Sec-Fetch-Site':'none',
            'Sec-Fetch-User':'?1',
            'Upgrade-Insecure-Requests':'1',
            'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }
        bgc, tpc = self.requests.get(bg, headers=c_captcha_headers), self.requests.get(tp, headers=c_captcha_headers)
        bg, tp = bgc.content, tpc.content 
        bg_img = cv2.imdecode(np.frombuffer(bg, np.uint8), cv2.IMREAD_COLOR)  
        tp_img = cut_slide(tp)
        bg_edge = cv2.Canny(bg_img, 100, 200)
        tp_edge = cv2.Canny(tp_img, 100, 200)
        bg_pic = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)
        tp_pic = cv2.cvtColor(tp_edge, cv2.COLOR_GRAY2RGB)
        res = cv2.matchTemplate(bg_pic, tp_pic, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)  
        tl = max_loc
        return tl[0]

 #submit 方法负责执行预约流程。它在尝试预约之前会获取页面 token，
 # 并根据需要解决验证码。然后使用 get_submit 提交预约请求。新的的时间段预约要求新的submit请求（每次请求的token不同）
    def submit(self, times, roomid, seatid, action):
        for seat in seatid:
            suc = False
            while not suc and self.max_attempt > 0:
                for time_slot in [(times[0], times[1]), (times[1], times[2]), (times[2], times[3])]:
                    token = self._get_page_token(self.url.format(roomid, seat))
                    logging.info(f"Get token: {token}")
                    captcha = self.resolve_captcha() if self.enable_slider else ""
                    logging.info(f"Captcha token {captcha}")
                    suc = self.get_submit(self.submit_url, time_slot, token, roomid, seat, captcha, action)
                   
                    time.sleep(self.sleep_time)
                    self.max_attempt -= 1
            return False

    def get_submit(self, url, time_slot, token, roomid, seatid, captcha="", action=False):
        delta_day = 1 if self.reserve_next_day else 0
        day = datetime.date.today() + datetime.timedelta(days=0+delta_day)  # 预约今天，修改days=1表示预约明天
        if action:
            day = datetime.date.today() + datetime.timedelta(days=1+delta_day)  # 由于action时区问题导致其早+8区一天
        parm = {
            "roomId": roomid,
            "startTime": time_slot[0],
            "endTime": time_slot[1],
            "day": str(day),
            "seatNum": seatid,
            "captcha": captcha,
            "token": token
        }
        logging.info(f"submit parameter {parm} ")
        parm["enc"] = enc(parm)
        html = self.requests.post(
            url=url, params=parm, verify=True).content.decode('utf-8')
        self.submit_msg.append(
            time_slot[0] + "~" + time_slot[1] + ':  ' + str(json.loads(html)))
        logging.info(json.loads(html))
        return json.loads(html)["success"]
    

    def sign_in(self):
        day = datetime.date.today().strftime("%Y-%m-%d")
        sign_data = self.get_my_seat_id(day)    #sign_date得到是前面得到的json字典（当日预约记录）
        need_sign_data = []
        for index in sign_data:
            if index['status'] == 1:
                print("[exist]今日已签: {}".format(
                    index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index['seatNum']))
            if index['status'] == 0 or index['status'] == 3 or index['status'] == 5:
                need_sign_data.append(index)
                continue
        if need_sign_data:
            for need_sign in need_sign_data:
                response = self.requests.get(
                    url='https://office.chaoxing.com/data/apps/seat/sign?id={}'.format(need_sign["id"]))
                location = need_sign['firstLevelName'] + need_sign['secondLevelName'] + need_sign['thirdLevelName'] + \
                           need_sign['seatNum']
                if response.json()['success']:
                    print("[true]成功签到: {}".format(location))
                else:
                    print("[false]签到失败: {}\n反馈信息: {}".format(location, response.json()['msg']))
        else:
            print("[none]今日没有需要签到的数据")
    

    def get_my_seat_id(self, current_date):
        response = self.requests.get(url='https://office.chaoxing.com/data/apps/seat/reservelist?'
                                         'indexId=0&'
                                         'pageSize=100&'
                                         'type=-1').json()['data']['reserveList']   #这里的url是查询座位记录，此处的type用于查询预约类型
        result = []
        for index in response:
            if index['type'] == -1:                         #type值为‘-1’表示未违约
                if index['today'] == current_date:
                    # 今日签到信息
                    result.append(index)           #传这个字典的核心目的是为了拿到里面的id，签到要携带此字段
        return result                              #id是从预约记录里面拿的，即签到不需要桌位号（拓展性想法：这个ID是本地生成的还是客户端传过来的）
    
 #----------------------------------------------------------------------------------------------------------
    #不同的type值代表不同的违约类型 ，status表示不同的状态
        
    #  status:          0 '待履约'                              type:      1 : 使用完毕未退座 
    #                   1:'学习中'                                         0 : 未在规定时间内签到
    #                   2:'已履约'                                         5 : 被监督后，未在规定时间内落座
    #                   3:'暂离中'                                         3 : 暂离后未在规定时间内返回
    #                   5:'被监督中'
    #                   7:'已取消'
 #-----------------------------------------------------------------------------------------------------------
    def signback_(self):
        day = datetime.date.today().strftime("%Y-%m-%d")
        info = self.get_my_seat_id(day)
        for index in info:
            if index['status'] == 1 or index['status'] == 3 or index['status'] == 5:
                location = index['firstLevelName'] + index['secondLevelName'] + index['thirdLevelName'] + index[
                    'seatNum']
                response = self.requests.get(
                    url='https://office.chaoxing.com/data/apps/seat/signback?id={}'.format(index['id']))
                if response.json()['success']:
                    return "{}：座位已退出".format(location)
                return "{}：{}".format(location, response.json()['msg'])
        return "当前没有座位可退"
