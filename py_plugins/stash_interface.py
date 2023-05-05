# 对 Stash 进行底层操作的接口脚本
# Stash 使用的是 GraphQL，在 Stash 库的 stash/graphql/documents 文件夹里有具体的数据结构

import requests
import sys
import log
from urllib.parse import urlparse


class StashInterface:
    datas = {}

    port = ""
    url = ""
    headers = {
        "Accept-Encoding": "gzip, deflate, br",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Connection": "keep-alive",
        "DNT": "1"
    }
    cookies = {}

    def __init__(self, conn):
        self.port = conn['Port']
        scheme = conn['Scheme']

        # Session cookie for authentication
        self.cookies = {
            'session': conn.get('SessionCookie').get('Value')
        }

        try:
            # If stash does not accept connections from all interfaces use the host specified in the config
            host = conn.get('Host') if '0.0.0.0' not in conn.get('Host') or '' else 'localhost'
        except TypeError:
            # Pre stable 0.8
            host = 'localhost'

        # Stash GraphQL endpoint
        self.url = scheme + "://" + host + ":" + str(self.port) + "/graphql"
        log.LogDebug(f"Using stash GraphQl endpoint at {self.url}")

    # 调用 Stash 的 GraphQL 接口，通过网络请求调用
    def __callGraphQL(self, query, variables=None):
        json = {'query': query}
        if variables is not None:
            json['variables'] = variables

        response = requests.post(self.url, json=json, headers=self.headers, cookies=self.cookies)

        if response.status_code == 200:
            result = response.json()
            if result.get("error", None):
                for error in result["error"]["errors"]:
                    raise Exception("GraphQL error: {}".format(error))
            if result.get("data", None):
                return result.get("data")
        elif response.status_code == 401:
            sys.exit("HTTP Error 401, Unauthorised. Cookie authentication most likely failed")
        else:
            raise ConnectionError(
                "GraphQL query failed:{} - {}. Query: {}. Variables: {}".format(
                    response.status_code, response.content, query, variables)
            )


    # 查询指定名称的标签
    def findTagIdWithName(self, name):
        query = """
            query($name: String!) {
                findTags(
                    tag_filter: {
                        name: {value: $name, modifier: EQUALS}
                    }
                ){
                    tags{
                        id
                        name
                    }
                }
            }
        """

        variables = {
            'name': name,
        }

        result = self.__callGraphQL(query, variables)
        if result.get('findTags') is not None and result.get('findTags').get('tags') != []:
            return result.get('findTags').get('tags')[0].get('id')
        return None

    # 创建指定名称的标签
    def createTagWithName(self, name):
        query = """
            mutation tagCreate($input:TagCreateInput!) {
                tagCreate(input: $input){
                    id
                }
            }
        """
        variables = {'input': {
            'name': name
        }}

        result = self.__callGraphQL(query, variables)
        if result.get('tagCreate'):
            log.LogDebug(f"Created tag: {name}")
            return result.get('tagCreate').get("id")
        else:
            log.LogError(f"Could not create tag: {name}")
            return None

    # 更新图集信息
    def updateGallery(self, gallery_data):
        query = """
            mutation GalleryUpdate($input: GalleryUpdateInput!) {
                galleryUpdate(input: $input) {
                    id
                }
            }
        """

        variables = {'input': gallery_data}

        self.__callGraphQL(query, variables)

    # 更新图片信息
    def updateImage(self, image_data):
        query = """
            mutation($input: ImageUpdateInput!) {
                imageUpdate(input: $input) {
                    id
                }
            }
        """

        variables = {'input': image_data}

        self.__callGraphQL(query, variables)

    # 查询带有指定标签的图集，标签是以列表形式传入的
    def findGalleriesByTags(self, tag_ids):
        query = """
        query($tags: [ID!]) {
            findGalleries(
            gallery_filter: { tags: { modifier: INCLUDES, value: $tags } }
            filter: { per_page: -1 }
            ) {
            count
            galleries {
                id
                title
                date
                url
                details
                rating100
                organized
                image_count
                studio {
                    id
                }
                tags {
                    id
                }
                performers {
                    id
                }
                scenes {
                    id
                }
            }
          }
        }
        """

        variables = {
            "tags": tag_ids
        }

        result = self.__callGraphQL(query, variables)
        galleries = result.get('findGalleries').get('galleries')
        return galleries

    # 查找图集
    def findGalleries(self, gallery_filter=None):
        return self.__findGalleries(gallery_filter)

    # 查找图集
    def __findGalleries(self, gallery_filter=None, page=1):
        per_page = 100
        query = """
            query($studio_ids: [ID!], $page: Int, $per_page: Int) {
                findGalleries(
                    gallery_filter: { studios: { modifier: INCLUDES, value: $studio_ids } }
                    filter: { per_page: $per_page, page: $page }
                ) {
                    count
                    galleries {
                        id
                        title
                        date
                        url
                        details
                        rating100
                        organized
                        image_count
                        studio {
                            id
                        }
                        tags {
                            id
                        }
                        performers {
                            id
                        }
                        scenes {
                            id
                        }
                    }
                }
            }
        """

        variables = {
            "page": page,
            "per_page": per_page
        }
        if gallery_filter:
            variables['gallery_filter'] = gallery_filter

        result = self.__callGraphQL(query, variables)

        galleries = result.get('findGalleries').get('galleries')

        # If page is full, also scan next page(s) recursively:
        if len(galleries) == per_page:
            next_page = self.__findGalleries(gallery_filter, page + 1)
            for gallery in next_page:
                galleries.append(gallery)

        return galleries

    # 查询图片
    def findImages(self, image_filter=None):
        return self.__findImages(image_filter)

    # 查询图片
    def __findImages(self, image_filter=None, page=1):
        per_page = 1000
        query = """
        query($per_page: Int, $page: Int, $image_filter: ImageFilterType) {
            findImages(image_filter: $image_filter ,filter: { per_page: $per_page, page: $page }) {
                count
                images {
                    id
                    title
                    date
                    url
                    rating100
                    organized
                    o_counter
                    galleries {
                        id
                    }
                    studio {
                        id
                    }
                    tags {
                        id
                    }
                    performers {
                        id
                    }
                }
            }
        }
        """

        variables = {
            'per_page': per_page,
            'page': page
        }
        if image_filter:
            variables['image_filter'] = image_filter

        result = self.__callGraphQL(query, variables)

        images = result.get('findImages').get('images')

        if len(images) == per_page:
            next_page = self.__findImages(image_filter, page + 1)
            for image in next_page:
                images.append(image)

        return images

    # 更新图片的工作室信息
    def updateImageStudio(self, image_ids, studio_id):
        query = """
        mutation($ids: [ID!], $studio_id: ID) {
            bulkImageUpdate(input: { ids: $ids, studio_id: $studio_id }) {
                id
            }
        }
        """

        variables = {
            "ids": image_ids,
            "studio_id": studio_id
        }

        self.__callGraphQL(query, variables)
