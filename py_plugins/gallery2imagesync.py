import json
import sys
import time

import log
from stash_interface import StashInterface

# 功能标签的名字
sync_gallery_to_image_tag_name = "🛠️将图库信息同步至图片"
converge_image_to_gallery_tag_name = "🛠️将图片信息集中到图库"
disposable_sync_gallery_to_image_tag_name = "🛠️一次性将图库信息同步至图片"
disposable_converge_image_to_gallery_tag_name = "🛠️一次性将图片信息集中到图库"

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
			create_function_tags(client)
		elif mode_arg == "SYNC_WITH_TAG":
			# 将有“需要同步”标签的图集进行同步
			client = StashInterface(json_input["server_connection"])
			sync_with_tag(client)
		elif mode_arg == "SYNC_ALL":
			# 将所有图集进行同步
			client = StashInterface(json_input["server_connection"])
			sync_all(client)
	except Exception:
		raise

	# 输出信息里加一个完成信息
	output["output"] = "ok"


# 把图集关联的第一个视频的标签复制给图集
# Helper function
def __copy_tags(client, galleries):
	# TODO: Multithreading
	count = 0

	# 遍历所有图集
	for gallery in galleries:
		# 对于有关联场景的进行处理
		if (gallery.get('scenes') is not None) and (len(gallery.get('scenes')) > 0):
			# 关联场景多于一个，发出提示表示只复制第一个场景的
			if len(gallery.get('scenes')) > 1:
				log.LogInfo(f'Gallery {gallery.get("id")} has multiple scenes, only copying tags from first scene')

			# 找到第一个场景
			# Select first scene from gallery scenes
			scene_id = gallery.get('scenes')[0].get('id')
			scene = client.getSceneById(scene_id)

			log.LogInfo(f'JSON 字符串化 scene 对象：{json.dumps(scene)}')

			# 准备图集的新数据
			gallery_data = {
				'id': gallery.get('id'),
				'title': scene.get('title')
			}

			# 对于各种数据的复制，场景有的数据放进参数，差量更新没传的数据不会被覆盖清空
			if scene.get('details'):
				gallery_data['details'] = scene.get('details')
			if scene.get('url'):
				gallery_data['url'] = scene.get('url')
			if scene.get('date'):
				gallery_data['date'] = scene.get('date')
			if scene.get('rating'):
				gallery_data['rating'] = scene.get('rating')
			if scene.get('studio'):
				gallery_data['studio_id'] = scene.get('studio').get('id')
			if scene.get('tags'):
				# 这是一个转换，类似 Linq.Select，把场景对象里的标签对象列表转为标签ID列表，就是取出标签对象里的ID取出来组成列表
				tag_ids = [t.get('id') for t in scene.get('tags')]
				# 存入到了新数据里
				gallery_data['tag_ids'] = tag_ids
			if scene.get('performers'):
				performer_ids = [p.get('id') for p in scene.get('performers')]
				gallery_data['performer_ids'] = performer_ids

			# 更新图集数据
			client.updateGallery(gallery_data)

			log.LogDebug(f'Copied information to gallery {gallery.get("id")}')
			count += 1

	return count

# 找到“需要同步标签”标签的图集，将这些图集关联的第一个场景的标签复制到图集上，没有关联的场景则不处理
def copy_tags(client):
	# 通过名字查找“需要同步标签”标签的 ID
	tag = client.findTagIdWithName(sync_gallery_to_image_tag_name)

	# 没有这个标签，结束运行
	if tag is None:
		sys.exit(f"Tag {sync_gallery_to_image_tag_name} does not exist. Please create it via the 'Create CopyTags tag' task")

	# 查出有这个标签的图集
	tag_ids = [tag]
	galleries = client.findGalleriesByTags(tag_ids)

	log.LogDebug(f"Found {len(galleries)} galleries with {sync_gallery_to_image_tag_name} tag")

	log.LogInfo(f'JSON 字符串化 galleries 列表：{json.dumps(galleries)}')

	# 复制标签
	count = __copy_tags(client, galleries)

	log.LogInfo(f'Copied scene information to {count} galleries')

