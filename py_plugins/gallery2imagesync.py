import json
import sys
import time

import log
from stash_interface import StashInterface

# 功能标签的名字
sync_gallery_to_image_tag_name = "🛠️将图库信息同步至图片"
converge_image_to_gallery_tag_name = "🛠️将图片信息集中到图库"
bidirectional_sync_tag_name = "🛠️将图库信息和图片信息双向同步"
disposable_sync_gallery_to_image_tag_name = "🛠️一次性将图库信息同步至图片"
disposable_converge_image_to_gallery_tag_name = "🛠️一次性将图片信息集中到图库"
disposable_bidirectional_sync_tag_name = "🛠️一次性将图库信息和图片信息双向同步"

def main():
	# 读取 JSON 格式的输入
	json_input = read_json_input()

	# 进行处理并记录运行期间的消息
	output = {}
	run(json_input, output)

	# 输出消息
	out = json.dumps(output)
	print(out + "\n")


def read_json_input():
	# 此处有点…没有道理，我猜测是这个样子的：已知 stdin 是类似 C 的输入输出流的东西，我猜测是 Stash 向这个流里先输入了一些数据，之后通知插件，插件从流里读取数据
	json_input = sys.stdin.read()
	return json.loads(json_input)


def run(json_input, output):
	# 获取操作模式，这个模式是在 gallerytags.yml 里定义的，取决于操作时点击了插件提供的哪个按钮，并不是 Stash 内部的操作识别码
	mode_arg = json_input['args']['mode']
	# log.LogInfo(f'JSON 字符串化 json_input 对象：{json.dumps(json_input)}')

	try:
		if mode_arg == "CREATE_FUNCTION_TAG":
			# 创建“需要同步”标签，这个是在标签库里创建出来，不是给某个视频或图库或其他什么资源添加标签
			client = StashInterface(json_input["server_connection"])
			add_data_to_client(client)
			create_function_tags(client)
		elif mode_arg == "SYNC_WITH_TAG":
			# 将有“需要同步”标签的图集进行同步
			client = StashInterface(json_input["server_connection"])
			add_data_to_client(client)
			sync_with_tag(client)
		elif mode_arg == "SYNC_ALL":
			# 将所有图集进行同步
			client = StashInterface(json_input["server_connection"])
			add_data_to_client(client)
			sync_all(client)
	except Exception:
		raise

	# 输出信息里加一个完成信息
	output["output"] = "ok"

def add_data_to_client(client):
	# 所有功能标签的 id
	client.datas['gallery_to_image_tag_id'] = client.findTagIdWithName(sync_gallery_to_image_tag_name)
	client.datas['image_to_gallery_tag_id'] = client.findTagIdWithName(converge_image_to_gallery_tag_name)
	client.datas['bidirectional_tag_id'] = client.findTagIdWithName(bidirectional_sync_tag_name)
	client.datas['disposable_gallery_to_image_tag_id'] = client.findTagIdWithName(disposable_sync_gallery_to_image_tag_name)
	client.datas['disposable_image_to_gallery_tag_id'] = client.findTagIdWithName(disposable_converge_image_to_gallery_tag_name)
	client.datas['disposable_bidirectional_tag_id'] = client.findTagIdWithName(disposable_bidirectional_sync_tag_name)

	# 所有功能标签的 id 列表
	client.datas['all_function_tag_id_list'] = [
		client.datas['gallery_to_image_tag_id'],
		client.datas['image_to_gallery_tag_id'],
		client.datas['bidirectional_tag_id'],
		client.datas['disposable_gallery_to_image_tag_id'],
		client.datas['disposable_image_to_gallery_tag_id'],
		client.datas['disposable_bidirectional_tag_id'],
	]

	# 所有图库到图片标签的 id 列表
	client.datas['gallery_to_image_tag_id_list'] = [
		client.datas['gallery_to_image_tag_id'],
		client.datas['disposable_gallery_to_image_tag_id'],
		client.datas['bidirectional_tag_id'],
		client.datas['disposable_bidirectional_tag_id'],
	]

	# 所有图片到图库标签的 id 列表
	client.datas['gallery_to_image_tag_id_list'] = [
		client.datas['image_to_gallery_tag_id'],
		client.datas['disposable_image_to_gallery_tag_id'],
		client.datas['bidirectional_tag_id'],
		client.datas['disposable_bidirectional_tag_id'],
	]

	# 所有一次性功能标签的 id 列表
	client.datas['disposable_tag_id_list'] = [
		client.datas['disposable_gallery_to_image_tag_id'],
		client.datas['disposable_image_to_gallery_tag_id'],
		client.datas['disposable_bidirectional_tag_id'],
	]

