import re

TGWTG_PREFIX      = '/video/thatguywiththeglasses'
TGWTG_URL         = 'http://thatguywiththeglasses.com'
IMAGE_BASEURL     = 'http://a.images.blip.tv/'
BLIP_API          = 'http://www.blip.tv/player/episode/%s?skin=json&version=2&callback='
BLIP_SEARCH_API   = 'http://www.blip.tv/search/view/?search=%s&skin=json&version=2&callback='
BLIP_CATEGORY_API = 'http://www.blip.tv/%s?skin=json&version=2&callback='

CACHE_FRONTPAGE   = CACHE_1HOUR
CACHE_SHOWPAGE    = CACHE_1WEEK

ART               = 'art-default.jpg'
ICON              = 'icon-default.png'
SEARCH            = 'icon-search.png'

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(TGWTG_PREFIX, ShowSelector, L('tgwtg'), ICON, ART)
  Plugin.AddViewGroup('List', viewMode='List', mediaType='items')
  Plugin.AddViewGroup('InfoList', viewMode='InfoList', mediaType='items')
  MediaContainer.art = R(ART)
  MediaContainer.viewGroup = 'List'
  MediaContainer.title1 = L('tgwtg')
  DirectoryItem.thumb = R(ICON)
  VideoItem.thumb = R(ICON)
  
  HTTP.CacheTime = 3600

def ShowSelector(sender=None, parentID='', title1=L('tgwtg'), title2=''):
  dir = MediaContainer()

  page = HTML.ElementFromURL(TGWTG_URL, cacheTime=CACHE_FRONTPAGE)

  if(parentID == ''):
    parent = page.xpath("//ul[@class='menutop']")[0]
    children = parent.xpath("./li")
  else:
    parent = page.xpath("//li[contains(@class, '"+parentID+"')]")[0]
    children = parent.xpath("./div/ul/li")

  for child in children:
    url = TGWTG_URL + child.xpath("./a")[0].get('href')
    title = child.xpath("./a/span")[0].text
    # Update : Some child can be skipped (no videos) for the root element. Not very clean, feel free to correct with a better way
    if(title == 'Articles' or title == 'Home' or title == 'Site Stuff' or title == 'Store' or title == 'Community' or title == 'Blogs'):
      continue
    liClass = child.get('class')
    # If the child's class contains 'parent' then it has it's own children
    if liClass.count('parent') > 0:
      # Is a parent, extract the item
      #Update: $ removed, the class is at the start now
      childID = re.search(r'(item\d+)', liClass).group(1)
      dir.Append(Function(DirectoryItem(ShowSelector, title=title, thumb=R(ICON)), parentID=childID, title1=title2, title2=title))
    else:
      # Is not a parent, is a show, so pass to ShowBrowser
      childId = liClass
      dir.Append(Function(DirectoryItem(ShowBrowser, title=title, thumb=R(ICON)), showUrl=url, order=title, title1=title2))

#   if sender == None:
#     for cat in ['popular', 'recent', 'random', 'featured']:
#       dir.Append(Function(DirectoryItem(ShowCategoryNSearch,str(cat).capitalize(), str(cat).capitalize(), str(cat).capitalize(), thumb=R(ICON)), category = cat))
#     dir.Append(Function(InputDirectoryItem(ShowCategoryNSearch,"Search...", "Search...", "Search...", thumb=R(SEARCH))))

  return dir

def ShowBrowser(sender, showUrl, order, title1, page = 1):
  PAGELEN = 20
  dir = MediaContainer(title1 = title1, title2 = L(order), replaceParent = (page!=1), viewGroup = 'InfoList')

  episodes = HTML.ElementFromURL(showUrl).xpath("//tr[starts-with(@class,'sectiontableentry')]");
  if page > 1 :
    dir.Append(Function(DirectoryItem(ShowBrowser,"Previous Page"), showUrl=showUrl, order=order, title1=title1, page = page - 1))  
  if (page*PAGELEN-1>len(episodes)):
    maxIndex = len(episodes)
  else:
    maxIndex = page*PAGELEN-1
  
  for episode in  episodes[(page-1)*PAGELEN:maxIndex]:
    url = TGWTG_URL + episode.xpath("./td[position()=2]/a")[0].get('href')
    try:
      blipid = HTML.ElementFromURL(url, cacheTime=CACHE_SHOWPAGE).xpath("//embed")[0].get('src')
      blipid = (blipid[blipid.rfind('/')+1:]).replace('%2B','+').replace('%2D','-')
    except:
      blipid = None

    #Log(blipid)
    if blipid!=None:
      if len(blipid)>11:
        blipid = blipid[:blipid.rfind('+')]

      jsonresponse = HTTP.Request(BLIP_API%blipid).content.replace('([{','[{').replace(']);',']').replace("\\'","'")

      for episodeInfo in JSON.ObjectFromString(jsonresponse):
        if "error" in episodeInfo:
          continue
#          Log("Error")
        else:
          url = episodeInfo['mediaUrl']
          title = episodeInfo['title']
          subtitle = episodeInfo['description']
          summary = episodeInfo['description']
          try:
            thumb = episodeInfo['thumbnailUrl']
          except:
            thumb = None
          duration = int(episodeInfo['media']['duration'])*1000

          dir.Append(VideoItem(url, title=title, subtitle=subtitle, thumb=Function(GetThumb, url=thumb), summary=summary, duration = duration))
  if maxIndex != len(episodes):
    dir.Append(Function(DirectoryItem(ShowBrowser,"Next Page"), showUrl=showUrl, order=order, title1=title1, page = page + 1))  
  if len(dir) == 0:
    return MessageContainer("Error","This section does not contain any video")
  else:
    return dir

def ShowCategoryNSearch(sender, query = None,category = None):

  dir = MediaContainer(viewGroup = 'InfoList')

  if query == None:
    jsonresponse = HTTP.Request(BLIP_CATEGORY_API%category).content.replace('([{','[{').replace(']);',']').replace("\\'","'")
  else:
    jsonresponse = HTTP.Request(BLIP_SEARCH_API%query).content.replace('([{','[{').replace(']);',']').replace("\\'","'")
  for episodeInfo in JSON.ObjectFromString(jsonresponse):
    if "error" in episodeInfo:
      continue
#      Log("Error")
    else:
      url = episodeInfo['mediaUrl']
      title = episodeInfo['title']
      subtitle = episodeInfo['description']
      summary = episodeInfo['description']
      try:
        thumb = episodeInfo['thumbnailUrl']
      except:
        thumb = None
      duration = int(episodeInfo['media']['duration'])*1000

      dir.Append(VideoItem(url, title=title, subtitle=subtitle, thumb=Function(GetThumb, url=thumb), summary=summary, duration=duration))
  return dir

def GetThumb(url):
  if url:
    try:
      return DataObject(HTTP.Request(url, cacheTime=CACHE_1WEEK).content, 'image/jpeg')
    except:
      pass

  return Redirect(R(ICON))