# 对所有有关联场景的图集，将这些图集关联的第一个场景的标签复制到图集上
def copy_all_tags(client):
	log.LogWarning("#######################################")
	log.LogWarning("Warning! This task will copy all information to all galleries with attached scenes")
	log.LogWarning("You have 1 seconds to cancel this task before it starts copying")
	log.LogWarning("#######################################")

	time.sleep(1)
	log.LogInfo("Start copying information. This may take a while depending on the amount of galleries")

	# 把所有的图集都找出来
	# Get all galleries
	galleries = client.findGalleriesByTags([])
	log.LogDebug(f"Found {len(galleries)} galleries")

	log.LogInfo(f'JSON 字符串化 galleries 列表：{json.dumps(galleries)}')

	# 复制标签
	count = __copy_tags(client, galleries)

	log.LogInfo(f'Copied scene information to {count} galleries')

# 将图库的工作室信息复制到其中的每个单图上
def image_studio_copy(client):
	# 获取图库列表
	galleries = client.findGalleries()

	# 工作室 id 到图库列表的映射表
	# List of gallery ids for each studio
	# {'studio_id': [gallery_ids]}
	studio_mapping = {}

	# 遍历所有的图库
	# Get studio from each gallery and add it to the mapping
	for gallery in galleries:
		# 获取工作室信息
		studio = gallery.get('studio')
		# 有工作室则继续操作
		if studio is not None:
			# 如果映射表里有这个工作室的列表，追加；否则新建一个列表并存入
			if studio_mapping.get(studio.get('id')):
				studio_mapping[studio.get('id')].append(int(gallery.get('id')))
			else:
				studio_mapping[studio.get('id')] = [int(gallery.get('id'))]

	log.LogDebug(f'Found {len(studio_mapping)} studios with galleries')

	# 遍历整个映射表
	# Bulk update all images in galleries for each studio
	for studio, galleries in studio_mapping.items():
		# 获取工作室 id
		studio_id = int(studio)
		log.LogDebug(f'There are {len(galleries)} galleries with studio id {studio_id}')

		# TODO: 没看懂，从名字分辨是一个过滤器或过滤规则；根据后续代码似乎是一个类似 SQL where 的过滤规则，
		# Get images with gallery ids
		image_filter = {
			"galleries": {
				"value": galleries,
				"modifier": "INCLUDES"
			}
		}

		# 查找图片列表
		images = client.findImages(image_filter)
		log.LogDebug(f'There is a total of {len(images)} images with studio id {studio_id}')

		# 筛选出其中工作室不是当前遍历到的工作室的图片
		# Only update images with no studio or different studio
		to_update = [int(image.get('id')) for image in images if (image.get('studio') is None or int(image.get('studio').get('id')) != studio_id)]
		log.LogInfo(f'Adding studio {studio_id} to {len(to_update)} images')

		# Bulk update images with studio_id
		client.updateImageStudio(image_ids=to_update, studio_id=studio_id)










# 创建“需要同步”的标签
def create_function_tags(client):
	create_tag(client, sync_gallery_to_image_tag_name)
	create_tag(client, converge_image_to_gallery_tag_name)
	create_tag(client, disposable_sync_gallery_to_image_tag_name)
	create_tag(client, disposable_converge_image_to_gallery_tag_name)

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

	# 功能标签 id 列表
	tag_ids = []

	# 遍历所有功能标签的名字
	for tag_name in [sync_gallery_to_image_tag_name, converge_image_to_gallery_tag_name, disposable_sync_gallery_to_image_tag_name, disposable_converge_image_to_gallery_tag_name]:
		# 通过名字查询 id
		tag_id = client.findTagIdWithName(tag_name)
		# 查到了 id 则加入到列表里
		if tag_id is not None:
			tag_ids.append(tag_id)

	# 如果所有功能标签都没找到则直接结束操作
	if(len(tag_ids) == 0):
		sys.exit(f'All function tags not exist')

	# 查出有这些标签的图集
	galleries = client.findGalleriesByTags(tag_ids)

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

	# FIXME: 这里需要补一个移除一次性标签的功能