# 创建“需要同步”的标签
def create_function_tags(client):
	create_tag(client, sync_gallery_to_image_tag_name)
	create_tag(client, converge_image_to_gallery_tag_name)
	create_tag(client, bidirectional_sync_tag_name)
	create_tag(client, disposable_sync_gallery_to_image_tag_name)
	create_tag(client, disposable_converge_image_to_gallery_tag_name)
	create_tag(client, disposable_bidirectional_sync_tag_name)

# 创建指定名称的标签
def create_tag(client, tag_name):
	tag_id = client.findTagIdWithName(tag_name)

	if tag_id is None:
		client.createTagWithName(tag_name)
		log.LogInfo(f'Tag {tag_name} created')
	else:
		log.LogInfo(f'Tag {tag_name} already exists')

# 对带有“需要同步”标签的图库进行同步
def sync_with_tag(client):
	log.LogInfo('Start synchronization Galleries with function tags')

	# 查出有这些标签的图集
	galleries = client.findGalleriesByTags(client.datas['all_function_tag_id_list'])

	log.LogDebug(f"Found {len(galleries)} galleries with function tags")

	# 复制标签
	for gallery in galleries:
		sync_gallery_and_image(client, gallery)

	log.LogInfo(f'Copied scene information to {len(galleries)} galleries')

# 对所有图库进行同步
def sync_all(client):
	log.LogWarning("#######################################")
	log.LogWarning("即将进行对所有图库和其中图片的数据同步，这个操作可能导致极大范围的错误修改，您有30秒的时间取消这个操作")
	log.LogWarning("#######################################")

	time.sleep(30)
	log.LogInfo('Start synchronization all Galleries')

	# 查出所有图集
	galleries = client.findGalleriesByTags([])

	log.LogDebug(f"Found {len(galleries)} galleries")

	# 复制标签
	for gallery in galleries:
		sync_gallery_and_image(client, gallery)

	log.LogInfo(f'Copied scene information to {len(galleries)} galleries')

# 对指定的图集进行同步
def sync_gallery_and_image(client, gallery):
	# 获取图库id便于后续操作
	galleryId = [int(gallery.get('id'))]

	# 一个筛选规则，这个规则是根据 Stash 的 stash\graphql\documents\queries\image.graphql 里的格式写的
	# 在 stash\graphql\documents\data\image.graphql 中写了图片的结构，图片里有一个参数是 galleries，是图集id列表，传多个图集id就是一次查询多个图集
	image_filter = {
		"galleries": {
			"value": galleryId,
			"modifier": "INCLUDES"
		}
	}

	# 查找图片列表
	images = client.findImages(image_filter)

	log.LogDebug(f'Gallery with ID {galleryId} has {len(images)} images')

	if(len(images) == 0):
		log.LogInfo(f'There are no images in the Gallery with ID {galleryId}')
	elif(len(images) == 1):
		log.LogDebug(f'Gallery with ID {galleryId} has ONE image, Use ONE-TO-ONE synchronization')
		sync_one_to_one(client, gallery, images[0])
	else:
		log.LogDebug(f'Gallery with ID {galleryId} has More Than One images, Use ONE-TO-MANY synchronization')
		sync_ont_to_many(client, gallery, images)

