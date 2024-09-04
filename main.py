import json
import time
import argparse
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

#如果在GitHub Actions上运行的话，需要将时区调整到UTC时间（相当于在获取的本地时间上加八小时）
from utils import reserve, get_user_credentials  #判断时间和星期
get_current_time = lambda action: time.strftime("%H:%M:%S", time.localtime(time.time() + 8*3600)) if action else time.strftime("%H:%M:%S", time.localtime(time.time()))
get_current_dayofweek = lambda action: time.strftime("%A", time.localtime(time.time() + 8*3600)) if action else time.strftime("%A", time.localtime(time.time()))


SLEEPTIME = 1 # 每次抢座的间隔
ENDTIME = "21:40:30" # 根据学校的预约座位时间+1min即可,截止时间，系统时间小于此时间就一直执行

ENABLE_SLIDER = False # 是否有滑块验证
MAX_ATTEMPT = 3 # 最大尝试次数
RESERVE_NEXT_DAY = False # 预约明天而不是今天的 



def login_and_reserve(users, usernames, passwords, action, success_list=None):
    logging.info(f"Global settings: \nSLEEPTIME: {SLEEPTIME}\nENDTIME: {ENDTIME}\nENABLE_SLIDER: {ENABLE_SLIDER}\nRESERVE_NEXT_DAY: {RESERVE_NEXT_DAY}")
    if action and len(usernames.split(",")) != len(users):
        raise Exception("user number should match the number of config")
    if success_list is None:
        success_list = [False] * len(users)
    current_dayofweek = get_current_dayofweek(action)
    for index, user in enumerate(users):
        username, password, times, roomid, seatid, daysofweek = user.values()
        if action:
            username, password = usernames.split(',')[index], passwords.split(',')[index]
        if(current_dayofweek not in daysofweek):
            logging.info("Today not set to reserve")
            continue
        if not success_list[index]: 
            logging.info(f"----------- {username} -- {times} -- {seatid} try -----------")
            s = reserve(sleep_time=SLEEPTIME, max_attempt=MAX_ATTEMPT, enable_slider=ENABLE_SLIDER, reserve_next_day=RESERVE_NEXT_DAY)
            s.get_login_status()
            s.login(username, password)
            s.requests.headers.update({'Host': 'office.chaoxing.com'})
            suc = s.submit(times, roomid, seatid, action)
            success_list[index] = suc
    return success_list


def main(users, action=False):
    current_time = get_current_time(action)  #根据action参数获取时间（当前时间或是加8h）
    logging.info(f"start time {current_time}, action {'on' if action else 'off'}")
    attempt_times = 0
    usernames, passwords = None, None
    if action:
        usernames, passwords = get_user_credentials(action)     #获取用户名密码的方式
    success_list = None
    current_dayofweek = get_current_dayofweek(action)
    today_reservation_num = sum( 1 
                                for user in users
                                       if current_dayofweek in user.get('daysofweek')) #大佬的代码好难，简单来说today_reservation_num用于统计当天有多少人需要预约
                                        
    while current_time < ENDTIME:
        attempt_times += 1      
        success_list = login_and_reserve(users, usernames, passwords, action, success_list)
        print(f"attempt time {attempt_times}, time now {current_time}, success list {success_list}")
        current_time = get_current_time(action)
        if sum(success_list) == today_reservation_num:
            print(f"reserved successfully!")
            return