# 对仅有一张图片的图库和其中图片进行一对一的数据合并
def sync_one_to_one(client, gallery, image):
	# 把图集和图片的信息全都找出来，要查的完整
	# 把 title(标题)、date(日期)、url(链接)、rating100(分数)、organized(是否已整理)、studio(工作室) 按照“有的同步给没有的，都有则不同步”的原则进行同步
	# 把 tags(标签)、performers(角色) 合并后给双方存入

	log.LogInfo(f'JSON 字符串化 gallery 对象：{json.dumps(gallery)}')
	log.LogInfo(f'JSON 字符串化 image 对象：{json.dumps(image)}')

	# 用三目的方式把可以用 None 区分的属性先取出来，对于字符串型需要判断空串，空串和 None 在 if 里都被视为 false
	title = (gallery.get('title')) if gallery.get('title') else image.get('title')
	date = (gallery.get('date') is not None) if gallery.get('date') else image.get('date')
	url = (gallery.get('url')) if gallery.get('url') else image.get('url')
	rating100 = (gallery.get('rating100') is not None) if gallery.get('rating100') else image.get('rating100')
	studio = (gallery.get('studio') is not None) if gallery.get('studio') else image.get('studio')

	# 是否已整理是 bool 型，如果任何一个是已整理那就都算作已整理
	organized = gallery.get('organized') or image.get('organized')

	# 标签，不需要进行排序，Stash 会自己排序
	tags = gallery.get('tags')
	tags += image.get('tags') # python 的拼接列表简单又舒坦，就是一个加法，跟两个数字相加一样简单
	tag_ids = [t.get('id') for t in tags]
	tag_ids = list(dict.fromkeys(tag_ids))

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
	if (not gallery.get('title')) and (title is not None):
		gallery_data['title'] = title
	if (gallery.get('date') is None) and (date is not None):
		gallery_data['date'] = date
	if (not gallery.get('url')) and (url is not None):
		gallery_data['url'] = url
	if (gallery.get('rating100') is None) and (rating100 is not None):
		gallery_data['rating100'] = rating100
	if (gallery.get('studio') is None) and (studio is not None):
		gallery_data['studio_id'] = studio.get('id')

	log.LogInfo(f'更新图集参数：{json.dumps(gallery_data)}')

	# 更新图集数据
	client.updateGallery(gallery_data)

# 对拥有多张图片的图库和其中的图片进行双向的数据同步
def sync_ont_to_many(client, gallery, images):
	# FIXME: 多图图库功能还没解决
	# 查出四种标签的 id
	gallery_to_image_tag_id = client.findTagIdWithName(sync_gallery_to_image_tag_name)
	image_to_gallery_tag_id = client.findTagIdWithName(converge_image_to_gallery_tag_name)
	disposable_gallery_to_image_tag_id = client.findTagIdWithName(disposable_sync_gallery_to_image_tag_name)
	disposable_image_to_gallery_tag_id = client.findTagIdWithName(disposable_converge_image_to_gallery_tag_name)

	# 查出图库的标签 id 列表
	gallery_tag_id_list = [t.get('id') for t in gallery.get('tags')]

	# 有图库同步到图片标签则进行图库数据同步到图片的处理
	if gallery_to_image_tag_id in gallery_tag_id_list or disposable_gallery_to_image_tag_id in gallery_tag_id_list:
		# TODO: 图库数据同步到图片的处理
		pass

	# 有图片数据集中到图库的标签则进行图片数据集中到图库的处理
	if image_to_gallery_tag_id in gallery_tag_id_list or disposable_image_to_gallery_tag_id in gallery_tag_id_list:
		# TODO: 图片数据集中到图库的处理
		pass

	# TODO: 保存数据
	pass
	# 把图集和图片的信息全都找出来，要查的完整
	# 首先把图集的所有信息都传入到图片上，遵循“有的同步给没有的”，包括：data(日期)、url(链接)、rating100(分数)、organized(是否已整理)、studio(工作室)、tags(标签)、performers(角色)
	# 之后把图片的信息集中后传给图集，这里只会同步能存在多个的内容，即：tags(标签)、performers(角色)

main()