# 对仅有一张图片的图库和其中图片进行一对一的数据合并
def sync_one_to_one(client, gallery, image):
	# 把图集和图片的信息全都找出来，要查的完整
	# 把 title(标题)、date(日期)、url(链接)、rating100(分数)、organized(是否已整理)、studio(工作室) 按照“有的同步给没有的，都有则不同步”的原则进行同步
	# 把 tags(标签)、performers(角色) 合并后给双方存入

	# log.LogInfo(f'JSON 字符串化 gallery 对象：{json.dumps(gallery)}')
	# log.LogInfo(f'JSON 字符串化 image 对象：{json.dumps(image)}')

	# 用三目的方式把可以用 None 区分的属性先取出来，空串和 None 在 if 里都被视为 false
	title = (gallery.get('title')) if gallery.get('title') else image.get('title')
	date = (gallery.get('date')) if gallery.get('date') else image.get('date')
	url = (gallery.get('url')) if gallery.get('url') else image.get('url')
	rating100 = (gallery.get('rating100')) if gallery.get('rating100') else image.get('rating100')
	studio = (gallery.get('studio')) if gallery.get('studio') else image.get('studio')

	# 是否已整理是 bool 型，如果任何一个是已整理那就都算作已整理
	organized = gallery.get('organized') or image.get('organized')

	# 标签，不需要进行排序，Stash 会自己排序
	tags = gallery.get('tags')
	tags += image.get('tags') # python 的拼接列表简单又舒坦，就是一个加法，跟两个数字相加一样简单
	tag_ids = [t.get('id') for t in tags]
	tag_ids = list(dict.fromkeys(tag_ids))
	# 【移除一次性的功能标签】
	tag_ids = [i for i in tag_ids if i not in client.datas['disposable_tag_id_list']]

	# 演员
	performers = gallery.get('performers')
	performers += image.get('performers') # python 的拼接列表简单又舒坦，就是一个加法，跟两个数字相加一样简单
	performer_ids = [t.get('id') for t in performers]
	performer_ids = list(dict.fromkeys(performer_ids))
	
	# 准备图集的新数据，是差量更新的所以只有有的会保存和更新。对于这个特性也只有画廊里没有的属性会更新，标签和演员是合并的所以直接更新
	gallery_data = {
		# 这几个属性必存在不用判空
		'id': gallery.get('id'),
		'organized': organized,
		'tag_ids': tag_ids,
		'performer_ids': performer_ids,
	}
	if (not gallery.get('title')) and (title):
		gallery_data['title'] = title
	if (not gallery.get('date')) and (date):
		gallery_data['date'] = date
	if (not gallery.get('url')) and (url):
		gallery_data['url'] = url
	if (not gallery.get('rating100')) and (rating100):
		gallery_data['rating100'] = rating100
	if (not gallery.get('studio')) and (studio):
		gallery_data['studio_id'] = studio.get('id')

	log.LogDebug(f'更新图集参数：{json.dumps(gallery_data)}')

	# 更新图集数据
	client.updateGallery(gallery_data)

	# 图片数据也进行一遍更新
	image_data = {
		# 这几个属性必存在不用判空
		'id': image.get('id'),
		'organized': organized,
		'tag_ids': tag_ids,
		'performer_ids': performer_ids,
	}
	if (not image.get('title')) and (title):
		image_data['title'] = title
	if (not image.get('date')) and (date):
		image_data['date'] = date
	if (not image.get('url')) and (url):
		image_data['url'] = url
	if (not image.get('rating100')) and (rating100):
		image_data['rating100'] = rating100
	if (not image.get('studio')) and (studio):
		image_data['studio_id'] = studio.get('id')

	log.LogDebug(f'更新图片参数：{json.dumps(image_data)}')

	# 更新图片数据
	client.updateImage(image_data)

