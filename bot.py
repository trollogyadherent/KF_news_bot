import asyncio
import os

import dotenv
from nio import AsyncClient, MatrixRoom, RoomMessageText

import functions as fn


dotenv.load_dotenv()

conf_filename = os.getenv('CONFIG_FILE')

fn.generate_conf(conf_filename)
config = fn.read_conf(conf_filename)

loop = asyncio.get_event_loop()

client = AsyncClient(os.getenv('MATRIX_HOST'), os.getenv('MATRIX_USERNAME'))

async def main(client) -> None:
	#client = AsyncClient(os.getenv('MATRIX_HOST'), os.getenv('MATRIX_USERNAME'))
	print(await client.login(os.getenv('MATRIX_PASSWORD')))
	await client.sync()

	async def message_callback(room, event) -> None:
		if room.room_id not in config.allowed_channel_ids_for_commands:
			return
		if event.body.startswith(config.prefix + 'help'):
			await fn.send(room.room_id, 'List of available commands: news, source', client)
		if event.body.startswith(config.prefix + 'news') and await fn.has_news_command_perms(event.sender, room, client):
			news = fn.get_news()
			if not news:
				await fn.send(room.room_id, 'Could not fetch featured articles. Are the farms down?', client)
			print('got news')
			if news and len(news) > 0 and len(news[0]) > 0:
				print('not empty')
				await fn.send(room.room_id, news[0], client, True, news[1])
				#await client.room_send(room.room_id, message_type='m.room.message', content={'msgtype': 'm.text', 'format': 'org.matrix.custom.html', 'formatted_body':news[1], 'body': news[0]})
		if event.body.startswith(config.prefix + 'source'):
			await fn.send(room.room_id, 'https://github.com/trollogyadherent/KF_news_bot', client)

	client.add_event_callback(message_callback, RoomMessageText)
	await client.sync_forever(timeout=30000)

async def periodic():
	while True:
		try:
			await fn.handle_news(client)
		except Exception as e:
			print(e)
		await asyncio.sleep(60)
loop.run_until_complete(asyncio.gather(periodic(), main(client)))

#loop.create_task(fn.handle_news(client))
#loop.create_task(main(client))
#loop.run_forever()