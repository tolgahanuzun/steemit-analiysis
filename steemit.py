import requests
from datetime import datetime
VESTING_URL = 'http://www.steemdollar.com/vests.php'

def parse_url(url):
    _url = url.split('@')[1].split('/')
    return _url[0], _url[1]

def get_url(url):
    link = "https://steemit.com/@{}.json".format(url)
    response = requests.get(link)

    if response.json()['status'] == '200':
        return True , response.json()

    return False, None

def blog_list(author):
    url = 'https://api.steemjs.com/get_discussions_by_blog?query={'  + '"tag":"{}","limit": "50"'.format(author) + "}"
    data = requests.get(url).json()

    result = {
        'blog':[],
        'tittle':[],
        'category':[],
        'votes':[],
        'price':[]
    }

    for blog in data:
        if (datetime.now() - datetime.strptime(blog['created'], '%Y-%m-%dT%H:%M:%S')).days < 8 and author == blog['author']:
            result['blog'].append(blog['url'])
            result['tittle'].append(blog['title'])
            result['category'].append(blog['category'])
            result['votes'].append(blog['net_votes'])
            result['price'].append(float(blog['pending_payout_value'].split(' ')[0]))

    return result

def convert(result):
    new_result = {}
    new_result['blog'] = db_con(result['blog'])
    new_result['tittle'] = db_con(result['tittle'])
    new_result['category'] = db_con(result['category'])
    new_result['votes'] = db_con(result['votes'])
    new_result['price'] = db_con(result['price'])

    return new_result

def db_con(old_d):
    text = ''
    for res in old_d:
        text = text + ':::' +  str(res) 
    return text

def deconvert(result):
    return result.split(':::')[1:]


def category(blog_list):
    url = 'https://api.steemjs.com/get_state?path=@{}'.format(author)
    data = requests.get(url).json()
    blog_list = data['content']
    

def ff_count(author):
    link = 'https://steemdb.com/api/accounts?account={}'.format(author)

    data = requests.get(link).json()[0]
    return data['followers_count'], data['following_count']

def vesting_calculator(response):
    vests_func = float(requests.get(VESTING_URL).text.split('1 VESTS =')[1].split('\t')[0].replace(' ',''))
    
    vesting = float(response['vesting_shares'].split(' ')[0]) 
    vesting = vesting + float(response['received_vesting_shares'].split(' ')[0])
    vesting = vesting - float(response['delegated_vesting_shares'].split(' ')[0])
    
    return vesting / 1e6 *  vests_func

def vote_count(author):
    url = 'https://api.steemjs.com/get_account_votes?voter={}'.format(author)
    return len(requests.get(url).json())