def debug(users, action=False):
    logging.info(f"Global settings: \nSLEEPTIME: {SLEEPTIME}\nENDTIME: {ENDTIME}\nENABLE_SLIDER: {ENABLE_SLIDER}\nRESERVE_NEXT_DAY: {RESERVE_NEXT_DAY}")
    suc = False
    logging.info(f" Debug Mode start! , action {'on' if action else 'off'}")
    if action:
        usernames, passwords = get_user_credentials(action)
    current_dayofweek = get_current_dayofweek(action)
    for index, user in enumerate(users):
        username, password, times, roomid, seatid, daysofweek = user.values()
        if type(seatid) == str:
            seatid = [seatid]
        if action:
            username ,password = usernames.split(',')[index], passwords.split(',')[index]  #读取多个用户名和密码，如果有的话,index为索引
        if(current_dayofweek not in daysofweek):
            logging.info("Today not set to reserve")
            continue
        logging.info(f"----------- {username} -- {times} -- {seatid} try -----------")
        s = reserve(sleep_time=SLEEPTIME,  max_attempt=MAX_ATTEMPT, enable_slider=ENABLE_SLIDER, reserve_next_day=RESERVE_NEXT_DAY)
        s.get_login_status()
        s.login(username, password)
        s.requests.headers.update({'Host': 'office.chaoxing.com'})
        suc = s.submit(times, roomid, seatid, action)
        if suc:
            return


def sign(users, action=False):
    logging.info(f" Sign Mode start! , action {'on' if action else 'off'}")
    if action:
        usernames, passwords = get_user_credentials(action)
    suc = False
    for index, user in enumerate(users):
        username, password, times, roomid, seatid, daysofweek = user.values()
        if type(seatid) == str:
            seatid = [seatid]
        if action:
            username ,password = usernames.split(',')[index], passwords.split(',')[index]  #读取多个用户名和密码，如果有的话,index为索引

        s = reserve()               #创建 reserve 类的一个新实例 s
        s.get_login_status()        #访问登录页面，但是没有从登录页面拿任何的数据，难道是提交post请求前一定要访问一下登录页？
        s.login(username, password) #提交登录的post请求 
        s.requests.headers.update({'Host': 'office.chaoxing.com'})  #更新host到预约座位系统
        s.sign_in()         # 签到今日座位
      

def signback(users, action=False):
    logging.info(f" Signback Mode start! , action {'on' if action else 'off'}")
    if action:
        usernames, passwords = get_user_credentials(action)
    suc = False
    for index, user in enumerate(users):
        username, password, times, roomid, seatid, daysofweek = user.values()
        if type(seatid) == str:
            seatid = [seatid]
        if action:
            username ,password = usernames.split(',')[index], passwords.split(',')[index]  #读取多个用户名和密码，如果有的话,index为索引

        s = reserve()               #创建 reserve 类的一个新实例 s
        s.get_login_status()        #访问登录页面，但是没有从登录页面拿任何的数据，难道是提交post请求前一定要访问一下登录页？
        s.login(username, password) #提交登录的post请求 
        s.requests.headers.update({'Host': 'office.chaoxing.com'})  #更新host到预约座位系统
        suc = s.signback_()    # 签退
        logging.info(f" complete! , signback {suc}")     
        return suc
    



def get_roomid(args1, args2):
    username = input("请输入用户名：")
    password = input("请输入密码：")
    s = reserve(sleep_time=SLEEPTIME, max_attempt=MAX_ATTEMPT, enable_slider=ENABLE_SLIDER, reserve_next_day=RESERVE_NEXT_DAY)
    s.get_login_status()
    s.login(username=username, password=password)
    s.requests.headers.update({'Host': 'office.chaoxing.com'})
    encode = input("请输入deptldEnc：")
    s.roomid(encode)



if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), 'config.json') #得到完整的配置文件路径
    parser = argparse.ArgumentParser(prog='Chao Xing seat auto reserve')
    parser.add_argument('-u','--user', default=config_path, help='user config file')
    parser.add_argument('-m','--method', default="reserve" ,choices=["reserve", "debug", "room" ,"sign" ,"signback"], help='默认检测系统时间运行，debug模式立即运行，room选项中的deptIdEnc参数在预约记录的get请求中')
    parser.add_argument('-a','--action', action="store_true",help='use --action to enable in github action')
    args = parser.parse_args()  #解析命令行参数，将解析结果存储在 args 对象中
    func_dict = {"reserve": main, "debug":debug, "room": get_roomid ,"sign": sign , "signback": signback}
    with open(args.user, "r+") as data:
        usersdata = json.load(data)["reserve"]
    func_dict[args.method](usersdata, args.action)