# 对拥有多张图片的图库和其中的图片进行双向的数据同步
def sync_ont_to_many(client, gallery, images):
	# 查出图库的标签 id 列表
	gallery_tag_id_list = [t.get('id') for t in gallery.get('tags')]

	# 根据图库的标签来判断需要进行的操作
	needSyncToImage = not set(gallery_tag_id_list).isdisjoint(client.datas['gallery_to_image_tag_id_list'])
	needConvergeToGallery = not set(gallery_tag_id_list).isdisjoint(client.datas['gallery_to_image_tag_id_list'])

	# 图库的属性，用不到的数据注释掉节约运算量
	# gallery_title = gallery.get('title')
	gallery_date = gallery.get('date')
	gallery_url = gallery.get('url')
	# gallery_rating100 = gallery.get('rating100')
	gallery_studio = gallery.get('studio')
	# gallery_organized = gallery.get('organized')
	gallery_tag_ids = [t.get('id') for t in gallery.get('tags')]
	gallery_performer_ids = [t.get('id') for t in gallery.get('performers')]

	# 根据数据的差异生成出修改请求的参数对象，修改请求通过参数对象发出而不是通过获取数据时得到的对象发出
	gallery_update_data = {
		'id': gallery.get('id'),
		'tag_ids': gallery_tag_ids.copy(), # 复制一份防止原始数据被修改
		'performer_ids': gallery_performer_ids.copy(),
	}
	image_update_data_list = []
	for image in images:
		# 获取比较麻烦的图片属性先获取出来便于后续重复使用
		image_tag_ids = [t.get('id') for t in image.get('tags')]
		image_performer_ids = [t.get('id') for t in image.get('performers')]

		# 同步图库的数据给图片
		if needSyncToImage:
			# 准备一个参数对象
			image_update_data = {
				'id': image.get('id'),
			}

			# 标题不做处理，单页的标题可能是 PXXX_XXXXXX，跟图库标题完全不一样
			# 评分不同步，图库整体的评分和单图是有很大差距的
			# 是否已整理不同步，图库已整理不能代表每个图片都已经详细整理过了

			# 日期、链接、工作室，如果图片没有则同步给图片
			if (gallery_date) and (not image.get('date')):
				image_update_data['date'] = gallery_date
			if (gallery_url) and (not image.get('url')):
				image_update_data['url'] = gallery_url
			if (gallery_studio) and (not image.get('studio')):
				image_update_data['studio_id'] = gallery_studio

			# 标签、演员，合并给图片。这里使用图库的原始数据，防止图库在数据集中过程中得到了其他图片的数据之后错误地进行了跨图片的数据同步
			image_update_data['tag_ids'] = [i for i in list(dict.fromkeys(image_tag_ids + gallery_tag_ids)) if i not in client.datas['all_function_tag_id_list']] # 标签要过滤掉功能标签
			image_update_data['performer_ids'] = list(dict.fromkeys(image_performer_ids + gallery_performer_ids))

			# 参数对象保存到列表里
			image_update_data_list.append(image_update_data)

		# 集中图片的数据给图库
		if needConvergeToGallery:
			# 标题不做处理，单页的标题可能是 PXXX_XXXXXX，跟图库标题完全不一样
			# 评分不同步，图库整体的评分和单图是有很大差距的
			# 是否已整理不同步，单个图片是否整理完成不能代表整个图库是否整理完成
			# 日期不同步，可能图库里的各个图片是不同时间依次更新的
			# 链接不同步，如果图片不是同时更新同时发布的话链接也就会不一样，不能给出统一的链接
			# 工作室不同步，图库里可能有多人合作但 Stash 不支持多工作室

			# 标签、演员，合并给图集
			gallery_update_data['tag_ids'] = list(dict.fromkeys(gallery_update_data['tag_ids'] + image_tag_ids))
			gallery_update_data['performer_ids'] = list(dict.fromkeys(gallery_update_data['performer_ids'] + image_performer_ids))


	# 保存图片数据
	if needSyncToImage:
		for image_update_data in image_update_data_list:
			client.updateImage(image_update_data)

	# 【移除一次性的功能标签】
	gallery_update_data['tag_ids'] = [i for i in gallery_update_data['tag_ids'] if i not in client.datas['disposable_tag_id_list']]
	# 保存画廊数据
	if needConvergeToGallery:
		client.updateGallery(gallery_update_data)

main()
