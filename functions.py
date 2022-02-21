import asyncio
import json
import os

from bs4 import BeautifulSoup
import dotenv
import requests

dotenv.load_dotenv()

conf_filename = os.getenv('CONFIG_FILE')
default_conf = {
	"prefix":"!",
	"allowed_channel_ids_for_commands": [],
	"news_command_usage_powelevel": 0,
	"refusal_message": "You don\'t have the permission to do that. cope",
	"auto_send_news": "false",
	"auto_send_news_channels": [],
	"seconds_between_check_news": 600,
	"add_feature_links": "false",
	"add_kf_homepage_link": "true"
}

def write_JSON(data, json_file):
	json_file.seek(0)
	json.dump(data, json_file, indent=4)
	json_file.truncate()

def generate_conf(conf_filename):
	if not os.path.isfile(conf_filename):
		with open(conf_filename, 'w') as outfile:
			write_JSON(default_conf, outfile)
	with open(conf_filename, 'r+') as json_file:
		data = json.load(json_file)
		for key in default_conf:
			if not key in data:
				data[key] = default_conf[key]
		write_JSON(data, json_file)

def read_conf(conf_filename):
	class Config(object):
		pass
	conf = Config()
	with open(conf_filename, 'r') as json_file:
		data = json.load(json_file)
		for key in data:
			setattr(conf, key, data[key])
	return conf


generate_conf(conf_filename)
config = read_conf(conf_filename)

async def has_news_command_perms(user_id, room, client):
	powerlevels = room.power_levels
	powerlevel = powerlevels.get_user_level(user_id)
	if powerlevel < int(config.news_command_usage_powelevel):
		await send(room.room_id, config.rcon_refusal_message, client)
		return False
	return True

async def is_mod(user_id, room, client):
	powerlevels = room.power_levels
	powerlevel = powerlevels.get_user_level(user_id)
	if powerlevel < int(os.getenv('MATRIX_MOD_POWERLEVEL')):
		await send(room.room_id, 'You don\'t have the permission to do that. cope', client)
		return False
	return True

async def is_admin(user_id, room, client):
	powerlevels = room.power_levels
	powerlevel = powerlevels.get_user_level(user_id)
	if powerlevel < int(os.getenv('MATRIX_ADMIN_POWERLEVEL')):
		await send(room.room_id, 'You don\'t have the permission to do that. cope', client)
		return False
	return True

async def send(room_id, message, client, html=False, formatted_message=None):
	if not html:
		await client.room_send(room_id, message_type='m.room.message', content={'msgtype': 'm.text', 'body': message})
	elif formatted_message:
		await client.room_send(room_id, message_type='m.room.message', content={'msgtype': 'm.text', 'format': 'org.matrix.custom.html', 'formatted_body': formatted_message, 'body': message})

def get_news(get_list=False):
	url = 'https://kiwifarms.net/'
	news = None
	try:
		r = requests.get(url, allow_redirects=True, headers={'User-Agent': 'KF news bot', 'From': 'Sneed'})
		html = r.text
		soup = BeautifulSoup(html, features="html.parser")

		pbody_pagecontent = soup.find_all("div", {"class": "p-body-pageContent"})[0]
		featured_block = pbody_pagecontent.find_all("div", {"class": "block-body"})[0]
		featured_block_rows = featured_block.find_all("div", {"class": "block-row"})
		n = []
		n_html = []
		n_ = []
		links = []

		for row in featured_block_rows:
			link_ = str(row.find_all('a', href=True)[0])
			links.append('https://kiwifarms.net' + link_[9:link_.find('">')])

		for row in featured_block_rows:
			n_.append(row.find_all("div", {"class": "contentRow-main contentRow-main--close"})[0].text)
		
		for i in range(len(featured_block_rows)):
			nl = '\n'
			n.append(f"• {n_[i].replace(nl, '')}")
			if config.add_feature_links == 'true':
				n_html.append(f"• {n_[i].replace(nl, '')} [<a href='{links[i]}'>link</a>]")
			else:
				n_html.append(f"• {n_[i].replace(nl, '')}")
		
		if get_list:
			news = [n_, links]
		else:
			news = ['\n'.join(n), '<br>'.join(n_html)]
			if config.add_kf_homepage_link == 'true':
				news[1] += "<br>[<a href='https://kiwifarms.net/'>kiwifarms</a>]"
	except Exception as e:
		#print(e)
		raise e
	return news


def cache_news(news, urls):
	with open('news_cache.json', 'w+') as nc:
		write_JSON({"news": news, "urls": urls}, nc)

def read_news_cache():
	if not os.path.isfile('news_cache.json'):
		return None
	with open('news_cache.json', 'r') as nc:
		return json.load(nc)

async def handle_news(client):
	print('sneed')
	if config.auto_send_news == 'false' or len(config.auto_send_news_channels) == 0:
		return
	#while True:
	news = get_news(True)
	news_cache = read_news_cache()

	if not news_cache or not 'urls' in news_cache:
		cache_news(news[0], news[1])
		return

	new_news = []
	new_news_html = []
	for i in range(len(news[0])):
		n = news[0][i]
		link = news[1][i]
		if not link in news_cache['urls']:
			nl = '\n'
			new_news.append(f"• + {n.replace(nl, '')}")
			if config.add_feature_links == 'true':
				new_news_html.append(f"• {n.replace(nl, '')} [<a href='{link}'>link</a>]")
			else:
				new_news_html.append(f"• {n.replace(nl, '')}")
	if len(new_news) == 0:
		return
		#continue
	res = 'New featured post on Kiwifarms!\n'
	res_html = '<b>New featured post on Kiwifarms!</b><br>'
	if len(new_news) > 1:
		res = 'New featured posts on Kiwifarms!\n'
		res_html = '<b>New featured posts on Kiwifarms!</b><br>'
	res += '\n'.join(new_news)
	res_html += '<br>'.join(new_news_html)
	if config.add_kf_homepage_link == 'true':
		res_html += "<br>[<a href='https://kiwifarms.net/'>kiwifarms</a>]"
	for room_id in config.auto_send_news_channels:
		await send(room_id, res, client, True, res_html)
	cache_news(news[0], news[1])
		#await asyncio.sleep(config.seconds_between_check_news)