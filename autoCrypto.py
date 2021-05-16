from os import supports_effective_ids
from pandas._libs.tslibs import Timestamp
import time
import pyupbit
import datetime
import requests

access = ''
secret = ''
myToken = ''#업비트용 봇의 주소


global log_file
log_file = open("C:autoTradeLog.txt", 'a')
is_logfile_closed = False

def file_write(msg):
    log_file.write(msg)

def post_message(token, channel, text):
    """슬랙 메시지 전송"""
    crp = '#crypto99'
    file_write(text)
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": crp,"text": text}
    
)

#이동 평균선 조회
def get_ma15(ticker):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=15)
    ma15 = df['close'].rolling(15).mean().iloc[-1]
    return ma15

def get_ma_21(ticker, count_N = 21):
    """N일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count_N = 21)
    ma_N = df['close'].rolling(count_N).mean().iloc[-1]
    return ma_N    

def get_target_price(ticker, k):#(코인이름,k값)
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    
    #목표가 = 장 마감 가격(=다음날 시가) + (고 - 저) * k
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]#인덱스의 첫번째 값이 시간 값임.
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
        
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

def get_basic_name(coin_name):
    "잔고 조회시 필요한 'KRW'제거된 코인이름 리턴"
    temp = coin_name.strip().split('-')
    return temp[1]

def info_combine(result, coin_price, price):
    """매수/매도 시 평균가, 금액 리턴"""
    key_list = ['created_at', 'market', 'price', 'remaining_fee', 'remaining_volume', 'locked']
    pstr =''
    for k in key_list:
        pstr += k +': '+str(result[k])+'\n'

    pstr += '[매수/매도 평균가]' +': '+str(coin_price)+'\n'
    pstr += '[매수/매도 금액]' +': '+str(price)+'\n'
    return pstr


def profit_calculator(now, coin_name, buy_coin_price, buy_price):
    coin_basic_name = get_basic_name(coin_name)
    
    curr_price = get_current_price(coin_name)
    coin_balance = get_balance(coin_basic_name)
    estimated_value = coin_balance*curr_price
    estimated_profit = estimated_value-buy_price

    if bought_not_yet == True:
        percent_profit = 0.0
    else:
        percent_profit = estimated_profit/buy_price

    print_str = ''
    print_str += '[날짜] ' + str(now) + '\n'
    print_str += '[코인명] ' + str(coin_name) + '\n'
    print_str += '[보유량] ' + str(coin_balance) + '\n'
    print_str += '[현재가] ' + str(curr_price) + '\n'
    print_str += '[매수평균가] ' + str(buy_coin_price) + '\n'
    print_str += '[매수금액] ' + str(buy_price) + '\n'
    print_str += '[평가금액] ' + str(estimated_value) + '\n'
    print_str += '[평가손익] ' + str(estimated_profit) + '\n'
    print_str += '[수익률] ' + str(percent_profit) + '\n'

    return print_str
        
def profit_calculator_slack(now, coin_name,buy_coin_price, buy_price):
    """1시간마다 수익률, 평가손익 SLACK!"""
    coin_info = profit_calculator(now, coin_name,buy_coin_price, buy_price)
    post_message(myToken,"#crypto", coin_info)


def days_of_profit_calculator(start_time, coin_name, buy_coin_price, sell_coin_price, buy_price, sell_price, balance):
    
    if bought_not_yet == True:
        percent_prof = 0
    else:
        percent_prof = (sell_price-buy_price)/buy_price

    print_str = ''
    print_str += '[날짜] ' + str(start_time) + '\n'
    print_str += '[코인명] ' + str(coin_name) + '\n'
    print_str += '[매수평균가] ' + str(buy_coin_price) + '\n'
    print_str += '[매도평균가] ' + str(sell_coin_price) + '\n'
    print_str += '[매수금액] ' + str(buy_price) + '\n'
    print_str += '[매도금액] ' + str(sell_price) + '\n'
    print_str += '[수익률] ' + str(percent_prof) + '\n'
    print_str += '[평가손익] ' + str(sell_price-buy_price) + '\n'
    print_str += '[잔고] ' + str(balance) + '\n'

    return print_str
    #print_str += '[] ' + str() + '\n'

def sum_balances():
    balances = upbit.get_balances()
    sumof_krw = 0

    kr = 1
    for b in balances:
        if b['currency'] in coin_name_list:
            amount = b['balance']
            cp = get_current_price("KRW-" + b['currency'])
            kr = float(amount) * float(cp)

        sumof_krw += kr
        
    return sumof_krw

def count_False(bought_not_yet):
    cnt = 0
    for v in bought_not_yet:
        if v == False:
            cnt+=1
    return cnt

def remove_timestamp_minutes(now):
    st = str(now)
    sp = st.split(':')
    removed_min = sp[0] +':00:00'
    ts = Timestamp(removed_min)
    return ts


def init_trade_info(i):
    buy_result[i] = 0
    buy_coin_price[i] = 0
    buy_price[i] = 0

    #매도 정보
    sell_result[i] = 0
    sell_coin_price[i] = 0
    sell_price[i] = 0

    bought_not_yet[i] = True
    sold_not_yet[i] = True


"""투자 기본 세팅하기"""
upbit = pyupbit.Upbit(access, secret)
post_message(myToken,"#crypto99", "[UpBit Logged In]")
print("[UpBit Logged In]")
# 투자 할 코인 선택
coin_list = [['KRW-ADA', 1.365, 0.15], ['KRW-BCH', 1.5, 0.25],['KRW-NEO', 1.279, 0.1], ['KRW-STEEM', 1.551, 0.1],['KRW-XRP', 1.124, 0.1]]
coin_name_list = ['ADA','BCH','NEO','STEEM','XRP']
INDEX = 0#ADA:0 BCH:1 NEO:2 STEEM:3 XRP:4


#매수 정보

#시뮬레이션용
buy_r = {'uuid': '56d41e8c-64cd-4f27-b9ab-cca66c0f9baa', 'side': 'bid', 'ord_type': 'price', 'price': '39980.0', 'state': 'wait', 'market': 'KRW-XRP', 'created_at': '2021-05-13T13:23:01+09:00', 'volume': None, 'remaining_volume': None, 'reserved_fee': '19.99', 'remaining_fee': '19.99', 'paid_fee': '0.0', 'locked': '39999.99', 'executed_volume': '0.0', 'trades_count': 0}
#sell_r = {'uuid': 'fe833e1f-96d9-4f48-962d-0726ae0e82f2', 'side': 'ask', 'ord_type': 'market', 'price': None, 'state': 'wait', 'market': 'KRW-ADA', 'created_at': '2021-05-13T13:12:00+09:00', 'volume': '19.22413651', 'remaining_volume': '19.22413651','reserved_fee': '0.0', 'remaining_fee': '0.0', 'paid_fee': '0.0', 'locked': '19.22413651', 'executed_volume': '0.0', 'trades_count': 0}


buy_result = [0,0,0,0,0]
buy_coin_price = [0, 0, 0, 0, 0]
buy_price = [0, 0, 0, 0, 0]

#매도 정보
sell_result = [0, 0, 0, 0, 0]
sell_coin_price = [0, 0, 0, 0, 0]
sell_price = [0, 0, 0, 0, 0]

#코인별 예수금 정보
latest_sell_price = [40000.0, 40000.0, 40000.0, 40000.0, 40000.0]#코인별 수익에 따른 예수금변화를 반영하기 위함->총 액 20만원 , 시작시 각 코인당 4만원 씩 부여


bought_not_yet = [True,True,True,True,True]
sold_not_yet = [True,True,True,True,True]
alarm_not_yet = [True,True,True,True,True]

tmpnow = datetime.datetime.now()
tmpnow_hour = remove_timestamp_minutes(tmpnow)
every_hour = tmpnow_hour+datetime.timedelta(hours=1)#10:00
every_hour_cnt = 0

sumof_evaluated_coinbalace = sum_balances()
krw_cash = upbit.get_balance("KRW")

print('[예수금]:%d\n' % krw_cash)
post_message(myToken,"#crypto", "[=====AUTO TRADE START=====]\n"+  '[예수금]:%d\n' % krw_cash )

print('[평가손익 총합]:%d\n' % sumof_evaluated_coinbalace)
post_message(myToken,"#crypto",'[평가손익 총합]:%d\n' % sumof_evaluated_coinbalace)

for x in range(0, len(coin_list)):
    coin_name = coin_list[x][0]
    k_value = coin_list[x][2]
    current_p = get_current_price(coin_name)
    target_p = get_target_price(coin_name, k_value)
    
    strprint = "[코인명]:"+ coin_name +'\n'+"[ k ]:" + str(k_value) + '\n' + "[현재가]:" + str(current_p) + '\n' + "[목표가]:" + str(target_p) +'\n' + "[잔고 KRW]:"+ str(latest_sell_price[x]) + '\n'
    print(strprint)
    post_message(myToken,"#crypto", "[autotrade start]\n"+ strprint )



"""ADA 부터 시작!"""
coin_name = coin_list[INDEX][0]
k_value = coin_list[INDEX][2]

# 자동매매 시작
while True:
    try:
        if is_logfile_closed == True:
            log_file = open("C:autoTradeLog.txt", 'a')
            is_logfile_closed = False

        for i in range(0,len(coin_list)):
            coin_name = coin_list[i][0]
            k_value = coin_list[i][2]
            
            now = datetime.datetime.now()#현재시간
            start_time = get_start_time(coin_name)#시작시간 09:00
            end_time = start_time + datetime.timedelta(days=1)#끝나는 시간 시작시간 + 1일
            #tmp_time = start_time + datetime.timedelta(hours=4) => 테스트용
        
            #09:00 < now < 08:57:00
            if start_time < now < end_time - datetime.timedelta(minutes=3):
                if bought_not_yet[i] == True:#아직 안산 코인들만 확인한다.
                    target_price = get_target_price(coin_name, k_value)
                    current_price = get_current_price(coin_name)
                    ma15 = get_ma15(coin_name)
            
            
                    #목표가 < 현재가 -> 변동성 돌파했으면 -> 코인을 매수한다.
                    if target_price < current_price and current_price <= target_price*1.03 and ma15 < current_price:#and  ma_N < current_price
                        krwcash_for_this_coin = latest_sell_price[i]

                        #5000원 이상만 거래가 됨.
                        if krwcash_for_this_coin > 5003 and bought_not_yet[i]:# krw*(1/len(coin_list)) 전부 매수하고 나면 예수금 전체에서 1/5(코인 종목 수)씩만 투자함.
                            buy_result[i] = upbit.buy_market_order(coin_name, krwcash_for_this_coin*0.9995)#buy_r
                   
                            buy_coin_price[i] = get_current_price(coin_name)#매수 시 코인가격 저장
                            buy_price[i] = float(buy_result[i]['price'])#매수총액 저장

                            post_message(myToken,"#crypto", coin_name + "buy : " + info_combine(buy_result[i], buy_coin_price[i], buy_price[i]))
                            print("<<<<삼>>>>\n" + info_combine(buy_result[i], buy_coin_price[i], buy_price[i]))

                            bought_not_yet[i] = False
                
                else:#이미 변동성 돌파해서 매수 한 코인은 손익률만 2시간마다 출력해줌.
                
                    #1시간마다 손익률, 평가손익 SLACK
                    if every_hour < now and every_hour < end_time - datetime.timedelta(minutes=3):
                        if every_hour_cnt < count_False(bought_not_yet):
                            
                            if alarm_not_yet[i] == True:
                                profit_calculator_slack(now, coin_name, buy_coin_price[i], buy_price[i])
                                alarm_not_yet[i] = False
                                every_hour_cnt += 1
                                
                        else:
                            every_hour = every_hour + datetime.timedelta(hours=2)
                            every_hour_cnt = 0
                            alarm_not_yet = [True,True,True,True]
                    
            #08:59:30 ~ 08:57:00
            else:
                if bought_not_yet[i] == False and sold_not_yet[i] == True:#샀는데 아직 안팔았다면
                    current_price = get_current_price(coin_name)
                    coin_basic_name = get_basic_name(coin_name)
                    coin_balance = get_balance(coin_basic_name)
        
                    up_5000 = float(5003/current_price)
                
                    if coin_balance > up_5000:
                        sell_result[i] = upbit.sell_market_order(coin_name, coin_balance*0.9995)#sell_r

                        sell_coin_price[i] = float((get_current_price(coin_name)))
                        tmp_float = float(sell_result[i]['locked'])
                        sell_price[i] =  tmp_float * float(sell_coin_price[i])# 1(BCH) = N (KRW) => 1 * 0.00xx (BCH) = N * 0.00xx (KRW)
                        now_balance = sell_price[i] #코인종목 당 투자한 금액(1/5)에 해당하는 만큼의 KRW를 반환.


                        post_message(myToken,"#crypto", coin_name + "buy : " + info_combine(sell_result[i], sell_coin_price[i], sell_price[i]))
                        print("<<<<팔림>>>>\n:" + info_combine(sell_result[i], sell_coin_price[i], sell_price[i]))

                        resultOf_day = days_of_profit_calculator(start_time, coin_name, buy_coin_price[i], sell_coin_price[i], buy_price[i], sell_price[i], now_balance)
                        print(resultOf_day)
                        post_message(myToken,"#crypto", resultOf_day)

                        latest_sell_price[i] = sell_price[i]
                        init_trade_info(i)

                log_file.close()
                is_logfile_closed = True
                        
            time.sleep(1)
    except Exception as e:
        print(e)
        log_file.write(str(e))
        time.sleep(1)