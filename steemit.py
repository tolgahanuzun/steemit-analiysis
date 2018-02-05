import requests

def parse_url(url):
    _url = url.split('@')[1].split('/')
    return _url[0], _url[1]

def test_url(url):
    status = False
    valid = 'https://steemit'
    if not valid == url.split('.com')[0]:
        return status

    link = "{}.json".format(url)
    if requests.get(link).status_code == 200:
        status = True
    return status

def post_comment(url):
    author, permlink = parse_url(url)
    api_link = 'https://api.steemjs.com/get_content_replies?author={}&permlink={}'.format(
        author, permlink)

    comments = requests.get(api_link).json()
    comment_list = [comment['author'] for comment in comments]

    return comment_list

def post_vote(url):
    link = "{}.json".format(url)
    post = requests.get(link).json()['post']
    upvote = post['active_votes']
    vote_list = [vote['voter'] for vote in upvote]

    return vote_list

def post_follow(url):
    author, permlink = parse_url(url)

    link = 'https://steemdb.com/api/accounts?account={}'.format(author)

    data = requests.get(link).json()[0]
    return data['followers']
